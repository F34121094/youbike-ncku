# 成大周圍 YouBike 可借車數預測（youbike-ncku）

大學課程小組期末專案。

## 專案簡介

我們想回答一個問題：**「30 分鐘後，成大附近這個 YouBike 站還借得到車嗎？」**

做法分成四步，每位組員負責一步：

| 步驟 | 負責的程式 | 做什麼 |
|---|---|---|
| 1. 收集資料 | `collect/collect.py` | 每 5 分鐘向交通部 TDX 抓一次台南市 YouBike 即時車數，只留成大周圍 1.5 公里內的站 |
| 2. 整理資料 | `process/clean.py` | 清理資料、算出「現在車數、15/30 分鐘前車數、幾點、星期幾、天氣」等特徵 |
| 3. 訓練模型 | `model/train.py` | 用特徵預測 30 分鐘後的可借車數，比較幾個模型的誤差 |
| 4. 做網站 | `app/app.py` | 用 Streamlit 做網頁，在地圖上顯示每站的預測結果 |

每一步只透過「檔案」交接，所以只要大家遵守下面的**檔案格式約定**，就可以同時各做各的。
還沒有真資料時，可以先用 `tools/make_fake_data.py` 產生假資料來開發。

## 資料夾說明

```
youbike-ncku/
├── README.md                  ← 你正在看的這份說明
├── requirements.txt           ← 需要安裝的 Python 套件清單
├── .gitignore                 ← 告訴 git 哪些檔案不要上傳（例如金鑰 .env）
├── .env.example               ← 金鑰檔範本（複製成 .env 再填入真的金鑰）
├── data/
│   ├── stations.csv           ← 站點資訊（collect.py 產生）
│   ├── raw/youbike_raw.csv    ← 原始可借車數，每 5 分鐘累積一批（collect.py 產生）
│   └── processed/features.csv ← 整理好的特徵表（clean.py 產生）
├── collect/collect.py         ← 步驟 1：抓資料
├── process/clean.py           ← 步驟 2：整理資料
├── model/train.py             ← 步驟 3：訓練模型
├── app/app.py                 ← 步驟 4：網站
├── tools/make_fake_data.py    ← 產生假資料（開發用）
├── models/                    ← 訓練好的模型 model.joblib（train.py 產生）
├── results/                   ← 評估結果 metrics.csv、predictions.csv（train.py 產生）
├── logs/                      ← 執行紀錄 collect.log（collect.py 產生，不上傳）
└── .github/workflows/collect.yml ← GitHub Actions 自動抓資料（備案）
```

每個資料夾裡都有一份 `README.md`，寫著該資料夾的輸入、輸出和檢查方式。

## 檔案格式約定（欄位名稱不可更動！）

> 欄位名稱、大小寫、順序都要和下表一模一樣，否則下一位組員的程式會讀不到。
> 想改欄位，請先在群組討論，並同時更新這份 README 和各資料夾的 README。

### `data/stations.csv`（由 `collect/collect.py` 產生）

| 欄位 | 型態 | 說明 | 範例 |
|---|---|---|---|
| station_id | 文字 | 站點代碼（TDX 的 StationUID） | TNN501201001 |
| station_name | 文字 | 站名 | 成功大學光復校區 |
| lat | 小數 | 緯度 | 22.997 |
| lon | 小數 | 經度 | 120.219 |
| capacity | 整數 | 總車位數 | 30 |

### `data/raw/youbike_raw.csv`（由 `collect/collect.py` 每次 append）

| 欄位 | 型態 | 說明 | 範例 |
|---|---|---|---|
| fetch_time | 時間 | 抓取時間（台灣時間，`YYYY-MM-DD HH:MM:SS`） | 2025-01-06 08:05:12 |
| station_id | 文字 | 站點代碼，對應 stations.csv | TNN501201001 |
| available_bikes | 整數 | 可借車數 | 7 |
| available_spaces | 整數 | 可還空位數 | 23 |

### `data/processed/features.csv`（由 `process/clean.py` 產生）

| 欄位 | 型態 | 說明 |
|---|---|---|
| station_id | 文字 | 站點代碼 |
| time | 時間 | 對齊到 5 分鐘整點的時間（`YYYY-MM-DD HH:MM:SS`） |
| bikes_now | 整數 | 現在的可借車數 |
| bikes_15min_ago | 整數 | 15 分鐘前的可借車數 |
| bikes_30min_ago | 整數 | 30 分鐘前的可借車數 |
| hour | 整數 | 幾點（0–23） |
| weekday | 整數 | 星期幾（0=星期一 … 6=星期日） |
| is_weekend | 整數 | 週末為 1，平日為 0 |
| temperature | 小數 | 氣溫（攝氏） |
| is_rain | 整數 | 有下雨為 1，沒有為 0 |
| capacity | 整數 | 總車位數 |
| bikes_after_30min | 整數 | **30 分鐘後的可借車數（預測目標／答案）** |

### `results/predictions.csv`（由 `model/train.py` 產生）

