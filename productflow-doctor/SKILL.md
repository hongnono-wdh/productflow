---
name: productflow-doctor
version: 1.0.0
description: ProductFlow 安装后的「深度自检 / 体检」——比 /productflow-init 更彻底：查全部依赖 + 跑测试套件 + 校验代码完整性（关键文件齐全 / git 完整）+ 真调本地生图 skill 批量出 2 张图确认「生图通路 + 批量并发」都真的通。用户说「自检 / 体检 / 检查装好没 / 确认能用 / 检查生图能不能用 / install check / doctor ProductFlow」，或刚装完想确认真的能跑时，用本 skill。
---

# ProductFlow 深度自检（doctor）

比 `/productflow-init` 更彻底的一次性体检——**装完跑它确认 ProductFlow 真的能用**（不是只看依赖在不在，而是端到端验一遍）：

- **① 依赖 + 测试**：复用 `setup.py` 查 claude / Python / Playwright / Docker / 生图 skill / key，并跑整套测试套件。
- **② 代码完整性**：关键文件齐全且非空（server / pf_state / dist 编译产物 / 7 阶段手册 / gen.py / edit.py …）+ git 仓库完整性（`fsck`）——确认**装全了、没缺没损坏**。
- **③ 真出图**：实际调用本地 openai-image-gen **批量生成 2 张图**，确认生图通路 + 批量并发都通（端到端真出一次，约 2 张小图开销）。

## 跑

```bash
python3 ~/.claude/skills/productflow/scripts/doctor.py
```

路径不存在就 find 兜底：

```bash
DR="$(find ~ /opt -path '*/skills/productflow/scripts/doctor.py' 2>/dev/null | head -1)"
[ -n "$DR" ] && python3 "$DR" || echo "没找到 ProductFlow，请确认已装到 ~/.claude/skills/productflow"
```

不想真调付费生图 API（CI / 离线 / 只想快检）：加 `--no-image`（跳过 ③，其余照跑）。

## 转达结果

把它逐项的 ✅/⚠️/❌ **原样转达用户**（别只说"成功了"）：

- **退出码 0**：依赖 + 测试 + 代码完整 + 真出图都就绪 → 让用户 `/productflow-start` 启动操作台。可选项（Docker / Playwright）缺了只让相关阶段降级，照实说明影响哪步。
- **退出码非 0**：**停下**，按脚本输出告诉用户缺什么、怎么补——依赖缺（装对应依赖）、关键文件缺/损坏（重装或 `/productflow-update` 即 git pull）、真出图失败（查 `~/.config/openai/env` 的 key / 网关连通性）。

> 关系：`/productflow-init` 是**快检**（依赖 + 测试，约 1 分钟）；本 `doctor` 是**深检**（再加代码完整性 + 真出图），新机安装、换机、或排查"为什么生不出图/某阶段不工作"时用它。
