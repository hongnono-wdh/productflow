---
name: productflow-init
description: 初始化并自检 ProductFlow 落地页操作台。装好 ProductFlow 后第一次运行 /productflow-init——检查依赖（Python / Playwright / Docker / 生图 key）并跑测试套件，确认装对了、能正常工作。用户说 /productflow-init、初始化 ProductFlow、检查 ProductFlow 装好没、ProductFlow 自检 / setup / doctor 时，就用本 skill。
---

# ProductFlow 初始化自检

跑 ProductFlow 的自检脚本，把它逐项的 ✅/⚠️/❌ 结果**原样转达用户**（别只说"成功了"）：

```bash
python3 ~/.claude/skills/productflow/scripts/setup.py
```

若该路径不存在（skill 装在别处），用 find 兜底再跑：

```bash
SETUP="$(find ~ /opt -path '*/skills/productflow/scripts/setup.py' 2>/dev/null | head -1)"
[ -n "$SETUP" ] && python3 "$SETUP" || echo "没找到 ProductFlow skill，请确认已装到 ~/.claude/skills/productflow"
```

脚本会查依赖 + 跑测试套件（约 20s）。读它的退出结果：

- **全部就绪 / 只缺可选项**（退出码 0）：告诉用户「环境就绪，运行 `/productflow-start` 启动操作台」。可选项（Docker / 生图 key / Playwright）缺了只让相关阶段降级，不挡主流程——照实说明缺哪个、影响哪步。
- **有致命问题**（退出码非 0）：**停下**，照脚本输出告诉用户缺什么、怎么补（如 `pip install playwright && playwright install chromium`、装并启动 Docker），别强行往下。

这一步只做"自检+确认装对了"，不创建项目、不起服务。装好后只需跑一次；之后日常用 `/productflow-start` 启动。
