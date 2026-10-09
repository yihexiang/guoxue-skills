# guoxue-skills · 可安装的国学/命理 Agent Skills

把中国传统命理与取名方法蒸馏成**可在主流 Agent 里直接安装调用**的技能包：
不是聊天式玄学，而是**有确定性引擎、有完成标准、有边界声明**的能力卡。

每个技能都遵循通用的 **Agent Skills 约定**（技能目录下含 `SKILL.md`，frontmatter 里有 `name` + `description`），
因此不绑定任何单一客户端。

---

## 目录

| 技能 | 一句话 | 依赖 | 引擎自检 |
|---|---|---|---|
| [`bazi-paipan`](skills/bazi-paipan/) | 八字四柱排盘：干支/藏干/十神/纳音/空亡/神煞/起运大运 | 无 | 41 项全绿 |
| [`geju-yunshi`](skills/geju-yunshi/) | 已排好的盘怎么读：格局、日主强弱、大运描述性解读 | `bazi-paipan` | — |
| [`quming-xue`](skills/quming-xue/) | 依八字喜用神取名/体检：五格/三才/生肖/平仄 | `bazi-paipan`（取八字）、`geju-yunshi`（取喜用） | 15 项全绿 |
| [`zhouyi-yili`](skills/zhouyi-yili/) | 周易义理：观象—析爻—落行动的处境分析（**不做预测与算命**） | 无 | 89 项全绿（引擎 47 + 参考 42） |

> `geju-yunshi` 依赖 `bazi-paipan` 的排盘引擎 `scripts/paipan.py`。
> 用 `./install.sh --skill geju-yunshi` 时安装器会**自动一并安装** `bazi-paipan`。
>
> ⚠️ `zhouyi-yili` **与上面三个不是一路**：它不用生辰、不做预测断言、不给吉凶定论。
> 它做的是"当下处境的结构分析 + 行动建议"，源自《周易》六十四卦结构与《易传》十翼的**义理**传统。
> 想让它算运势、算彩票、断疾病，它会拒答——这是设计，不是缺陷。

---

## 安装

### 方式 1 · 自动安装（推荐）

```bash
git clone https://github.com/yihexiang/guoxue-skills.git
cd guoxue-skills
./install.sh                 # 自动检测本机已装的 Agent 并安装
```

一行版（脚本会自行获取仓库再安装）：

```bash
curl -fsSL https://raw.githubusercontent.com/yihexiang/guoxue-skills/main/install.sh | bash
```

> 管道模式下安装器先尝试 `git clone`，失败则**自动降级为下载 tarball**
> （实测某些代理环境会拦 git 的 https 连接，但 curl 正常）。
> 因此即使本机没装 git 也能用。想装到指定位置：`curl -fsSL <上面的地址> | bash -s -- --target <目录>`；
> 换仓库/分支可用环境变量 `REPO` 与 `BRANCH` 覆盖。

### 方式 2 · 指定目标

```bash
./install.sh --agent claude                  # 只装到 Claude Code
./install.sh --target ~/.myagent/skills      # 任意 Agent 的技能目录
./install.sh --skill quming-xue --agent claude
./install.sh --list                          # 查看检测结果与安装状态
./install.sh --dry-run                       # 只预览，不落盘
```

安全约定：**安装器永不删除任何东西**。目标已存在时默认跳过；确需覆盖用 `--force`，
覆盖前会自动把旧版备份为 `<slug>.bak-<时间戳>`。

### 方式 3 · 手动复制（任何支持该约定的客户端）

把整个目录复制进去即可：

```bash
cp -R skills/quming-xue ~/.claude/skills/    # 换成你客户端的技能目录
```

支持的 Agent（会自动识别）：

| Agent | 技能目录 |
|---|---|
| Claude Code | `~/.claude/skills` |
| WorkBuddy | `~/.workbuddy/skills` |
| Codex CLI | `~/.codex/skills` |
| Cursor | `~/.cursor/skills` |
| Gemini CLI | `~/.gemini/skills` |
| OpenCode | `~/.config/opencode/skills` |
| Windsurf | `~/.codeium/windsurf/skills` |
| 其他 / 项目级 | `--target <目录>`，或直接复制 |

---

## 用法

安装后直接用自然语言提问即可（Agent 会按 `description` 自行判断是否激活）。也给出了完全确定、可复跑的命令：

**排盘**
```bash
python3 <skills>/bazi-paipan/scripts/paipan.py "1990-05-15 14:30" --gender 乾
```

