#!/usr/bin/env bash
# =============================================================================
# guoxue-skills · 跨 Agent 安装器
#
# 用法：
#   ./install.sh                          # 自动检测本机已装的 Agent 并安装
#   ./install.sh --agent claude           # 只装到 Claude Code
#   ./install.sh --target ~/.myagent/skills
#   ./install.sh --all                    # 装到所有已知 Agent（会创建目录）
#   ./install.sh --skill quming-xue       # 只装某一个技能
#   ./install.sh --list                   # 查看检测结果与安装状态
#   ./install.sh --dry-run                # 只预览，不落盘
#   ./install.sh --force                  # 覆盖已存在的同名技能（自动备份）
#
# 免 git 安装（管道模式，脚本会自行 clone）：
#   curl -fsSL https://raw.githubusercontent.com/yihexiang/guoxue-skills/main/install.sh | bash
#
# 安全约定：本脚本**永不删除**任何东西。
#   · 目标已存在且未给 --force  → 跳过（不覆盖）
#   · 目标已存在且给了 --force  → 先备份为 <slug>.bak-<时间戳> 再安装
# =============================================================================
set -uo pipefail

REPO="${REPO:-https://github.com/yihexiang/guoxue-skills}"
BRANCH="${BRANCH:-main}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo .)"
SKILLS_SRC="$SCRIPT_DIR/skills"

