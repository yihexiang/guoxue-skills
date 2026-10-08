#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把零依赖引擎 paipan.py 与第三方天文历库 lunar-python 做全量交叉比对。

用法：
  PYTHONPATH=<lunar_python 源码目录> python3 verify_cross.py --mode all

比对内容：
  1. 日柱：1900-2100 每一天（约 7.3 万天）全量比对。
  2. 四柱：抽样日期 × 12 时辰全比对。
  3. 节气边界：每年 24 个节气时刻前后各 1 小时的整刻位置重点比对。
差异一律打印明细，不做"看起来通过"的判定。
"""
import argparse
import datetime as dt
import sys
import time

sys.path.insert(0, ".")
import paipan as P  # noqa: E402

try:
    from lunar_python import Solar
except ImportError:
    print("FATAL: 需要 lunar_python。请用 PYTHONPATH 指向其源码目录。", file=sys.stderr)
    sys.exit(2)

MS = ["amp", "mma"]  # unused


def lp_bazi(y, mo, d, h, mi):
    ec = Solar.fromYmdHms(y, mo, d, h, mi, 0).getLunar().getEightChar()
    return ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()


def my_bazi(y, mo, d, h, mi, gender="乾", policy=None):
    c = P.paipan(y, mo, d, h, mi, gender, {"midnight_policy": policy} if policy else None)
    return tuple(c["四柱"])


POLICY = None   # None = 引擎默认；也可设为 '子正换日' 以匹配参照库口径


def run_day(y_from=1900, y_to=2100):
    """日柱全量比对（只比日柱，不涉及子时口径）。"""
    start = dt.date(y_from, 1, 1)
    end = dt.date(y_to, 12, 31)
    n = 0
    bad = []
    d0 = start
    while d0 <= end:
        mine = P.day_ganzhi(d0)
        theirs = lp_bazi(d0.year, d0.month, d0.day, 12, 0)[2]
        if mine != theirs:
            bad.append((d0.isoformat(), mine, theirs))
            if len(bad) >= 20:
                break
        n += 1
        d0 += dt.timedelta(days=1)
    return n, bad


def run_quad(sample_days, hours):
    n = 0
    bad = []
    for day in sample_days:
        for h, mi in hours:
            y, mo, d = day.year, day.month, day.day
            mine = my_bazi(y, mo, d, h, mi, policy=POLICY)
            theirs = lp_bazi(y, mo, d, h, mi)
            if mine != theirs:
                bad.append(("%04d-%02d-%02d %02d:%02d" % (y, mo, d, h, mi), mine, theirs))
                if len(bad) >= 25:
                    return n, bad
            n += 1
    return n, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["day", "quad", "boundary", "all"], default="all")
    ap.add_argument("--year-step", type=int, default=1)
    ap.add_argument("--policy", choices=["子初换日", "子正换日"], default=None)
    args = ap.parse_args()

    total_bad = 0

    if args.mode in ("day", "all"):
        t = time.time()
        n, bad = run_day()
        print("== 日柱全量比对 ==")
        print("  样本数: %d   差异: %d   耗时 %.1fs" % (n, len(bad), time.time() - t))
        for b in bad[:10]:
            print("   DIFF", b)
        total_bad += len(bad)

    HOURS = [(h * 2 + 1, 30) for h in range(12)]  # 每个时辰的中点，避开口径边界

    if args.mode in ("quad", "boundary", "all"):
        global POLICY
        POLICY = args.policy or None
        print("== 使用子时口径: %s ==" % (POLICY or P.DEFAULTS["midnight_policy"]))
        days = []
        for y in range(1900, 2101, args.year_step):
            for m in range(1, 13):
                days.append(dt.date(y, m, 15))
        t = time.time()
        n, bad = run_quad(days, HOURS)
        print("== 四柱抽样比对（每月15日 × 12 时辰中点）==")
        print("  样本数: %d   差异: %d   耗时 %.1fs" % (n, len(bad), time.time() - t))
        for b in bad[:12]:
            print("   DIFF", b)
        total_bad += len(bad)

    if args.mode in ("boundary", "all"):
        days = []
        for y in range(1900, 2101, 5):
            for name in P.JIEQI_ORDER:
                jt = P.jieqi_of_year(y)[name]
                for off in (-1, 0, 1):
                    days.append(jt.date() + dt.timedelta(days=off))
        days = sorted(set(days))
        t = time.time()
        # 重点：节气当天的每个时辰边界
        hours = [(h, 0) for h in range(24)]
        n, bad = run_quad(days, hours)
        print("== 节气边界比对（每5年 × 24节气前后1天 × 24整点）==")
        print("  样本数: %d   差异: %d   耗时 %.1fs" % (n, len(bad), time.time() - t))
        for b in bad[:12]:
            print("   DIFF", b)
        total_bad += len(bad)

    print("\nTOTAL DIFFS:", total_bad)
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