| 欄位 | 型態 | 說明 |
|---|---|---|
| station_id | 文字 | 站點代碼 |
| time | 時間 | 做預測的時間點 |
| actual | 整數 | 30 分鐘後實際的車數 |
| predicted | 小數 | 模型預測的車數 |

### `results/metrics.csv`（由 `model/train.py` 產生）

| 欄位 | 型態 | 說明 |
|---|---|---|
| model_name | 文字 | 模型名稱，例如 baseline、linear_regression、random_forest |
| mae | 小數 | 平均絕對誤差（平均差幾台車，越小越好） |

### `models/model.joblib`（由 `model/train.py` 產生）

用 `joblib.dump()` 存下的 scikit-learn 模型，`app/app.py` 用 `joblib.load()` 讀取。

## 本機執行方式

以下指令都在「專案根目錄」（有 `README.md` 的那層）執行。

### 1. 下載專案

```bash
git clone https://github.com/<帳號>/youbike-ncku.git
cd youbike-ncku
```

### 2. 建立虛擬環境（每個專案有自己的一套套件，不會互相干擾）

Windows：

```bash
python -m venv .venv
.venv\Scripts\activate
```

Mac / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

成功的話，命令列前面會出現 `(.venv)`。之後每次重新打開終端機，都要再執行一次 `activate` 那行。

### 3. 安裝套件

```bash
pip install -r requirements.txt
```

### 4. 設定金鑰

1. 到 [TDX 運輸資料流通服務](https://tdx.transportdata.tw/) 註冊會員，在「會員中心 → 資料服務 → API 金鑰」取得 Client Id 與 Client Secret。
2. 把 `.env.example` 複製一份，改名為 `.env`：
   - Windows：`copy .env.example .env`
   - Mac / Linux：`cp .env.example .env`
3. 用記事本打開 `.env`，把 `your-client-id-here`、`your-client-secret-here` 換成你的金鑰。

> ⚠️ `.env` 裡是你的私人金鑰，**不能上傳到 GitHub**。`.gitignore` 已經設定好會忽略它，請不要硬加進去。

### 5. 抓一次資料

```bash
python collect/collect.py
```

成功時畫面會印出 API 的第一筆回傳（用來檢查欄位），並在 `data/stations.csv`、`data/raw/youbike_raw.csv` 寫入資料。
有錯誤時請看 `logs/collect.log`。

這支程式「跑一次就抓一次」。要每 5 分鐘自動抓，請用一台常開的電腦設定排程：
- Windows：「工作排程器」→ 建立基本工作 → 觸發程序選「每天」，進階設定裡設「每 5 分鐘重複一次」，動作執行 `.venv\Scripts\python.exe`，引數填 `collect/collect.py`，「開始位置」填專案資料夾路徑。
- Mac / Linux：`crontab -e` 加入 `*/5 * * * * cd /專案路徑 && .venv/bin/python collect/collect.py`

### 6. 其他步驟

```bash
python tools/make_fake_data.py   # 還沒有真資料時，先產生假資料
python process/clean.py          # 整理資料 → data/processed/features.csv
python model/train.py            # 訓練模型 → models/、results/
streamlit run app/app.py         # 開啟網站（瀏覽器會自動打開）
```

> ⚠️ 假資料請不要 commit 上傳。用完想還原成空檔案：`git checkout -- data/`

## 如何改用 GitHub Actions 自動抓資料（沒有常開電腦時的備案）

GitHub 可以幫我們每 5 分鐘在雲端跑一次 `collect.py`，再把新資料自動 commit 回 repo。
缺點是**排程常會延遲或被跳過**，所以只在找不到常開電腦時才用。設定檔是 `.github/workflows/collect.yml`。

1. **新增金鑰**：到 GitHub repo 頁面 → `Settings` → `Secrets and variables` → `Actions` → `Secrets` 分頁 → `New repository secret`，新增兩個：
   - `TDX_CLIENT_ID`：你的 Client Id
   - `TDX_CLIENT_SECRET`：你的 Client Secret
2. **手動測試一次**：到 `Actions` 分頁 → 左邊選 `collect-youbike` → `Run workflow`。跑完（綠色勾勾）後，repo 裡應該會多一個 `data: auto collect ...` 的 commit。
3. **開啟自動排程**：同一個 `Secrets and variables` → `Actions` 頁面，切到 `Variables` 分頁 → `New repository variable`，名稱 `ENABLE_ACTIONS_COLLECT`、值 `true`。
4. **停用**：把 `ENABLE_ACTIONS_COLLECT` 改成 `false`。

注意事項：
- 開啟 Actions 後，資料會由 GitHub 直接 commit，組員開始工作前請先 `git pull`，避免衝突。
- 不要同時開「常開電腦排程」和「GitHub Actions」，否則會重複抓。
- public repo 的 Actions 免費；private repo 每月有免費分鐘數上限（GitHub Free 約 2,000 分鐘），每 5 分鐘跑一次大約會用掉 8,000 分鐘以上，**private repo 很可能會超過額度**，這種情況請把 repo 改成 public 或改用常開電腦。
