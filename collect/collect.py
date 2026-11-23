"""
collect.py — 從交通部 TDX 抓取台南市 YouBike 即時可借車數（跑一次就抓一次）

輸入：
    .env（或環境變數）裡的 TDX_CLIENT_ID、TDX_CLIENT_SECRET
    （GitHub Actions 沒有 .env，會直接從環境變數讀；兩種方式程式都支援）
輸出：
    data/stations.csv           station_id, station_name, lat, lon, capacity
                                （只在檔案不存在 / 沒有資料時才呼叫 Station API 產生，省 TDX 點數）
    data/raw/youbike_raw.csv    fetch_time, station_id, available_bikes, available_spaces（每次 append）
    logs/collect.log            執行紀錄、錯誤訊息、每次 API 回傳的大小（bytes，用來估算點數）

執行方式（在專案根目錄）：
    python collect/collect.py                     # 一般執行：抓一次可借車數
    python collect/collect.py --refresh-stations  # 強制重抓站點清單（會多用一次 Station API）

TDX 點數（我們的帳號只有 3 點）：
    點數 = 呼叫次數 ÷ 1500 + 傳輸量 MB ÷ 150
    - Station API（整個台南的站，資料量較大）只在 stations.csv 不存在時呼叫一次。
    - 之後每次只呼叫 1 次 Availability API，並用 $filter 只查成大附近的站、$select 只取需要的欄位。
    - 每次 API 回傳的 bytes 都會記在 logs/collect.log，用 tools/check_data.py 可以估算累計點數。

注意：
    - 這支程式「不會」自己無限重複執行。要每 15 分鐘抓一次，請交給外部排程
      （Windows 工作排程器、Mac/Linux cron，或 .github/workflows/collect.yml）。
    - 網路失敗會重試 3 次；仍失敗就把錯誤寫進 logs/collect.log 並正常結束，不會寫入半份資料。
    - API 路徑與欄位名稱依 TDX 官方 Swagger（公共自行車 Basic v2）：
      https://tdx.transportdata.tw/api-service/swagger/basic/2cc9b888-a592-496f-99de-9ab35b7fb70d
"""

import argparse
import csv
import io
import json
import logging
import math
import os
import sys
import time
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
# 成大中心點（光復 / 成功校區交界附近）。2026-11-23 用真實站點校正：成大 3 km 內站名含「成大 / 成功大學」
# 的 6 站中心約 (22.9980, 120.2190)，和這個值只差約 110 公尺，所以維持不變。
NCKU_LAT = 22.997
NCKU_LON = 120.219
RADIUS_KM = 1.5

# 人工確認用的地標（座標為約略值），只用來在畫面上標示「篩選結果有沒有包含這些地方附近的站」
LANDMARKS = {
    "台南火車站": (22.9971, 120.2127),
    "大東夜市": (22.9853, 120.2245),
    "花園夜市": (23.0110, 120.2004),
    "武聖夜市": (22.9997, 120.1878),
}
LANDMARK_NEAR_KM = 0.3  # 離地標 300 公尺內算「附近」

# 台灣時間（UTC+8，沒有夏令時間）。GitHub Actions 主機是 UTC，所以要明確指定。
TAIPEI_TZ = timezone(timedelta(hours=8))

TDX_TOKEN_URL = (
    "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
)
TDX_STATION_URL = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/Tainan"
TDX_AVAILABILITY_URL = (
    "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/Tainan"
)
# $select：只取需要的欄位，減少傳輸量（= 省點數）
STATION_SELECT = "StationUID,StationName,StationPosition,BikesCapacity,ServiceType"
AVAILABILITY_SELECT = "StationUID,AvailableRentBikes,AvailableReturnBikes,UpdateTime"
# $filter 會把每個站寫進網址，網址太長時才拆成多次呼叫（正常情況只需要 1 次）
MAX_FILTER_CHARS = 6000

REQUEST_TIMEOUT = 30  # 秒
MAX_RETRIES = 3  # 失敗後最多重試幾次
RETRY_WAIT = 5  # 每次重試前等幾秒


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
    # log 裡的時間一律用台灣時間（GitHub Actions 主機是 UTC）
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    fmt.converter = lambda t: datetime.fromtimestamp(t, TAIPEI_TZ).timetuple()
    # newline="\n"：Windows 上也只寫 LF，和 GitHub Actions 寫的 log 一致，避免 git 出現假差異
    file_handler = logging.StreamHandler(open(LOG_FILE, "a", encoding="utf-8", newline="\n"))
    file_handler.setFormatter(fmt)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


