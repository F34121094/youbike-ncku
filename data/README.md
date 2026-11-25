# data/ — 資料

這個資料夾放專案的資料檔，**會上傳到 GitHub** 讓組員共用。

| 檔案 | 由誰產生 | 內容 / 欄位 |
|---|---|---|
| `stations.csv` | `collect/collect.py`（只在不存在時產生，省 TDX 點數） | 成大周圍 1.5 公里內的站點：station_id, station_name, lat, lon, capacity |
| `raw/youbike_raw.csv` | `collect/collect.py`（每次 append） | 每 15 分鐘的原始可借車數：fetch_time, station_id, available_bikes, available_spaces（優先用 TDX，TDX 沒資料時用 YouBike 官方資料補上） |
| `raw/youbike_official_raw.csv` | `collect/collect.py`（每次 append，2026-11-25 起） | YouBike 官方資料，和上面同一個 fetch_time，核對用：fetch_time, station_id, available_bikes, available_spaces, source_update_time |
| `processed/features.csv` | `process/clean.py` | 模型用的特徵表：station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min |

- `stations.csv`、`raw/youbike_raw.csv` 已經是真資料（2026-11-23 開始收集）；`processed/features.csv` 目前只有標題列。
- 用 `python tools/check_data.py` 可以看資料筆數、每天筆數與缺漏時段。
- `tools/make_fake_data.py` 也會寫入 `stations.csv` 和 `raw/youbike_raw.csv`，但假資料**不要 commit**。（已有真資料時它會拒絕覆蓋；`collect.py` 看到 FAKE 站點也會拒絕執行。）
- 請不要手動修改 `raw/youbike_raw.csv` 和 `raw/youbike_official_raw.csv`，它們是原始資料。後續步驟（clean.py 之後）只讀 `youbike_raw.csv`。
- **已知缺漏**：2026-11-25 07:45 起 TDX 回傳空資料，07:45–12:00 之間只有 08:30 那一批，其他時段 `youbike_raw.csv` 沒有資料，清理時請當成缺值。詳見 [`collect/README.md`](../collect/README.md#疑難排解紀錄tdx-回傳空資料2026-11-25)。
- **核對兩個來源**：用 `fetch_time + station_id` 合併兩份檔案。只拿 `collect.log` 裡 `source=tdx` 的批次比較才有意義（`source=youbike_official` 的批次兩份資料本來就一樣）。
