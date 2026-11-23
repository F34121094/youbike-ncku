"""
app.py — Streamlit 網站：在地圖上顯示成大周圍站點，並顯示 30 分鐘後的預測可借車數（骨架，待組員實作）

輸入：
    data/stations.csv            station_id, station_name, lat, lon, capacity
    data/processed/features.csv  （取每站最新一筆當作預測的輸入）
    models/model.joblib          train.py 訓練好的模型
    results/metrics.csv          model_name, mae
    results/predictions.csv      station_id, time, actual, predicted

輸出：
    網頁（不產生檔案）

執行方式（在專案根目錄）：
    streamlit run app/app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
STATIONS_CSV = ROOT / "data" / "stations.csv"
FEATURES_CSV = ROOT / "data" / "processed" / "features.csv"
MODEL_FILE = ROOT / "models" / "model.joblib"
METRICS_CSV = ROOT / "results" / "metrics.csv"
PREDICTIONS_CSV = ROOT / "results" / "predictions.csv"

st.set_page_config(page_title="成大周圍 YouBike 預測", layout="wide")
st.title("成大周圍 YouBike：30 分鐘後可借車數預測")
st.info("網站還在開發中（app/app.py 目前只是骨架）")

# 區塊 1：讀資料
#   - 用 @st.cache_data 包住讀 CSV 的函式、@st.cache_resource 包住 joblib.load，避免每次重整都重讀
#   - 檔案不存在時用 st.warning 提示「請先跑 clean.py / train.py」，不要讓網頁直接報錯

# 區塊 2：地圖（folium + streamlit_folium）
#   - 以成大（22.997, 120.219）為中心
#   - 每個站畫一個圓點，顏色依「預測可借車數」分級（例如 0–2 紅、3–5 黃、6 以上綠）
#   - 點擊站點顯示：站名、現在車數、30 分鐘後預測車數、總車位

# 區塊 3：選擇站點（st.selectbox）
#   - 顯示該站近期的實際車數走勢（plotly 折線圖）
#   - 用 model.predict(最新一筆特徵[FEATURE_COLS]) 算 30 分鐘後的預測
#     FEATURE_COLS 要和 model/train.py 完全一樣

# 區塊 4：模型表現
#   - 讀 results/metrics.csv，用表格或長條圖比較各模型 MAE
#   - 讀 results/predictions.csv，畫 actual vs predicted
