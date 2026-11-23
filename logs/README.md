# logs/ — 執行紀錄

| 檔案 | 由誰產生 | 內容 |
|---|---|---|
| `collect.log` | `collect/collect.py` | 每次抓資料的時間、筆數，以及錯誤訊息（`[ERROR]` 開頭） |

- 抓資料出問題時，先打開這個檔案看最後幾行。
- `*.log` 已被 `.gitignore` 忽略，不會上傳（每台電腦各自留紀錄）。用 GitHub Actions 抓時，紀錄請到 repo 的 Actions 頁面看。

（`.gitkeep` 只是讓 git 保留這個空資料夾用的，可以忽略。）