log = setup_logger()


class CollectError(Exception):
    """這次執行無法完成（已經重試過），主程式會記錄錯誤後正常結束。"""


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
# 網路請求（含重試）
# ---------------------------------------------------------------------------
def request_with_retry(method: str, url: str, name: str, count_points: bool, **kwargs):
    """
    發送 HTTP 請求，失敗時最多重試 MAX_RETRIES 次。
    - 連線失敗、逾時、伺服器錯誤（5xx）、太頻繁（429）→ 等 RETRY_WAIT 秒後重試
    - 其他錯誤（例如 401 金鑰錯誤、400 參數錯誤）重試也沒用 → 直接放棄
    - count_points=True 時，每次收到回應都在 log 記一行 "API name=... bytes=..."，
      tools/check_data.py 會用這些行估算 TDX 點數。
    """
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 2):  # 第 1 次 + 重試 3 次
        try:
            resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        except requests.RequestException as e:
            last_error = f"{type(e).__name__}: {e}"
        else:
            if count_points:
                log.info(
                    "API name=%s status=%d bytes=%d attempt=%d",
                    name, resp.status_code, len(resp.content), attempt,
                )
            if resp.ok:
                return resp
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            if resp.status_code != 429 and resp.status_code < 500:
                raise CollectError(f"{name} 請求失敗（不重試）：{last_error}")

        if attempt <= MAX_RETRIES:
            log.warning("%s 第 %d 次失敗，%d 秒後重試：%s", name, attempt, RETRY_WAIT, last_error)
            time.sleep(RETRY_WAIT)
    raise CollectError(f"{name} 重試 {MAX_RETRIES} 次仍失敗：{last_error}")


