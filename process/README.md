# process/ — 整理資料

## 這個資料夾負責什麼
`clean.py` 把原始的可借車數清理乾淨，並算出模型需要的特徵（現在車數、15/30 分鐘前車數、時間、天氣），以及要預測的答案（30 分鐘後車數）。

## 輸入
| 檔案 | 欄位 |
|---|---|
| `data/raw/youbike_raw.csv` | fetch_time, station_id, available_bikes, available_spaces |
| `data/stations.csv` | station_id, station_name, lat, lon, capacity |
| 天氣資料（來源待決定） | 用來產生 temperature, is_rain |

還沒有真資料時，先執行 `python tools/make_fake_data.py` 產生假資料。

## 輸出
`data/processed/features.csv`，欄位（順序也要一樣）：

station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min

- `time`：對齊到 5 分鐘整點，格式 `YYYY-MM-DD HH:MM:SS`
- `weekday`：0=星期一 … 6=星期日；`is_weekend`、`is_rain`：0 或 1
- `bikes_after_30min`：30 分鐘後的可借車數（預測目標）

## 做完的檢查方式
1. 執行 `python process/clean.py`，確認 `data/processed/features.csv` 有產生。
2. 第一列必須剛好是：`station_id,time,bikes_now,bikes_15min_ago,bikes_30min_ago,hour,weekday,is_weekend,temperature,is_rain,capacity,bikes_after_30min`
3. 行數：大約等於 raw 的行數，減掉每站頭尾各 30 分鐘（每站約 12 筆）。用假資料時約 8,500 行。
4. 用 pandas 檢查：`df.isna().sum()` 應該都是 0（天氣來源還沒決定前，temperature 可以暫時是空的）；`bikes_now` 不會是負數、也不會超過 `capacity`。
5. 抽查一站：某一列的 `bikes_after_30min`，應該等於同一站 30 分鐘後那一列的 `bikes_now`。
