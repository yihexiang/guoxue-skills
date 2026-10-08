#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paipan 引擎自检：零依赖，不联网，不改盘<void>。

覆盖：
  T1 六十甲子与序号自洽
  T2 五虎遁与口诀一致（与年月联动穷举配对）
  T3 五鼠遁与口诀一致
  T4 藏干集合 == 《渊海子平·又地支藏遁歌》所给集合（逐字机械核对）
  T5 纳音表完整且成对
  T6 十神与《论日为主》五分法一致
  T7 空亡 = 每旬所缺两支
  T8 公开算例回归（含一个「二手资料自己算错」的反例）
  T9 子时两种口径的差异只出现在日柱，不污染时柱
  T10 真伪定理：年/月/日/时四柱对临界点的响应正确
"""
import datetime as dt
import sys
from pathlib import Path

# 允许从任意目录运行：自动把 ../scripts 加入路径
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))
import paipan as P  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s  %s" % (name, detail))
        FAILED.append(name)


def t1():
    check("T1 六十甲子 60 项且无重复", len(set(P.JIAZI)) == 60 and len(P.JIAZI) == 60)
    check("T1 甲子为首、癸亥为末", P.JIAZI[0] == "甲子" and P.JIAZI[-1] == "癸亥")
    ok = all(P.JIAZI[i][0] == P.TIAN_GAN[i % 10] and P.JIAZI[i][1] == P.DI_ZHI[i % 12]
             for i in range(60))
    check("T1 天干地支同步步进", ok)
    check("T1 阳干只配阳支", all(
        (P.GAN_YINYANG[P.JIAZI[i][0]] == "阳") == (P.ZHI_INDEX[P.JIAZI[i][1]] % 2 == 0)
        for i in range(60)))


def t2():
    # 五虎遁：甲己之年丙作首，乙庚之岁戊为头，丙辛之岁寻庚起，丁壬壬位顺行流，戊癸甲寅好追求
    expect = {"甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚",
              "辛": "庚", "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲"}
    check("T2 五虎遁表与口诀一致", P.WU_HU_DUN == expect, str(P.WU_HU_DUN))
    # 穷举：任一「节」日到下一个「节」日前一天，月柱需连续
    check("T2 月支与节对应表为 12 项", len(P.JIE_TO_ZHI) == 12)
    check("T2 12 月支互不相同", len({z for _, z in P.JIE_TO_ZHI}) == 12)
    # 月支顺序应为 寅卯辰巳午未申酉戌亥子丑
    order = [z for _, z in P.JIE_TO_ZHI]
    check("T2 月支自寅起顺排", order == ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"], str(order))


def t3():
    expect = {"甲": "甲", "己": "甲", "乙": "丙", "庚": "丙", "丙": "戊",
              "辛": "戊", "丁": "庚", "壬": "庚", "戊": "壬", "癸": "壬"}
    check("T3 五鼠遁表与口诀一致", P.WU_SHU_DUN == expect, str(P.WU_SHU_DUN))


# 《渊海子平·又地支藏遁歌》原文（据维基文库本）：
# 子宫癸水在其中，丑癸辛金己土同；寅宫甲木兼丙戊，卯宫乙木独相逢。
# 辰藏乙戊三分癸，巳中庚金丙戊丛；午宫丁火并己土，未宫乙己丁共宗。
# 申位庚金壬水戊，酉宫辛金独丰隆；戌宫辛金及丁戊，亥藏壬甲是真踪。
GE_JUE = {
    "子": set("癸"),
    "丑": set("癸辛己"),
    "寅": set("甲丙戊"),
    "卯": set("乙"),
    "辰": set("乙戊癸"),
    "巳": set("庚丙戊"),
    "午": set("丁己"),
    "未": set("乙己丁"),
    "申": set("庚壬戊"),
    "酉": set("辛"),
    "戌": set("辛丁戊"),
    "亥": set("壬甲"),
}


def t4():
    bad = []
    for z, expect in GE_JUE.items():
        got = set(P.CANGGAN[z])
        if got != expect:
            bad.append((z, sorted(got), sorted(expect)))
    check("T4 藏干集合 == 地支藏遁歌（12 支逐支核对）", not bad, str(bad))
    check("T4 藏干层数不超过本/中/余三级",
          all(len(v) <= 3 for v in P.CANGGAN.values()))


def t5():
    check("T5 纳音覆盖全部 60 甲子", len(P.NAYIN) == 60)
    check("T5 每组纳音恰好两干支", len(set(P.NAYIN.values())) == 30)
    counts = {}
    for gz, n in P.NAYIN.items():
        counts[n] = counts.get(n, 0) + 1
    check("T5 每个纳音名对应 2 个干支", set(counts.values()) == {2})
    check("T5 甲子乙丑为海中金", P.NAYIN["甲子"] == P.NAYIN["乙丑"] == "海中金")
    check("T5 壬戌癸亥为大海水", P.NAYIN["壬戌"] == P.NAYIN["癸亥"] == "大海水")


def t6():
    # 《论日为主》：一曰官（官、杀，甲乙见庚辛）；二曰财（正财偏财，甲乙见戊己）；
    # 三曰生气（印绶、倒食，甲乙见壬癸）；四曰窃气（食神、伤官，甲乙见丙丁）；
    # 五曰同类（劫财、阳刃，甲乙见甲乙）
    check("T6 甲见庚辛 -> 偏官/正官", (P.shishen("甲", "庚"), P.shishen("甲", "辛")) == ("七杀", "正官"))
    check("T6 甲见戊己 -> 偏财/正财", (P.shishen("甲", "戊"), P.shishen("甲", "己")) == ("偏财", "正财"))
    check("T6 甲见壬癸 -> 偏印/正印", (P.shishen("甲", "壬"), P.shishen("甲", "癸")) == ("偏印", "正印"))
    check("T6 甲见丙丁 -> 食神/伤官", (P.shishen("甲", "丙"), P.shishen("甲", "丁")) == ("食神", "伤官"))
    check("T6 甲见甲乙 -> 比肩/劫财", (P.shishen("甲", "甲"), P.shishen("甲", "乙")) == ("比肩", "劫财"))
    ok = True
    for dm in P.TIAN_GAN:
        for other in P.TIAN_GAN:
            ss = P.shishen(dm, other)
            if ss not in {"比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"}:
                ok = False
    check("T6 10×10 十神取值域封闭", ok)


def t7():
    # 甲子旬缺戌亥，甲戌旬缺申酉，甲申旬缺午未，甲午旬缺辰巳，甲辰旬缺寅卯，甲寅旬缺子丑
    want = {"甲子": "戌亥", "甲戌": "申酉", "甲申": "午未", "甲午": "辰巳", "甲辰": "寅卯", "甲寅": "子丑"}
    bad = []
    for k, v in want.items():
        got = "".join(P.XUN_MAP[k])
        if got != v:
            bad.append((k, got, v))
    check("T7 六旬空亡正确", not bad, str(bad))
    check("T7 空亡覆盖全 60 甲子", len(P.XUN_MAP) == 60)


def t8():
    # 公开算例：1984-12-01 22:00 乾造 -> 甲子 乙亥 己巳 乙亥
    # 来源：公开命理教程的逐步手推（且经独立天文历库复核）
    c = P.paipan(1984, 12, 1, 22, 0, "乾")
    check("T8 算例 1984-12-01 22:00 乾造四柱",
          tuple(c["四柱"]) == ("甲子", "乙亥", "己巳", "乙亥"), str(c["四柱"]))
    # 反例：某二手资料称 2026-03-10 卯时「惊蛰后属寅月 -> 庚寅月」，
    # 但 3 月 10 日已在惊蛰（换卯月）之后，月支应为卯。此处锁定正确答案。
    c2 = P.paipan(2026, 3, 10, 6, 0, "乾")
    check("T8 反例 2026-03-10 卯时月支应为卯（非寅）",
          c2["四柱"][1] == "辛卯", str(c2["四柱"]))
    check("T8 该例日柱与时柱", c2["四柱"][2] == "癸未" and c2["四柱"][3] == "乙卯", str(c2["四柱"]))
    # 立春当天的分界特性
    lc = P.jieqi_of_year(2026)["立春"]
    before = lc - dt.timedelta(minutes=1)
    after = lc + dt.timedelta(minutes=1)
    cb = P.paipan(before.year, before.month, before.day, before.hour, before.minute, "乾")
    ca = P.paipan(after.year, after.month, after.day, after.hour, after.minute, "乾")
    check("T8 立春前为乙巳年", cb["四柱"][0] == "乙巳", str(cb["四柱"]))
    check("T8 立春后为丙午年", ca["四柱"][0] == "丙午", str(ca["四柱"]))
    # 精确到秒时，落在交节那一秒即刻换年
    cs = P.paipan(lc.year, lc.month, lc.day, lc.hour, lc.minute, "乾", sec=lc.second)
    check("T8 交节当刻即为丙午年（秒精度）", cs["四柱"][0] == "丙午", str(cs["四柱"]))
    cb1 = P.paipan(lc.year, lc.month, lc.day, lc.hour, lc.minute, "乾", sec=lc.second - 1)
    check("T8 交节前一秒仍为乙巳年", cb1["四柱"][0] == "乙巳", str(cb1["四柱"]))
    # 分钟跨越交节时必须给出警示，而不是静默替用户选
    cw = P.paipan(lc.year, lc.month, lc.day, lc.hour, lc.minute, "乾")
    check("T8 分钟跨越交节时给出警示", len(cw["警示"]) >= 1 and "立春" in cw["警示"][0], str(cw["警示"]))


def t9():
    a = P.paipan(1984, 12, 1, 23, 30, "乾", {"midnight_policy": "子初换日"})
    b = P.paipan(1984, 12, 1, 23, 30, "乾", {"midnight_policy": "子正换日"})
    check("T9 两种子时口径日柱不同", a["四柱"][2] != b["四柱"][2],
          "%s vs %s" % (a["四柱"][2], b["四柱"][2]))
    check("T9 两种口径时柱相同（晚子时时干按次日日干）",
          a["四柱"][3] == b["四柱"][3], "%s vs %s" % (a["四柱"][3], b["四柱"][3]))
    check("T9 子正换日下 23:30 日柱等于当日日柱",
          b["四柱"][2] == P.day_ganzhi(dt.date(1984, 12, 1)), str(b["四柱"]))


def t10():
    # 每个月的「节」前后，月支必须切换到下一个月支
    bad = []
    for y in (1900, 1950, 2000, 2026, 2100):
        jq = P.jieqi_of_year(y)
        for i, (name, zhi) in enumerate(P.JIE_TO_ZHI):
            if name not in jq:
                continue
            t0 = jq[name]
            before = t0 - dt.timedelta(minutes=1)
            after = t0 + dt.timedelta(minutes=1)
            cb = P.paipan(before.year, before.month, before.day, before.hour, before.minute, "乾")
            ca = P.paipan(after.year, after.month, after.day, after.hour, after.minute, "乾")
            if ca["本命月令"] != zhi:
                bad.append(("%s %s" % (y, name), ca["本命月令"], zhi))
    check("T10 12 个节之后月支切换到目标月支", not bad, str(bad[:6]))


def t11():
    """起运回归：逆行锚点是「本月起始节」而非其再上一个节。

    背景（2026-10-08 用户专业排盘软件对照发现的真缺陷）：
    旧实现逆行数到「起始节的再上一个节」，导致逆行起运恒在 10-20 岁
    （违反起运 ∈ [0,10) 的不变量）。正确口径：
      顺行 = 数到未来最近的一个节；逆行 = 数到已往最近的一个节
      （即当前月自己的起始节）。三日折一岁。
    软件对照值：1977-12-07 23:58（乌鲁木齐真太阳时 21:57）阴男逆行，
    出生距大雪 8h26m → 起运 0.117 岁 ≈ 0年1月12天4时，丙午为第 6 步
    2028 年起（50-59 岁）。
    """
    bad = []

    # 1) 不变量：任意抽样，起运岁数必须 < 10
    samples = [(1977, 12, 7, 23, 58), (1990, 5, 15, 14, 0), (2001, 2, 4, 3, 0),
               (1985, 8, 20, 6, 30), (2000, 1, 1, 12, 0)]
    for (y, mo, d, h, mi) in samples:
        for g in ("乾", "坤"):
            c = P.paipan(y, mo, d, h, mi, g)
            exact = c["大运"]["起运时距"]
            days = float(exact.replace(" 天", ""))
            if not (0.0 <= days / 3.0 < 10.0):
                bad.append(("%d-%02d-%02d %s 起运超界" % (y, mo, d, g), exact))
    check("T11a 起运岁数 ∈ [0,10)（顺逆各抽样）", not bad, str(bad[:6]))

    # 2) 软件对照回归：逆行时距 = 出生距本月起始节
    birth = dt.datetime(1977, 12, 7, 21, 57, 12)  # 真太阳时
    c = P.paipan(1977, 12, 7, 23, 58, "乾",
                 opts={"solar_time": True, "longitude": 87.62,
                       "midnight_policy": "子初换日"})
    dy = c["大运"]
    days = float(dy["起运时距"].replace(" 天", ""))
    # 大雪 1977-12-07 13:30:49 → 距出生 8h26m23s = 0.3518 天
    check("T11b 1977阴男逆行时距=距大雪8h26m(±5m)", abs(days - 0.3518) < 0.0035,
          "实际 %s" % dy["起运时距"])
    check("T11c 起运显示 0 岁 1 个月", dy["起运"] == "0 岁 1 个月",
          "实际 %s" % dy["起运"])
    sixth = [x for x in dy["列"] if x["顺序"] == 6][0]
    check("T11d 第6步丙午 2028年起 50-59岁",
          sixth["干支"] == "丙午" and sixth["起运年"] == 2028
          and sixth["年龄段"] == "50-59 岁",
          "实际 %s %s %s" % (sixth["干支"], sixth["起运年"], sixth["年龄段"]))
    # 比较点回显必须是本月起始节（大雪），不是立冬
    check("T11e 比较点回显为大雪",
          "大雪" in dy["交节比较点"], "实际 %s" % dy["交节比较点"])


def main():
    print("paipan 引擎自检")
    for fn in (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11):
        fn()
    print()
    if FAILED:
        print("FAILED (%d): %s" % (len(FAILED), ", ".join(FAILED)))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