def get_token(client_id: str, client_secret: str) -> str:
    """用 client_credentials 流程向 TDX 換 access token（換 token 不算 API 點數）。"""
    resp = request_with_retry(
        "POST",
        TDX_TOKEN_URL,
        "Token",
        count_points=False,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    try:
        return resp.json()["access_token"]
    except (ValueError, KeyError) as e:
        raise CollectError(f"token 回傳格式不對：{e}") from e


def call_api(url: str, name: str, token: str, params: dict) -> list:
    """呼叫 TDX API，回傳 list（每個元素是一個站的 dict）。"""
    resp = request_with_retry(
        "GET",
        url,
        name,
        count_points=True,
        headers={"authorization": f"Bearer {token}", "Accept-Encoding": "gzip"},
        params={**params, "$format": "JSON"},
    )
    try:
        data = resp.json()
    except ValueError as e:
        raise CollectError(f"{name} 回傳不是 JSON：{resp.text[:200]}") from e
    if not isinstance(data, list):
        raise CollectError(f"{name} 回傳格式不是 list：{str(data)[:200]}")
    return data


# ---------------------------------------------------------------------------
# 站點資訊（只在 stations.csv 不存在時呼叫 Station API）
# ---------------------------------------------------------------------------
def parse_station(rec: dict) -> dict | None:
    """把 Station API 的一筆資料整理成約定欄位；欄位不齊就回傳 None。"""
    try:
        name_obj = rec.get("StationName") or {}
        pos = rec["StationPosition"]
        return {
            "station_id": rec["StationUID"],  # 用 StationUID（Availability API 也有，兩邊對得起來）
            "station_name": name_obj.get("Zh_tw") or name_obj.get("Zh_Tw") or "",
            "lat": float(pos["PositionLat"]),
            "lon": float(pos["PositionLon"]),
            "capacity": int(rec.get("BikesCapacity") or 0),
        }
    except (KeyError, TypeError, ValueError) as e:
        log.warning("站點資料欄位解析失敗，跳過這筆：%r（%s）", rec, e)
        return None


def report_stations(all_stations: list[dict], near: list[dict]) -> None:
    """印出篩選結果，讓組員人工確認範圍是否合理。"""
    print(f"\n===== 篩選結果：台南共 {len(all_stations)} 站，成大 ({NCKU_LAT}, {NCKU_LON}) "
          f"{RADIUS_KM} km 內有 {len(near)} 站 =====")
    for i, s in enumerate(near, 1):
        print(f"{i:3d}. {s['station_name']}  ({s['dist_km']:.2f} km, 車位 {s['capacity']})")

    # 校正參考：站名含「成大 / 成功大學」的站的中心點
    # （只看 3 km 內，排除歸仁校區、台達大樓等遠處的同名站）
    ncku = [s for s in all_stations
            if ("成大" in s["station_name"] or "成功大學" in s["station_name"]) and s["dist_km"] <= 3]
    if ncku:
        clat = sum(s["lat"] for s in ncku) / len(ncku)
        clon = sum(s["lon"] for s in ncku) / len(ncku)
        print(f"\n[校正參考] 站名含「成大/成功大學」共 {len(ncku)} 站，中心點約 ({clat:.4f}, {clon:.4f})，"
              f"離目前設定 {haversine_km(NCKU_LAT, NCKU_LON, clat, clon) * 1000:.0f} 公尺")
        for s in ncku:
            print(f"    - {s['station_name']} ({s['lat']:.5f}, {s['lon']:.5f})")

    print("\n[人工確認] 是否包含下列地點附近的站（地標座標為約略值）：")
    for lm, (llat, llon) in LANDMARKS.items():
        d_center = haversine_km(NCKU_LAT, NCKU_LON, llat, llon)
        hits = [s["station_name"] for s in near
                if haversine_km(llat, llon, s["lat"], s["lon"]) <= LANDMARK_NEAR_KM]
        mark = "有包含" if hits else "沒有包含"
        print(f"    {lm}（離成大 {d_center:.2f} km）：{mark}  {'、'.join(hits)}")
    keyword_hits = [s["station_name"] for s in near
                    if any(k in s["station_name"] for k in ("火車站", "車站", "夜市"))]
    print(f"    站名含「火車站/車站/夜市」的站：{'、'.join(keyword_hits) or '（無）'}")
    print("=" * 50 + "\n")


def fetch_and_save_stations(token: str) -> list[dict]:
    records = call_api(TDX_STATION_URL, "Station", token, {"$select": STATION_SELECT})
    print_sample("Station", records)
    all_stations = [s for s in (parse_station(r) for r in records) if s]
    near = []
    for s in all_stations:
        s["dist_km"] = haversine_km(NCKU_LAT, NCKU_LON, s["lat"], s["lon"])
        if s["dist_km"] <= RADIUS_KM:
            near.append(s)
    near.sort(key=lambda s: s["dist_km"])
    if not near:
        raise CollectError("成大周圍找不到任何站點，請檢查座標、半徑或欄位名稱")
    report_stations(all_stations, near)

    # 先寫到暫存檔再整個換掉，避免寫到一半當掉留下壞掉的 stations.csv
    STATIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATIONS_CSV.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STATION_COLUMNS, lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(near)
    os.replace(tmp, STATIONS_CSV)
    log.info("站點資訊：成大周圍 %.1f km 內共 %d 站，已存到 data/stations.csv", RADIUS_KM, len(near))
    return near


def load_station_ids() -> list[str]:
    """讀 data/stations.csv 的站點代碼；檔案不存在或只有標題列時回傳空 list。"""
    if not STATIONS_CSV.exists():
        return []
    with open(STATIONS_CSV, newline="", encoding="utf-8") as f:
        return [row["station_id"] for row in csv.DictReader(f) if row.get("station_id")]


# ---------------------------------------------------------------------------
# 即時可借車數
# ---------------------------------------------------------------------------
def build_filters(station_ids: list[str]) -> list[str]:
    """產生 OData $filter，例如 StationUID eq 'TNN500101001' or StationUID eq '...'。"""
    filters, current = [], []
    for sid in station_ids:
        term = "StationUID eq '{}'".format(sid.replace("'", "''"))
        if current and len(" or ".join(current + [term])) > MAX_FILTER_CHARS:
            filters.append(" or ".join(current))
            current = []
        current.append(term)
    if current:
        filters.append(" or ".join(current))
    return filters


def fetch_availability(token: str, station_ids: list[str], fetch_time: str) -> tuple[list[dict], str]:
    records = []
    for flt in build_filters(station_ids):
        records += call_api(TDX_AVAILABILITY_URL, "Availability", token,
                            {"$filter": flt, "$select": AVAILABILITY_SELECT})
    print_sample("Availability", records)

    wanted = set(station_ids)
    rows, seen, update_times = [], set(), []
    for rec in records:
        try:
            sid = rec["StationUID"]
            if sid not in wanted or sid in seen:
                continue
            row = {
                "fetch_time": fetch_time,
                "station_id": sid,
                "available_bikes": int(rec["AvailableRentBikes"]),
                "available_spaces": int(rec["AvailableReturnBikes"]),
            }
        except (KeyError, TypeError, ValueError) as e:
            log.warning("可借車數欄位解析失敗，跳過這筆：%r（%s）", rec, e)
            continue
        rows.append(row)
        seen.add(sid)
        if rec.get("UpdateTime"):
            update_times.append(rec["UpdateTime"])

    missing = wanted - seen
    if missing:
        log.warning("這次有 %d 站沒有回傳資料：%s", len(missing), ", ".join(sorted(missing)))
    if not rows:
        raise CollectError("Availability 沒有任何可用的資料，這次不寫入")
    latest_update = max(update_times) if update_times else "?"
    return rows, latest_update


def append_raw(rows: list[dict]) -> None:
    """
    append 到 youbike_raw.csv；檔案不存在（或是空的）時先寫標題列。
    先把要寫的內容整理成一整段文字一次寫入；萬一寫到一半出錯，就把檔案切回原本的長度，
    保證不會留下半寫入的資料。
    """
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    old_size = RAW_CSV.stat().st_size if RAW_CSV.exists() else 0

    buf = io.StringIO()
    if old_size == 0:
        buf.write(",".join(RAW_COLUMNS) + "\n")
    else:
        with open(RAW_CSV, "rb") as f:  # 確認原本最後一行有換行，避免黏在一起
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                buf.write("\n")
    writer = csv.DictWriter(buf, fieldnames=RAW_COLUMNS, lineterminator="\n")
    writer.writerows(rows)
    data = buf.getvalue().encode("utf-8")

    with open(RAW_CSV, "ab") as f:
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            f.truncate(old_size)
            raise


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------
def main(refresh_stations: bool = False) -> None:
    # 有 .env 就讀 .env；GitHub Actions 沒有 .env，會直接用環境變數（已存在的環境變數不會被覆蓋）
    load_dotenv(ROOT / ".env")
    client_id = os.getenv("TDX_CLIENT_ID")
    client_secret = os.getenv("TDX_CLIENT_SECRET")
    if not client_id or not client_secret:
        log.error("找不到 TDX_CLIENT_ID / TDX_CLIENT_SECRET，請確認 .env 已建立並填好金鑰")
        return

    # 同一次執行的所有站都用同一個 fetch_time（台灣時間，格式 YYYY-MM-DD HH:MM:SS）
    fetch_time = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")

    station_ids = [] if refresh_stations else load_station_ids()
    if any(sid.startswith("FAKE") for sid in station_ids):
        log.error("data/stations.csv 是假資料（FAKE 開頭），請先執行 git checkout -- data/ 還原再抓真資料")
        return

    try:
        token = get_token(client_id, client_secret)
        if not station_ids:
            station_ids = [s["station_id"] for s in fetch_and_save_stations(token)]
        rows, latest_update = fetch_availability(token, station_ids, fetch_time)
        append_raw(rows)
    except CollectError as e:
        log.error("%s", e)
        return

    log.info("OK fetch_time=%s stations=%d rows=%d tdx_update=%s",
             fetch_time, len(station_ids), len(rows), latest_update)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓一次成大周圍 YouBike 可借車數")
    parser.add_argument("--refresh-stations", action="store_true",
                        help="強制重新呼叫 Station API 更新 data/stations.csv（會多用點數）")
    args = parser.parse_args()
    try:
        main(refresh_stations=args.refresh_stations)
    except Exception as e:  # 最後一道防線：任何沒預料到的錯誤都只記錄，不讓程式崩潰
        log.exception("未預期的錯誤：%s", e)
