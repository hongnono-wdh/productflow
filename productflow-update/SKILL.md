---
name: productflow-update
description: 把 ProductFlow 落地页操作台更新到 GitHub 最新版（git pull + 数据迁移 + 重启 7717），用户数据自动保留。用户说 /productflow-update、更新 ProductFlow、升级 ProductFlow、ProductFlow 有新版本吗 / 拉最新版、update productflow 时，就用本 skill。
---

# 更新 ProductFlow

跑更新脚本：拉 GitHub 最新版 → 跑数据迁移钩子 → 重启操作台让新代码生效。把它的输出**原样转达用户**：

```bash
sh ~/.claude/skills/productflow/scripts/update.sh
```

路径不存在就 find 兜底：

```bash
UP="$(find ~ /opt -path '*/skills/productflow/scripts/update.sh' 2>/dev/null | head -1)"
[ -n "$UP" ] && sh "$UP" || echo "没找到 ProductFlow skill，请确认已装到 ~/.claude/skills/productflow"
```

读脚本结果，照实告诉用户：

- **更新成功**（`v旧 → v新`）：操作台已自动重启，刷新 http://127.0.0.1:7717/ 即用新版。
- **已是最新版**：无需操作。
- **不是 git 安装 / git pull 失败**（退出码非 0）：照脚本提示转达——不是 git clone 装的就重装，有本地改动就先 `git stash`，网络问题稍后重试。**别强行覆盖用户的本地改动。**

## 数据安全（可向用户说明）

用户的项目数据在 skill **之外**——全局 `~/.productflow/`（项目注册表、待接单、部署凭证）和各项目目录里的 `.productflow/`（状态、产物、画布）。`git pull` 只更新 skill 代码，碰不到这些，所以**升级天然不丢数据**。迁移钩子（`scripts/migrate.py`）只在数据格式变更时做幂等转换、且先备份。

> 也可以在操作台网页右上角的「有新版本 → 立即更新」按钮触发更新（走 server 的 `/api/update`），效果相同；区别是网页按钮更新后需手动重启进程，本 skill 会**自动重启** 7717。
