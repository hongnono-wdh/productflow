# ProductFlow（Codex / 无 Skill 机制的 agent 引导）

> 这份文件是给 **不会自动加载 `SKILL.md` frontmatter 的 agent**（如 Codex 读 AGENTS.md）用的。把本节内容并入你的 `AGENTS.md`，agent 就会在合适场景触发这套流水线。`SKILL.md` 是 Claude Code 的等价物（多了自动加载用的 YAML 头），两者正文一致——以 `SKILL.md` + `references/` 为准。

## 何时遵循本流程

当用户要"做一个网站 / Web 产品 / 应用 / 落地页 / 官网 / waitlist"、"做一个带后端和数据库的产品"、"复刻某产品"、"从调研到上线"，或提到 ProductFlow / 操作台 / landing page pipeline 时，按下面的阶段推进，并读对应的 `references/phase-N-*.md` 手册。ProductFlow 做的是**完整互联网产品**（从落地页到带数据库与后端的功能性 Web 应用），落地页只是最简单的一种。

```
①市场调研 → ②页面设计 → ③功能与数据设计 → ④开发实现 → ⑤部署上线
```

## 与 Claude Code 的差异（降级要点）

核心流水线是 **agent-中立**的：状态机 `scripts/pf_state.py` + 操作台 `scripts/server.py` 都是纯 Python 标准库、`__file__` 自定位，拷过来直接能跑。需要降级的只有编排层的几处 Claude 专属说法：

- **"调用 X skill"** = 用你 agent 的对应能力；没有 Skill 机制就把它当**方法论名词**手动做：
  - design-taste-frontend → 手写 anti-slop 的落地页 HTML/CSS（参考 `references/phase-4-pages.md` 的设计原则）
  - openai-image-gen → ③④ 强制用 `gpt-image-2` 出图，需 OpenAI 生图 key。**有生图能力但缺 key**（`~/.config/openai/env` 无 `OPENAI_API_KEY`）→ 不静默降级，按 `SKILL.md`「启动·4. 生图 key 预检」在 CLI 向用户**强制索取 key 并写入**后再进 ③④；**只有连图像生成能力都没有**才跳过 Phase 3 首图生成、在 Phase 4 直接写页面而非参考图
  - database-schema-designer → 按 `references/phase-5-spec.md` 内置的 SQLite 约定直接设计
  - test-driven-development / verification-before-completion / systematic-debugging → 先写测试 / 跑验证命令再说完成 / 先复现定位根因再改
  - deploy-cf-pages → 按 `references/phase-7-deploy.md` 的 wrangler 命令手动部署
- **Agent Teams / 并行子代理** → 没有就**串行**逐个做（如多竞品分析），结果一样，别去调不存在的 `TeamCreate`。
- **`~/.claude/skills/...` 路径** → 那是 Claude Code 的布局，你的环境以实际安装位置为准，或直接走上面的降级。

## 启动（每会话）

```bash
SKILL_DIR=<本目录绝对路径>
curl -s http://127.0.0.1:7717/api/version \
  || nohup python3 "$SKILL_DIR/scripts/server.py" >/tmp/productflow-server.log 2>&1 &
export PF_PROJECT=~/code/<产品slug>
mkdir -p "$PF_PROJECT" && python3 "$SKILL_DIR/scripts/pf_state.py" init --product "<产品名>"
```

手动访问 `http://127.0.0.1:7717/`（server 不自动弹浏览器）。每个 Bash 块开头重设 `SKILL_DIR`/`PF_PROJECT`（shell 状态不跨调用持久）。

其余一切（状态协议、检查点节奏、各阶段步骤、前置依赖表）见 `SKILL.md` 与 `references/`，对所有 agent 通用。
