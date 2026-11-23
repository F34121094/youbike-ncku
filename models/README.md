# models/ — 訓練好的模型

| 檔案 | 由誰產生 | 內容 |
|---|---|---|
| `model.joblib` | `model/train.py` | 表現最好的 scikit-learn 模型，用 `joblib.dump()` 存檔；`app/app.py` 用 `joblib.load()` 讀取 |

模型輸入欄位：bikes_now, bikes_15min_ago, bikes_30min_ago, hour, weekday, is_weekend, temperature, is_rain, capacity
預測目標：bikes_after_30min

（`.gitkeep` 只是讓 git 保留這個空資料夾用的，可以忽略。）
