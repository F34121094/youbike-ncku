"""
collect.py — 從交通部 TDX 抓取台南市 YouBike 站點與即時可借車數（跑一次就抓一次）

輸入：
    .env（或環境變數）裡的 TDX_CLIENT_ID、TDX_CLIENT_SECRET
輸出：
    data/stations.csv           station_id, station_name, lat, lon, capacity（每次覆蓋，存最新站點資訊）
    data/raw/youbike_raw.csv    fetch_time, station_id, available_bikes, available_spaces（每次 append）
    logs/collect.log            執行紀錄與錯誤訊息

執行方式（在專案根目錄）：
    python collect/collect.py

注意：
    - 這支程式「不會」自己無限重複執行。要每 5 分鐘抓一次，請交給外部排程
      （Windows 工作排程器、Linux/Mac cron，或 .github/workflows/collect.yml）。
    - 發生錯誤時會寫進 logs/collect.log，程式不會整個當掉。
    - 標了 TODO 的地方是「欄位名稱 / 數值需要對照真實 API 回傳再確認」的地方。
"""

import csv
import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 路徑設定（不管從哪個資料夾執行，都以專案根目錄為準）
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
STATIONS_CSV = ROOT / "data" / "stations.csv"
RAW_CSV = ROOT / "data" / "raw" / "youbike_raw.csv"
LOG_FILE = ROOT / "logs" / "collect.log"

# 欄位名稱是全組約定，不可更動
STATION_COLUMNS = ["station_id", "station_name", "lat", "lon", "capacity"]
RAW_COLUMNS = ["fetch_time", "station_id", "available_bikes", "available_spaces"]

# ---------------------------------------------------------------------------
# 參數設定
# ---------------------------------------------------------------------------
# TODO(確認): 成大中心點座標，之後請用 Google Maps 校正（目前約為成大光復校區）
NCKU_LAT = 22.997
NCKU_LON = 120.219
RADIUS_KM = 1.5

# 台灣時間（UTC+8，沒有夏令時間）。GitHub Actions 主機是 UTC，所以要明確指定。
TAIPEI_TZ = timezone(timedelta(hours=8))

TDX_TOKEN_URL = (
    "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
)
# TODO(確認): 城市代碼 Tainan、API 版本 v2 是否正確，請對照 TDX 官網 API 文件
TDX_STATION_URL = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/Tainan"
TDX_AVAILABILITY_URL = (
    "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/Tainan"
)
REQUEST_TIMEOUT = 30  # 秒


# ---------------------------------------------------------------------------
# 紀錄（log）設定：同時印在螢幕上、也寫進 logs/collect.log
# ---------------------------------------------------------------------------
def setup_logger() -> logging.Logger:
    # Windows 終端機有時不是 UTF-8，遇到印不出來的字就用 ? 取代，避免因為「印字」而出錯
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("collect")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


