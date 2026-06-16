---
name: productflow-start
description: 启动 ProductFlow 落地页操作台（本地 localhost:7717）并打开浏览器，准备好工作环境。用户说 /productflow-start、启动 ProductFlow、打开 ProductFlow 操作台 / 控制台、起 7717、准备好 ProductFlow 环境 时，就用本 skill。
---

# 启动 ProductFlow 操作台

起本地操作台（已在跑则只开页面）并自动打开浏览器：

```bash
sh ~/.claude/skills/productflow/scripts/start.sh
```

路径不存在就 find 兜底：

```bash
START="$(find ~ /opt -path '*/skills/productflow/scripts/start.sh' 2>/dev/null | head -1)"
[ -n "$START" ] && sh "$START" || echo "没找到 ProductFlow skill，请确认已装到 ~/.claude/skills/productflow"
```

启动后告诉用户：

- 操作台地址 **http://127.0.0.1:7717/**（本地工具，只 bind 127.0.0.1，不暴露公网）；
- 在网页点「＋ 新建项目」（只填名称 + 平台）开始，或直接对你（agent）说想做什么落地页——两边状态共享。
- 服务是全局单例，一个进程服务所有项目；日志在 `/tmp/productflow-server.log`。

> 还没自检过的新机器：先跑一次 `/productflow-init` 确认依赖装齐，再 `/productflow-start`。
> 真正干活、走 7 阶段流水线时，用主 skill `productflow`（它带完整阶段手册）。
