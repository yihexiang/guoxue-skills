#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zhouyi.py — 《周易》六爻结构与《易传》十翼的结构化分析引擎。

**它做的**：给定一个卦（或掷钱币起卦），输出可机械复算的结构分析——
上下卦与卦德、每一爻的当位/中/应/承乘、变爻与之卦、以及大象辞的行动纲领。

**它不做的**：不断吉凶、不算命、不给预测断言。《易传》本身就把《易》从卜筮之书
转成了观象玩辞、穷理尽性的义理之学（繫辭上第二章"君子居則觀其象而玩其辭"），
本引擎只实现结构，不越界宣称能预测未来。

数据来源：
  · 卦名序列 / 大象辞 → 维基文库《易傳·大象傳》原文（本机 corpus/anchored/src-07-daxiang.md）
  · 八卦卦德（健順動入陷麗止說）→ 《說卦傳》第七章
零依赖、不联网。命令行：
    python3 zhouyi.py 蒙
    python3 zhouyi.py 蒙 --moving 1,3
    python3 zhouyi.py --cast --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# ---------------------------------------------------------------- 八卦
YANG, YIN = 1, 0
# 三爻由下而上：(初, 中, 上)
# 三爻由下而上。☳震 是「陽爻在初」（雷动于下），☶艮 是「陽爻在上」（止于上）——
# 这两者最容易记反，一旦记反，综卦/错卦/当位全部错位。
# 本表由 tests/test_engine.py 的综卦与错卦不变量把关，不是靠印象。
TRIGRAM = {
    "乾": (1, 1, 1), "兌": (1, 1, 0), "離": (1, 0, 1), "震": (1, 0, 0),
    "巽": (0, 1, 1), "坎": (0, 1, 0), "艮": (0, 0, 1), "坤": (0, 0, 0),
}
# 卦德：出自《說卦傳》第七章「乾，健也。坤，順也。震，動也。巽，入也。坎，陷也。離，麗也。艮，止也。兌，說也。」
NATURE = {
    "乾": "健", "坤": "順", "震": "動", "巽": "入",
    "坎": "陷", "離": "麗", "艮": "止", "兌": "說",
}
ELEMENT = {
    "乾": "天", "坤": "地", "震": "雷", "巽": "風",
    "坎": "水", "離": "火", "艮": "山", "兌": "澤",
}

# ---------------------------------------------------------------- 六十四卦
# (卦名, 上卦, 下卦)，按文王卦序。此表由 `tests/test_engine.py` 的结构自洽性
# 测试把关——尤其是「非乾坤頤大過坎離中孚小過」各组卦序对必须互为综卦（六爻倒转）。
HEXAGRAMS = [
    ("乾", "乾", "乾"), ("坤", "坤", "坤"), ("屯", "坎", "震"), ("蒙", "艮", "坎"),
    ("需", "坎", "乾"), ("訟", "乾", "坎"), ("師", "坤", "坎"), ("比", "坎", "坤"),
    ("小畜", "巽", "乾"), ("履", "乾", "兌"), ("泰", "坤", "乾"), ("否", "乾", "坤"),
    ("同人", "乾", "離"), ("大有", "離", "乾"), ("謙", "坤", "艮"), ("豫", "震", "坤"),
    ("隨", "兌", "震"), ("蠱", "艮", "巽"), ("臨", "坤", "兌"), ("觀", "巽", "坤"),
    ("噬嗑", "離", "震"), ("賁", "艮", "離"), ("剝", "艮", "坤"), ("復", "坤", "震"),
    ("无妄", "乾", "震"), ("大畜", "艮", "乾"), ("頤", "艮", "震"), ("大過", "兌", "巽"),
    ("坎", "坎", "坎"), ("離", "離", "離"), ("咸", "兌", "艮"), ("恒", "震", "巽"),
    ("遯", "乾", "艮"), ("大壯", "震", "乾"), ("晉", "離", "坤"), ("明夷", "坤", "離"),
    ("家人", "巽", "離"), ("睽", "離", "兌"), ("蹇", "坎", "艮"), ("解", "震", "坎"),
    ("損", "艮", "兌"), ("益", "巽", "震"), ("夬", "兌", "乾"), ("姤", "乾", "巽"),
    ("萃", "兌", "坤"), ("升", "坤", "巽"), ("困", "兌", "坎"), ("井", "坎", "巽"),
    ("革", "兌", "離"), ("鼎", "離", "巽"), ("震", "震", "震"), ("艮", "艮", "艮"),
    ("漸", "巽", "艮"), ("歸妹", "震", "兌"), ("豐", "震", "離"), ("旅", "離", "艮"),
    ("巽", "巽", "巽"), ("兌", "兌", "兌"), ("渙", "巽", "坎"), ("節", "坎", "兌"),
    ("中孚", "巽", "兌"), ("小過", "震", "艮"), ("既濟", "坎", "離"), ("未濟", "離", "坎"),
]

