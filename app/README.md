# app/ — Streamlit 網站

## 這個資料夾負責什麼
`app.py` 是給使用者看的網站：在地圖上顯示成大周圍的 YouBike 站，以及每站 30 分鐘後的預測可借車數和模型表現。

## 輸入
| 檔案 | 欄位 / 內容 |
|---|---|
| `data/stations.csv` | station_id, station_name, lat, lon, capacity |
| `data/processed/features.csv` | station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min |
| `models/model.joblib` | train.py 存下的模型 |
| `results/metrics.csv` | model_name, mae |
| `results/predictions.csv` | station_id, time, actual, predicted |

## 輸出
不產生檔案，輸出是網頁畫面。

## 做完的檢查方式
1. 在專案根目錄執行 `streamlit run app/app.py`，瀏覽器會自動打開 http://localhost:8501 。
2. 地圖中心在成大，站點數量和 `data/stations.csv` 的行數 − 1 相同。
3. 點站點能看到站名、現在車數、預測車數；預測值不會是負數、也不會超過 capacity。
4. 模型表現區塊顯示的 MAE 和 `results/metrics.csv` 一致。
5. 把 `models/model.joblib` 暫時改名，網頁應顯示提示訊息，而不是一大串紅色錯誤。
