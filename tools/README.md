# tools/ — 開發用小工具

## 這個資料夾負責什麼
`make_fake_data.py` 產生「假的」站點與可借車數資料（10 站、3 天、每 5 分鐘一筆，白天車少、晚上車多），讓負責 clean / train / app 的組員在還沒有真資料時就能先開發。

## 輸入
不需要輸入檔。可選參數：`--force`（已有資料時強制覆蓋）、`--seed 42`（亂數種子）。

## 輸出
格式和 `collect.py` 產生的真資料完全一樣：

| 檔案 | 欄位 | 行數 |
|---|---|---|
| `data/stations.csv` | station_id, station_name, lat, lon, capacity | 10 站 + 標題列 = 11 行 |
| `data/raw/youbike_raw.csv` | fetch_time, station_id, available_bikes, available_spaces | 8,640 筆 + 標題列 = 8,641 行 |

假站點的 station_id 是 `FAKE001` ~ `FAKE010`，一看就知道是假的。

## 做完的檢查方式
1. 執行 `python tools/make_fake_data.py`，畫面顯示「已產生 … 10 站」「已產生 … 8640 筆」。
2. 兩個檔案的第一列和上表欄位完全一樣。
3. 抽查同一站：中午的 available_bikes 明顯比半夜少；每一列 available_bikes + available_spaces = capacity。
4. 如果 data/ 裡已經有真資料，程式會拒絕覆蓋（這是保護機制）。
5. ⚠️ 假資料不要 commit！用完執行 `git checkout -- data/` 還原。