# 简体写法容差：中国大陆用户输入的卦名往往是简体，而底稿是繁体。
ALIAS = {
    "讼": "訟", "师": "師", "谦": "謙", "随": "隨", "蛊": "蠱", "临": "臨",
    "观": "觀", "贲": "賁", "剥": "剝", "复": "復", "颐": "頤", "过": "過",
    "离": "離", "遁": "遯", "晋": "晉", "损": "損", "归妹": "歸妹", "丰": "豐",
    "兑": "兌", "涣": "渙", "节": "節", "济": "濟", "壮": "壯", "恆": "恒",
    # 「無妄」是本卦最常见的写法（繁体底稿即作「无妄」，但多数据源作「無妄」）
    "無": "无",
}

BY_NAME = {n: (n, up, low) for n, up, low in HEXAGRAMS}
ORDER = {n: i + 1 for i, (n, _, _) in enumerate(HEXAGRAMS)}


def norm_name(name: str) -> str:
    """把各种写法归一到本表的卦名。找不到就原样返回（让上层抛 KeyError）。"""
    s = name.strip()
    if s in BY_NAME:
        return s
    for simp, trad in ALIAS.items():
        s = s.replace(simp, trad)
    return s if s in BY_NAME else name.strip()


def lines_of(name: str) -> tuple[int, ...]:
    """返回六爻，**由下而上**（初爻在前）。"""
    n = norm_name(name)
    if n not in BY_NAME:
        raise KeyError(f"未知卦名：{name}（请用六十四卦名，如 蒙 / 蒙卦）")
    _, up, low = BY_NAME[n]
    return TRIGRAM[low] + TRIGRAM[up]


def line_word(v: int) -> str:
    return "陽" if v == YANG else "陰"


def opposite(v: int) -> int:
    return YIN if v == YANG else YANG


# ---------------------------------------------------------------- 结构关系
def dang_wei(v: int, pos: int) -> bool:
    """当位：阳爻居阳位（初/三/五），阴爻居阴位（二/四/上）。位序从 1 起，由下而上。"""
    yang_pos = pos % 2 == 1
    return (v == YANG) == yang_pos


def is_zhong(pos: int) -> bool:
    """得中：二爻、五爻分居下卦与上卦之中。"""
    return pos in (2, 5)


# 应：初↔四、二↔五、三↔上，阴阳相配为「有应」，同为阴阳则「无应」
RESPOND_PAIRS = {1: 4, 2: 5, 3: 6, 4: 1, 5: 2, 6: 3}


