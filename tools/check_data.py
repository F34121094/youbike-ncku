"""
check_data.py — 檢查收集到的資料，並估算已經用掉多少 TDX 點數

輸入：
    data/raw/youbike_raw.csv   collect.py 累積的原始資料
    logs/collect.log           collect.py 的執行紀錄（裡面有每次 API 回傳的 bytes）
輸出（只印在畫面上，不改任何檔案）：
    1. 總筆數、第一筆與最後一筆 fetch_time、抓了幾次
    2. 每天的筆數與抓取次數
    3. 相鄰兩次抓取間隔超過 --gap-minutes（預設 20 分鐘）的缺漏時段
    4. 依 log 估算的累計 TDX 點數（點數 = 呼叫次數 ÷ 1500 + 傳輸量 MB ÷ 150）

執行方式（在專案根目錄）：
    python tools/check_data.py
    python tools/check_data.py --gap-minutes 30 --budget 3

說明：
    - 我們每 15 分鐘抓一次，GitHub Actions 又常延遲幾分鐘，所以預設間隔超過 20 分鐘才算缺漏。
    - 點數估算用「解壓縮後」的回傳大小，會比 TDX 實際計算的略高（偏保守），
      正確數字請以 TDX 會員中心為準。
    - log 只記錄「這份 log 所在的電腦 / GitHub Actions」的呼叫；同一組金鑰若在別台電腦也用過，
      那些呼叫不會算進來。
"""

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "youbike_raw.csv"
LOG_FILE = ROOT / "logs" / "collect.log"
TIME_FMT = "%Y-%m-%d %H:%M:%S"

CALLS_PER_POINT = 1500
MB_PER_POINT = 150
RUNS_PER_DAY = 24 * 4  # 每 15 分鐘一次

# collect.py 每次收到 API 回應會寫一行：... [INFO] API name=Availability status=200 bytes=12095 attempt=1
API_LINE = re.compile(r"^(\S+ \S+) \[\w+\] API name=(\w+) status=(\d+) bytes=(\d+)")


def check_raw(gap_minutes: int) -> None:
    print("=" * 60)
    print(f"原始資料：{RAW_CSV.relative_to(ROOT)}")
    print("=" * 60)
    if not RAW_CSV.exists():
        print("找不到檔案，請先執行 python collect/collect.py")
        return

    per_time = Counter()  # fetch_time → 這次抓到幾站
    with open(RAW_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            per_time[row["fetch_time"]] += 1
    total = sum(per_time.values())
    if total == 0:
        print("檔案只有標題列，還沒有資料")
        return

    times = sorted(datetime.strptime(t, TIME_FMT) for t in per_time)
    print(f"總筆數：{total:,}（共抓 {len(times)} 次，平均每次 {total / len(times):.1f} 站）")
    print(f"第一筆 fetch_time：{times[0].strftime(TIME_FMT)}")
    print(f"最後一筆 fetch_time：{times[-1].strftime(TIME_FMT)}")

    print("\n每天筆數：")
    rows_per_day, runs_per_day = Counter(), Counter()
    for t_str, n in per_time.items():
        day = t_str[:10]
        rows_per_day[day] += n
        runs_per_day[day] += 1
    for day in sorted(rows_per_day):
        print(f"  {day}  {rows_per_day[day]:>6,} 筆  （抓 {runs_per_day[day]:>3} 次，"
              f"完整一天應為 {RUNS_PER_DAY} 次）")

    gap = timedelta(minutes=gap_minutes)
    gaps = [(a, b) for a, b in zip(times, times[1:]) if b - a > gap]
    print(f"\n相鄰兩次抓取間隔超過 {gap_minutes} 分鐘的缺漏時段：{len(gaps)} 段")
    for a, b in gaps:
        mins = (b - a).total_seconds() / 60
        print(f"  {a.strftime(TIME_FMT)}  →  {b.strftime(TIME_FMT)}  （間隔 {mins:.0f} 分鐘）")


def check_points(budget: float) -> None:
    print("\n" + "=" * 60)
    print(f"TDX 點數估算（依 {LOG_FILE.relative_to(ROOT)}）")
    print("=" * 60)
    if not LOG_FILE.exists():
        print("找不到 log 檔，無法估算")
        return

    calls, total_bytes = Counter(), defaultdict(int)
    last_avail_bytes = None
    with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = API_LINE.match(line)
            if not m:
                continue
            name, size = m.group(2), int(m.group(4))
            calls[name] += 1
            total_bytes[name] += size
            if name == "Availability" and m.group(3) == "200":
                last_avail_bytes = size

    if not calls:
        print("log 裡還沒有 API 呼叫紀錄")
        return

    n_calls = sum(calls.values())
    mb = sum(total_bytes.values()) / 1_000_000
    points = n_calls / CALLS_PER_POINT + mb / MB_PER_POINT
    for name in sorted(calls):
        print(f"  {name:<13} 呼叫 {calls[name]:>6,} 次，回傳 {total_bytes[name] / 1_000_000:8.3f} MB")
    print(f"  合計：呼叫 {n_calls:,} 次 ÷ {CALLS_PER_POINT} + {mb:.3f} MB ÷ {MB_PER_POINT}"
          f" ≈ {points:.4f} 點（額度 {budget} 點，剩約 {budget - points:.4f} 點）")

    if last_avail_bytes:
        per_day = RUNS_PER_DAY * (1 / CALLS_PER_POINT + last_avail_bytes / 1_000_000 / MB_PER_POINT)
        days_left = (budget - points) / per_day if per_day else float("inf")
        print(f"  以每 15 分鐘 1 次、每次約 {last_avail_bytes:,} bytes 計算："
              f"每天約 {per_day:.4f} 點，剩下的點數大約還能抓 {days_left:.0f} 天")


def main() -> None:
    parser = argparse.ArgumentParser(description="檢查 youbike_raw.csv 並估算 TDX 點數")
    parser.add_argument("--gap-minutes", type=int, default=20,
                        help="相鄰兩次抓取間隔超過幾分鐘算缺漏（預設 20）")
    parser.add_argument("--budget", type=float, default=3.0, help="TDX 點數額度（預設 3）")
    args = parser.parse_args()
    check_raw(args.gap_minutes)
    check_points(args.budget)


if __name__ == "__main__":
    main()
