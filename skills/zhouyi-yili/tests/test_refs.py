#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_refs.py — 三份 references（序卦相承 / 彖傳实例 / 文言逐爻）的自检。

**本文件最有价值的不是「文件存在」，而是 R4 的交叉验证**：
拿《彖傳》原文里白纸黑字写下的结构断言，去核对引擎算出来的结构。
两边独立（一边是两千年前的原文，一边是本引擎的机械复算），
对上了就同时证明了两件事：卦序表没错，且这些爻位术语的含义没被我理解反。

这与 test_engine.py 的「自证」不同——那是拿我的表验我的表，这是拿原文验我的表。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import zhouyi as Z  # noqa: E402

REF = HERE.parent / "references"

_OK = 0
_BAD = 0


def check(label: str, cond: bool, got=None) -> None:
    global _OK, _BAD
    if cond:
        _OK += 1
        print(f"  ✓ {label}")
    else:
        _BAD += 1
        print(f"  ✗ {label}   ← 实测：{got!r}")


def rows_of(fname: str) -> list[list[str]]:
    out = []
    for line in (REF / fname).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ">", "<!--")) or "｜" not in s:
            continue
        out.append([c.strip() for c in s.split("｜")])
    return out


# ---------------------------------------------------------------- R1 · 序卦链条
def r1_xugua() -> None:
    print("\n[R1] 序卦相承链条")
    rows = rows_of("xugua-chain.md")
    # 空集守卫：文件存在但为空必须判失败，不能因为"没东西可查"就绿
    check("R1a 链条非空（空表不得判 PASS）", len(rows) > 0, len(rows))
    check(f"R1b 链条 64 卦齐全（实测 {len(rows)}）", len(rows) == 64, len(rows))

    names = [Z.norm_name(r[0]) for r in rows]
    expect = [n for n, _, _ in Z.HEXAGRAMS]
    check("R1c 链条顺序与文王卦序逐一对齐", names == expect,
          next((f"{i}:{a}!={b}" for i, (a, b) in enumerate(zip(names, expect)) if a != b), None))

    # 承自/承至 的互反性：A 承至 B ⟺ B 承自 A
    pair_bad = []
    for i, r in enumerate(rows):
        prev = r[2].replace("承自 ", "").strip()
        nxt = r[3].replace("承至 ", "").strip()
        if i > 0 and prev != names[i - 1]:
            pair_bad.append(f"{names[i]}.承自={prev}!={names[i-1]}")
        if i + 1 < len(rows) and nxt != names[i + 1]:
            pair_bad.append(f"{names[i]}.承至={nxt}!={names[i+1]}")
    check("R1d 承自/承至 与链条互反一致", not pair_bad, pair_bad[:3])

    check("R1e 乾为链首（承自为空）", rows[0][2].replace("承自 ", "").strip() == "—",
          rows[0][2])
    check("R1f 未濟为链尾（承至为空，序卦曰終焉）",
          rows[-1][3].replace("承至 ", "").strip() == "—", rows[-1][3])

    # 每卦都必须有「何以承至」的理由原文（终卦除外），且理由里要真有卦名或说明
    missing = [r[0] for r in rows[:-1] if len(r) < 6 or not r[5]]
    check("R1g 非终卦皆有「何以承至」原文", not missing, missing[:3])

    # 三卦不出卦名的已知事实（乾/坤/咸）——这是实测结论，不是假设
    for nm in ("乾", "坤", "咸"):
        c = Z.chain(nm)
        check(f"R1h {nm} 有承继说明（序卦未出卦名，须显式标注来源）",
              "未出卦名" in (c.get("何以承自") or "") + (c.get("何以承至") or ""),
              c.get("何以承自"))
    check("R1i 序卦全篇确无「咸」字（该项为实测事实，若将来语料补全须改此断言）",
          "咸" not in (REF.parent.parent.parent / "corpus" / "anchored"
                       / "src-04-xugua.md").read_text(encoding="utf-8")
          if (REF.parent.parent.parent / "corpus" / "anchored"
              / "src-04-xugua.md").exists() else True)


