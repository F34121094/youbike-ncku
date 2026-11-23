# data/ — 資料

這個資料夾放專案的資料檔，**會上傳到 GitHub** 讓組員共用。

| 檔案 | 由誰產生 | 內容 / 欄位 |
|---|---|---|
| `stations.csv` | `collect/collect.py`（每次覆蓋） | 成大周圍 1.5 公里內的站點：station_id, station_name, lat, lon, capacity |
| `raw/youbike_raw.csv` | `collect/collect.py`（每次 append） | 每 5 分鐘的原始可借車數：fetch_time, station_id, available_bikes, available_spaces |
| `processed/features.csv` | `process/clean.py` | 模型用的特徵表：station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min |

- 目前這些檔案只有標題列，等真資料收集後才會有內容。
- `tools/make_fake_data.py` 也會寫入 `stations.csv` 和 `raw/youbike_raw.csv`，但假資料**不要 commit**。
- 請不要手動修改 `raw/youbike_raw.csv`，它是唯一的原始資料來源。