def analyze(name: str, moving: list[int] | None = None) -> dict:
    """结构分析。moving 为变爻位（1-6，由下而上），为空则只看本卦。"""
    n = norm_name(name)
    if n not in BY_NAME:
        raise KeyError(f"未知卦名：{name}")
    _, up, low = BY_NAME[n]
    lines = list(lines_of(n))
    moving = moving or []

    yaos = []
    for i, v in enumerate(lines, start=1):
        other = RESPOND_PAIRS[i]
        pair_v = lines[other - 1]
        # 承乘（传统义，**皆就陰爻對陽爻而言**，2026-10-09 修正）：
        #   承剛 = 陰爻緊鄰其上的是陽爻（柔承剛，順）
        #   乘剛 = 陰爻緊鄰其下的是陽爻（柔乘剛，逆）
        #   兩者可同時成立（陰爻夾在兩陽之間），故用列表而非單值。
        # 舊實現在兩處皆反：把「本爻陽且上一爻陰」判成乘剛，且 i==6 時永不判乘。
        cheng: list[str] = []
        if v == YIN:
            if i < 6 and lines[i] == YANG:      # 上一爻（位序 i+1）
                cheng.append("承剛")
            if i > 1 and lines[i - 2] == YANG:  # 下一爻（位序 i-1）
                cheng.append("乘剛")
        yaos.append({
            "位": i,
            "爻": line_word(v),
            "當位": dang_wei(v, i),
            "得中": is_zhong(i),
            "應位": other,
            "有應": pair_v != v,
            "相鄰": "／".join(cheng) if cheng else None,
            "變爻": i in moving,
        })

    changed = None
    if moving:
        nl = lines[:]
        for m in moving:
            if 1 <= m <= 6:
                nl[m - 1] = opposite(nl[m - 1])
        changed = name_of(tuple(nl))

    return {
        "卦名": n,
        "卦序": ORDER[n],
        "上卦": up, "下卦": low,
        "上卦象": ELEMENT[up], "下卦象": ELEMENT[low],
        "上卦德": NATURE[up], "下卦德": NATURE[low],
        "自然象": f"{ELEMENT[up]}{ELEMENT[low]}",
        "六爻": " ".join("——" if v else "-  -" for v in reversed(lines)),
        "當位數": sum(1 for y in yaos if y["當位"]),
        "有應數": sum(1 for y in yaos if y["有應"]),
        "爻詳": yaos,
        "變爻": moving or [],
        "之卦": changed,
        "大象": daxiang(n),
        # 之卦的大象辞一并给出（2026-10-09：答题 Agent 指出多变爻「贞悔相参」
        # 要拿之卦大象辞，但输出只有之卦名，逼用户再跑一次命令 → 步骤达不成）。
        # 取不到时返回 None，**不臆造**，与 daxiang() 的「查不到就明说」同一纪律。
        "之卦大象": (daxiang(changed) if changed else None),
    }


def name_of(lines6: tuple[int, ...] | list[int]) -> str | None:
    """六爻反查卦名。"""
    key = tuple(lines6)
    for nm, up, low in HEXAGRAMS:
        if TRIGRAM[low] + TRIGRAM[up] == key:
            return nm
    return None


def complement(name: str) -> str | None:
    """错卦（旁通）：六爻全反。"""
    n = norm_name(name)
    return name_of([opposite(v) for v in lines_of(n)])


def reversed_hex(name: str) -> str | None:
    """综卦（覆卦）：六爻倒转。"""
    n = norm_name(name)
    return name_of(list(reversed(lines_of(n))))


# ---------------------------------------------------------------- 大象辞
_DAXIANG_CACHE: dict[str, str] | None = None


def daxiang(name: str) -> str:
    """取大象辞（《大象傳》原文：某自然象 + 君子以…）。

    语料随技能附在 references/daxiang.md；找不到时明确返回说明，
    **绝不臆造**——这是本项目反复强调的边界：查不到要明说。
    """
    global _DAXIANG_CACHE
    n = norm_name(name)
    if _DAXIANG_CACHE is None:
        _DAXIANG_CACHE = {}
        for cand in (Path(__file__).resolve().parent.parent / "references" / "daxiang.md",
                     Path(__file__).resolve().parent.parent.parent / "corpus"
                     / "anchored" / "src-07-daxiang.md"):
            if not cand.exists():
                continue
            for line in cand.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or "：" not in line and ":" not in line:
                    continue
                sep = "：" if "：" in line else ":"
                head, _, tail = line.partition(sep)
                head = head.strip().lstrip("-*#").strip()
                if head:
                    _DAXIANG_CACHE[head] = tail.strip()
            break
    if n in _DAXIANG_CACHE:
        return _DAXIANG_CACHE[n]
    for k, v in _DAXIANG_CACHE.items():
        if norm_name(k) == n:
            return v
    return "（未找到大象辞）"


# ---------------------------------------------------------------- 三份 references 查询
# 序卦相承 / 彖傳实例 / 文言逐爻。三份文件均由 tools/build_refs.py 从语料生成，
# 此处只做查表，**查不到就明说，绝不臆造**——与 daxiang() 同一纪律。
def _ref(name: str) -> Path | None:
    for base in (Path(__file__).resolve().parent.parent / "references",
                 Path(__file__).resolve().parent.parent.parent / "dist"
                 / "zhouyi-yili" / "references"):
        p = base / name
        if p.exists():
            return p
    return None


def _load_rows(fname: str) -> list[list[str]] | None:
    """按「｜」切分的数据行；注释与标题行跳过。文件不存在返回 None（区分于空表）。"""
    p = _ref(fname)
    if p is None:
        return None
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ">", "<!--")):
            continue
        if "｜" not in s:
            continue
        rows.append([c.strip() for c in s.split("｜")])
    return rows