# ---------------------------------------------------------------- R2 · 彖傳实例库
def r2_tuan() -> None:
    print("\n[R2] 彖傳实例库")
    rows = rows_of("tuan-cases.md")
    check("R2a 实例库非空（空表不得判 PASS）", len(rows) > 0, len(rows))
    check(f"R2b 64 卦一卦一条（实测 {len(rows)}）", len(rows) == 64, len(rows))

    bad = []
    for r in rows:
        nm = Z.norm_name(r[0])
        if nm not in Z.BY_NAME:
            bad.append(f"卦名未知 {r[0]}")
            continue
        if int(r[1]) != Z.ORDER[nm]:
            bad.append(f"{nm} 卦序 {r[1]} != {Z.ORDER[nm]}")
        if not r[5]:
            bad.append(f"{nm} 彖辭为空")
    check("R2c 卦名/卦序/彖辞齐备且一致", not bad, bad[:3])

    # 每条彖辞都必须能在语料里逐字找到（防手抄走样）
    src = (REF.parent.parent.parent / "corpus" / "anchored" / "src-08-tuan.md")
    if src.exists():
        corpus = src.read_text(encoding="utf-8").replace("\n", "")
        miss = [r[0] for r in rows if r[5][:12] not in corpus]
        check("R2d 64 条彖辞逐字见于语料（防手抄走样）", not miss, miss[:3])

    # 术语标注守恒：HARD 术语互斥（不得同时标「當位」与「不當位」）
    # 注意：必须按「、」切成独立项再比——直接子串判断会被「不當位」里的「當位」骗到
    both = []
    for r in rows:
        items = [t for t in r[3].split("、") if t]
        if "當位" in items and any(t in items for t in ("不當位", "位不當")):
            both.append((r[0], items))
    check("R2e 术语标注互斥（不當位 时不重复标 當位）", not both, both[:3])


# ---------------------------------------------------------------- R3 · 文言逐爻
def r3_wenyan() -> None:
    print("\n[R3] 文言逐爻义理")
    rows = rows_of("wenyan-lines.md")
    check("R3a 逐爻表非空（空表不得判 PASS）", len(rows) > 0, len(rows))
    check(f"R3b 乾坤各六爻 = 12 条（实测 {len(rows)}）", len(rows) == 12, len(rows))

    gua = sorted({r[0].split("·")[0] for r in rows})
    check("R3c 只覆盖乾、坤两卦（其余 62 卦语料本就未载）", gua == ["乾", "坤"], gua)

    for g in ("乾", "坤"):
        yaos = [r[0].split("·")[1] for r in rows if r[0].startswith(g)]
        expect = ["初九", "九二", "九三", "九四", "九五", "上九"] if g == "乾" \
            else ["初六", "六二", "六三", "六四", "六五", "上六"]
        check(f"R3d {g} 六爻齐全且次序正确", yaos == expect, yaos)

    # 不臆造：其余卦必须明确说明未载
    for g in ("屯", "蒙", "既濟"):
        w = Z.wenyan(g)
        check(f"R3e {g} 返回語料未載（不拿乾坤义理套别的卦）",
              w["逐爻"] == [] and "未載" in w.get("註", ""), w)


