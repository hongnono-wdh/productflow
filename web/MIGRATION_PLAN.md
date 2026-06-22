# ProductFlow 操作台 → React+TS + 全局 WebSocket 迁移计划

> 目标：把单文件 vanilla-JS SPA（`assets/console.html`，2538 行）端到端重写为 **React + TypeScript**，
> 用**一条全局 WebSocket 订阅**取代全部 `setInterval` 轮询，**局部渲染**消除闪烁；
> 交付**编译产物**（用户运行端零 Node）。旧 `console.html` 保留为回退，直到新版逐屏 diff 通过。
>
> 纪律：**先计划 → 逐步执行 → 每步 diff 比对 → 不要遗漏**。每完成一屏，对照本文件「Diff 检查清单」与
> `web/.migration/inventory.json`（136 条：24 屏 + 49 数据流 + 27 交互 + 36 端点 + 完备性评审）核对。

---

## 架构决定（已定）

| 维度 | 决定 | 理由 |
|------|------|------|
| 传输 | **原生 WebSocket（RFC6455）** 手写在 stdlib `ThreadingHTTPServer` 的 `do_GET` 里升级 | 用户指定 WS；零依赖；线程/连接撑长连 |
| 推送触发 | **服务端 per-project mtime 监听**（非「自己 POST 才推」） | **关键**：`pf_state.py`(agent CLI) 直接写大多数文件、服务端不经手 |
| 前端框架 | React + TS（Vite 构建） | 类型静态检查防错；reconciliation = 局部渲染 |
| 状态 | 手写外部 store + `useSyncExternalStore`（0 依赖，按 slice 订阅 → 只重渲染变化组件） | 局部渲染、无多余依赖 |
| 路由 | 手写微路由（`/` 首页 / `/p/:id/` 项目；stage 用 hash `#s<n>`） | 仅两路由，免依赖 |
| 样式 | 把 `console.html` 的 `<style>` **逐字搬进 global.css**，类名保持一致 | 最大化视觉 diff parity、最低风险 |
| 厂商库 | d3 / markmap / viewer.js **继续用 `/vendor` 动态加载现有文件**（不走 npm） | markmap 调色板依赖内部 `node.state.path`，版本必须锁定 |
| 客户端→服务端 | **全部仍走 POST**；结果经对应 channel 回流（乐观更新→确认） | 双向无必要；保留并发 409 |
| 构建产物 | `web/` 源 → 构建到 `assets/dist/`，`base:'/dist/'`，提交进仓库 | 用户运行端零 Node |
| 静态服务 | `/` 与 `/p/<id>/` → `dist/index.html`(no-store)；`/dist/*` 长缓存；`/vendor`、`/p/<id>/artifacts/`、`/api/*` 不变；`/api/version` 保持 `{app:'productflow'}` | 单实例探测/start 脚本不破 |

## WebSocket 频道集（13 推送频道；评审已定）

**project 作用域**（连 `/p/<id>/api/ws`）：
- `state` ← `state.json`（pf_state 写）→ board/stepper/steps/gallery/log/product/meta/next/compat/overview/P6预览
- `inbox` ← `inbox.jsonl`（server+agent 写）→ 聊天抽屉、未读红点（3 种消息体：plain/canvas-feedback/preview-feedback）
- `health` ← `health.json`（仅 server `_health_loop` 每 300s）→ #health-line（**一次 health 写要同时推 health + projects**）
- `pages` ← `pages.json`（server POST + pf_state page）→ ④ 页面卡（按 page id+version file 做 key）
- `choices` ← `choices.json`（pf_state ask / server answer）→ #choices-bar（**choices 变要同时重算并推对应 stage 的 waiting**）
- `brief` ← `brief.json`（server POST + `_auto_gen_brief`）→ P1 摘要（confirm-lag/生成中/失败 由 request 槽推导，本地保 description/clarify/answers）
- `explore` ← `explore.json`（server POST + `_auto_explore` + pf_state + 清槽）→ ② refs / ③ hero+dialog / overview（request{} 槽驱动 spinner；searchFailed 来自 agent-log:search-refs）
- `agent-log:research` ← `agent-log-research.jsonl` → P1 市场调研尾行 running/failed（本地保 instr）
- `agent-log:search-refs` ← `agent-log-search-refs.jsonl` → P2 searchFailed（仅 tail kind==='error'）
- `agent-log:stage-<n>` (n=4,5,6,7) ← `agent-log-stage-N.jsonl` **+ 内存 `_STAGE_RUNNING`（无文件）** → P5/6/7 running/waiting/failed、P4 stagebar。**running/waiting 是运行时标志，推送必须带上**；`_STAGE_RUNNING` 变更(run-stage/run-action add；finally discard) 与 choices 变更都要触发
- `wizard` ← `wizard.json`（建项目时写）→ pfWizard{primary,platforms}，仅驱动 ⑥⑦ 按钮文案。**可只 mount 拉一次**

