#!/bin/sh
# ProductFlow 更新器：拉取 GitHub 最新版 + 跑数据迁移 + 重启操作台。
# 用法：sh scripts/update.sh
#
# 数据安全：用户项目数据在 skill 之外（全局 ~/.productflow/ 和各项目目录里的 .productflow/），
# git pull 只动 skill 代码、碰不到这些 —— 升级天然保留数据。迁移钩子只在数据格式变更时转换。
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
URL="http://127.0.0.1:7717/"

# 1) 必须是 git clone 装的，才能一键更新
ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$ROOT" ]; then
  echo "❌ 当前不是 git 克隆安装，无法一键更新。"
  echo "   请用安装提示词里的 git clone 方式重装，或手动下载最新包覆盖。"
  exit 1
fi

# 2) 记录旧版本
OLD="$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo '?')"
echo "当前版本：v$OLD  仓库：$ROOT"

# 3) 拉新版（仅快进，避免本地改动冲突时硬覆盖）
echo "拉取最新版…"
if ! git -C "$ROOT" pull --ff-only; then
  echo "❌ git pull 失败（可能本地有改动 / 网络问题）。"
  echo "   有本地改动就先 git stash 或提交；网络问题稍后重试。"
  exit 1
fi

# 4) 数据迁移钩子（无 schema 变更时为空操作）
if [ -f "$SKILL_DIR/scripts/migrate.py" ]; then
  echo "运行数据迁移…"
  python3 "$SKILL_DIR/scripts/migrate.py" || echo "⚠️ 迁移脚本报错（数据已备份，可人工检查）"
fi

NEW="$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo '?')"
if [ "$OLD" = "$NEW" ]; then
  echo "✅ 已是最新版 v$NEW（无更新）。"
else
  echo "✅ 已更新：v$OLD → v$NEW"
fi

# 5) 重启操作台让新代码生效（server.py 改动必须重启进程）
if curl -s "${URL}api/version" >/dev/null 2>&1; then
  echo "重启操作台（让新版生效）…"
  lsof -ti:7717 2>/dev/null | xargs kill 2>/dev/null || true
  sleep 1
  nohup python3 "$SKILL_DIR/scripts/server.py" >/tmp/productflow-server.log 2>&1 &
  i=0
  while [ $i -lt 40 ]; do
    curl -s "${URL}api/version" >/dev/null 2>&1 && break
    sleep 0.25; i=$((i+1))
  done
  echo "操作台已重启：$URL"
else
  echo "操作台当前未运行；下次 /productflow-start 启动即用新版。"
fi
