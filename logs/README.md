# logs/ — 執行紀錄

| 檔案 | 由誰產生 | 內容 |
|---|---|---|
| `collect.log` | `collect/collect.py` | 每次 API 回傳的大小（bytes）、抓到幾站、錯誤訊息（`[ERROR]` 開頭） |

- 抓資料出問題時，先打開這個檔案看最後幾行。
- `collect.log` **會上傳到 GitHub**：GitHub Actions 每次執行後會把它 commit 回 repo，`tools/check_data.py` 用裡面的 `API name=... bytes=...` 行估算累計用掉多少 TDX 點數。請不要手動修改或刪除。
- 其他 `.log` 檔（例如 cron 的 `cron.log`）不會上傳。

（`.gitkeep` 只是讓 git 保留這個空資料夾用的，可以忽略。）
