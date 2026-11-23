"""
make_fake_data.py — 產生「假的」站點與可借車數資料，讓組員在還沒有真資料時就能開發

輸出（格式和 collect.py 產生的真資料完全一樣）：
    data/stations.csv          station_id, station_name, lat, lon, capacity（10 站）
    data/raw/youbike_raw.csv   fetch_time, station_id, available_bikes, available_spaces
                               （3 天 × 每 5 分鐘 × 10 站 = 8,640 筆）

規律：白天（約 8:00–17:00）學生把車騎走，車少；晚上車多。再加上一點隨機雜訊。

執行方式（在專案根目錄）：
    python tools/make_fake_data.py
    python tools/make_fake_data.py --force   # 檔案裡已有資料時，強制覆蓋

⚠️ 注意：這會覆蓋 data/ 裡的檔案。如果裡面已經有真資料，程式會拒絕執行（除非加 --force）。
   假資料請「不要」commit 推上 GitHub，以免和真資料混在一起。
"""

import argparse
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIONS_CSV = ROOT / "data" / "stations.csv"
RAW_CSV = ROOT / "data" / "raw" / "youbike_raw.csv"

STATION_COLUMNS = ["station_id", "station_name", "lat", "lon", "capacity"]
RAW_COLUMNS = ["fetch_time", "station_id", "available_bikes", "available_spaces"]

NCKU_LAT, NCKU_LON = 22.997, 120.219
N_STATIONS = 10
N_DAYS = 3
INTERVAL_MIN = 5
START = datetime(2025, 1, 6, 0, 0, 0)  # 從某個星期一 00:00 開始


def has_data(path: Path) -> bool:
    """檔案存在且除了標題列外還有資料。"""
    if not path.exists():
        return False
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f) > 1


def make_stations(rng: random.Random) -> list[dict]:
    stations = []
    for i in range(1, N_STATIONS + 1):
        stations.append(
            {
                "station_id": f"FAKE{i:03d}",
                "station_name": f"假站點{i:02d}",
                # 在成大周圍約 1 公里內隨機撒點（0.01 度 ≈ 1.1 公里）
                "lat": round(NCKU_LAT + rng.uniform(-0.009, 0.009), 6),
                "lon": round(NCKU_LON + rng.uniform(-0.009, 0.009), 6),
                "capacity": rng.choice([20, 24, 30, 36, 40]),
            }
        )
    return stations


def bikes_ratio(t: datetime) -> float:
    """回傳 0~1：這個時間點大約有幾成的車位有車。白天低、晚上高。"""
    hour = t.hour + t.minute / 60
    # 以 13 點為最低點、凌晨 1 點為最高點的餘弦曲線
    return 0.5 + 0.35 * math.cos((hour - 1) / 24 * 2 * math.pi)


def make_raw(stations: list[dict], rng: random.Random) -> list[dict]:
    rows = []
    n_steps = N_DAYS * 24 * 60 // INTERVAL_MIN
    for s in stations:
        cap = s["capacity"]
        offset = rng.uniform(-0.1, 0.1)  # 每站各自有點偏差，才不會每站都一樣
        noise = 0.0
        for step in range(n_steps):
            t = START + timedelta(minutes=INTERVAL_MIN * step)
            noise = 0.8 * noise + rng.gauss(0, 0.04)  # 會延續的雜訊，比較像真實資料
            bikes = round(cap * (bikes_ratio(t) + offset + noise))
            bikes = max(0, min(cap, bikes))
            # 真實資料的 fetch_time 不會剛好在整點，加幾秒誤差
            fetch_time = t + timedelta(seconds=rng.randint(0, 40))
            rows.append(
                {
                    "fetch_time": fetch_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "station_id": s["station_id"],
                    "available_bikes": bikes,
                    "available_spaces": cap - bikes,
                }
            )
    rows.sort(key=lambda r: (r["fetch_time"], r["station_id"]))
    return rows


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="產生假的 YouBike 資料")
    parser.add_argument("--force", action="store_true", help="已有資料時仍強制覆蓋")
    parser.add_argument("--seed", type=int, default=42, help="亂數種子（同一個種子會產生同樣的資料）")
    args = parser.parse_args()

    if not args.force and (has_data(STATIONS_CSV) or has_data(RAW_CSV)):
        print("data/ 裡已經有資料（可能是真資料），為了安全不覆蓋。")
        print("確定要覆蓋請加上 --force：python tools/make_fake_data.py --force")
        return

    rng = random.Random(args.seed)
    stations = make_stations(rng)
    raw = make_raw(stations, rng)
    write_csv(STATIONS_CSV, STATION_COLUMNS, stations)
    write_csv(RAW_CSV, RAW_COLUMNS, raw)
    print(f"已產生 {STATIONS_CSV.relative_to(ROOT)}（{len(stations)} 站）")
    print(f"已產生 {RAW_CSV.relative_to(ROOT)}（{len(raw)} 筆）")
    print("提醒：假資料請不要 commit。想還原成空檔案可執行：git checkout -- data/")


if __name__ == "__main__":
    main()
