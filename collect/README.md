# collect/ — 收集資料

## 這個資料夾負責什麼
`collect.py` 向交通部 TDX 抓台南市 YouBike 的站點資訊和即時可借車數，只留下成大周圍 1.5 公里內的站，存成 CSV。跑一次抓一次，每 5 分鐘自動執行要交給外部排程。

## 輸入
- `.env`（從 `.env.example` 複製）：`TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`
- TDX API：台南市 Bike Station（站點）與 Bike Availability（即時車數）

## 輸出
| 檔案 | 寫入方式 | 欄位 |
|---|---|---|
| `data/stations.csv` | 每次整份覆蓋 | station_id, station_name, lat, lon, capacity |
| `data/raw/youbike_raw.csv` | 每次往後 append（不覆蓋） | fetch_time, station_id, available_bikes, available_spaces |
| `logs/collect.log` | 往後 append | 執行紀錄與錯誤訊息 |

## 做完的檢查方式
1. 在專案根目錄執行 `python collect/collect.py`，畫面會印出 Station 與 Availability API 的第一筆回傳。對照程式裡標 `TODO(確認)` 的欄位名稱（StationUID、StationName、BikesCapacity、AvailableRentBikes…）是否一致。
2. `data/stations.csv` 的第一列必須剛好是 `station_id,station_name,lat,lon,capacity`；站數大概幾十站（成大周圍 1.5 公里）。
3. `data/raw/youbike_raw.csv` 的第一列必須剛好是 `fetch_time,station_id,available_bikes,available_spaces`；每跑一次，行數增加「站數」那麼多行。
4. 再跑一次，確認 raw 檔是「變多」而不是被覆蓋。
5. 打開 `logs/collect.log`，最後幾行應該是 `[INFO]`，沒有 `[ERROR]`。
6. 在 Google Maps 上抽查幾個站的經緯度，確認真的在成大附近；必要時校正程式裡的 `NCKU_LAT`、`NCKU_LON`。