# 若 skills/ 不在脚本旁边（说明是 curl | bash 管道模式），先把仓库取到临时目录。
# 两种取法都要有：某些代理环境下 git 走 https 会被拦（实测 CONNECT tunnel 502），
# 而同一台机器的 curl 却能正常下载 —— 所以 git 失败时自动降级为 tarball。
if [ ! -d "$SKILLS_SRC" ]; then
  have_curl=0; command -v curl >/dev/null 2>&1 && have_curl=1
  have_tar=0;  command -v tar  >/dev/null 2>&1 && have_tar=1
  have_git=0;  command -v git  >/dev/null 2>&1 && have_git=1
  if [ "$have_git" = 0 ] && { [ "$have_curl" = 0 ] || [ "$have_tar" = 0 ]; }; then
    echo "✗ 未找到本地 skills/ 目录，且本机既没有 git 也没有 curl+tar。" >&2
    echo "  请先手动下载仓库（https://github.com/yihexiang/guoxue-skills）再运行 install.sh。" >&2
    exit 1
  fi
  TMPROOT="$(mktemp -d)"
  trap 'rm -rf "$TMPROOT"' EXIT
  echo "› 管道模式：获取 $REPO 到 $TMPROOT"

  got=0
  # 方式 1：git（能保留 .git，便于日后更新）
  if [ "$have_git" = 1 ]; then
    if git clone --depth 1 "$REPO" "$TMPROOT/guoxue-skills" >/dev/null 2>&1; then
      SKILLS_SRC="$TMPROOT/guoxue-skills/skills"; got=1
    else
      echo "  · git clone 失败（代理/网络限制常见），改用 tarball 下载"
    fi
  fi
  # 方式 2：tarball（不依赖 git）
  if [ "$got" = 0 ]; then
    repo_path="${REPO#https://github.com/}"; repo_path="${repo_path%.git}"
    tar_url="https://codeload.github.com/${repo_path}/tar.gz/refs/heads/${BRANCH}"
    if [ "$have_curl" = 1 ] && [ "$have_tar" = 1 ] \
       && curl -fsSL --retry 2 --max-time 60 "$tar_url" 2>/dev/null \
              | tar -xz -C "$TMPROOT" 2>/dev/null; then
      # tarball 解出的顶层目录名随 ref 而定（如 guoxue-skills-main），按布局自适应
      for d in "$TMPROOT"/*/; do
        if [ -d "${d}skills" ]; then SKILLS_SRC="${d}skills"; got=1; break; fi
      done
    fi
  fi
  if [ "$got" = 0 ]; then
    echo "✗ 获取仓库失败：$REPO" >&2
    echo "  请检查网络/代理，或手动下载后运行本地的 install.sh。" >&2
    exit 1
  fi
fi

KNOWN_AGENTS="claude workbuddy codex cursor gemini opencode windsurf"
ALL_SKILLS="$(ls -1 "$SKILLS_SRC" 2>/dev/null)"

usage() {
  cat <<'USAGE'
install.sh — guoxue-skills 跨 Agent 安装器

选项：
  -a, --agent <name>     安装到指定 Agent（claude|workbuddy|codex|cursor|gemini|opencode|windsurf）
  -t, --target <dir>     安装到任意技能父目录（适配未在列表里的 Agent）
      --all              安装到所有已知 Agent（自动创建目录）
  -s, --skill <slug>     只安装指定技能（可重复）
      --list             查看检测结果与当前安装状态
      --dry-run          只预览将要做什么，不写入磁盘
      --force            目标存在时覆盖（先自动备份）
  -h, --help             显示本帮助

无参数运行 = 自动检测本机已装的 Agent 并安装（不做任何覆盖）。
USAGE
}

die() { echo "✗ $*" >&2; exit 1; }

agent_path() {
  case "$1" in
    claude)     echo "$HOME/.claude/skills" ;;
    workbuddy)  echo "$HOME/.workbuddy/skills" ;;
    codex)      echo "$HOME/.codex/skills" ;;
    cursor)     echo "$HOME/.cursor/skills" ;;
    gemini)     echo "$HOME/.gemini/skills" ;;
    opencode)   echo "$HOME/.config/opencode/skills" ;;
    windsurf)   echo "$HOME/.codeium/windsurf/skills" ;;
    *)          return 1 ;;
  esac
}
# 判定某 Agent 是否"本机已装"：看技能目录的父目录是否存在
agent_parent() { dirname "$(agent_path "$1")"; }
agent_detected() { [ -d "$(agent_parent "$1")" ]; }
agent_label() {
  case "$1" in
    claude) echo "Claude Code";; workbuddy) echo "WorkBuddy";; codex) echo "Codex CLI";;
    cursor) echo "Cursor";; gemini) echo "Gemini CLI";; opencode) echo "OpenCode";;
    windsurf) echo "Windsurf";; *) echo "$1";;
  esac
}

TARGETS=""; AGENTS=""; SELECT=""; FORCE=0; DRY=0; LIST=0; ALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)   usage; exit 0 ;;
    --dry-run)   DRY=1; shift ;;
    --force)     FORCE=1; shift ;;
    --all)       ALL=1; shift ;;
    --list)      LIST=1; shift ;;
    -t|--target) [ $# -ge 2 ] || die "--target 缺少参数"; TARGETS="$TARGETS $2"; shift 2 ;;
    -a|--agent)  [ $# -ge 2 ] || die "--agent 缺少参数";  AGENTS="$AGENTS $2";   shift 2 ;;
    -s|--skill)  [ $# -ge 2 ] || die "--skill 缺少参数";  SELECT="$SELECT $2";   shift 2 ;;
    *)           echo "✗ 未知参数：$1"; usage; exit 1 ;;
  esac
done

# ---- 收集目标目录 ----
DESTS=""
for t in $TARGETS; do DESTS="$DESTS $t"; done
for a in $AGENTS; do
  agent_path "$a" >/dev/null 2>&1 || die "未知 Agent '$a'。已知：${KNOWN_AGENTS}（或直接用 --target）"
  DESTS="$DESTS $(agent_path "$a")"
done
if [ "$ALL" = 1 ]; then
  for a in $KNOWN_AGENTS; do DESTS="$DESTS $(agent_path "$a")"; done
fi
if [ -z "$TARGETS" ] && [ -z "$AGENTS" ] && [ "$ALL" = 0 ]; then
  for a in $KNOWN_AGENTS; do
    if agent_detected "$a"; then DESTS="$DESTS $(agent_path "$a")"; fi
  done
fi
[ -z "$ALL_SKILLS" ] && die "在 $SKILLS_SRC 下没有找到任何技能"

# ---- --list：只报状态 ----
if [ "$LIST" = 1 ]; then
  echo "本地技能：" && for s in $ALL_SKILLS; do echo "  · $s"; done
  echo ""
  echo "Agent 检测 / 安装状态："
  for a in $KNOWN_AGENTS; do
    p="$(agent_path "$a")"
    state="未安装"
    [ -d "$(agent_parent "$a")" ] || state="未安装此 Agent"
    found=""
    for s in $ALL_SKILLS; do [ -d "$p/$s" ] && found="$found $s"; done
    [ -n "$found" ] && state="已安装：$found"
    printf '  %-10s %-28s %s\n' "$a" "$p" "$state"
  done
  exit 0
fi

if [ -z "$DESTS" ]; then
  echo "✗ 未检测到任何已知 Agent 的技能目录。"
  echo "  可用 --target <dir> 指定（例如 ./install.sh --target ~/.myagent/skills）"
  echo "  或 --all 安装到所有已知 Agent。"
  exit 1
fi

# ---- 待安装技能清单 ----
SKILLS=""
if [ -n "$SELECT" ]; then
  for s in $SELECT; do
    echo "$ALL_SKILLS" | tr ' ' '\n' | grep -qx "$s" || die "技能 '$s' 不存在。可用：$ALL_SKILLS"
    SKILLS="$SKILLS $s"
  done
else
  SKILLS="$ALL_SKILLS"
fi

# ---- 依赖自动补全 ----
# geju-yunshi 依赖 bazi-paipan 的排盘引擎（scripts/paipan.py），单装会缺依赖。
need_dep=""
for s in $SKILLS; do [ "$s" = "geju-yunshi" ] && need_dep="bazi-paipan"; done
if [ -n "$need_dep" ]; then
  has=0; for s in $SKILLS; do [ "$s" = "$need_dep" ] && has=1; done
  if [ "$has" = 0 ]; then
    SKILLS="$need_dep $SKILLS"
    echo "› 提示：geju-yunshi 依赖 bazi-paipan（排盘引擎），已自动加入安装清单"
    echo ""
  fi
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
installed=0; skipped=0
echo "技能来源：$SKILLS_SRC"
[ "$DRY" = 1 ] && echo "⚠️  dry-run 模式：不写入磁盘"
echo ""

for dest in $DESTS; do
  echo "── 目标：$dest"
  for s in $SKILLS; do
    src="$SKILLS_SRC/$s"; tgt="$dest/$s"
    if [ -d "$tgt" ]; then
      if [ "$FORCE" = 0 ]; then
        echo "   ↷ $s 已存在，跳过（覆盖请用 --force）"; skipped=$((skipped+1)); continue
      else
        bak="$tgt.bak-$STAMP"
        [ "$DRY" = 1 ] || { mv "$tgt" "$bak" && echo "   📦 已备份 $s → $(basename "$bak")"; }
        [ "$DRY" = 1 ] && echo "   📦 将备份 $s → $(basename "$bak")"
      fi
    fi
    if [ "$DRY" = 1 ]; then
      echo "   ✓ 将安装 $s"
    else
      mkdir -p "$dest" || { echo "   ✗ 无法创建 $dest"; continue; }
      cp -R "$src" "$tgt" || { echo "   ✗ 复制失败 $s"; continue; }
      echo "   ✓ 已安装 $s"
    fi
    installed=$((installed+1))
  done
  echo ""
done

echo "──────────────────────────────"
echo "完成：安装 $installed 项，跳过 $skipped 项"
echo ""
echo "验证（以 quming-xue 为例）："
for dest in $DESTS; do
  echo "  ls $dest/quming-xue"
  echo "  python3 $dest/quming-xue/tests/test_engine.py"
  break
done
echo ""
echo "若你的 Agent 不在列表里：任何支持 Agent Skills 约定（目录内含 SKILL.md，"
echo "frontmatter 有 name + description）的客户端，直接把 skills/<slug> 整个目录"
echo "复制到它的技能目录即可。通用写法：./install.sh --target <它的技能父目录>"