log = setup_logger()


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """用 haversine 公式計算地球上兩點的直線距離（公里）。"""
    r = 6371.0  # 地球半徑（公里）
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def print_sample(name: str, records: list) -> None:
    """印出 API 回傳的第一筆資料，讓組員檢查欄位名稱。"""
    if not records:
        log.warning("%s API 回傳是空的", name)
        return
    print(f"\n===== {name} API 第一筆回傳（請檢查欄位名稱）=====")
    print(json.dumps(records[0], ensure_ascii=False, indent=2))
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# TDX API
# ---------------------------------------------------------------------------
def get_token(client_id: str, client_secret: str) -> str:
    """用 client_credentials 流程向 TDX 換 access token。"""
    resp = requests.post(
        TDX_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def call_api(url: str, token: str) -> list:
    """呼叫 TDX API，回傳 list（每個元素是一個站的 dict）。"""
    resp = requests.get(
        url,
        headers={"authorization": f"Bearer {token}"},
        params={"$format": "JSON"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# 站點資訊
# ---------------------------------------------------------------------------
def parse_stations(records: list) -> list[dict]:
    """把 Station API 的回傳整理成約定欄位，並只留下成大周圍 RADIUS_KM 公里內的站。"""
    rows = []
    for rec in records:
        try:
            # TODO(確認): 用 StationUID 當 station_id（Availability API 也有 StationUID，
            #             兩邊才對得起來）。若想改用 StationID，兩邊都要一起改。
            station_id = rec["StationUID"]
            # TODO(確認): 站名欄位是否為 StationName.Zh_tw（注意大小寫 tw / Tw）
            name_obj = rec.get("StationName", {})
            station_name = name_obj.get("Zh_tw") or name_obj.get("Zh_Tw") or ""
            # TODO(確認): 座標欄位是否為 StationPosition.PositionLat / PositionLon
            lat = float(rec["StationPosition"]["PositionLat"])
            lon = float(rec["StationPosition"]["PositionLon"])
            # TODO(確認): 總車位數欄位是否為 BikesCapacity
            capacity = int(rec.get("BikesCapacity", 0))
        except (KeyError, TypeError, ValueError) as e:
            log.warning("站點資料欄位解析失敗，跳過這筆：%r（%s）", rec, e)
            continue

        if haversine_km(NCKU_LAT, NCKU_LON, lat, lon) <= RADIUS_KM:
            rows.append(
                {
                    "station_id": station_id,
                    "station_name": station_name,
                    "lat": lat,
                    "lon": lon,
                    "capacity": capacity,
                }
            )
    return rows


def save_stations(rows: list[dict]) -> None:
    """站點資訊每次整份覆蓋（存最新的狀態）。"""
    STATIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(STATIONS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STATION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_station_ids_from_csv() -> set[str]:
    """Station API 失敗時的備案：讀上次存下來的 stations.csv。"""
    if not STATIONS_CSV.exists():
        return set()
    with open(STATIONS_CSV, newline="", encoding="utf-8") as f:
        return {row["station_id"] for row in csv.DictReader(f)}


# ---------------------------------------------------------------------------
# 即時可借車數
# ---------------------------------------------------------------------------
def parse_availability(records: list, station_ids: set[str], fetch_time: str) -> list[dict]:
    rows = []
    for rec in records:
        try:
            station_id = rec["StationUID"]  # TODO(確認): 要和 parse_stations 用同一個 ID 欄位
            if station_id not in station_ids:
                continue
            # TODO(確認): 可借車數 = AvailableRentBikes、可還空位 = AvailableReturnBikes
            #             （台南可能同時有 YouBike 1.0 / 2.0，有些 API 會再細分車種，請檢查）
            rows.append(
                {
                    "fetch_time": fetch_time,
                    "station_id": station_id,
                    "available_bikes": int(rec["AvailableRentBikes"]),
                    "available_spaces": int(rec["AvailableReturnBikes"]),
                }
            )
        except (KeyError, TypeError, ValueError) as e:
            log.warning("可借車數欄位解析失敗，跳過這筆：%r（%s）", rec, e)
    return rows


def append_raw(rows: list[dict]) -> None:
    """append 到 youbike_raw.csv；檔案不存在（或是空的）時先寫標題列。"""
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    need_header = not RAW_CSV.exists() or RAW_CSV.stat().st_size == 0
    with open(RAW_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS, lineterminator="\n")
        if need_header:
            writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------
def main() -> None:
    load_dotenv(ROOT / ".env")
    client_id = os.getenv("TDX_CLIENT_ID")
    client_secret = os.getenv("TDX_CLIENT_SECRET")
    if not client_id or not client_secret:
        log.error("找不到 TDX_CLIENT_ID / TDX_CLIENT_SECRET，請確認 .env 已建立並填好金鑰")
        return

    # fetch_time 一律用台灣時間，格式 YYYY-MM-DD HH:MM:SS
    fetch_time = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # 1. 換 token
    try:
        token = get_token(client_id, client_secret)
    except Exception as e:
        log.error("取得 TDX token 失敗：%s", e)
        return

    # 2. 站點資訊（失敗的話就沿用上次的 stations.csv，不中斷）
    station_ids: set[str] = set()
    try:
        station_records = call_api(TDX_STATION_URL, token)
        print_sample("Station", station_records)
        stations = parse_stations(station_records)
        if stations:
            save_stations(stations)
            station_ids = {s["station_id"] for s in stations}
            log.info("站點資訊：成大周圍 %.1f km 內共 %d 站", RADIUS_KM, len(stations))
        else:
            log.warning("成大周圍找不到任何站點，請檢查座標、半徑或欄位名稱")
    except Exception as e:
        log.error("抓取站點資訊失敗：%s", e)

    if not station_ids:
        station_ids = load_station_ids_from_csv()
        if station_ids:
            log.info("改用既有的 stations.csv（%d 站）", len(station_ids))
        else:
            log.error("沒有可用的站點清單，這次不寫入可借車數")
            return

    # 3. 即時可借車數
    try:
        avail_records = call_api(TDX_AVAILABILITY_URL, token)
        print_sample("Availability", avail_records)
        rows = parse_availability(avail_records, station_ids, fetch_time)
        append_raw(rows)
        log.info("可借車數：寫入 %d 筆（fetch_time=%s）", len(rows), fetch_time)
    except Exception as e:
        log.error("抓取可借車數失敗：%s", e)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 最後一道防線：任何沒預料到的錯誤都只記錄，不讓程式崩潰
        log.exception("未預期的錯誤：%s", e)
