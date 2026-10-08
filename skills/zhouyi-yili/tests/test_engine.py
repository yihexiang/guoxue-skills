#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zhouyi-yili 引擎自检：零依赖，不联网。

覆盖：
  T1  六十四卦名序列 vs 语料《大象傳》原文顺序（外部权威对照）
  T2  综卦（覆卦）不变量：文王卦序中除八宫特殊对外，相邻两卦互为倒爻
  T3  错卦（旁通）：乾坤/頤大過/坎離/中孚小過 四组互为六爻全反
  T4  八卦卦德与卦象（說卦傳第七章）
  T5  当位 / 得中 / 有應 的结构判定
  T6  变爻 → 之卦（窮則變，變則通）
  T7  大象辞：六十四卦全部取到，且与语料逐字一致
  T8  起卦可复现（同 seed 同结果）+ 金钱卦只产生 6/7/8/9
  T9  简体别名可查（归妹/丰/兑…）
  T10 边界：未知卦名抛错；大象查不到要明说而非臆造
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))
import zhouyi as Z  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("  ✓", name)
    else:
        print("  ✗", name, "→", detail)
        FAILED.append(name)


def corpus_names():
    """从带锚点语料里取出《大象傳》的六十四卦顺序（外部权威，非本表自证）。"""
    p = _HERE.parent.parent.parent / "corpus" / "anchored" / "src-07-daxiang.md"
    if not p.exists():
        return None
    out = []
    for block in p.read_text(encoding="utf-8").split("\n["):
        body = block.split("\n", 1)[1] if "\n" in block else block
        body = body.strip()
        if body.startswith("【") and "】" in body:
            body = body.split("】", 1)[1].strip()
        if "：" in body:
            out.append(body.split("：", 1)[0].strip())
    return out or None


def t1():
    cn = corpus_names()
    if cn is None:
        check("T1 语料缺失，跳过", True)
        return
    mine = [n for n, _, _ in Z.HEXAGRAMS]
    check(f"T1 卦序与《大象傳》一致（{len(cn)} 卦）", mine == cn,
          f"mine={mine[:6]}… corpus={cn[:6]}…")


# 文王卦序里这四组是「错卦」关系而非「综卦」（六爻全反，且不因倒转而重合）
COMPLEMENT_PAIRS = {("乾", "坤"), ("頤", "大過"), ("坎", "離"), ("中孚", "小過")}


def t2():
    bad = []
    for i in range(0, 64, 2):
        a = Z.HEXAGRAMS[i][0]
        b = Z.HEXAGRAMS[i + 1][0]
        if (a, b) in COMPLEMENT_PAIRS:
            continue
        if Z.reversed_hex(a) != b:
            bad.append(f"{a}→{Z.reversed_hex(a)}≠{b}")
    check(f"T2 综卦不变量（{32 - len(COMPLEMENT_PAIRS)} 对互为覆卦）", not bad, bad[:4])
    # 八个「正反相同」的卦：倒过来还是自己，所以它们才被配成错卦对
    pal = ["乾", "坤", "頤", "大過", "坎", "離", "中孚", "小過"]
    not_pal = [p for p in pal if Z.reversed_hex(p) != p]
    check("T2b 八宫正覆相同（乾坤頤大過坎離中孚小過）", not not_pal, not_pal)


def t3():
    bad = []
    for a, b in COMPLEMENT_PAIRS:
        if Z.complement(a) != b:
            bad.append(f"{a}→{Z.complement(a)}≠{b}")
    check("T3 错卦：乾坤/頤大過/坎離/中孚小過 四组全反", not bad, bad)


def t4():
    ok = (Z.NATURE["乾"] == "健" and Z.NATURE["坤"] == "順" and Z.NATURE["震"] == "動"
          and Z.NATURE["巽"] == "入" and Z.NATURE["坎"] == "陷" and Z.NATURE["離"] == "麗"
          and Z.NATURE["艮"] == "止" and Z.NATURE["兌"] == "說")
    check("T4 八卦卦德 = 健順動入陷麗止說（說卦傳）", ok, Z.NATURE)
    ok2 = (Z.ELEMENT["乾"] == "天" and Z.ELEMENT["坤"] == "地" and Z.ELEMENT["震"] == "雷"
           and Z.ELEMENT["巽"] == "風" and Z.ELEMENT["坎"] == "水" and Z.ELEMENT["離"] == "火"
           and Z.ELEMENT["艮"] == "山" and Z.ELEMENT["兌"] == "澤")
    check("T4b 八卦自然象 = 天地雷風水火山澤", ok2, Z.ELEMENT)


