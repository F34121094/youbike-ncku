"""
train.py — 訓練「30 分鐘後可借車數」的預測模型（骨架，待組員實作）

輸入：
    data/processed/features.csv
        station_id, time, bikes_now, bikes_15min_ago, bikes_30min_ago,
        hour, weekday, is_weekend, temperature, is_rain, capacity, bikes_after_30min

輸出：
    models/model.joblib        表現最好的模型（用 joblib.dump 存）
    results/metrics.csv        model_name, mae（每個模型一列）
    results/predictions.csv    station_id, time, actual, predicted（測試集的預測結果）

執行方式（在專案根目錄）：
    python model/train.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES_CSV = ROOT / "data" / "processed" / "features.csv"
MODEL_FILE = ROOT / "models" / "model.joblib"
METRICS_CSV = ROOT / "results" / "metrics.csv"
PREDICTIONS_CSV = ROOT / "results" / "predictions.csv"

# 模型要用的輸入欄位（X）與預測目標（y）
# 注意：app/app.py 預測時也要用「完全一樣」的欄位與順序
FEATURE_COLS = [
    "bikes_now", "bikes_15min_ago", "bikes_30min_ago",
    "hour", "weekday", "is_weekend", "temperature", "is_rain", "capacity",
]
TARGET_COL = "bikes_after_30min"


def main() -> None:
    # 步驟 1：讀檔
    #   df = pd.read_csv(FEATURES_CSV, parse_dates=["time"])

    # 步驟 2：切訓練集 / 測試集 —— 要「依時間切」，不能隨機切！
    #   例如前 80% 的時間當訓練、最後 20% 當測試（隨機切會讓模型偷看到未來）

    # 步驟 3：訓練並比較幾個模型，每個都算測試集的 MAE（平均絕對誤差，越小越好）
    #   - baseline：直接猜「30 分鐘後 = 現在」（predicted = bikes_now），當作最低標準
    #   - LinearRegression
    #   - RandomForestRegressor
    #   提示：from sklearn.metrics import mean_absolute_error

    # 步驟 4：存結果
    #   - results/metrics.csv：欄位 model_name, mae
    #   - results/predictions.csv：最佳模型在測試集的結果，欄位 station_id, time, actual, predicted
    #   - models/model.joblib：joblib.dump(best_model, MODEL_FILE)

    raise NotImplementedError("train.py 尚未實作，請依照上面的步驟完成")


if __name__ == "__main__":
    main()