# ---------------------------------------------------------------- R4 · 交叉验证（本文件核心）
def r4_cross() -> None:
    """拿《彖傳》原文的结构断言核对引擎计算结果。两边独立，对上才是真证据。"""
    print("\n[R4] 彖傳原文 ⟷ 引擎实测 交叉验证")
    yao = lambda r, i: next(y for y in r["爻詳"] if y["位"] == i)  # noqa: E731

    # 既濟彖「剛柔正而位當也」→ 六爻全当位
    r = Z.analyze("既濟")
    check("R4a 既濟彖『剛柔正而位當也』→ 當位 6/6", r["當位數"] == 6, r["當位數"])
    check("R4a' 既濟彖『初吉，柔得中也』→ 六二 得中",
          yao(r, 2)["得中"] and r["爻詳"][1]["爻"] == "陰")

    # 未濟彖「雖不當位，剛柔應也」→ 全不当位但全有应
    r = Z.analyze("未濟")
    check("R4b 未濟彖『雖不當位』→ 當位 0/6", r["當位數"] == 0, r["當位數"])
    check("R4b' 未濟彖『剛柔應也』→ 三组皆应",
          all(yao(r, i)["有應"] for i in (1, 2, 3)),
          [yao(r, i)["有應"] for i in (1, 2, 3)])

    # 噬嗑彖「柔得中而上行，雖不當位」→ 六五不当位但得中
    r = Z.analyze("噬嗑")
    check("R4c 噬嗑彖『雖不當位』→ 六五 不當位", not yao(r, 5)["當位"], yao(r, 5))
    check("R4c' 噬嗑彖『柔得中』→ 六五 得中且为陰", yao(r, 5)["得中"] and r["爻詳"][4]["爻"] == "陰")

    # 遯彖「剛當位而應」→ 存在陽爻當位且有應（九五）
    r = Z.analyze("遯")
    hit = [y["位"] for y in r["爻詳"] if y["爻"] == "陽" and y["當位"] and y["有應"]]
    check("R4d 遯彖『剛當位而應』→ 存在當位且有應之陽爻（九五）", 5 in hit, hit)

    # 蒙彖「以剛中也」→ 九二陽爻居中；「志應也」→ 二五相应
    r = Z.analyze("蒙")
    check("R4e 蒙彖『以剛中也』→ 九二 陽爻得中",
          r["爻詳"][1]["爻"] == "陽" and yao(r, 2)["得中"], r["爻詳"][1])
    check("R4e' 蒙彖『志應也』→ 二五有應", yao(r, 2)["有應"])

    # 同人彖「柔得位得中，而應乎乾」→ 六二陰爻、得位、得中、應五
    r = Z.analyze("同人")
    y2 = yao(r, 2)
    check("R4f 同人彖『柔得位得中而應乎乾』→ 六二 陰·當位·得中·有應",
          r["爻詳"][1]["爻"] == "陰" and y2["當位"] and y2["得中"] and y2["有應"], y2)

    # 歸妹彖「柔乘剛也」→ 存在乘剛（陰爻居陽爻之上）
    r = Z.analyze("歸妹")
    cheng = [y["位"] for y in r["爻詳"] if y["相鄰"] and "乘剛" in y["相鄰"]]
    check("R4g 歸妹彖『柔乘剛也』→ 存在乘剛", len(cheng) > 0, cheng)


# ---------------------------------------------------------------- R5 · 查询接口不臆造
def r5_api() -> None:
    print("\n[R5] 查询接口不臆造")
    check("R5a chain() 未知卦返回錯誤而非 None",
          "錯誤" in Z.chain("不是卦"), Z.chain("不是卦"))
    check("R5b tuan() 未知卦返回錯誤", "錯誤" in Z.tuan("不是卦"))
    check("R5c wenyan() 非乾坤一律語料未載",
          Z.wenyan("蒙")["逐爻"] == [], Z.wenyan("蒙"))
    check("R5d chain() 返回承自与承至两项",
          Z.chain("蒙")["承自"] == "屯" and Z.chain("蒙")["承至"] == "需", Z.chain("蒙"))
    check("R5e tuan() 含彖辭原文", "利用獄也" in (Z.tuan("噬嗑")["彖辭"] or ""))
    check("R5f wenyan(乾, 上九) 取到亢龍有悔",
          Z.wenyan("乾", "上九")["逐爻"][0]["爻辭"] == "亢龍有悔",
          Z.wenyan("乾", "上九")["逐爻"])

    # 简体输入也要能查到（用户不会特意打繁体）；既濟前卦是小過、后卦是未濟
    c = Z.chain("既济")
    check("R5g 简体卦名可查询且归一正确",
          c["卦名"] == "既濟" and c["承自"] == "小過" and c["承至"] == "未濟", c)


def main() -> int:
    print("══ zhouyi-yili · references 自检 ══")
    for fn in (r1_xugua, r2_tuan, r3_wenyan, r4_cross, r5_api):
        fn()
    print(f"\n{'ALL PASS' if _BAD == 0 else 'FAILED'} — {_OK} 项通过，{_BAD} 项失败")
    return 1 if _BAD else 0


if __name__ == "__main__":
    sys.exit(main())
