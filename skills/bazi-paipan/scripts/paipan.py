#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八字（四柱）排盘引擎 · 零依赖纯 Python.

设计原则：
1. 全部历算数据内置（`_jieqi_data.py`），不联网、不依赖第三方库。
2. 每一步都可被独立验证：见同目录 `tests/`。
3. 有歧义处（子时换日、真太阳时、藏干主次、起运取整）一律**显式参数化**，
   不替用户做选择，默认值写在 `DEFAULTS` 里并在输出中回显。
"""
import datetime as dt
import math
import sys
from functools import lru_cache

from _jieqi_data import JIEQI_DATA, JIEQI_ORDER

TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
# 地支方位：用于在第六层做「经线订正」之外的用途
ZHI_INDEX = {z: i for i, z in enumerate(DI_ZHI)}
GAN_INDEX = {g: i for i, g in enumerate(TIAN_GAN)}

JIAZI = [TIAN_GAN[i % 10] + DI_ZHI[i % 12] for i in range(60)]

# 换月之「节」：12 个节 -> 12 个月支。子平法以「节」分月令，不以农历初一。
JIE_TO_ZHI = [
    ("立春", "寅"), ("惊蛰", "卯"), ("清明", "辰"), ("立夏", "巳"),
    ("芒种", "午"), ("小暑", "未"), ("立秋", "申"), ("白露", "酉"),
    ("寒露", "戌"), ("立冬", "亥"), ("大雪", "子"), ("小寒", "丑"),
]

# 五虎遁：年干 -> 寅月天干
WU_HU_DUN = {"甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚",
             "辛": "庚", "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲"}
# 五鼠遁：日干 -> 子时天干
WU_SHU_DUN = {"甲": "甲", "己": "甲", "乙": "丙", "庚": "丙", "丙": "戊",
              "辛": "戊", "丁": "庚", "壬": "庚", "戊": "壬", "癸": "壬"}

# 地支藏干。先说清楚一件事：**每一支藏哪几个干，两派是一致的；
# 争的是本气/中气/余气的排法。** 分歧集中在丑、巳两支。
#
# 派别 A（现代通行，本实现的默认）：丑=己癸辛，巳=丙庚戊
# 派别 B（《三命通会》系统的判定法「当令者旺、令生者相、生令者休、
#          克令者囚、令克者死」推得）：丑=己辛癸，巳=丙戊庚
# 两者集合相同、顺序不同，故分成两张表，由参数 canggan_sect 选择：
CANGGAN = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}
# 派别 B：同一集合，本/中/余按「旺相休囚死」重排
CANGGAN_SECT_B = dict(CANGGAN)
CANGGAN_SECT_B.update({"丑": ["己", "辛", "癸"], "巳": ["丙", "戊", "庚"]})
CANGGAN_SECTS = {"现代通行": CANGGAN, "旺相休囚死": CANGGAN_SECT_B}
CANGGAN_LEVEL = ["本气", "中气", "余气"]
# 藏干含量（分制）：藏一干100；藏二干本70中30；藏三干本60中30余10
CANGGAN_SCORE = {1: [100], 2: [70, 30], 3: [60, 30, 10]}

# 六十甲子纳音（30 组，每两组一纳音）
NAYIN_PAIRS = [
    ("海中金", 0), ("炉中火", 2), ("大林木", 4), ("路旁土", 6), ("剑锋金", 8),
    ("山头火", 10), ("涧下水", 12), ("城头土", 14), ("白蜡金", 16), ("杨柳木", 18),
    ("泉中水", 20), ("屋上土", 22), ("霹雳火", 24), ("松柏木", 26), ("长流水", 28),
    ("沙中金", 30), ("山下火", 32), ("平地木", 34), ("壁上土", 36), ("金箔金", 38),
    ("覆灯火", 40), ("天河水", 42), ("大驿土", 44), ("钗钏金", 46), ("桑柘木", 48),
    ("大溪水", 50), ("沙中土", 52), ("天上火", 54), ("石榴木", 56), ("大海水", 58),
]
NAYIN = {}
for _name, _start in NAYIN_PAIRS:
    NAYIN[JIAZI[_start]] = _name
    NAYIN[JIAZI[_start + 1]] = _name

# 五行
GAN_WUXING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
              "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_WUXING = {"子": "水", "亥": "水", "寅": "木", "卯": "木", "巳": "火", "午": "火",
              "申": "金", "酉": "金", "辰": "土", "戌": "土", "丑": "土", "未": "土"}
GAN_YINYANG = {g: ("阳" if i % 2 == 0 else "阴") for i, g in enumerate(TIAN_GAN)}

# 旬空（空亡）：每旬十日，日柱所属旬中缺的两个地支
XUN_MAP = {}
for _i in range(6):
    _start = _i * 10
    _all = set(DI_ZHI)
    for _k in range(10):
        _all.discard(DI_ZHI[(_start + _k) % 12])
    for _k in range(10):
        XUN_MAP[JIAZI[_start + _k]] = sorted(_all, key=lambda z: ZHI_INDEX[z])

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}

DEFAULTS = {
    "canggan_sect": "现代通行",      # 或 "旺相休囚死"（丑/巳两支的中余气次序不同）
    "midnight_policy": "子初换日",   # 或 "子正换日"（晚子时/早子时）
    "solar_time": False,             # 真太阳时订正（流派选项，默认关）
    "longitude": None,               # 出生地经度（东经），solar_time=True 时必填
    "qiyun_rounding": "月",          # 起运岁数取整粒度：月 / 日 / 不取整
    "dayun_count": 8,
}

__all__ = ["paipan", "jieqi_of_year", "day_ganzhi", "DEFAULTS"]


# ---------- 历算基础 ----------

@lru_cache(maxsize=256)
def jieqi_of_year(year):
    """返回 {节气名: datetime}，该年全部 24 节气（北京时间）。"""
    import base64
    rec = JIEQI_DATA[str(year)]
    bits = []
    for byte in base64.b64decode(rec):
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    out = {}
    for k, name in enumerate(JIEQI_ORDER):
        v = 0
        for i in range(26):
            v = (v << 1) | bits[k * 26 + i]
        mo, d, h, mi, s = ((v >> 22) & 15, (v >> 17) & 31, (v >> 12) & 31, (v >> 6) & 63, v & 63)
        out[name] = dt.datetime(year, mo, d, h, mi, s)
    return out


def _jie(y, name):
    """取某年的某个节气；小寒可能落在该年1月，冬至可能落在该年12月，都在表中。"""
    return jieqi_of_year(y)[name]


def day_ganzhi_index(date):
    """日干支序号 0..59。基准：公历 2000-01-01 = 戊午（序号 54）。"""
    base = dt.date(2000, 1, 1)
    days = (date - base).days
    return (54 + days) % 60


def day_ganzhi(date):
    return JIAZI[day_ganzhi_index(date)]


def ganzhi_of_year_pillar(birth_dt):
    """年柱：以立春**时刻**为界。立春前属上一年干支。"""
    y = birth_dt.year
    lichun = _jie(y, "立春")
    use_year = y if birth_dt >= lichun else y - 1
    return JIAZI[(use_year - 4) % 60], lichun


def month_zhi_and_jie(birth_dt):
    """月支：以「节」的**时刻**为界。返回 (月支, 所在节气名, 该节气时刻)。"""
    y = birth_dt.year
    cands = []
    for dy in (-1, 0, 1):
        yy = y + dy
        if str(yy) not in JIEQI_DATA:
            continue
        for name, zhi in JIE_TO_ZHI:
            try:
                t = _jie(yy, name)
            except KeyError:
                continue
            cands.append((t, zhi, name))
    cands.sort()
    prev = None
    for t, zhi, name in cands:
        if birth_dt >= t:
            prev = (zhi, name, t)
        else:
            break
    if prev is None:
        raise ValueError("超出节气表覆盖范围")
    return prev


def month_ganzhi(birth_dt, year_gan):
    zhi, jie, jt = month_zhi_and_jie(birth_dt)
    # 五虎遁：从寅月天干起，按60甲子顺数到该月支
    start_idx = JIAZI.index(WU_HU_DUN[year_gan] + "寅")
    target = start_idx + (ZHI_INDEX[zhi] - ZHI_INDEX["寅"]) % 12
    return JIAZI[target % 60], zhi, jie, jt


def time_zhi(hour):
    """时辰地支。子时跨 23:00-01:00。"""
    idx = ((hour + 1) // 2) % 12
    return DI_ZHI[idx]


def normalize_datetime(y, mo, d, h, mi, policy):
    """处理子时换日。返回 (有效日期 date, 有效时分, 是否晚子时)。

    - 子初换日（术数界主流，多数排盘软件）：23:00 起即入次日。日柱取次日。
    - 子正换日（历法天文口径）：00:00 才换日；23:00-24:00 称「晚子时」，
      日柱仍取当日，但时柱天干按**次日**日干用五鼠遁推。两种口径下时柱相同，
      只有日柱不同——这才是这一派真正的分歧所在。
    """
    midnight = policy == "子正换日"
    if h >= 23:
        if midnight:
            return dt.date(y, mo, d), (h, mi), True   # 晚子时：日柱当日
        return dt.date(y, mo, d) + dt.timedelta(days=1), (h, mi), False
    return dt.date(y, mo, d), (h, mi), False


def onoff(b):
    """把开关渲染成中文，避免输出里出现裸 True/False 让用户猜。"""
    return "已启用" if b else "未启用（默认：直接用钟表时间）"


def true_solar_time(date, hour, minute, longitude):
    """近似真太阳时 = 平太阳时 + 经度订正 + 均时差。longitude 为东经度数。"""
    if longitude is None:
        raise ValueError("true solar time requires longitude")
    day_of_year = date.timetuple().tm_yday
    # 均时差（分钟），Bailey/Spencer 近似式
    b = 2 * math.pi * (day_of_year - 81) / 364.0
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    minutes = hour * 60 + minute + (longitude - 120.0) * 4.0 + eot
    days = math.floor(minutes / 1440.0)
    minutes -= days * 1440.0
    return date + dt.timedelta(days=days), minutes / 60.0


# ---------- 十神 ----------

def shishen(day_gan, gan):
    me = GAN_WUXING[day_gan]
    other = GAN_WUXING[gan]
    same_yy = GAN_YINYANG[day_gan] == GAN_YINYANG[gan]
    if other == me:
        return "比肩" if same_yy else "劫财"
    if SHENG[me] == other:
        return "食神" if same_yy else "伤官"
    if KE[me] == other:
        return "偏财" if same_yy else "正财"
    if KE[other] == me:
        return "七杀" if same_yy else "正官"
    if SHENG[other] == me:
        return "偏印" if same_yy else "正印"
    raise AssertionError("unreachable")


# ---------- 起运 / 大运 ----------

def qiyun(birth_dt, forward):
    """起运时距：从出生**时刻**数到相邻换月之「节」的**时刻**。

    forward=True (阳男阴女顺)：顺数到下一个「节」（未来最近的一个）
    forward=False(阴男阳女逆)：逆数到已往的「节」——即当前月自己的
        起始节（出生时刻往回数遇到的第一个节）。
        注意不是「起始节的再上一个节」：起运数必须落在 [0,10) 岁
        （顺逆对称：量的是「本月节气已行多少」，三日折一岁）。
    """
    zhi, cur_name, cur_time = month_zhi_and_jie(birth_dt)
    next_t, next_name = _adjacent_jie(cur_time, cur_name, +1)
    prev_t, prev_name = _adjacent_jie(cur_time, cur_name, -1)
    if forward:
        target = next_t
    else:
        target = cur_time
    delta = abs((target - birth_dt).total_seconds())
    return target, (delta / 86400.0), (next_name, next_t, prev_name, prev_t)


def age_text(days, rounding):
    """三日为一岁，一日为四月，一时辰为十天。"""
    years_exact = days / 3.0
    if rounding == "不取整":
        return years_exact, "%.6f 岁" % years_exact
    if rounding == "日":
        total_days = days / 3.0 * 360
        return years_exact, "%d 岁零 %d 天" % (int(total_days // 360), int(round(total_days % 360)))
    # 取整到月
    months_total = years_exact * 12
    mo = int(round(months_total))
    y = mo // 12
    m = mo % 12
    return years_exact, ("%d 岁 %d 个月" % (y, m) if m else "%d 岁" % y)


def dayun_pillars(month_gz, forward, count):
    start = JIAZI.index(month_gz)
    res = []
    for i in range(1, count + 1):
        idx = (start + i) % 60 if forward else (start - i) % 60
        res.append(JIAZI[idx])
    return res


# ---------- 神煞 ----------

TIAN_YI = {"甲戊庚": ["丑", "未"], "乙己": ["子", "申"], "丙丁": ["亥", "酉"],
           "壬癸": ["巳", "卯"], "辛": ["寅", "午"]}
WENCHANG = {"甲": "巳", "乙": "午", "丙戊": "申", "丁己": "酉", "庚": "亥",
            "辛": "子", "壬": "寅", "癸": "卯"}
YIMA = {"申子辰": "寅", "寅午戌": "申", "巳酉丑": "亥", "亥卯未": "巳"}
TAOHUA = {"申子辰": "酉", "寅午戌": "卯", "巳酉丑": "午", "亥卯未": "子"}
HUAGAI = {"申子辰": "辰", "寅午戌": "戌", "巳酉丑": "丑", "亥卯未": "未"}
LU_SHEN = {"甲": "寅", "乙": "卯", "丙戊": "巳", "丁己": "午", "庚": "申",
           "辛": "酉", "壬": "亥", "癸": "子"}


def _lookup(table, key):
    for ks, v in table.items():
        if key in ks:
            return v
    return None


def shensha(year_zhi, day_zhi, month_zhi, day_gan, year_gan, all_zhis):
    """常用神煞。返回 [(名称, 出现在第几柱/说明)]。"""
    out = []
    # 天乙贵人：以日干（亦有用年干者）
    ty = _lookup(TIAN_YI, day_gan)
    if ty:
        for i, z in enumerate(all_zhis):
            if z in ty:
                out.append(("天乙贵人", ["年支", "月支", "日支", "时支"][i]))
    # 文昌贵人
    wc = _lookup(WENCHANG, day_gan)
    if wc:
        for i, z in enumerate(all_zhis):
            if z == wc:
                out.append(("文昌贵人", ["年支", "月支", "日支", "时支"][i]))
    # 禄神
    lu = _lookup(LU_SHEN, day_gan)
    if lu:
        for i, z in enumerate(all_zhis):
            if z == lu:
                out.append(("禄神", ["年支", "月支", "日支", "时支"][i]))
    # 驿马 / 桃花 / 华盖：以年支（亦有用日支者）三合局查
    for label, table in (("驿马", YIMA), ("桃花咸池", TAOHUA), ("华盖", HUAGAI)):
        tri = None
        for k in table:
            if year_zhi in k:
                tri = k
                break
        if tri:
            target = table[tri]
            for i, z in enumerate(all_zhis):
                if z == target:
                    out.append((label, ["年支", "月支", "日支", "时支"][i]))
    return out


# ---------- 主入口 ----------

def paipan(y, mo, d, h, mi=0, gender="乾", opts=None, sec=0):
    """排盘。gender: '乾'(男) / '坤'(女)。opts 见 DEFAULTS。

    sec 缺省为 0。若出生时刻只精确到分钟，而该分钟跨越某个交节时刻，
    结果里 `警示` 字段会明确指出——不静默替用户选。
    """
    o = dict(DEFAULTS)
    if opts:
        o.update(opts)

    trace = []
    warnings = []
    date0 = dt.date(y, mo, d)
    # 对外承诺范围（两端留的一年只用于算相邻节气）
    if not (1900 <= int(y) <= 2100):
        raise ValueError("年份 %d 超出内置节气表可用范围 1900-2100" % y)

    hour, minute = h, mi
    if o["solar_time"]:
        date0, hh = true_solar_time(date0, hour, minute, o["longitude"])
        hour, minute = int(hh), int(round((hh - int(hh)) * 60))
        trace.append("已做真太阳时订正（经度 %.4f）→ %s %02d:%02d" % (o["longitude"], date0, hour, minute))

    date, (hour, minute), late_zi = normalize_datetime(date0.year, date0.month, date0.day, hour, minute, o["midnight_policy"])

    # 年柱
    birth_dt = dt.datetime(date.year, date.month, date.day, hour, minute, sec)
    _cross = _jie_in_minute_window(birth_dt)
    if _cross:
        warnings.append(
            "出生时刻只精确到分钟，而 %s 的交节时刻 %s 落在这同一分钟内；"
            "按分钟的起点判定为「交节%s」。若实际出生秒数在交节之后，结论应相反。"
            % (_cross[0], _cross[1].strftime("%H:%M:%S"), "前" if birth_dt < _cross[1] else "后"))
    year_gz, lichun = ganzhi_of_year_pillar(birth_dt)
    trace.append("年柱：%s（立春 %s，交节时刻 %s）" %
                 (year_gz, "后" if birth_dt >= lichun else "前", lichun.strftime("%Y-%m-%d %H:%M")))

    # 月柱
    month_gz, month_zhi, jie_name, jie_time = month_ganzhi(birth_dt, year_gz[0])
    trace.append("月柱：%s  月支按「节」定界，在%s之后（交节 %s）" % (month_gz, jie_name, jie_time.strftime("%Y-%m-%d %H:%M")))

    # 日柱
    day_gz = day_ganzhi(date)
    trace.append("日柱：%s（日干支按六十甲子逐日顺轮；子时口径=%s）" % (day_gz, o["midnight_policy"]))

    # 时柱
    tz = time_zhi(hour)
    start = JIAZI.index(WU_SHU_DUN[day_gz[0]] + "子")
    time_gz = JIAZI[(start + ZHI_INDEX[tz]) % 60]
    if late_zi:
        start = JIAZI.index(WU_SHU_DUN[day_ganzhi(date + dt.timedelta(days=1))[0]] + "子")
        time_gz = JIAZI[(start + ZHI_INDEX[tz]) % 60]
        note = "晚子时：日柱取当日，时干按次日日干推"
    else:
        note = "日柱与时干同属一日"
    trace.append("时柱：%s（时支 %s；%s）" % (time_gz, tz, note))

    pills = [year_gz, month_gz, day_gz, time_gz]
    names = ["年柱", "月柱", "日柱", "时柱"]
    day_master = day_gz[0]

    detail = []
    all_zhis = [p[1] for p in pills]
    cgs_table = CANGGAN_SECTS[o["canggan_sect"]]
    for name, gz in zip(names, pills):
        gan, zhi = gz[0], gz[1]
        cgs = cgs_table[zhi]
        scores = CANGGAN_SCORE[len(cgs)]
        detail.append({
            "柱": name,
            "干支": gz,
            "天干": gan,
            "地支": zhi,
            "纳音": NAYIN[gz],
            "干五行": GAN_WUXING[gan],
            "支五行": ZHI_WUXING[zhi],
            "十神": shishen(day_master, gan),
            "藏干": [{"干": g, "十神": shishen(day_master, g),
                      "层次": CANGGAN_LEVEL[i] if i < len(CANGGAN_LEVEL) else "余气",
                      "分值": scores[i]}
                     for i, g in enumerate(cgs)],
        })

    # 起运
    yang = GAN_YINYANG[year_gz[0]] == "阳"
    forward = (yang and gender == "乾") or ((not yang) and gender == "坤")
    _, days, (_nname, _nt, _pname, _pt) = qiyun(birth_dt, forward)
    _czhi, _cname, _ctime = month_zhi_and_jie(birth_dt)
    years_exact, years_text = age_text(days, o["qiyun_rounding"])
    start_date = date + dt.timedelta(days=int(round(years_exact * 365.2422)))
    dayun = []
    for i, gz in enumerate(dayun_pillars(month_gz, forward, o["dayun_count"])):
        dayun.append({
            "干支": gz,
            "纳音": NAYIN[gz],
            "顺序": i + 1,
            "起运年": start_date.year + i * 10,
            "年龄段": "%d-%d 岁" % (int(years_exact) + i * 10, int(years_exact) + i * 10 + 9),
        })

    return {
        "输入": {"公历": "%04d-%02d-%02d %02d:%02d" % (y, mo, d, h, mi),
                "性别": gender,
                "参数": {k: v for k, v in o.items() if k in
                         ("canggan_sect", "midnight_policy", "solar_time",
                          "longitude", "qiyun_rounding")}},
        "口径": {"藏干次序": o["canggan_sect"],
                "子时": o["midnight_policy"],
                "真太阳时": onoff(o["solar_time"])},
        "四柱": pills,
        "四柱详": detail,
        "日主": day_master,
        "日主五行": GAN_WUXING[day_master],
        "空亡": XUN_MAP[day_gz],
        "本命月令": month_zhi,
        "大运": {"顺逆": "顺行" if forward else "逆行",
                "依据": "年干%s为%s，%s命" % (year_gz[0], GAN_YINYANG[year_gz[0]], gender),
                "起运时距": "%.4f 天" % days,
                "交节比较点": ("下一节 %s %s" if forward else "已往节(本月起始) %s %s") % (
                    (_nname, _nt.strftime("%Y-%m-%d %H:%M")) if forward
                    else (_cname, _ctime.strftime("%Y-%m-%d %H:%M"))),
                "起运": years_text,
                "列": dayun},
        "神煞": shensha(pills[0][1], pills[2][1], pills[1][1], day_master, pills[0][0], all_zhis),
        "警示": warnings,
        "推算轨迹": trace,
    }


_JIE_NAMES = [n for n, _ in JIE_TO_ZHI]


def _jie_in_minute_window(birth_dt):
    """若 birth_dt 所在的那一分钟里含有某个换月之「节」的交节时刻，返回 (名, 时刻)。"""
    minute_start = birth_dt.replace(second=0, microsecond=0)
    minute_end = minute_start + dt.timedelta(minutes=1)
    for dy in (-1, 0, 1):
        yy = birth_dt.year + dy
        if str(yy) not in JIEQI_DATA:
            continue
        try:
            table = jieqi_of_year(yy)
        except KeyError:
            continue
        for name in _JIE_NAMES:
            t = table.get(name)
            if t is not None and minute_start <= t < minute_end:
                return name, t
    return None


def _adjacent_jie(cur_time, cur_name, step):
    """给定当前所处的「节」，找它的上一个/下一个「节」及其时刻。"""
    idx = _JIE_NAMES.index(cur_name)
    target_idx = (idx + step) % 12
    # 以 piv(source year) 为基准：找相邻年的同表 index
    y = cur_time.year
    candidates = []
    for dy in (-1, 0, 1):
        yy = y + dy
        if str(yy) not in JIEQI_DATA:
            continue
        name = _JIE_NAMES[target_idx]
        t = jieqi_of_year(yy)[name]
        candidates.append((t, name))
    candidates.sort()
    if step > 0:
        cand = [c for c in candidates if c[0] > cur_time]
        return cand[0] if cand else candidates[-1]
    cand = [c for c in candidates if c[0] <= cur_time]
    return cand[-1] if cand else candidates[0]


def render(chart):
    """把结果渲染成中文文本盘面。"""
    L = []
    L.append("=" * 46)
    L.append("公历 %s  %s造" % (chart["输入"]["公历"], chart["输入"]["性别"]))
    L.append("=" * 46)
    seq = [("年柱", 0), ("月柱", 1), ("日柱", 2), ("时柱", 3)]
    L.append("        " + "    ".join("%-6s" % n for n, _ in seq))
    L.append("天干    " + "    ".join("%-6s" % chart["四柱详"][i]["十神"] for _, i in seq))
    L.append("干支    " + "    ".join("%-6s" % chart["四柱"][i] for _, i in seq))
    L.append("地支    " + "    ".join("%-6s" % chart["四柱详"][i]["地支"] for _, i in seq))
    L.append("藏干    " + "    ".join("%-6s" % "/".join(c["干"] for c in chart["四柱详"][i]["藏干"]) for _, i in seq))
    L.append("藏干十神 " + "   ".join("|".join(c["十神"] for c in chart["四柱详"][i]["藏干"]) for _, i in seq))
    L.append("纳音    " + "    ".join("%-6s" % chart["四柱详"][i]["纳音"] for _, i in seq))
    L.append("-" * 46)
    L.append("日主 %s（%s）   空亡：%s    月令：%s" %
             (chart["日主"], chart["日主五行"], "、".join(chart["空亡"]), chart["本命月令"]))
    L.append("大运：%s（%s）  %s 起运   期间差 %s" %
             (chart["大运"]["顺逆"], chart["大运"]["依据"], chart["大运"]["起运"], chart["大运"]["起运时距"]))
    du = chart["大运"]["列"]
    L.append("      " + "  ".join("%s(%d岁)" % (x["干支"], int(x["年龄段"].split("-")[0])) for x in du))
    if chart["神煞"]:
        L.append("-" * 46)
        L.append("神煞：" + "、".join("%s[%s]" % (n, p) for n, p in chart["神煞"]))
    if chart.get("警示"):
        L.append("-" * 46)
        for w in chart["警示"]:
            L.append("⚠ " + w)
    return "\n".join(L)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="八字排盘")
    ap.add_argument("datetime", help="YYYY-MM-DD HH:MM")
    ap.add_argument("--gender", choices=["乾", "坤"], default="乾")
    ap.add_argument("--midnight", choices=["子初换日", "子正换日"], default=None)
    ap.add_argument("--qiyun", choices=["月", "日", "不取整"], default=None)
    ap.add_argument("--trace", action="store_true")
    args = ap.parse_args()
    ds, ts = args.datetime.split()
    yy, mm, dd = [int(x) for x in ds.split("-")]
    hh, mii = [int(x) for x in ts.split(":")]
    opts = {}
    if args.midnight:
        opts["midnight_policy"] = args.midnight
    if args.qiyun:
        opts["qiyun_rounding"] = args.qiyun
    c = paipan(yy, mm, dd, hh, mii, args.gender, opts)
    print(render(c))
    if args.trace:
        print("\n--- 推算轨迹 ---")
        for t in c["推算轨迹"]:
            print("·", t)