**格局解读**：先排盘，再问"这个盘什么格局、日主强弱如何、大运怎么看"。
本卡只给**框架性、描述性**解读，不做预测断言。

**取名 / 姓名体检**
```bash
python3 <skills>/quming-xue/scripts/wuge.py 李 昱坤 \
  --strokes 7,9,8 --zodiac 马 --xiyong 火,土 --tones 3,4,1
```

**周易析卦**（多变爻会一次给出本卦与之卦两张大象辞，供"贞悔相参"对读）
```bash
python3 <skills>/zhouyi-yili/scripts/zhouyi.py 蒙 --moving 1
python3 <skills>/zhouyi-yili/scripts/zhouyi.py 既濟 --moving 1,3
python3 <skills>/zhouyi-yili/scripts/zhouyi.py --cast --seed 7   # 金钱卦起卦，同 seed 可复现
```

**深读三命令**（十翼原文先例，引擎实测交叉验证）
```bash
python3 <skills>/zhouyi-yili/scripts/zhouyi.py 既濟 --chain     # 序卦相承：承自/承至哪卦、序卦原话理由
python3 <skills>/zhouyi-yili/scripts/zhouyi.py 噬嗑 --tuan      # 彖傳实例：该卦彖辞 + 术语标注 + 引擎实测
python3 <skills>/zhouyi-yili/scripts/zhouyi.py 乾 --wenyan --line 上九   # 文言逐爻（仅乾坤两卦）
```

**跑自检**（安装是否正确、引擎是否可用的最硬证据）
```bash
python3 <skills>/bazi-paipan/tests/test_engine.py    # 41 项
python3 <skills>/quming-xue/tests/test_engine.py     # 15 项
python3 <skills>/zhouyi-yili/tests/test_engine.py    # 47 项
python3 <skills>/zhouyi-yili/tests/test_refs.py      # 42 项（三块深读参考的交叉验证）
```

---

## 为什么敢说"算得准"

`bazi-paipan` 的排盘结果不依赖古籍解读，它是可交叉验证的历算。技能自带的
`VERIFY.md` 记录了与参照历算库 `lunar-python` 的比对：**合计 173,426 次，差异 0**
（日柱逐日 73,414 / 四柱 28,944 / 节气边界 70,848 / 大运 220）。

复跑方式见 [`skills/bazi-paipan/VERIFY.md`](skills/bazi-paipan/VERIFY.md)。
该功能为零依赖纯本地 Python，**不联网、不调用任何 API**。

## 诚实的边界（请务必读）

- **这些技能不做命运预测。** 三张卡都明确写明：不做对个人具体事件的预测断言、
  吉凶定论与人生建议。它们做的是**把传统方法结构化、可复算地呈现出来**。
- **来源厚度差异如实标注。** `quming-xue` 的底稿是对权威姓名学文献的**结构化合成提取**，
  一手原文占比 0.30（而非 1.0），这一点在其报告中被记为扣分，不夸大。
- **流派差异不假装唯一正确。** 取格法、旺衰权衡向来有门户之别，卡片会声明口径。
- 内容属传统文化研究与工具化范畴，**不替代医学、法律、金融或任何专业决策**。

## 目录结构

```
guoxue-skills/
├── install.sh                    # 跨 Agent 安装器
├── README.md
├── LICENSE                       # MIT
└── skills/
    ├── bazi-paipan/
    │   ├── SKILL.md              # 入口（渐进式披露）
    │   ├── VERIFY.md             # 交叉验证报告
    │   ├── references/           # 来源/覆盖/十神等详解卡
    │   ├── scripts/paipan.py     # 零依赖排盘引擎
    │   └── tests/test_engine.py
    ├── geju-yunshi/
    │   └── SKILL.md
    └── quming-xue/
        ├── SKILL.md
        ├── scripts/wuge.py       # 五格/三才/生肖评名引擎
        └── tests/test_engine.py
```

> 注：`bazi-paipan/references/cards/geju-yunshi.md` 与 `skills/geju-yunshi/SKILL.md`
> 是同一份内容的两处存在——前者供 `bazi-paipan` 内部渐进式引用，后者是独立可触发的技能。

## 许可

MIT。技能正文与引擎代码均可自由使用与修改；所引古典文献均为公有领域。

## 相关

- [`rulai-distill`](https://github.com/yihexiang/rulai-distill) —— 产出这些技能的蒸馏工厂
  （七阶段管线 + FIDELITY 双 Agent 出厂质检）。本仓库的技能是由它蒸馏并过质检后发布。
