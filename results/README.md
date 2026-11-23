# results/ — 模型評估結果

| 檔案 | 由誰產生 | 欄位 |
|---|---|---|
| `metrics.csv` | `model/train.py` | model_name, mae（每個模型一列，MAE 越小越好） |
| `predictions.csv` | `model/train.py` | station_id, time, actual, predicted（測試集的實際值與預測值） |

這兩個檔案會上傳到 GitHub，`app/app.py` 會讀它們來顯示模型表現。

（`.gitkeep` 只是讓 git 保留這個空資料夾用的，可以忽略。）