def chain(name: str) -> dict:
    """序卦相承：这一卦从哪来、往哪去、序卦给的理由是什么。

    《序卦傳》讲的就是「卦与卦之间为什么这么排」——每一卦都是上一卦的必然后果。
    解完一卦被追问「下一步呢」时查这里，不要凭印象编因果。
    """
    n = norm_name(name)
    rows = _load_rows("xugua-chain.md")
    if rows is None:
        return {"卦名": n, "承自": None, "承至": None, "錯誤": "未找到 references/xugua-chain.md"}
    for r in rows:
        if len(r) >= 6 and norm_name(r[0]) == n:
            return {
                "卦名": n, "卦序": ORDER.get(n),
                "承自": r[2].replace("承自 ", "").strip(),
                "承至": r[3].replace("承至 ", "").strip(),
                "何以承自": r[4],
                "何以承至": r[5],
            }
    return {"卦名": n, "承自": None, "承至": None, "錯誤": f"序卦链条中无此卦：{name}"}


def tuan(name: str) -> dict:
    """彖傳实例：该卦彖辞原文 + 术语标注 + 引擎实测，供「十翼自己怎么解释这套结构」。

    价值在于**对照**：左边是《彖傳》的判断，右边是引擎算出的结构事实。
    两者一致时，结论有原文先例撑着；不一致时，以引擎为准并注明原文措辞。
    """
    n = norm_name(name)
    rows = _load_rows("tuan-cases.md")
    if rows is None:
        return {"卦名": n, "彖辭": None, "錯誤": "未找到 references/tuan-cases.md"}
    for r in rows:
        if len(r) >= 6 and norm_name(r[0]) == n:
            a = analyze(n)
            return {
                "卦名": n, "段號": r[2],
                "術語": [t for t in r[3].split("、") if t and t != "—"],
                "引擎實測": r[4],
                "彖辭": r[5],
                "當位數": a["當位數"], "有應數": a["有應數"],
            }
    return {"卦名": n, "彖辭": None, "錯誤": f"彖傳中无此卦：{name}"}


def wenyan(name: str, line: str | None = None) -> dict:
    """文言逐爻义理。**语料只覆盖乾、坤两卦**——《文言傳》本就只解乾坤。

    其余 62 卦一律返回「語料未載」，不拿乾坤的义理去套别的卦。
    """
    n = norm_name(name)
    if n not in ("乾", "坤"):
        return {"卦名": n, "逐爻": [], "註": "語料未載：《文言傳》只解乾、坤兩卦，"
                                              "其餘 62 卦不得援引此處義理類推"}
    rows = _load_rows("wenyan-lines.md")
    if rows is None:
        return {"卦名": n, "逐爻": [], "錯誤": "未找到 references/wenyan-lines.md"}
    out = []
    for r in rows:
        if len(r) >= 4 and norm_name(r[0].split("·")[0]) == n:
            yao = r[0].split("·")[1]
            if line and yao != line:
                continue
            out.append({"爻": yao, "段號": r[1], "爻辭": r[2], "義理": r[3]})
    return {"卦名": n, "逐爻": out}


# ---------------------------------------------------------------- 起卦
COIN_NAMES = {6: "老陰（變）", 7: "少陽", 8: "少陰", 9: "老陽（變）"}


