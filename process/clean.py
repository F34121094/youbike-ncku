"""
clean.py — 把原始資料整理成「模型可以直接用的特徵表」（骨架，待組員實作）

輸入：
    data/raw/youbike_raw.csv   fetch_time, station_id, available_bikes, available_spaces
    data/stations.csv          station_id, station_name, lat, lon, capacity
    （天氣資料）               temperature, is_rain 的來源，TODO: 決定用中央氣象署 API 或手動下載

輸出：
    data/processed/features.csv
        station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago,
        hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min

執行方式（在專案根目錄）：
    python process/clean.py

沒有真資料時，可以先跑 python tools/make_fake_data.py 產生假資料來開發。
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "youbike_raw.csv"
STATIONS_CSV = ROOT / "data" / "stations.csv"
FEATURES_CSV = ROOT / "data" / "processed" / "features.csv"

# 欄位名稱是全組約定，不可更動（順序也請照這個）
FEATURE_COLUMNS = [
    "station_id", "time", "bikes_now", "bikes_15min_ago", "bikes_30min_ago",
    "hour", "weekday", "is_weekend", "temperature", "is_rain", "capacity",
    "bikes_after_30min",
]


def main() -> None:
    # 步驟 1：讀檔
    #   raw = pd.read_csv(RAW_CSV, parse_dates=["fetch_time"])
    #   stations = pd.read_csv(STATIONS_CSV)

    # 步驟 2：清理
    #   - 刪除重複列（同一站、同一 fetch_time 出現兩次）
    #   - 刪除明顯錯誤的值（負數、超過 capacity）
    #   - 把 fetch_time 對齊到 5 分鐘整點（例如 10:03:12 → 10:05:00），存成 time 欄位
    #     提示：raw["time"] = raw["fetch_time"].dt.round("5min")

    # 步驟 3：每個站各自補齊時間軸
    #   - 每站依 time 排序，缺少的 5 分鐘時段用前一筆補（ffill），缺太久的（例如超過 30 分鐘）就不要補

    # 步驟 4：做特徵（每站分開做，用 groupby("station_id")）
    #   - bikes_now         = 這個時間點的 available_bikes
    #   - bikes_15min_ago   = 15 分鐘前（往前 3 筆）的 available_bikes
    #   - bikes_30min_ago   = 30 分鐘前（往前 6 筆）的 available_bikes
    #   - bikes_after_30min = 30 分鐘後（往後 6 筆）的 available_bikes ← 這是「答案」（預測目標）
    #   - hour       = time 的小時（0–23）
    #   - weekday    = 星期幾（0=星期一 … 6=星期日）
    #   - is_weekend = weekday 是 5 或 6 時為 1，否則 0
    #   - capacity   = 從 stations.csv 依 station_id 合併進來

    # 步驟 5：合併天氣
    #   - temperature：攝氏溫度（float）
    #   - is_rain    ：有下雨為 1，沒有為 0
    #   - TODO: 還沒決定天氣來源前，可以先填 temperature=NaN、is_rain=0

    # 步驟 6：刪掉有空值的列（最前面 30 分鐘沒有 lag、最後 30 分鐘沒有答案）

    # 步驟 7：只留下約定欄位並存檔
    #   - time 存成 "YYYY-MM-DD HH:MM:SS" 格式字串
    #   features[FEATURE_COLUMNS].to_csv(FEATURES_CSV, index=False, encoding="utf-8")

    raise NotImplementedError("clean.py 尚未實作，請依照上面的步驟完成")


if __name__ == "__main__":
    main()
