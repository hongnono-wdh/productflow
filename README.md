# ProductFlow

把"做一个互联网产品"变成一条可视化流水线的 **Claude Code 工具**——从落地页、官网，到带数据库与后端的功能性 Web 应用（落地页只是最简单的一种）。装上后说一句"做一个 XX"，AI 就启动一个跑在 `localhost:7717` 的操作台，逐阶段往前推：

> 🌐 在线介绍页：**https://pf.gjs.ink**

```
①市场调研 → ②找参考 → ③首图设计 → ④页面设计 → ⑤功能与数据设计 → ⑥开发实现 → ⑦部署上线
```

你既能在 CLI 对话（主通道），也能在网页操作台看进度、翻产物、圈选方案、给 agent 留言——两边共享同一份状态。**完全本地运行**，数据都在你自己机器上，不上云、不共享。

---

## 一键安装（推荐）

把下面这整段复制，**粘进 Claude Code**（或 Claude 桌面端）。它会自己从克隆装到启动操作台，全程不用手动分步：

```
请帮我在这台电脑上安装并启动 ProductFlow（一个把"做互联网产品"变成 7 阶段流水线、配本地操作台的 Claude Code 工具，从落地页到带后端和数据库的 Web 应用都能做）。下面每一步你来执行，做完告诉我怎么用：

1. 克隆代码到固定位置（已存在就进目录 git pull 更新）：
   git clone https://github.com/hongnono-wdh/productflow.git ~/.local/share/productflow 2>/dev/null || (cd ~/.local/share/productflow && git pull)

2. 把全部 skill 软链进 Claude Code 的 skills 目录（含随仓库一起装的 openai-image-gen 生图 skill）：
   mkdir -p ~/.claude/skills
   for s in ~/.local/share/productflow/*/; do [ -f "$s/SKILL.md" ] && ln -sfn "${s%/}" ~/.claude/skills/"$(basename "$s")"; done

3. 一并装好 Playwright + chromium（②找参考截图、⑥端到端测试要用——建议安装时就装上，免得到时缺、体验差；装不上也没关系，相关阶段会降级）：
   pip install playwright && playwright install chromium

4. 跑自检（查依赖 + 跑测试，确认装对了）：
   python3 ~/.local/share/productflow/productflow/scripts/setup.py
   自检会硬性检查（缺了报致命、挡安装）：claude 在 PATH、生图 skill openai-image-gen 已装（随仓库软链上去）、~/.config/openai/env 有 OpenAI key（③首图/④页面 AI 生图必需）。没配 OpenAI key 就提醒我去配 OPENAI_API_KEY / OPENAI_BASE_URL。Docker 可选（⑦本地部署用到再装），缺了只降级不挡主流程。

5. 启动操作台并打开浏览器：
   sh ~/.local/share/productflow/productflow/scripts/start.sh
   然后告诉我操作台地址 http://127.0.0.1:7717/，以及"新开会话可用 /productflow-init、/productflow-start，或直接说想做什么产品/网站"。

必需：Python3 + Claude Code + OpenAI 生图 key（openai-image-gen skill 随仓库一起装）；Playwright / Docker 可选。
```

装好后新开一个 Claude Code 会话，可用四个命令：

| 命令 | 作用 |
|------|------|
| `/productflow` | 主 skill —— 走 7 阶段流水线做互联网产品 |
| `/productflow-init` | 装好后自检（查依赖 + 跑测试，确认装对了） |
| `/productflow-start` | 启动操作台并打开浏览器 |
| `/productflow-update` | 升级到最新版（git pull + 数据迁移 + 重启，数据不丢） |

## 手动安装（不想用提示词时）

```bash
git clone https://github.com/hongnono-wdh/productflow.git ~/.local/share/productflow
mkdir -p ~/.claude/skills
# 软链所有带 SKILL.md 的目录（含随仓库一起装的 openai-image-gen 生图 skill）
for s in ~/.local/share/productflow/*/; do
  [ -f "$s/SKILL.md" ] && ln -sfn "${s%/}" ~/.claude/skills/"$(basename "$s")"
done
python3 ~/.local/share/productflow/productflow/scripts/setup.py   # 自检
```

## 前置依赖

| 依赖 | 必需性 | 说明 |
|------|--------|------|
| **Claude Code（claude）** | 必需 | 这是 Claude Code 的 skill；流水线靠 `claude -p` 跑各阶段 Agent |
| **Python 3.8+** | 必需 | 操作台 server + 状态机，仅用标准库、无需 pip 装包；前端是预编译产物，**端上零 Node** |
| **openai-image-gen skill** | 必需 | ③首图 / ④页面 AI 生图引擎；**随本仓库一起装**（安装会自动软链，无需另装） |
| **OpenAI 生图 key** | 必需 | 上面的生图 skill 还需 key 才能真出图，放 `~/.config/openai/env`（`OPENAI_API_KEY` / `OPENAI_BASE_URL`） |
| Playwright + chromium | 可选（建议装） | ②找参考截图 / ⑥端到端测试用：`pip install playwright && playwright install chromium`。**建议安装时就一并装好，免得到时缺、体验差**；真缺了相关阶段降级、agent 会提示 |
| Docker | 可选 | ⑦部署到本地用（静态站走 `nginx:alpine`）；缺了可改 Cloudflare / 单机部署。**到 ⑦ 缺了再装也行** |

**必需项**缺任意一个，`/productflow-init` 会报致命、挡安装（确保核心流程能跑）；**可选项**缺了只让相关阶段降级，用到那一步再按需装（agent 会提示），不挡主流程。**本工具不内置任何 API key，不绑定任何服务器或网关。**

## 更新

操作台检测到新版会在顶部提示。两种更新方式，数据都原样保留（项目数据在 skill 之外，`git pull` 碰不到）：

- 网页：操作台右上「有新版本 → 立即更新」按钮（更新后手动重启进程）；
- 命令：`/productflow-update`（git pull + 数据迁移 + **自动重启** 7717）。

## 仓库结构

```
productflow/          主 skill（SKILL.md 编排 + references/ 各阶段手册 + scripts/ + assets/console.html）
productflow-init/     /productflow-init 自检命令
productflow-start/    /productflow-start 启动命令
productflow-update/   /productflow-update 更新命令
landing/              本工具的落地页（index.html，纯静态，可本地打开或自行托管）
```

## 边界

- 复刻竞品 = 学习布局结构 / 信息架构 / 风格思路；**不抄文案、不盗图、不复制品牌元素**。
- 操作台是本地工具，只 bind `127.0.0.1`，**不要部署到公网**。
- 流水线产物（竞品截图、调研报告）含第三方内容，提交 git 前请自行检查。

## License

MIT
