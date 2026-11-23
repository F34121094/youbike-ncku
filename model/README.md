# model/ — 訓練模型

## 這個資料夾負責什麼
`train.py` 用特徵表訓練「30 分鐘後可借車數」的預測模型，比較幾個模型的誤差（MAE），存下表現最好的模型和預測結果。

## 輸入
`data/processed/features.csv`，欄位：

station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min

- 模型輸入（X）：bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity
- 預測目標（y）：bikes_after_30min

## 輸出
| 檔案 | 欄位 / 內容 |
|---|---|
| `models/model.joblib` | 表現最好的模型（`joblib.dump` 存檔） |
| `results/metrics.csv` | model_name, mae（每個模型一列） |
| `results/predictions.csv` | station_id, time, actual, predicted（測試集） |

## 做完的檢查方式
1. 執行 `python model/train.py`，確認上面三個檔案都有產生。
2. `results/metrics.csv` 第一列剛好是 `model_name,mae`；行數 = 比較的模型數量 + 1（標題列）。
3. 至少要有一個 baseline（直接猜「30 分鐘後 = 現在」），而且其他模型的 MAE 應該比 baseline 小，不然模型沒有學到東西。
4. `results/predictions.csv` 第一列剛好是 `station_id,time,actual,predicted`；行數約為 features.csv 的 20%（測試集比例）。
5. 確認訓練 / 測試是「依時間切」：測試集的 time 全部晚於訓練集。
6. 在 Python 裡 `joblib.load("models/model.joblib")` 能成功讀回，並能對一列特徵 `predict`。