**home/global 作用域**（连 `/api/ws`）：
- `projects` ← 注册表 `<pid>.json` + 各 `state.json`/`health.json` + `pending/*.json` → 首页卡墙。**`working` 是时间派生(updated<120s)→需周期 tick 重算，否则「进行中」徽章不灭**；cover=`/p/<pid>/artifacts/<rel>`
- `system/version` ← `VERSION` + 内存 `_latest_version` → 侧栏版本/更新条（全局 `/api/version`、`/api/update-check` 无 `/p/` 前缀；**可保留 60s 轮询，不值得 watcher**）

**非频道（保持 request/response）**：
- `canvas` ← `canvas.json`（per-stage '3'/'4'；**本客户端**防抖 600ms 写，`_CANVAS_LOCK` 串行）→ 用户自有布局，**不回推**（与实时拖拽打架）。`enterCanvas` GET + 防抖 POST + 离开 flush
- `deploy-creds` ← `~/.productflow/secrets/<pid>.env`（600，API 仅回显掩码）→ 乐观更新+refetch，**绝不推明文**
- 纯副作用 RPC：`/api/reveal`、`/api/update`（无 channel）

---

## 执行阶段（逐步；每阶段带 verify）

- **P0 盘点&计划** ✅ 完成（inventory workflow + 完备性评审 → `web/.migration/inventory.json` + 本文件）
- **P1 脚手架&基建** ✅ 完成&验证：Vite+React+TS（`web/`）→ 构建到 `productflow/assets/dist/`(base `/dist/`)；global.css 逐字搬入(536 行)；server `_console()` 受 `PF_UI=dist` 门控 serve dist、`/dist/*` 长缓存、否则回退旧 console；`/api/version` 形状不变。已验证：dist serve / 长缓存 / 旧版回退三态。
- **P2 WebSocket 传输**：
  - 服务端 ✅ 完成&验证：`do_GET` 内手写 RFC6455 升级(101 + Sec-WebSocket-Accept，强制 HTTP/1.1)+`_host_ok`+Origin 校验；双线程(reader 处理 ping/close、本线程 ~0.6s 扫描 push-on-change，md5 负载指纹)；14 个 project 频道 + 2 个 home 频道 payload 与 GET 逐字一致(`_ws_channel_payload`)。已验证：home/project 两作用域握手 101 + 全频道初始快照。
  - 客户端 ✅ 完成&验证：`web/src/bus.ts` 全局 WS（重连退避）→ `web/src/store.ts`（0 依赖 Slice + useSyncExternalStore，按频道订阅=局部渲染）。已验证：home 页 WS 连上、4 个真实项目从 `projects` 频道渲染。
  - 待补：push-on-change 实测 + WS handshake/payload-parity 进 test 套件（P5 或随手补）
