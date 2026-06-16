#!/bin/sh
# ProductFlow 启动器：一条命令起操作台（7717）并打开浏览器。
# 用法：sh scripts/start.sh
# 已在跑就不重复起；服务只 bind 127.0.0.1（本地工具，不暴露公网）。
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
URL="http://127.0.0.1:7717/"

if curl -s "${URL}api/version" >/dev/null 2>&1; then
  echo "操作台已在运行。"
else
  echo "启动操作台…"
  nohup python3 "$SKILL_DIR/scripts/server.py" >/tmp/productflow-server.log 2>&1 &
  # 等服务起来（最多 ~10s）
  i=0
  while [ $i -lt 40 ]; do
    curl -s "${URL}api/version" >/dev/null 2>&1 && break
    sleep 0.25; i=$((i+1))
  done
fi

# 打开浏览器：macOS `open` / Linux `xdg-open`，都没有就只打印地址
if command -v open >/dev/null 2>&1; then open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
else echo "请手动在浏览器打开：$URL"; fi

echo "ProductFlow 操作台：$URL  （日志：/tmp/productflow-server.log）"