def cast(seed: int | None = None) -> dict:
    """金钱卦起卦：三枚硬币掷六次，自下而上成卦。

    定 seed 后完全可复现，便于核对；不传 seed 则用随机。
    """
    rng = random.Random(seed)
    rows = []
    for _ in range(6):
        # 每枚字为 2、背为 3，三枚之和只可能是 6/7/8/9
        s = sum(rng.choice((2, 3)) for _ in range(3))
        rows.append(s)
    base = [YANG if s in (7, 9) else YIN for s in rows]
    moving = [i for i, s in enumerate(rows, start=1) if s in (6, 9)]
    name = name_of(base)
    return {
        "seed": seed, "每爻": [COIN_NAMES[s] for s in rows],
        "本卦": name, "變爻": moving, "之卦": name_of(
            [opposite(v) if i in moving else v for i, v in enumerate(base, start=1)]
        ) if name else None,
    }


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="周易六爻结构 + 易传义理分析")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--moving", help="变爻位，逗号分隔，如 1,3")
    ap.add_argument("--cast", action="store_true")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--chain", action="store_true", help="查序卦相承：承自哪卦、承至哪卦、凭什么")
    ap.add_argument("--tuan", action="store_true", help="查彖傳实例：原文 + 术语 + 引擎实测对照")
    ap.add_argument("--wenyan", action="store_true", help="查文言逐爻义理（**仅乾、坤两卦有**）")
    ap.add_argument("--line", help="配合 --wenyan 指定某一爻，如 初九 / 六二")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.cast or not a.name:
        r = cast(a.seed)
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
            return 0
        print("金钱卦起卦" + (f"（seed={a.seed}）" if a.seed is not None else ""))
        for i, w in enumerate(r["每爻"], 1):
            print(f"  第{i}爻：{w}")
        print(f"本卦：{r['本卦']}   變爻：{r['變爻'] or '無'}   之卦：{r['之卦']}")
        return 0

    try:
        n0 = norm_name(a.name)
        if n0 not in BY_NAME:
            raise KeyError(f"未知卦名：{a.name}（请用六十四卦名，如 蒙 / 蒙卦）")
    except KeyError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1

    if a.chain:
        c = chain(a.name)
        if a.json:
            print(json.dumps(c, ensure_ascii=False, indent=2))
            return 0
        if c.get("錯誤"):
            print(f"✗ {c['錯誤']}", file=sys.stderr)
            return 1
        print(f"══ 序卦相承 · {c['卦名']}（第{c['卦序']}卦）══")
        print(f"  承自：{c['承自']}")
        print(f"    何以承自 → {c['何以承自']}")
        print(f"  承至：{c['承至']}")
        print(f"    何以承至 → {c['何以承至']}")
        return 0

    if a.tuan:
        t = tuan(a.name)
        if a.json:
            print(json.dumps(t, ensure_ascii=False, indent=2))
            return 0
        if t.get("錯誤"):
            print(f"✗ {t['錯誤']}", file=sys.stderr)
            return 1
        print(f"══ 彖傳 · {t['卦名']}（{t['段號']}）══")
        print(f"  術語：{'、'.join(t['術語']) or '—'}")
        print(f"  引擎實測：{t['引擎實測']}")
        print(f"  彖辭：{t['彖辭']}")
        return 0

    if a.wenyan:
        w = wenyan(a.name, a.line)
        if a.json:
            print(json.dumps(w, ensure_ascii=False, indent=2))
            return 0
        if w.get("錯誤"):
            print(f"✗ {w['錯誤']}", file=sys.stderr)
            return 1
        if not w["逐爻"]:
            print(f"══ 文言 · {w['卦名']} ══\n  {w.get('註') or '查無此爻'}")
            return 0
        print(f"══ 文言 · {w['卦名']} ══")
        for y in w["逐爻"]:
            print(f"  【{y['爻']}】（{y['段號']}）爻辭：{y['爻辭']}")
            print(f"      義理：{y['義理']}")
        return 0

    moving = [int(x) for x in a.moving.split(",")] if a.moving else []
    try:
        res = analyze(a.name, moving)
    except KeyError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"══ {res['卦名']}（第{res['卦序']}卦）· {res['自然象']} ══")
    print(f"上卦 {res['上卦']}（{res['上卦象']}·{res['上卦德']}）／"
          f"下卦 {res['下卦']}（{res['下卦象']}·{res['下卦德']}）")
    print(f"六爻（自上而下）：{res['六爻']}")
    for y in res["爻詳"]:
        flag = " ★變" if y["變爻"] else ""
        print(f"  {y['位']}爻 {y['爻']}：當位={y['當位']} 得中={y['得中']} "
              f"應({y['應位']}爻)={y['有應']}"
              + (f" {y['相鄰']}" if y["相鄰"] else "") + flag)
    pairs = sum(1 for i in (1, 2, 3)
                if next(y for y in res["爻詳"] if y["位"] == i)["有應"])
    print(f"當位 {res['當位數']}/6　有應 {pairs}/3 組")
    print(f"大象：{res['大象']}")
    if res["之卦"]:
        print(f"之卦：{res['之卦']}")
        # 多变爻「贞悔相参」要的就是这两张大象辞对着读，一次给全，不逼用户再跑一次
        if res["之卦大象"]:
            print(f"之卦大象：{res['之卦大象']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