- **P3 React 共享层** ✅ 完成：`types.ts`、`store.ts`、`bus.ts`、`lib.ts`(PF_BASE/relTime/artUrl/post)、`icons.tsx`、`components/{Sidebar,Toast,UpdateBar}.tsx`。tsc 通过。
- **P4 逐屏迁移**（进行中，每屏 diff 比对）：
  - ✅ ① 首页卡墙 `screens/Home.tsx`（projCard/ghostCard/archive）——**diff 比对通过：与旧版 console 首页像素一致；flicker 探针 5s 内封面图重取=0（旧版每 3s 重取→闪）；0 console error**。遗留：新建/删除 modal 暂 toast 占位（随 ⑦ 端口）
  - ✅ ② 项目壳：`components/{Project,Stepper,Board,ChoicesBar,ChatDrawer,Modal,DocIcon}.tsx`——topbar(back/product/stepper/💬留言+未读点/📋全部产物/meta/下一步) + 兼容横幅 + choices 浮条(选项+自由文本，本地输入态=打字不被打断) + view-board(health-line/steps/gallery/log) + 聊天抽屉(inbox 3 种消息体/Enter 发/粘滚) + 基础 Modal(图/文本)。**diff 比对通过：product/7 胶囊/meta「4/7 完成」/`.sel`=开发实现(与 done 解耦)/5 steps/WS 连上/gallery 4s 重取=0/0 error，与旧版指标一致**。
    - 明确暂留(后续屏端口)：stage-extra 面板=③；canvas 视图=④；全部产物 overview + markmap=⑥；新建/删除 modal=⑦
  - ⏳ ③ 面板：
    - ✅ P5/6/7 runStage：`components/{StageRunPanel,DeployCredsCard}.tsx`——平台自适应主按钮(APP→构建并产出上线分发包)、⑥ iOS 预览按钮(📱构建并在模拟器预览)、reveal-code 的 navigator.platform Mac 嗅探(critic#4)、deploy-creds(request/response 非频道、绝不推明文)、running/waiting 来自 agent-log:stage-N 频道的服务端运行时标志、409 双击护栏。**diff 比对通过：s6/s7 按钮文本与旧版逐字一致、deploy-creds 卡在、0 error**。⑥ 圈选 previewSection 暂留 ⑤。
    - ✅ P1 brief 面板：`components/BriefPanel.tsx`——ref+force 模型忠实复刻原命令式 reconcile(confirm-lag：本地 confirmed 保到 server 跟上；generating/failed 由 server request 槽派生)；fold 澄清累加；市场调研卡(running/failed 从 agent-log:research 尾行派生)。**diff 比对通过：cards/summary 4 行/按钮文本与旧版逐字一致、0 error**。（TS 静态检查当场抓到漏初始化 `failed` 字段——正是 ts 价值）
    - ✅ P2 refs 面板：`components/RefsPanel.tsx`——风格标签(STAGE_TAGS 10)、ref 网格(选中/删除/🔍放大/🔗源/＋类似)、Viewer.js(从 /vendor 动态加载、隐藏画廊、open 时跳过重建)、搜索/采集/more-like、searchFailed 来自 agent-log:search-refs。**diff 比对通过：tags=10/refs=15/按钮文本一致、Viewer 加载并能放大、缩略图 3.5s 重取=0、0 error**。
  - **③ 完成**（P1 ✅ + P2 ✅ + P5/6/7 ✅）。
  - ✅ ④ 画布：`components/Canvas.tsx`（+内联 HeroDialog）——transform math 逐字移植(cvApply/zoomAt/zoomBy/fit)、pan/drag/wheel 用 addEventListener(wheel passive:false)、拖拽命令式改 DOM+pointerup 提交、interacting ref 替代 cvDragging 守卫、per-stage 布局 GET+防抖 POST+离开/卸载/**beforeunload flush(新增，修旧版拖后关页丢布局)**、cv.notes 透传保留、hero 卡(基调/删除)+page 卡(平台矩阵 on/off→预览/生成)、stagebar(③genHeroes / ④runPageMap+批量+整理+手动添加)、hero-dialog(图N 代号+勾选+生成记录+insertRefCode 光标)。**diff 比对通过：③18 卡+hero-dialog+controls+滚轮缩放(73%→126% transform 变)、④13 卡×3 平台徽章、canvas 图 3s 重取=0、仅 1 个 404(旧版同样 404 且 3×=预存数据瑕疵非回归)**。⑤改图 overlay 暂留 P4⑤(双击暂走图片预览)。
  - ✅ ⑤ 圈选/改图 overlay：`components/{PreviewOverlay,PreviewSection}.tsx`——归一化 0-1 框选(getBoundingClientRect/toFixed4/<0.02 拒)、feedback 模式(每框 prompt→inbox preview-feedback+可选重跑⑥)vs redraw 模式(共享 instr；框=inpaint /api/redraw、无框+stage3=gen-heroes baseImage、无框+其他=整图 /api/redraw)——**3 条路径 + 反馈文本串逐字**；⑥ previewSection 缩略图(state phase-6 图)；画布双击→openRedraw。**diff 比对通过：⑥12 缩略图+feedback overlay+Esc 关；④双击→redraw overlay(instr 显示)+画框成功+动作文案随框数翻转(整图改→重绘选中区域)、0 回归**。
  - ✅ ⑥ modal markmap + overview：`Modal.tsx` 扩展——mindmap 用 /vendor d3+markmap-lib+markmap-view 顺序加载、Transformer+Markmap.create、灰阶 palette 按 node.state.path 深度索引(逐字)、box.wide；overview 跨阶段聚合(brief 摘要/refs/heroes/pages×平台/各阶段 artifact，OvImg/OvDoc 卡)。**diff 比对通过：overview 6 段 block+63 图、markmap 渲染(wide+26 个 g 节点)、0 error**。
  - ✅ ⑦ 新建向导 + 删除 modal：`components/{NewProjectModal,DeleteModal}.tsx`——名称/slug(autoSlug+CJK 随机回退+slugEdited)、平台多选卡+主平台单选+可拖优先级、localStorage 草稿恢复；删除两档(软移除/彻底删除按精确输名解锁)。**diff 比对通过：向导 3 平台卡+3 主平台+优先级 2→3(APP 加入)+slug 自动'test'、删除两档+hard 按钮 init/错名 disabled、精确名 enabled、0 error**。⑧ 更新条✅/兼容横幅✅/toast✅
  - **✅ P4 全部 7 屏完成 + diff 验证**（①Home ②shell ③面板 ④画布 ⑤圈选 ⑥modal/overview/markmap ⑦向导/删除）。
- **P3 React 共享层**：所有 payload 的 TS 类型；bus→store slice；POST API 封装(PF_BASE)；共享组件(sidebar 232↔64 / topbar / toast / modal / Lucide 内联图标 / btn)。verify：tsc 通过、侧栏折叠 diff
- **P4 逐屏迁移**（闪烁优先；每屏对照 Diff 清单）：① 首页卡墙 → ② 项目壳(topbar+stepper+board) → ③ 面板(P1 brief/P2 refs+Viewer/P5-7 runStage+iOS 预览+平台文案/deploy-creds/choices/chat) → ④ 画布(P3 hero/P4 pages：pan/zoom/drag+hero dialog+stagebar+持久化) → ⑤ 圈选/重绘 overlay → ⑥ modal(图/html/文本/markmap)+overview → ⑦ 新建向导+删除(localStorage 草稿) → ⑧ 更新条+兼容横幅+toast
- **P5 构建&切换&验证** ✅ 完成：
  - ✅ 默认翻到 dist（server `_console()` 默认 serve React，`PF_UI=legacy` 显式回退旧 console）；:7717 已重启到新 React 应用。
  - ✅ WS 测试入套件 `tests/test_websocket.py`（握手 101 + 14 项目频道 + home 2 频道 + **payload-parity：每频道与对应 GET 逐字相等**）；全套 **155 测试通过**（e2e_console 钉 PF_UI=legacy 测回退）。
  - ✅ Playwright 逐屏 parity sweep（home + P1-P7 全绿、0 非-404 error、封面/产物图 0 重取=无闪烁）。
  - ✅ understand-anything `understand-diff`：分析改动 blast radius（server.py 中枢、tested_by/start.sh/docs 受影响、VERSION 形状保留）、写 diff-overlay.json；KG 早于迁移→建议日后 `/understand` 刷图收录 web/ React 层。
  - ✅ **omission 审计 workflow**（inventory 136 项 vs React 端口）：找出 5 处 divergent 遗漏，**全部修复**——①system 频道补到 project 作用域(版本/更新条在项目页恢复，已验证 v2.13.0)②genAllPages 指令串改回逐字③Sidebar checkUpdate 恢复 confirm→update/非git alert④画布 P3/P4 stagebar 补失败态红字+去②/跳③导航按钮⑤聊天未读 seen 开着抽屉时同步。修后 tsc+155 测试+build 全绿。
- **迁移完成**：7 屏全迁 + 全 diff 验证 + WS 订阅取代全部 setInterval + 局部渲染消闪烁 + 编译产物交付（用户运行端零 Node）+ 旧 console 保回退。

---

## Diff 检查清单（逐屏；源自评审 diffCheckpoints，每屏迁完逐条核对）

1. **首页卡墙** `#proj-grid/#arch-grid`：grid auto-fill minmax(280,1fr) gap18；cover img vs `.ph` 首字母占位；`.pname` 内联徽章(`.badge-working`/`.hdot`+ms)；`.segs` 每阶段 5px 条(done=ink/active=dim)；`N/7 阶段 · relTime`；`.pcard.broken` opacity.6 + 目录缺失/状态损坏；ghost「CLI 待接单」；归档区。**关键：3s 刷新封面图不闪**
2. **侧栏** 232 vs 64：collapse 时 label 隐藏；`.sb-collapse` 仅 hover 显(展开态)、收起隐；logo 收起=展开/展开=回首页；nav `.on`(block bg+600)；资产/设置 stub toast；`#sb-ver` 点=检查更新
3. **7 段 stepper**：宽屏 & ≤1180px；`.sel`(ink ring+填充 num+粗 label) 与 `.done`(IC_CHECK) 解耦；1180px 仅 `.sel` 留 label、其余收数字；step-sep 18→8；选中 auto-scrollIntoView(center)；done+sel 同时=环+勾
4. **P1 Brief**：摘要 4 态(ready 4 行/running spinner/failed 红/idle)；clarify chips 单选+`#st-clarify`；按钮(重新生成+✓确认 vs 生成摘要)；市场调研卡 running/failed(琥珀)。**EDGE：poll 中输入 `#st-brief` 不被重置(focus guard)**；foldClarifications 文案逐字
5. **P2 Refs + Viewer.js**：STAGE_TAGS 逐字(极简/现代/玻璃拟态/暗色/暖色调/编辑风/科技感/大胆活力/柔和未来/瑞士国际)；`.wz-ref` 全宽真比例、选中环+暗 rbar、🔍/🔗/＋类似/✕/勾；开 Viewer 后台 push **不拆**它(refsViewerOpen guard)；不闪
6. **画布 P3/P4**：点阵网格(radial #e3e3e1 1px@22px on #f7f7f6)；默认 view{x:60,y:80,z:0.7}；zoom clamp 0.08-3；`#cv-zoom`%；+/-/fit；`.cv-hint`；`#cv-empty`。拖卡：delta/zoom 跟手；wheel 光标锚点缩放；ctrl/捏合缩放；横向 wheel 平移；**拖拽中 Agent 更新不得拽飞(cvDragging guard)**；hero base 环；page 卡比例随平台(PC 横 1440/1080 vs 手机 1080/2340)+平台矩阵 on/off。**EDGE：拖后 600ms 内关页 → 现状丢布局(无 beforeunload flush)→ 决定补**
7. **③ hero dialog** `#hero-dialog`：仅 stage3 右停 320px；本次参考缩略图+图N(按 selectedRefs 顺序)，勾选改变重编号；生成记录(生成/改图蓝徽、ts、ref/result 数、缩略图、prompt)；折叠。**关键：insertRefCode 光标位置 + 图N→--image N 顺序逐字**
8. **预览/重绘 overlay** `#pv-overlay`：两模式暗罩；画框→归一化 0-1 toFixed(4)；<0.02 拒；feedback 每框文本、redraw 共享 `#pv-instr`；编号 `.pvn`+`.pvx` 删；按钮文案随模式+框数。**关键：反馈文本串「区域(左X% 上Y% 宽W% 高H%):text」与 3 条重绘路径(stage3 无框→gen-heroes baseImage；stage3 有框 & stage4→/api/redraw)逐字**；发送后 confirm()→重跑 stage6 桥接在
9. **产物 modal + overview + markmap**：image(.full contain)；html(开新标签不弹 modal)；text/md/json(`<pre>` 转义)；mindmap(.box.wide 94vw/88vh、懒加载 d3+markmap、灰阶调色板、autoFit、initialExpandLevel:-1)。openOverview 跨阶段聚合(`P{id} {name} · count` 头、★基调)。Esc 关 modal+preview
10. **聊天抽屉/choices**：抽屉滑入 372px；Enter 发/Shift+Enter 换行；距底 30px 内粘滚；`.has-unread` 红点逻辑。choices 暖 #fffaf0 卡、阶段N 标、选项 chip+自由文本、乐观移除。**两者：poll 中打字不被打断**
11. **新建+删除 modal**：新建 name/slug(autoSlug+CJK 随机回退、slugEdited 停自动)；平台 picker(PC/H5/APP 卡+设备 SVG+primary 单选+可拖优先级)；localStorage 草稿恢复 toast。删除两档(软移除 vs 精确输名解锁红删按钮)。草稿跨刷新存、建成清
12. **更新条/兼容横幅/toast**：`#update-bar` ink 横幅(两页都有、全局 /api 路径)；`#compat-banner` phases≠7 红警列 7 段名逐字；`#toast` 底部居中 2.2s 自隐、切 stage 清

---

## 遗漏监视清单（评审发现的 10 处 do/don't —— 显式决定，别误判）

1. **死 CSS**（旧分车道画布：`.cv-lane-label/.cv-grouplabel/.cv-mapcap/.cv-divider`、整个 `.cv-page*` 家族、`.cv-page-add`，CSS 317-318/357-381）→ **不要当功能移植**（JS 从不 emit；活动渲染是 `.cv-item`/`.cv-item.page-card`）
2. **无 beforeunload flush**（拖后 600ms 内关页丢布局）→ **决定：补 beforeunload/pagehide flush**（小改进）
3. **无 `<img onerror>` 兜底**（半生成/删除中显破图标）→ **决定：加优雅兜底**（所有 artifact img）
4. **`navigator.platform` OS 嗅探**（reveal-code 按钮 Mac=在访达打开/其它=打开代码目录）→ 与 pfWizard 不同码路，**保留**
5. **`pf_state.py` 是大多数文件的共同写者** → WS 必须 **mtime watch**，不能「自己 POST 才推」（已纳入架构）
6. **agent-log gen-heroes/collect-ref 未被当前 poller 消费**（P3 hero 进度读 explore.json request 槽 + heroGenFailed）→ **parity：不接它们**（接=行为新增，先确认）
7. **`working` 时间派生 + cover 路径派生 无文件事件** → projects 频道需 **周期 tick** 重算，否则「进行中」不灭
8. **`cv.notes` 加载/POST 但从不渲染**（无渲染透传）→ **payload 里原样保留**(否则抹掉 agent/legacy 数据)；`#cv-zoom` 读数 + cv-controls fit 图标保留
9. **markmap 灰阶调色板按 `parseInt(node.state.path.split('.')[1])` 索引**（脆、依赖 markmap 内部）→ **锁定 vendored d3/markmap 版本**(继续用 /vendor 文件)
10. **单实例探测靠 `/api/version` 的 `{app:'productflow'}` 形状** → **保持逐字**，否则 start 脚本探测破

---

## 风险登记（high 优先；附缓解，源自评审 risks）

- **[H] 画布 pan/drag/zoom 控制器**：Pointer Events + setPointerCapture、3px 阈值、closest() 白名单 bail、delta/zoom、光标锚点 `x=cx-(cx-x)*k`。缓解：**math 逐字移植**(cvApply/cvZoomAt/cvZoomBy/cvFit 含 y-40/+320 不对称 padding)；wheel 用 `ref+addEventListener('wheel',{passive:false})` 非 JSX onWheel；拖拽 session 用 useRef 命令式改 transform、pointerup 才提交 state；`isInteracting` ref 暂停 store→DOM 同步(替代 cvDragging/cvEditing bail)
- **[H] 圈选归一化坐标**(#pv-stage)：frac() via getBoundingClientRect、toFixed(4) 线协议、<0.02 拒、两模式共享、结构化反馈文本 + 3 条重绘路径。缓解：坐标归一化逐字、Pointer Events+setPointerCapture+touch-action:none、分支逐字、per-box 文本模型保留(改内联输入替 window.prompt)
- **[H] render-on-poll focus guard → WS 下「别冲掉草稿」**：缓解：所有可编辑/进行中字段保 **本地组件 state**(description/clarify/answers、stylePrefs/selectedRefs、pStageRun[n].instr、researchLog.instr、hd textarea、choice 回复、pv boxes)；push 只并入非编辑字段；不 remount 含焦点字段的面板
- **[H] agent-log:stage running/waiting 来自内存 `_STAGE_RUNNING`(无文件)+choices.json；409**：缓解：WS 在 `_STAGE_RUNNING` 变更 AND choices 变更时推 stage 状态、push 带 running/waiting；保留双击 guard + 409 toast；run-stage/run-action 共用 (pid,6) guard 与 stage-6 频道
- **[H] WS 握手在 stdlib server + 静态重指向 dist**：缓解：do_GET 内手算 Sec-WebSocket-Accept、劫持 self.connection 独立线程；WS 也过 `_host_ok`(仅 127.0.0.1)+Origin 校验；`_console()` 指向 dist/index.html(no-store)、加 hashed 静态 handler、保留 /vendor 与 /p/<id>/artifacts/ 为独立 base、保 VERSION 形状、ID_RE/CRED_KEY_RE/路径穿越/删除安全闸/凭证掩码
- **[M] Brief confirm-lag/生成失败 状态机**(由 request 槽存在派生，非显式 flag)：缓解：reconcile guard 逐字(本地 confirmed=true 直到 server 跟上；generating 由 request['gen-summary'] 在、failed 由槽消失而无 ready 派生)
- **[M] Viewer.js + markmap(d3) 命令式库**：缓解：Viewer 在 useEffect 实例化(ref'd 隐藏 gallery)、refs 变 destroy()+重建、开着时跳过列表 reconcile；Markmap memo 化 ensure promise、空 svg ref、open 时 create、close cleanup、d3 先于 markmap、**锁版本**
- **[M] per-stage 画布隔离 + 防抖存目标「离开的」stage；无 beforeunload**：缓解：防抖排程时闭包捕获目标 stage id；stage 变 useEffect cleanup flush；补 beforeunload flush；保 `_CANVAS_LOCK` + per-stage cell merge；不回推自己的写
- **[M] localStorage 草稿 + HTML5 拖排序 + CJK slug 回退**：缓解：useEffect 同步 localStorage、开时恢复+toast、建成才清；splice 重排、primary 反选、slugEdited、CJK→随机回退
- **[M] 闪烁**：6 处重建 `<img>`。缓解：keyed 组件(key=id+version/file)、src 稳定、仅文件真变才动 `?t=ts`、绝不整体重建 `#cv-world`(transform 用稳定容器)

---

## understand-anything 检查点（用户要求：检查遗漏）
- 迁移中：对照 `web/.migration/inventory.json`（已含 KG 交叉核对）逐屏勾 Diff 清单
- 迁移后：`understand`(增量刷 KG) → `understand-diff`(评估改动面&风险&遗漏) → `understand-chat "新版是否覆盖 <屏/端点/交互>"` 三道闸
