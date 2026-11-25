# collect/ — 收集資料

## 這個資料夾負責什麼
`collect.py` 向交通部 TDX 抓台南市 YouBike 的即時可借車數，只留下成大周圍 1.5 公里內的站（目前 61 站），存成 CSV。
同一次執行也會另外抓 **YouBike 官方公開資料**存成另一份 CSV，用來和 TDX 交叉核對；TDX 失敗或回傳空資料時，主要資料也會改用官方資料補上。
**跑一次抓一次就結束**，每 15 分鐘自動執行要交給排程（本機排程或 GitHub Actions，見下方）。

## TDX 點數限制（重要）
我們的 TDX 帳號只有 **3 點**：`點數 = 呼叫次數 ÷ 1500 + 傳輸量 MB ÷ 150`。所以程式這樣省點數：

| 做法 | 說明 |
|---|---|
| 每 15 分鐘抓一次 | 一天 96 次，約 0.07 點／天，3 點大約可以抓 **40 天** |
| Station API 只呼叫一次 | 只有 `data/stations.csv` 不存在（或只有標題列）時才抓全台南的站點（約 270 KB），篩出成大附近的站後存起來 |
| Availability 只查需要的站 | 用 OData `$filter=StationUID eq '…' or …` 只查 stations.csv 裡的站，`$select` 只取需要的欄位（每次約 12 KB） |
| 記錄傳輸量 | 每次 API 回傳的 bytes 都寫進 `logs/collect.log`，用 `python tools/check_data.py` 估算累計點數 |

> 想重新篩選站點（例如改了中心點或半徑）：`python collect/collect.py --refresh-stations`（會多用一次 Station API）。
> 換 token 不算點數；網路失敗的重試只要有收到回應，log 都會記一筆，估算時會一起算進去（偏保守）。

