# 对抗式 e2e 验证计划（从用户视角）

> 业务基准来自 understand-anything 抽取的领域图 `.understand-anything/domain-graph.json`
> （3 domains / 9 flows / 42 steps）。测试用例**贴真实业务流**，不凭空猜。
>
> 架构：两个 loop。**Loop 1 只发现、只积累、不修**；**Loop 2 定时复现+稳定+修复**。
> 两 loop 是**不同进程**，各自起独立沙箱 server（随机端口）+ 独立 browser → 多实例隔离，
> 互不抢线程/端口，也不碰用户的 :7717。

## Playwright 多实例（不靠多线程）
- sync API 非线程安全（对象绑定创建线程，跨线程抛 `Cannot switch to a different thread`）。
- 并发 = **多进程**：每个 persona 跑在独立进程，自带 `helpers.start_server`(free port) + 独立 browser。
- 单进程内模拟多用户 = **多 browser context**（隔离 cookie/storage）。本机 14 核，并行上限按核数留余量。
- 现有 `tests/helpers.py`（make_home + start_server free_port + cli 桩 claude）天生多实例隔离，直接复用。

## findings 记录（`findings/findings.jsonl`，每行一条 JSON）
`{id, ts, persona, journey, stage, severity(crash|broken|degraded|cosmetic), title, repro[], observed, expected, console_errors[], screenshot, status(open|fixed|wontfix), fix_commit?}`
- Loop 1 append（status=open）；Loop 2 改 status=fixed/wontfix + fix_commit。
- 去重：同 (persona, journey, title) 已 open 则不重复 append（计数 +1）。

## 用户 persona（对抗行为档；Loop 1 每次一个）
1. **impatient** 手快乱点：未加载就点、连点、双提交、狂点「下一步」
2. **overflow** 超长/特殊输入：CJK/emoji/超长名、slug 特殊字符、brief/chat 里塞 `<script>`/超长串
3. **flaky-net** 断网慢网：动作中 reload、agent 跑时切走/切回、offline→online
4. **multi-tab** 多标签：同项目两 tab、并发编辑、WS 重连后状态一致性
5. **keyboard** 纯键盘/无障碍：Tab 序、Enter/Esc、焦点可见、不用鼠标走流程
6. **canvas-power** 画布重度：狂拖狂缩、agent 更新中拖、拖到一半切阶段（验 isolation/guard）
7. **edge-empty** 空/边界：全新项目无数据、删光、旧数据(非 7 阶段)兼容横幅
8. **skipper** 不读说明：跳到⑦没做前置、前置不满足就 run-stage、乱序点阶段

## 每条旅程都查的对抗探针
console error / pageerror、卡死 spinner、WS 断后重连+全量补推是否补齐、打字时被推送抢焦点（focus-guard）、推送闪烁（图重取）、乐观态不一致、切阶段后残留态、连点竞态（双 POST / 409 是否被拦）、破图 404 暴露给用户、小视口&长文本布局崩、Esc/遮罩关闭。

## 分阶段业务旅程 + 不变量（对抗基准，源自 domain-graph）

**创建**：只填 name+platform → 进项目；platform(PC/H5/APP) 贯穿各阶段。对抗：超长名/CJK slug 自动占位、连点「创建」、草稿 localStorage 跨刷新。

**① 市场调研**：brief 写描述→生成摘要→4 字段(goal/users/need/scope)→**确认**。不变量：**confirm-lag**——重新生成会把 `confirmed` 重置为 false、需重新确认；生成中 `ready=false` 转圈，失败要停转。对抗：生成中切走/回来、打字时轮询不得抢焦点、市场调研 run 超时(30min, 见 2.14.1)的中断态显示。

**② 找参考**：风格标签→找参考(explore slot `search-refs`)→选 refs(`selectedRefs`)。不变量：slot 按 kind 隔离(②③ 不互覆盖)；访问全失败**不得** done-request、要可重试。对抗：Viewer 放大时后台推送不得拆查看器、连点找参考、选/删 ref 乐观态。

**③ 首图**：依 selectedRefs 生 2-4 张纯 UI 首图(slot `gen-heroes`)→单选 `selectedHero`→**styleSummary**(给④的视觉契约)。不变量：零输入也能生成；framed-redraw 加新版本不走 agent、原图保留。对抗：生成中切走、hero dialog 图N 代号顺序、设基调乐观态。

**④ 页面**：page-map 全量占位→设计→平台版本→`direction.md`(5 段)。不变量：**④依赖③(selectedHero/styleSummary)**；登记任一版本**自动 placeholder→done**；版本按 (file,platform) 去重；平台矩阵 on/off。对抗：③没定基调就进④的引导提示、点空平台格 confirm 生成、批量生成 409、画布拖拽持久化+per-stage 隔离。

**⑤ 功能与数据**：模块→ER→schema-ddl→api-contract→选模板。不变量(**平台分支矩阵**)：Web(PC/H5) schema/api done；iOS/Android schema→@Model/@Entity 且该步 **skipped**、api **skipped**；P-Desktop schema done(SQLite)、api skipped；T1 静态 er+schema skipped。对抗：换栈 choice、模块歧义 choice、输出是⑥的固定输入。

**⑥ 开发**：脚手架→前端→后端→测试→api 文档。不变量：**⑥依赖⑤(schema/template)**；test-report 四类必须显式 green/N-A、禁静默跳过；run-stage 并发护栏(运行中 409)；run-action preview **不推进阶段**。对抗：缺原生工具链要停而非刷 command-not-found、预览圈选按区域修、preview-feedback。

**⑦ 部署**：选目标(由⑤预设定)→部署→冒烟→交付报告。不变量：**⑦依赖⑥(测试全绿)**，pre-deploy checklist 拦(测试不绿退回⑥)；**deploy-creds 空→choice ask/CLI 补，绝不占位**；creds 存仓库外、注入为 env、不打印；原生/桌面停在提交商店前、无 deploy.json。对抗：没填凭证就部署、Web 子表单 choice、缺凭证的致命提示。

**跨阶段交互面**：choice ask/wait（wait 退出码恒 0、靠 stdout JSON 判超时）；inbox（仅 from:web 未读、reply 追加）；都在 :7717 控制台 + CLI 两通道，状态共享 `.productflow/`。

## 执行
- 引擎：`harness.py`（多实例：每跑一个 persona = 独立 server+browser，跑上面旅程的对抗变体，捕获 console/pageerror/截图，写 findings）。
- Loop 1：`/loop` 自驱，每次轮换一个 persona 调 harness，积累 open findings，不改码。
- Loop 2：`/loop <interval>` 读 open findings → 复现 → 修 → 独立实例回归 → 标 fixed。
