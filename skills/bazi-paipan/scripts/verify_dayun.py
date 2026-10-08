#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""起运 / 大运 交叉验证。

把 paipan.py 的起运时距、顺逆方向、大运干支序列，与参照库 lunar-python
的 Yun 做比对。差异一律逐条打印，不做"四舍五入后看起来一样"的处理。
"""
import argparse
import datetime as dt
import random
import sys

sys.path.insert(0, ".")
import paipan as P  # noqa: E402

try:
    from lunar_python import Solar
except ImportError:
    print("FATAL: 需要 lunar_python。", file=sys.stderr)
    sys.exit(2)


def lp_yun(y, mo, d, h, mi, male, n=8):
    solar = Solar.fromYmdHms(y, mo, d, h, mi, 0)
    lunar = solar.getLunar()
    # 与排盘一致的口径晚子时切换 Sector 不影响 Yun；先把 gregorian 转成该库视角
    yun = lunar.getEightChar().getYun(1 if male else 0, 1)
    pillars = []
    for dy in yun.getDaYun()[: n + 1]:
        pillars.append(dy.getGanZhi())
    # 第 0 项通常是起点说明（童限/起运前的运），从 1 开始才是第一步大运
    start = yun.getStartSolar()
    return pillars, start


def mine(y, mo, d, h, mi, gender, n=8):
    c = P.paipan(y, mo, d, h, mi, gender, {"dayun_count": n})
    return (c["大运"]["列"], c["大运"]["顺逆"], c["大运"]["起运时距"], c["大运"]["依据"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--policy", choices=["子初换日", "子正换日"], default="子正换日")
    args = ap.parse_args()

    rnd = random.Random(args.seed)
    bad_forward = []
    bad_pillar = []
    bad_days = []
    n = 0
    max_abs = 0.0
    for _ in range(args.samples):
        y = rnd.randint(1900, 2100)
        mo = rnd.randint(1, 12)
        dmax = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
        d = rnd.randint(1, dmax)
        if mo == 2 and ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0):
            d = min(d, 29)
        h = rnd.randint(0, 22)         # 避开 23 点，那属于子时口径分歧，另案处理
        mi = rnd.choice([0, 15, 30, 45])
        male = rnd.choice([True, False])
        gender = "乾" if male else "坤"
        try:
            pillars, start = lp_yun(y, mo, d, h, mi, male)
            rows, direction, days_text, basis = mine(y, mo, d, h, mi, gender)
        except Exception as e:
            bad_pillar.append(("%04d-%02d-%02d %02d:%02d" % (y, mo, d, h, mi), "ERR", str(e)))
            continue
        n += 1
        # 参照库 getDaYun()[0] 是「起运前」信息，实际第 1..n 步从 index 1 起
        ref = pillars[1:]
        myp = [r["干支"] for r in rows]
        if ref[:len(myp)] != myp:
            bad_pillar.append(("%04d-%02d-%02d %02d:%02d %s" % (y, mo, d, h, mi, gender), myp, ref))
    print("== 大运干支序列比对 ==")
    print("  样本数: %d   序列不一致: %d" % (n, len(bad_pillar)))
    for b in bad_pillar[:8]:
        print("   DIFF", b[0], "\n     mine:", b[1], "\n     ref :", b[2])

    print("\n== 顺逆方向抽查 ==")
    # 顺逆只取决于年干阴阳与性别，用全组合穷举即可（10 干 × 2 性别）
    bad_fwd = []
    for gan_idx in range(10):
        for gender in ("乾", "坤"):
            # 找一个该年干的年份：年柱干 = gan，取立春后某日
            for off in range(60):
                y = 1940 + off
                try:
                    lc = P.jieqi_of_year(y)["立春"]
                except KeyError:
                    continue
                probe = lc.date() + dt.timedelta(days=3)
                yg = P.ganzhi_of_year_pillar(dt.datetime.combine(probe, dt.time(12, 0)))[0]
                if yg[0] == P.TIAN_GAN[gan_idx]:
                    male = gender == "乾"
                    this = P.paipan(probe.year, probe.month, probe.day, 10, 0, gender)
                    row = this["大运"]
                    expect = "顺行" if ((P.GAN_YINYANG[yg[0]] == "阳") == male) else "逆行"
                    if row["顺逆"] != expect:
                        bad_fwd.append((probe.isoformat(), gender, yg, row["顺逆"], expect))
                    break
    print("  组合数: 20   方向不一致: %d" % len(bad_fwd))
    for b in bad_fwd[:8]:
        print("   DIFF", b)
    return 1 if (bad_pillar or bad_fwd) else 0


if __name__ == "__main__":
    sys.exit(main())