## 輸入
- `.env`（從 `.env.example` 複製）：`TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`。在 GitHub Actions 上沒有 `.env`，改從環境變數（repo Secrets）讀。
- TDX API（[官方 Swagger 文件](https://tdx.transportdata.tw/api-service/swagger/basic/2cc9b888-a592-496f-99de-9ab35b7fb70d)，公共自行車 Basic v2）：
  - `GET /api/basic/v2/Bike/Station/City/Tainan`：站點（StationUID、StationName.Zh_tw、StationPosition.PositionLat / PositionLon、BikesCapacity）
  - `GET /api/basic/v2/Bike/Availability/City/Tainan`：即時車數（StationUID、AvailableRentBikes、AvailableReturnBikes、UpdateTime）
- YouBike 官方公開資料（不需金鑰、**不算 TDX 點數**，每次約 6 MB，內容是全台所有站）：
  - `GET https://apis.youbike.com.tw/json/station-yb2.json`
  - 對應方式：官方 `station_no` = TDX `StationUID` 去掉前 3 碼城市代碼（`TNN501321004` → `501321004`），61 站全部對得上。
  - 欄位對應：`available_spaces` → 可借車數、`empty_spaces` → 可還空位、`updated_at` → 資料更新時間。
    （官方的 `available_spaces` 意思是「可借」，名稱容易搞混；可借 + 可還 = `parking_spaces` 總車位。）
  - 這不是有正式文件的 API，網址或欄位可能會改，所以只當作核對和備援用。

## 輸出
| 檔案 | 寫入方式 | 欄位 |
|---|---|---|
| `data/stations.csv` | 只在不存在時產生（`--refresh-stations` 時整份覆蓋） | station_id, station_name, lat, lon, capacity |
| `data/raw/youbike_raw.csv` | 每次往後 append（不覆蓋）；不存在時先寫標題列 | fetch_time, station_id, available_bikes, available_spaces |
| `data/raw/youbike_official_raw.csv` | 每次往後 append（不覆蓋）；不存在時先寫標題列 | fetch_time, station_id, available_bikes, available_spaces, source_update_time |
| `logs/collect.log` | 往後 append | 每次 API 的回傳大小、成功／失敗紀錄 |

- `station_id` 用 TDX 的 `StationUID`（例如 `TNN501321004`）。
- `fetch_time` 是台灣時間 `YYYY-MM-DD HH:MM:SS`，**同一次執行的所有站都是同一個時間**。
- 網路失敗會等 5 秒重試，最多重試 3 次；還是失敗就在 log 寫 `[ERROR]` 並正常結束，**不會寫入半份資料**。
- 兩個來源互相獨立，一個失敗不影響另一個寫入：
  | TDX | 官方 | `youbike_raw.csv` | `youbike_official_raw.csv` |
  |---|---|---|---|
  | 成功 | 成功 | 寫 TDX 資料（`source=tdx`） | 寫官方資料 |
  | 失敗／空的 | 成功 | 寫官方資料（`source=youbike_official`） | 寫官方資料 |
  | 成功 | 失敗 | 寫 TDX 資料 | 不寫 |
  | 失敗／空的 | 失敗 | 不寫 | 不寫 |
- log 的格式（`tools/check_data.py` 會讀，請不要改）：
  ```
  2026-11-23 20:55:18 [INFO] API name=Availability status=200 bytes=12095 attempt=1
  2026-11-23 20:55:18 [INFO] OFFICIAL fetch_time=2026-11-23 20:55:17 rows=61 official_update=2026-11-23 20:54:40
  2026-11-23 20:55:18 [INFO] OK fetch_time=2026-11-23 20:55:17 stations=61 rows=61 source=tdx update=2026-11-23T20:55:17+08:00
  ```
  - `OFFICIAL` 那行是官方資料寫進 `youbike_official_raw.csv` 的紀錄。
  - `OK` 那行的 `source=` 表示這批 `youbike_raw.csv` 來自 `tdx` 還是 `youbike_official`，`update=` 是該來源的資料更新時間。
  - 2026-11-25 之前的 log 只有 `OK ... tdx_update=...`（當時只有 TDX 一個來源）。

## 站點篩選結果（2026-11-23）
- 中心點 (22.997, 120.219)，在光復／成功校區交界附近。用站名含「成大／成功大學」的站校正，中心點只差約 110 公尺，所以維持不變。
- 1.5 公里內共 **61 站**，台南全市 803 站。
- **有包含台南火車站附近的站**：臺南車站(前鋒路)、(前站一)、(前站二)、(前站三)、成大公園等。火車站離成大約 0.6 公里。
- **有包含大東夜市附近的站**：長榮高中、衛國公園、衛生局(林森辦公室)。夜市離成大約 1.4 公里，在範圍邊緣，而且只有週一、二、五營業。
- 花園夜市（約 2.5 公里）、武聖夜市（約 3.2 公里）不在範圍內。
- 第一次抓站點時，畫面會印出完整站名清單和上面這些檢查，請人工確認。

## 做完的檢查方式
1. 在專案根目錄執行 `python collect/collect.py`，畫面會印出 Availability API 的第一筆回傳（第一次執行還會印 Station API 的第一筆和站點清單）。
2. `data/stations.csv` 的第一列必須剛好是 `station_id,station_name,lat,lon,capacity`，目前 61 站。
3. `data/raw/youbike_raw.csv` 的第一列必須剛好是 `fetch_time,station_id,available_bikes,available_spaces`；每跑一次多 61 行。
4. 再跑一次，確認 raw 檔是「變多」而不是被覆蓋。
5. 打開 `logs/collect.log`，最後一行應該是 `[INFO] OK ...`，沒有 `[ERROR]`。
6. 執行 `python tools/check_data.py`，看資料筆數、缺漏時段與累計點數。

---

## 本機排程：讓電腦每 15 分鐘自動執行一次

先確認手動執行 `python collect/collect.py` 成功，再設定排程。電腦必須**開著而且不能睡眠**，排程才會執行。

> ⚠️ 本機排程和 GitHub Actions 只能選一個開，否則會重複抓、浪費點數。

### Windows：工作排程器

**步驟 1：找出兩個路徑**（在專案資料夾打開命令提示字元或 PowerShell）

```bash
cd                        # 印出「專案資料夾路徑」，例如 D:\youbike-ncku
.venv\Scripts\activate
where python              # 第一行就是「python 路徑」，例如 D:\youbike-ncku\.venv\Scripts\python.exe
```

**步驟 2：建立工作**
1. 按「開始」，搜尋並打開「**工作排程器**」。
2. 右邊點「**建立基本工作…**」。
   - 名稱：`youbike-collect`，按「下一步」。
   - 觸發程序：選「**每天**」→ 下一步 → 開始時間選今天、任一個時間（例如 00:07）→ 下一步。
   - 動作：選「**啟動程式**」→ 下一步。
     - 程式或指令碼：貼上步驟 1 的「python 路徑」
     - 新增引數：`collect\collect.py`
     - 開始位置：貼上步驟 1 的「專案資料夾路徑」（**一定要填**，不然會找不到檔案）
   - 勾選「按一下 [完成] 時，開啟此工作的 [內容] 對話方塊」，按「完成」。

**步驟 3：設定每 15 分鐘重複**（在剛跳出的「內容」視窗）
1. 「**觸發程序**」分頁 → 選那一筆 → 「編輯」：
   - 勾選「**重複工作每**」，下拉選 **15 分鐘**（沒有的話直接手打 `15 分鐘`），「持續時間」選「**無限期**」→ 確定。
2. 「**一般**」分頁：選「**不論使用者登入與否均執行**」（之後要輸入 Windows 密碼），這樣登出也會跑。
3. 「**條件**」分頁：取消勾選「只有在電腦使用 AC 電源時才啟動工作」（筆電用電池時也要跑）；勾選「喚醒電腦以執行此工作」。
4. 「**設定**」分頁：勾選「排定的開始時間過後，盡快執行工作」→ 確定。

**步驟 4：測試**：在工作清單對 `youbike-collect` 按右鍵 →「**執行**」，然後打開 `logs\collect.log`，最後一行應出現新的 `OK`。

**停止**：對工作按右鍵 →「停用」或「刪除」。
另外，建議到「設定 → 系統 → 電源」把「睡眠」改成「永不」。

### macOS / Linux：cron

**步驟 1：找出兩個路徑**（在專案資料夾的終端機）

```bash
pwd                       # 「專案資料夾路徑」，例如 /Users/amy/youbike-ncku
ls .venv/bin/python       # 確認虛擬環境的 python 存在
```

**步驟 2：編輯排程**

```bash
crontab -e
```

第一次會問你用哪個編輯器，選 `nano` 最簡單。在檔案最後加一行（把路徑換成你的專案資料夾路徑）：

```
7,22,37,52 * * * * cd /Users/amy/youbike-ncku && .venv/bin/python collect/collect.py >> logs/cron.log 2>&1
```

- `7,22,37,52 * * * *` = 每小時的 7、22、37、52 分各執行一次（＝每 15 分鐘）。
- `>> logs/cron.log 2>&1` 把畫面輸出存起來，程式根本沒跑起來時可以看這個檔。
- nano 存檔：按 `Ctrl + O`、`Enter`，再按 `Ctrl + X` 離開。

**步驟 3：確認**

```bash
crontab -l                # 應該看到剛剛那行
tail logs/collect.log     # 等到下一個 :07 / :22 / :37 / :52 之後，應該有新的 OK
```

**停止**：`crontab -e` 把那行刪掉（或在開頭加 `#`）存檔。

macOS 補充：
- 第一次可能需要允許 cron 存取檔案：「系統設定 → 隱私權與安全性 → 完整磁碟取用權限」，按 `+` 加入 `/usr/sbin/cron`。
- Mac 睡眠時 cron 不會執行，請在「系統設定 → 電池／能源」設定不要自動睡眠。

### 本機收集時，記得定期上傳資料

本機排程只會更新你電腦上的檔案，請每天（或每幾天）把資料推上 GitHub 給組員用：

```bash
git add data/raw/youbike_raw.csv data/raw/youbike_official_raw.csv data/stations.csv logs/collect.log
git commit -m "data: update"
git pull --rebase
git push
```

---

## GitHub Actions 排程（備案）

設定檔：`.github/workflows/collect.yml`，cron 為 `7,22,37,52 * * * *`（每 15 分鐘，避開整點與 :30）。

### 開啟方式
1. Settings → Secrets and variables → Actions → **Secrets**：新增 `TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`。
2. 同一頁的 **Variables** 分頁：新增 `ENABLE_ACTIONS_COLLECT`，值 `true`（停用時改成 `false`）。
3. 到 Actions 頁面按「Run workflow」手動測一次，確認成功。

> ⚠️ 本機排程和 GitHub Actions 只能選一個開。

### 疑難排解紀錄：排程幾乎沒有觸發（2026-11-24）

**狀況**
- 11/24 00:46 開啟（手動 Run workflow 成功），到 10:28 照理應該有約 38 次排程，實際上只在 **08:45 跑了 1 次**（結果正常）。
- 08:45 這次其實是 08:37 那一格延遲 8 分鐘才觸發。

**檢查結果：設定沒有錯**
- cron 語法正確，workflow 狀態是 `active`，而且在預設分支 `main` 上（排程只會在預設分支執行）。
- 不是 `ENABLE_ACTIONS_COLLECT` 的問題：如果排程有觸發、只是變數沒設好，Actions 頁面會留下一筆 **skipped** 紀錄。這次連 skipped 都沒有，代表 GitHub 根本沒有發出排程事件。

**原因**
GitHub Actions 的 schedule 是「盡力而為」，系統忙的時候會延遲或整次丟掉。剛建立的 repo 和剛加上的排程特別常見，有時要過幾小時到一天才會穩定。

**怎麼檢查**
- Actions 頁面看執行紀錄：`event` 是 `schedule` 的有幾筆？有沒有 `skipped`？
- 公開 repo 不用登入也能用 API 查：
  ```bash
  curl -s "https://api.github.com/repos/F34121094/youbike-ncku/actions/runs?per_page=30"
  ```
- `python tools/check_data.py` 看資料的缺漏時段。

**解決方法（由簡單到可靠）**
1. **先觀察一段時間**（這次先觀察到 11/24 晚上）：很多時候過一陣子就會開始穩定觸發。
2. **改用外部服務觸發 `workflow_dispatch`**：例如用 [cron-job.org](https://cron-job.org) 每 15 分鐘送一個 POST 請求：
   ```
   POST https://api.github.com/repos/F34121094/youbike-ncku/actions/workflows/collect.yml/dispatches
   Header: Authorization: Bearer <PAT>
           Accept: application/vnd.github+json
   Body:   {"ref": "main"}
   ```
   - PAT 用 fine-grained token，只給這個 repo 的 **Actions: Read and write** 權限。
   - 手動觸發不會遇到 GitHub 排程的延遲，也不受 `ENABLE_ACTIONS_COLLECT` 限制；改用這個方式時，記得把變數改成 `false`，避免同一個時段跑兩次。
3. **改回本機排程**（見上方「本機排程」）：找一台常開的電腦執行，並把 `ENABLE_ACTIONS_COLLECT` 改成 `false`。

**後續（2026-11-24 晚上）：已改用 cron-job.org 觸發**
- 觀察到 14:00 仍然只有早上那 1 次排程，之後 18:29 又只跑了 1 次。等於從 11/24 00:46 開啟到 21:00，GitHub 排程總共只觸發 2 次，所以決定採用上面的方法 2。
- 21:19 從 cron-job.org 按 Test run，回應 204，GitHub Actions 出現一筆 `workflow_dispatch`，結果 success ✅。
- 目前的設定：
  - **cron-job.org**：Cronjobs → 新增 `youbike-collect`，每 15 分鐘執行一次，Time zone `Asia/Taipei`。
    - Request method：`POST`
    - Request body：`{"ref":"main"}`
    - Headers：
      | Key | Value |
      |---|---|
      | `Authorization` | `Bearer <token>`（`Bearer` 是固定字，後面空一格再接 token，不要加 `< >`） |
      | `Accept` | `application/vnd.github+json` |
  - **GitHub token**：fine-grained PAT，只開放 `youbike-ncku` 這個 repo 的 **Actions: Read and write** 權限。token 只存在 cron-job.org 裡，**不要放進 repo**。token 到期後要重新產生，並更新 cron-job.org 的 header。
  - **repo 變數** `ENABLE_ACTIONS_COLLECT` 改成 `false`：GitHub 自己的排程觸發時會直接跳過，避免跟 cron-job.org 重複抓。
- Test run 回傳錯誤時的對照：
  | 錯誤碼 | 原因 |
  |---|---|
  | `401` | token 錯誤，或 `Bearer` 後面少了空格 |
  | `403` / `404` | token 權限不足，或沒有選到這個 repo |
  | `422` | body 格式錯誤 |
- 想停止收集：到 cron-job.org 把這個 job 停用（Enable job 關掉）。

---

## 疑難排解紀錄：TDX 回傳空資料（2026-11-25）

**狀況**
- 排程照常每 15 分鐘觸發、也照常 commit，但從 **2026-11-25 07:45** 起，幾乎每次都沒有寫入新資料。
- `logs/collect.log` 裡是這樣：
  ```
  [INFO] API name=Availability status=200 bytes=2 attempt=1
  [WARNING] Availability API 回傳是空的
  [WARNING] 這次有 61 站沒有回傳資料：...
  [ERROR] Availability 沒有任何可用的資料，這次不寫入
  ```
  `status=200`、`bytes=2` 代表 TDX 正常回應，但內容是空陣列 `[]`。
- 07:45 到 11:45 共 17 次，只有 **08:30 那次成功**，其餘 16 次都是空的。

**檢查過程**：用同一組金鑰直接打 TDX，每個查詢只有幾 KB，幾乎不花點數

| 查詢 | 結果 | 代表 |
|---|---|---|
| 台南 Availability，只查 1 站 | `200 []` | — |
| 台南 Availability，**不加 `$filter`** | `200 []` | 不是 filter 或站點代碼的問題 |
| 台南 Station API | `200 []` | 連站點清單都是空的 |
| **台北** Availability | `200 []` | 不只台南，TDX 自行車資料整體都是空的 |

排除的原因：
- 金鑰／token：錯的話會回 `401`，不會是 `200`。
- 點數用完：不會是 `200` 加空資料。
- 排程（GitHub Actions／cron-job.org）：commit 都有照時間出現；在本機跑也是一樣的結果。

**原因**：TDX 公共自行車 API 端暫時沒有資料（上游資料中斷或 TDX 維護），不是我們程式的問題。同一時間 YouBike 官方公開資料是正常的（`updated_at` 是最新時間）。

**處理方式**
1. `collect.py` 加上第二個資料來源：每次都另外抓 YouBike 官方資料，存到 `data/raw/youbike_official_raw.csv`，可以和 TDX 交叉核對，也證明資料可信。
2. TDX 失敗或回傳空資料時，`youbike_raw.csv` 改用官方資料補上，並在 log 記 `source=youbike_official`，資料不會再整段中斷。
3. GitHub Actions 的 `git add` 和 `.gitattributes` 的 `merge=union` 都加上新檔案。

**影響**
- 07:45 到這次更新上線前的資料**補不回來**（兩個來源都只有「現在」的資料）。這段在 `process/clean.py` 請當成缺值處理。
- 官方資料每次約 6 MB，在 GitHub Actions 上沒問題，也不影響 TDX 點數。

**之後遇到類似狀況怎麼查**
1. 看 `logs/collect.log`：`status=200 bytes=2` 是 TDX 回空資料；`status=401` 是金鑰問題；`status=429` 是太頻繁或點數問題。
2. 看 `OK` 行的 `source=`：如果連續好幾批都是 `youbike_official`，代表 TDX 還沒恢復。
3. 可以到 [TDX 官網](https://tdx.transportdata.tw/)看最新消息／系統公告。