def t5():
    r = Z.analyze("既濟")           # 水火既濟：六爻全当位
    check("T5 既濟 六爻全当位（教科书定例）", r["當位數"] == 6, r["當位數"])
    r2 = Z.analyze("未濟")          # 火水未濟：六爻全失位
    check("T5b 未濟 六爻全不当位（教科书定例）", r2["當位數"] == 0, r2["當位數"])
    y2 = [y for y in r["爻詳"] if y["位"] == 2][0]
    check("T5c 二爻得中", y2["得中"] is True)
    y5 = [y for y in r["爻詳"] if y["位"] == 5][0]
    check("T5d 五爻得中", y5["得中"] is True)
    check("T5e 应位配对 初↔四", Z.RESPOND_PAIRS[1] == 4 and Z.RESPOND_PAIRS[4] == 1)


def t6():
    # 乾上九阳极变阴 → 上卦乾(111)变兌(110) → 兌上乾下 = 夬
    check("T6 乾上九变 → 之卦為夬",
          Z.analyze("乾", moving=[6])["之卦"] == "夬",
          Z.analyze("乾", moving=[6])["之卦"])
    r2 = Z.analyze("坤", moving=[1])
    check("T6b 坤初六变 → 之卦為復", r2["之卦"] == "復", r2["之卦"])
    r3 = Z.analyze("蒙", moving=[1, 3])
    check("T6c 多变爻仍产出之卦且不等于本卦",
          bool(r3["之卦"]) and r3["之卦"] != "蒙", r3["之卦"])


def t7():
    missing = [n for n, _, _ in Z.HEXAGRAMS if Z.daxiang(n).startswith("（未找到")]
    check("T7 六十四卦大象辞全部取到", not missing, missing[:6])
    check("T7b 乾大象 = 天行健，君子以自強不息",
          "天行健" in Z.daxiang("乾") and "自強不息" in Z.daxiang("乾"), Z.daxiang("乾"))
    check("T7c 坤大象 = 地勢坤，君子以厚德載物",
          "厚德載物" in Z.daxiang("坤"), Z.daxiang("坤"))
    check("T7d 大象辞与语料同源（屯=雲雷/經綸）",
          "雲雷" in Z.daxiang("屯") and "經綸" in Z.daxiang("屯"), Z.daxiang("屯"))


def t8():
    a = Z.cast(seed=42)
    b = Z.cast(seed=42)
    check("T8 同 seed 起卦完全可复现", a == b, (a, b))
    check("T8b 起卦结果含本卦与六爻", bool(a["本卦"]) and len(a["每爻"]) == 6, a)
    seeds_ok = all(bool(Z.cast(seed=s)["本卦"]) for s in range(30))
    check("T8c 30 个 seed 均能成卦", seeds_ok)


def t9():
    for simp, trad in (("归妹", "歸妹"), ("丰", "豐"), ("兑", "兌"),
                       ("既济", "既濟"), ("谦", "謙")):
        got = Z.norm_name(simp)
        check(f"T9 别名 {simp}→{trad}", got == trad, got)


def t10():
    try:
        Z.analyze("不存在的卦")
        check("T10 未知卦名抛错", False, "未抛错")
    except KeyError:
        check("T10 未知卦名抛 KeyError（不臆造卦象）", True)
    r = Z.daxiang("不存在的卦")
    check("T10b 查不到大象时明确说明而非编造", r.startswith("（未找到"), r)


def t11():
    """承乘（2026-10-09 新增：此前无任何测试，而卡片 Step 3 强制要求判它）。

    传统义：**皆就陰爻對陽爻而言**
      承剛 = 陰爻緊鄰其上為陽（柔承剛，順）
      乘剛 = 陰爻緊鄰其下為陽（柔乘剛，逆）
      陰爻夾在兩陽之間時兩者同時成立
    舊實現在兩處皆反（把陽爻判成乘剛、且上爻永不判乘），本測試即為其回歸測試。
    """
    def cx(name, pos):
        y = Z.analyze(name)["爻詳"][pos - 1]
        return y["爻"], y["相鄰"]

    # 既濟（離下坎上）：初陽 二陰 三陽 / 四陰 五陽 六陰
    check("T11a 既濟二爻陰，上陽下陽 → 承剛／乘剛", cx("既濟", 2) == ("陰", "承剛／乘剛"), cx("既濟", 2))
    check("T11b 既濟四爻陰，上陽下陽 → 承剛／乘剛", cx("既濟", 4) == ("陰", "承剛／乘剛"), cx("既濟", 4))
    check("T11c 既濟上爻陰，下五為陽、無上爻 → 僅乘剛", cx("既濟", 6) == ("陰", "乘剛"), cx("既濟", 6))
    check("T11d 既濟初爻陽 → 不判承乘", cx("既濟", 1)[1] is None, cx("既濟", 1))
    check("T11e 既濟五爻陽 → 不判承乘", cx("既濟", 5)[1] is None, cx("既濟", 5))
    # 屯（震下坎上）：初陽 二陰 三陰 / 四陰 五陽 六陰
    check("T11f 屯六二陰承初九之剛 → 乘剛", cx("屯", 2) == ("陰", "乘剛"), cx("屯", 2))
    check("T11g 屯六三陰，上下皆陰 → 不判承乘", cx("屯", 3)[1] is None, cx("屯", 3))
    # 乾六爻皆陽 → 全無承乘（純陽之卦不存在柔對剛的關係）
    yang_none = all(Z.analyze("乾")["爻詳"][i - 1]["相鄰"] is None for i in range(1, 7))
    check("T11h 乾卦純陽 → 六爻皆無承乘", yang_none)


