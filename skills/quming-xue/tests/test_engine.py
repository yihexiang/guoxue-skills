#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quming-xue 引擎自检：零依赖，不联网。

覆盖：
  T1 五格公式 vs 朱益成(6,10,7) 权威算例
  T2 五格公式 vs 张石(11,5) 单姓单名算例
  T3 五格公式 vs 诸葛亮(諸15,葛15,亮9) 复姓单名算例
  T4 数理五行映射（1-2木 3-4火 5-6土 7-8金 9-0水）
  T5 81 数理三档分类（1吉/2凶/6半吉/81吉）+ 边界数提示
  T6 三才配置等级（木火土大吉 / 金木土凶 / 木木木吉 / 木金土大凶）
  T7 生肖宜忌（马忌氵 / 鼠宜宀）
  T8 平仄三连仄检测
  T9 综合评名（给定笔画+生肖+喜用+声调）
  T10 边界：strokes 长度不符 / 缺字抛错
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))
import wuge as W  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("  ✓", name)
    else:
        print("  ✗", name, "→", detail)
        FAILED.append(name)


def t1():
    r = W.wuge("朱", "益成", [6, 10,7])
    g = r
    check("T1 朱益成 五格=天7人16地17外8总23",
          g["天格"]==7 and g["人格"]==16 and g["地格"]==17 and g["外格"]==8 and g["总格"]==23, g)


def t2():
    r = W.wuge("张", "石", [11, 5])
    g = r
    # 天格11+1=12 人格11+5=16 地格5+1=6 外格12+6-16=2 总格16
    check("T2 张石(单姓单名) 天12人16地6外2总16",
          g["天格"]==12 and g["人格"]==16 and g["地格"]==6 and g["外格"]==2 and g["总格"]==16, g)


def t3():
    r = W.wuge("诸葛", "亮", [15, 15, 9])  # 諸15 葛15 亮9
    g = r
    # 天格15+15=30 人格15+9=24 地格9+1=10 外格30+10-24=16 总格39
    check("T3 诸葛亮(复姓单名) 天30人24地10外16总39",
          g["天格"]==30 and g["人格"]==24 and g["地格"]==10 and g["外格"]==16 and g["总格"]==39, g)


def t4():
    ok = all(W.num_wuxing(n) == e for n, e in
             [(1,"木"),(2,"木"),(3,"火"),(4,"火"),(5,"土"),(6,"土"),
              (7,"金"),(8,"金"),(9,"水"),(10,"水"),(11,"木"),(20,"水"),(81,"木")])
    check("T4 数理五行映射", ok)


def t5():
    c1 = W.shenshu(1)["档"] == "吉"
    c2 = W.shenshu(2)["档"] == "凶"
    c6 = W.shenshu(6)["档"] == "半吉"
    c81 = W.shenshu(81)["档"] == "吉"
    c15 = "财富" in W.shenshu(15)["标签"] and "女德" in W.shenshu(15)["标签"]
    check("T5 81数理 1吉/2凶/6半吉/81吉 + 15含财富·女德标签", c1 and c2 and c6 and c81 and c15)


def t6():
    # 三才等级判定（天/人/地 五行 → 生克等级），用确定数理构造：
    #   木火土顺生：天木(11)、人火(3)、地土(5) → 天→人→地 顺生 大吉
    s1 = W.sancai(11, 3, 5)
    #   土土土：比和 吉
    s5 = W.sancai(15, 15, 15)
    #   金木土：天金(7)、人木(11)、地土(5) → 天克人(金克木) 凶
    s4 = W.sancai(7, 11, 5)
    #   木金土：天木(1)、人金(7)、地土(5) → 人克天(金克木) 大凶
    s6 = W.sancai(1, 7, 5)
    #   金土火：天金(7)、人土(5)、地火(3) → 地→人→天 逆生 中吉
    s7 = W.sancai(7, 5, 3)
    check("T6 三才 木火土大吉(11,3,5)", s1["等级"]=="大吉", s1)
    check("T6 三才 土土土吉(比和)", s5["等级"]=="吉", s5)
    check("T6 三才 金木土凶(天克人)", s4["等级"]=="凶", s4)
    check("T6 三才 木金土大凶(人克天)", s6["等级"]=="大凶", s6)
    check("T6 三才 金土火中吉(逆生)", s7["等级"]=="中吉", s7)


def t7():
    # 马忌氵：名「沐」部首氵 → 忌用字；鼠宜宀：「安」部首宀 → 宜用字
    m = W.shengxiao_check("马", ["沐", "浩"])
    ok_m = any(ch=="沐" for ch,_ in m["忌用字"]) and any(ch=="浩" for ch,_ in m["忌用字"])
    s = W.shengxiao_check("鼠", ["安", "宁"])
    ok_s = any(ch=="安" for ch,_ in s["宜用字"])
    check("T7 生肖 马忌氵(沐/浩) / 鼠宜宀(安)", ok_m and ok_s, (m, s))


def t8():
    p = W.pingze([4, 4, 4])
    check("T8 平仄 三连仄检测", "仄仄仄" in p["平仄序列"] and any("三连" in w for w in p["提示"]), p)
    p2 = W.pingze([1, 2, 4])
    check("T8 平仄 平仄相间无告警", p2["平仄序列"]=="平平仄" and not p2["提示"], p2)


def t9():
    # 综合：姓李(7) 名 沐(8) 辰(7)？ 用已知笔画：李7 沐8 辰7 → 天格7+1=8 人格7+8=15 地格8+7=15 外格8+15-15=8 总格22
    r = W.evaluate_name("李", "沐辰", strokes=[7,8,7], gender="乾", zodiac="马",
                        xiyong=["水","木"], tones=[3,4,2], verbose=False)
    ok = (r["五格"]["天格"]==8 and r["五格"]["人格"]==15 and r["五格"]["地格"]==15
          and r["五格"]["外格"]==8 and r["五格"]["总格"]==22)
    # 生肖马：沐(氵) 忌；辰(龙) 忌(午马与辰? 马忌辰? 传统 马不特别忌辰; 但 _radical_of 辰→辰 not in 宜忌集合 → 不报)
    ok_z = any(ch=="沐" for ch,_ in r["生肖宜忌"]["忌用字"])
    # 喜用 水木：沐(氵→水) 命中
    ok_x = r["喜用补字"].get("沐")=="水"
    check("T9 综合评名 李沐辰 五格+生肖忌(沐)+喜用补(沐=水)", ok and ok_z and ok_x, r["五格"])


def t10():
    # strokes 长度不符 → 抛 ValueError
    try:
        W.wuge("李", "沐辰", [7, 8])
        bad = True
    except ValueError:
        bad = False
    # 缺字 → KeyError
    try:
        W.wuge("赵", "铁柱")  # 赵/铁/柱 不在 KANGXI
        bad2 = True
    except KeyError:
        bad2 = False
    check("T10 边界：strokes 长度不符抛错 / 缺字抛 KeyError", (not bad) and (not bad2), (bad, bad2))


def main():
    print("quming-xue 引擎自检")
    for fn in (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10):
        fn()
    print()
    if FAILED:
        print("失败 %d 项：%s" % (len(FAILED), FAILED))
        raise SystemExit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