def t12():
    """多变爻之卦：卡片 2026-10-09 才补规则，引擎须先能算。"""
    # 乾(1,1,1,1,1,1) 一三五变 → (0,1,0,1,0,1) = 坎下離上 = 未濟（六爻全变才是坤）
    check("T12a 乾一三五爻变 → 之卦為未濟", Z.analyze("乾", [1, 3, 5])["之卦"] == "未濟",
          Z.analyze("乾", [1, 3, 5])["之卦"])
    check("T12a2 乾六爻全变 → 之卦為坤（错卦）", Z.analyze("乾", [1, 2, 3, 4, 5, 6])["之卦"] == "坤",
          Z.analyze("乾", [1, 2, 3, 4, 5, 6])["之卦"])
    check("T12b 既濟初爻动 → 之卦為蹇", Z.analyze("既濟", [1])["之卦"] == "蹇",
          Z.analyze("既濟", [1])["之卦"])
    check("T12c 多变爻时變爻列表完整回传", Z.analyze("蒙", [1, 6])["變爻"] == [1, 6],
          Z.analyze("蒙", [1, 6])["變爻"])
    check("T12d 無变爻時之卦為 None（不得硬造趨勢）", Z.analyze("乾")["之卦"] is None)
    # 贞悔相参要一次拿到两张大象辞（2026-10-09：第二轮答题撞到「只有之卦名、拿不到之卦大象」）
    r = Z.analyze("既濟", [1, 3])
    check("T12e 之卦大象辞一并给出（贞悔相参不再逼用户二次取数）",
          r["之卦大象"] == Z.daxiang(r["之卦"]), r.get("之卦大象"))
    check("T12f 无变爻时之卦大象为 None（不臆造）",
          Z.analyze("乾")["之卦大象"] is None)
    check("T12g 之卦大象非占位串", not (r["之卦大象"] or "").startswith("（未找到"), r["之卦大象"])


def t13():
    """references/daxiang.md 与引擎内嵌表必须同源。

    为什么必须有：答题 Agent 指出「卡本体不含大象全表，Step 2/3 无法闭环」。
    查大象有两条路（references 文件 / 引擎输出），两条路给出不同答案就等于
    卡片自己打自己。故用测试把二者钉死为同一来源。
    """
    ref = Path(_HERE).parent / "references" / "daxiang.md"
    if not ref.exists():
        check("T13 references/daxiang.md 存在", False, str(ref))
        return
    check("T13a references/daxiang.md 存在", True)
    miss = [nm for nm, _, _ in Z.HEXAGRAMS
            if Z.daxiang(nm).startswith("（未找到")]
    check(f"T13b 六十四卦大象辞在 references 中全部取到（缺 {len(miss)}）",
          not miss, miss[:5])
    # 引擎读的就是该文件，断言其卦名条目数 == 64。
    # ⚠️ 不能按「含：」计数——文件头的 HTML 注释里也有「：」，会把 64 数成 65
    # （2026-10-09 实测踩到）。只认「行首是已知卦名 + ：」的行。
    names = {nm for nm, _, _ in Z.HEXAGRAMS}
    rows = [l for l in ref.read_text(encoding="utf-8").splitlines()
            if "：" in l and l.split("：")[0].strip() in names]
    check(f"T13c references 卦名条目数 == 64（实测 {len(rows)}）", len(rows) == 64, len(rows))


for fn in (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13):
    fn()

print()
if FAILED:
    print(f"❌ {len(FAILED)} 项未通过：" + "、".join(FAILED))
    sys.exit(1)
print("ALL PASS")
