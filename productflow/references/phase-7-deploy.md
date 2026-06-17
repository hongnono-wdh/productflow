# Phase 7 — 部署上线

进入第七阶段（Phase 6 已 done、用户确认开始部署）时读本文件。本阶段目标：把产品发布出去（Web 上线到可访问 URL；iOS 构建上传到 TestFlight，停在提审前）、验证可用、交付运维交接报告，并完成全流程收尾。发布路径先看平台（`primary` = PC/H5 走 Web，APP 走 iOS），详见下方 pick-target。

## 阶段启动

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 7 开始：选择部署目标"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 pick-target --status active
```

## Step 1: pick-target — 选择部署路径

发布路径由 Phase 5 选定的预设决定（预设定义见 templates.md），不要临场发明别的形态。**先看平台**——读 `.productflow/wizard.json` 的 `primary`（`PC` / `H5` / `APP`，大写，与 server.py 的 `_read_primary` 一致；缺失则从 brief.json / 产品定位推断）：

- **primary = PC / H5（Web）** → 走 Web 路径 A/B/C（按所选预设 T1/T2/T3 对应）。
- **primary = APP（原生移动）** → 走 iOS 路径 **i**（P-iOS 预设，构建上架到 TestFlight；Android 本期 TODO，见 templates.md）。

| 路径 | 适用预设 | 形态 | 手段 |
|------|----------|------|------|
| A | T1 | 静态站点 | 默认 Cloudflare Pages（deploy-cf-pages skill）；用户要本机/容器自托管 → nginx:alpine 静态托管（见下方 A 小节） |
| B | T2 | 单 Worker 托管静态资源 + API，配 D1 | wrangler（见 templates.md T2） |
| C | T3 | 全栈带后端进程 | 单机服务器或本地：①裸机 rsync+systemd+caddy 或 ②Docker compose |
| i | P-iOS | 原生 iOS App | `xcodebuild archive` → distribution 签名导出 `.ipa` → 上传 TestFlight（fastlane `pilot` / `xcrun altool` / Transporter），停在提审前（见下方 iOS 小节） |

路径与预设一一对应，不再询问用户选哪条；Web 内部选目标形态（本机/CF/服务器、Docker/systemd）有歧义时用 `choice ask` 抛到网页让用户点选（见 SKILL.md）。

**部署凭证（重要）**：服务器地址/SSH 账号/端口/token 等由用户在操作台⑦「部署凭证」表单填，存在项目仓库外的 `~/.productflow/secrets/<项目id>.env`（600，不进 git/留言）。本阶段被触发时这些值**已作为环境变量注入**你的运行环境，直接引用即可：

```bash
ssh -p "$PF_SSH_PORT" "$PF_SSH_USER@$PF_SSH_HOST"   # 用户填的 PF_SSH_* 已是环境变量
# 自定义键（如 CF_API_TOKEN）同样可直接 $CF_API_TOKEN 引用
```

iOS 路径同理：App Store Connect API key（`.p8` 文件路径 + key id + issuer id，以及 distribution 证书 / provisioning profile）也走这套凭证机制注入（用户在⑦「部署凭证」表单填，存项目仓库外 `~/.productflow/secrets/<项目id>.env`），本阶段已作为环境变量注入，直接引用即可。

安全：**不要把这些值打印进 agent-log / 产物 / 留言**（ASC key 的 .p8 内容、key id、issuer id 一律不打印、不入库）。若 `$PF_SSH_HOST` / ASC 凭证等为空（用户还没填），用 `choice ask` 或在 CLI 让用户去⑦表单补，别瞎填占位值。涉及自定义域名时先与用户确认 DNS 归属。

### 部署前 checklist（任何路径都先过一遍）

逐项验证，全绿才进入 deploy 步骤（参照 verification-before-completion，不要凭"应该没问题"放行）：

1. **秘密不入库**：`.env`、`*.key`、token 在 `.gitignore` 中；`git grep -iE "api[_-]?key|secret|password" -- ':!*.md'` 无硬编码命中。
2. **构建通过 + 测试门禁**：`npm run build`（或项目等价命令）退出码 0，T1/T2 零构建则跳过构建项；**Phase 6 测试全绿**——确认 `artifacts/phase-6/test-report.md` 已登记，且单元/集成/E2E/回归四类各为「通过」或「显式 N/A」（没有这份产物或有某类静默跳过 → 退回 Phase 6 补齐，不许带病部署）。
3. **端口/域名确认（Web 路径）**：用户已给出目标域名（或接受 *.pages.dev / *.workers.dev 默认域）；路径 C 还需确认端口空闲——Linux `ss -ltnp | grep :PORT`，macOS `lsof -iTCP:PORT -sTCP:LISTEN`。iOS 路径 i 改为确认 **Bundle ID / 凭证就位**：ASC API key（.p8 + key id + issuer id）+ distribution 证书 + provisioning profile 已注入（缺则回⑦表单补），App Store Connect 里目标 App 记录与 Bundle ID 已建好（这步是用户手动，见 iOS 小节）。
4. **部署/构建工具就位**：
   - Web：按选定路径 `command -v wrangler`（CF）/ `command -v docker`（Docker）/ `command -v caddy`（自定义域名）检测，缺失就提示用户安装或改 `npx wrangler`，不要硬跑报 command not found。
   - iOS（路径 i）：`xcodebuild -version`、`xcrun simctl list devices`，上传若用 fastlane 则 `command -v fastlane`；缺了提示用户装 **Xcode / 命令行工具 / fastlane**，别硬跑报 command not found。
5. **inbox 检查**：`python3 "$SKILL_DIR/scripts/pf_state.py" inbox`，网页端若有部署相关指示先响应。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 pick-target --status done
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 deploy --status active
```

## Step 2: deploy — 三条路径

部署中任何报错按 systematic-debugging 处理：先看部署日志找根因，不要盲目重试。

### 路径 A：Cloudflare Pages（T1）

直接调用 deploy-cf-pages skill，它覆盖 wrangler 上传、CF API 建项目、自定义域名 CNAME 全流程，不要手写重复逻辑。给 skill 的输入：静态目录（T1 为 `public/`）、项目名（用产品名 slug）、自定义域名（若用户提供）。

部署完记录两个 URL：`*.pages.dev` 默认域 + 自定义域（如有），冒烟时两个都要测。

**T1 本机/容器自托管（用户明确要本地 nginx，而非 CF Pages 时）**

纯静态站直接用 nginx:alpine 托管 `public/`，零构建、无后端进程：

```dockerfile
# Dockerfile
FROM nginx:alpine
COPY public/ /usr/share/nginx/html/
```

```
# .dockerignore — 别把流水线产物/源材料打进镜像
.productflow
artifacts
*.md
```

```bash
docker build -t <product> .
docker run -d --name <product> -p 8080:80 <product>
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/   # 期望 200
```

易踩点：
- **healthcheck / 冒烟一律用 `127.0.0.1`，不要 `localhost`**——alpine/busybox 下 `localhost` 可能解析到 IPv6 `::1`，而 nginx 默认只听 IPv4，会得到假失败。
- 这是静态托管，**不要套用路径 C 的 docker-compose / journal_mode / better-sqlite3 那套**（T1 没数据库和后端进程）。
- 不要 `COPY . .`（会把 `.productflow`/`artifacts` 带进镜像），只 `COPY public/`。

### 路径 B：Cloudflare Worker + D1（T2）

```bash
# 1. 建数据库（仅首次），返回的 database_id 写入 wrangler.toml 的 [[d1_databases]]
wrangler d1 create <product>-db

# 2. 迁移 schema（worker/schema.sql 由 Phase 5 的 schema.sql 复制而来，--remote 作用于线上库）
wrangler d1 execute <product>-db --remote --file=worker/schema.sql

# 3. 秘密一律走 secret，不写进 wrangler.toml 的 [vars]（vars 是明文进仓库的）
wrangler secret put API_KEY

# 4. 部署
wrangler deploy
```

wrangler.toml 骨架以 templates.md T2 小节为准（main 指向 worker/src/index.js，`[assets]` 托管 public/）。静态前端由同一个 Worker 的 assets 一并上线，无需再走路径 A。

### 路径 C：单机部署（T3）—— 两种形态，问用户选

目标机和登录方式以用户提供为准（把下文的 `SERVER` 换成用户给的地址；若用户说"部署在本机"则去掉 ssh/rsync、直接在本地操作）。`<user>` 用用户的登录账号（root 或普通用户 + sudo，看环境，别假设 root）。

**形态 ①：Docker（项目带 Dockerfile/compose 时优先，本机或服务器都适用）**

```bash
# 本机：直接起；服务器：先 rsync 代码过去再在服务器上跑同样命令
cp .env.example .env   # 填入随机 MAILNEST_SECRET 等真实值
docker compose up -d --build
docker compose ps      # 确认 Up
```

Docker 必备两个易踩点（实战教训）：
- **`.dockerignore` 必须排除宿主 `node_modules`**——否则 `COPY . .` 会把宿主平台编译的原生模块（如 better-sqlite3）带进 Linux 容器，启动报 `invalid ELF header`。
- **SQLite 用 `journal_mode = DELETE`，不要 WAL**——Docker Desktop(macOS) 的 bind mount 是虚拟文件系统，不支持 WAL 的共享内存 mmap，会导致写入不落盘、重启丢数据（详见 phase-6 数据持久化验证）。

**形态 ②：裸机 systemd（无 Docker 时）**

前置：目标机要有 Node + npm；T3 用了 better-sqlite3（原生模块），多数平台有预编译二进制可直接装，但 ARM/非常规 glibc 会回退源码编译——这类机器先装编译工具链 `apt install -y build-essential python3`（否则 `npm ci` 报 node-gyp / `gyp ERR! find Python`）。嫌麻烦就改用形态 ① Docker（镜像自带工具链）。

```bash
# 1. 备份旧版（回滚依赖它），再 rsync 项目代码（T3 零构建，排除过程产物与本地数据）
ssh <user>@SERVER "[ -d /opt/<product> ] && cp -a /opt/<product> /opt/<product>.bak || true"
rsync -avz --delete --exclude .productflow --exclude node_modules --exclude data ./ <user>@SERVER:/opt/<product>/
ssh <user>@SERVER "cd /opt/<product> && npm ci --omit=dev"
# .env 单独传（不在 rsync 的 git 产物里）
scp .env.production <user>@SERVER:/opt/<product>/.env
```

最小 systemd unit（`/etc/systemd/system/<product>.service`）：

```ini
[Unit]
Description=<product>
After=network.target

[Service]
WorkingDirectory=/opt/<product>
EnvironmentFile=/opt/<product>/.env
ExecStart=/usr/bin/node server/app.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
ssh <user>@SERVER "systemctl daemon-reload && systemctl enable --now <product> && systemctl status <product> --no-pager"
```

caddy 反代（自动签发 https，前提是域名 A 记录已指向服务器）。在 `/etc/caddy/Caddyfile` 追加：

```
app.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

```bash
ssh <user>@SERVER "caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy"
```

### 路径 i：iOS 构建 + 上架 TestFlight（P-iOS）—— 停在提审前

只用于 `primary = APP` 的 iOS App（P-iOS 预设）。这条不部署到服务器/CF，而是构建 `.ipa` 上传 App Store Connect 的 **TestFlight**，**到提审为止留用户手动**（理由：正式提审涉及内容合规与发布决策，不替用户拍板）。前置工具检测见上方 checklist 第 4 项（`xcodebuild -version` / `xcrun simctl` / 可选 `fastlane`，缺了提示装，别硬跑）。

凭证全程走环境变量，**绝不打印、不入库**（ASC key 的 .p8 内容、key id、issuer id、证书一律不进 agent-log / 产物 / 留言）。

```bash
# 1. archive：构建可分发归档（scheme/Bundle ID 按工程实际；Release 配置）
xcodebuild archive \
  -scheme "MyApp" \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath build/MyApp.xcarchive

# 2. export：用 distribution 证书 + provisioning profile 导出 .ipa
#    ExportOptions.plist 指定 method=app-store-connect、signingStyle、teamID
#    （证书/profile 由凭证机制提供，不在仓库里硬编码 team id 之外的秘密）
xcodebuild -exportArchive \
  -archivePath build/MyApp.xcarchive \
  -exportOptionsPlist ExportOptions.plist \
  -exportPath build/export
```

上传 TestFlight（任选其一，凭 ASC API key 认证，**不在命令行明文贴 issuer/key id 之外的秘密**，.p8 路径由 `$ASC_KEY_PATH` 这类环境变量提供）：

```bash
# 方式 ① fastlane pilot（推荐：自带重试与处理状态轮询）
fastlane pilot upload \
  --ipa build/export/MyApp.ipa \
  --api_key_path "$ASC_API_KEY_JSON"     # 由凭证机制生成的 key 描述文件，含 .p8 路径/key id/issuer id

# 方式 ② xcrun altool（无 fastlane 时）
xcrun altool --upload-app -f build/export/MyApp.ipa -t ios \
  --apiKey "$ASC_KEY_ID" --apiIssuer "$ASC_ISSUER_ID"
# 注：altool 从 ~/.appstoreconnect/private_keys/AuthKey_<key id>.p8 读私钥，由凭证机制落位，不打印内容
```

上传后用 `notarytool`/`altool` 或 ASC 网页看 build 是否进入「Processing → Ready to Test」。**到此为止**——下列 App Store Connect 步骤是正式提审前的人工动作，**留给用户手动做**，本阶段不替用户点「提交审核」，只在交接报告里列清单：

- 在 App Store Connect 建 **App 记录**、注册 **Bundle ID**（与工程一致）。
- 填 App 元数据：名称、副标题、描述、关键词、分级、分类。
- 上传 App 截图（各机型尺寸；可用 `scripts/appstore_shots.py` 抓的竞品商店截图做版式参考）。
- 填 **隐私清单（App Privacy）/ 数据收集说明**、出口合规、测试账号（如需）。
- 在 TestFlight 配测试组/测试员发内测；确认无误后再由用户点「提交审核」。

iOS 路径无线上 URL / 端口，下方 deploy done 的 log 写「TestFlight build 已上传：<构建版本号>」即可。

部署完成后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 deploy --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "部署完成：<线上 URL>"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 smoke-test --status active
```

## Step 3: smoke-test — 线上冒烟 / 构建可装验证

**Web 路径（A/B/C）**：部署成功 ≠ 线上可用，必须打真实流量验证（iOS 路径见本节末尾「iOS 路径 i」）：

```bash
# 首页 + 每个关键 API 端点，期望 200（API 也可校验响应体）
curl -sS -o /dev/null -w "%{http_code}\n" https://<线上域名>/
curl -sS https://<线上域名>/api/health
```

然后**对部署产物复跑 Phase 6 的 E2E 旅程套件**（这是冒烟的主体——curl 200 只证明进程活着，证明不了"用户能走通"；登录态、视图切换、表单反馈这类问题只有旅程测试能抓）——按项目类型选 Phase 6 用的那套：

```bash
# Node 项目（T2/T3，@playwright/test）：
BASE_URL=https://<线上域名> npm run test:e2e
# 非 Node 项目（T1 纯静态，Phase 6 落成的 tests/e2e/test_journeys.py）：
BASE_URL=https://<线上域名> python3 tests/e2e/test_journeys.py
```

E2E 全绿后，打开线上首页截图，确认渲染正常（白屏/资源 404 是 curl 测不出来的），截图存为 `artifacts/phase-7/live.png` 并登记。**浏览器工具**：操作台触发的是 headless 后台 agent，没有浏览器 MCP——直接用本机已装的 **Python Playwright（chromium headless）** 写脚本截图（或 `playwright-cli` skill），别去 ToolSearch 找 MCP：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/live.png --title "线上首页截图"
```

冒烟通过后写 `.productflow/deploy.json`（项目目录下，三字段固定）。操作台读到它会自动开始健康监测：约每 5 分钟探测一次 url，结果显示在首页项目卡片与项目看板顶部：

```bash
cat > .productflow/deploy.json <<EOF
{"url": "https://<线上域名>/", "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "method": "<cf-pages|worker|docker|server>"}
EOF
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 smoke-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 handoff-report --status active
```

冒烟失败：回到 deploy 步骤排查（路径 C 先看 `journalctl -u <product> -n 50`；CF 看 `wrangler tail`），修复后重测，不要带病出报告。

**iOS 路径 i**：没有线上 URL、没有 curl/E2E 打线上——验证对象是「上传的 build 能被 TestFlight 接收并可安装」：

1. 确认 build 在 App Store Connect 进入 **Ready to Test**（`fastlane pilot builds` 或 ASC 网页看处理状态；卡在 Processing 是正常排队，Invalid 才是失败，按 systematic-debugging 看上传日志找根因）。
2. 安装态截图作为线上截图的等价物：在 Simulator 跑一遍冒烟旅程（`xcodebuild test` 已在 Phase 6 过；这里至少 `xcrun simctl io booted screenshot artifacts/phase-7/live.png` 截关键屏，确认 Release 配置下界面正常），登记为 `artifacts/phase-7/live.png`。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/live.png --title "TestFlight 构建预览截图"
```

iOS **不写** `.productflow/deploy.json`（无 url 可健康监测——操作台的 5 分钟探测只对 Web 线上 URL 有意义），直接收尾：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 smoke-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 handoff-report --status active
```

## Step 4: handoff-report — 交接报告

写 `artifacts/phase-7/report.md`，这是用户日后运维的唯一入口文档，必含四节：

1. **线上地址**：Web 给所有可访问地址（默认域 + 自定义域 + API base）；iOS 给 TestFlight 构建版本号 + App Store Connect App 链接（无 web URL）。
2. **部署/发布方式**：走了哪条路径、关键资源名（CF 项目名 / D1 库名 / 服务器路径与 unit 名；iOS 为 scheme / Bundle ID / 上传方式 fastlane|altool）、重新部署或重新出包上传的完整命令。
3. **回滚步骤**：
   - A：`wrangler pages deployment list` 找上一版，在 CF dashboard 一键回滚，或重发上一 commit 构建产物。
   - B：`wrangler rollback`；D1 schema 变更不可自动回滚，需反向 SQL。
   - C：`ssh <user>@SERVER "rm -rf /opt/<product> && mv /opt/<product>.bak /opt/<product> && systemctl restart <product>"`。
   - i（iOS）：TestFlight 无「回滚」概念——出新 build 提升 build number 重新 archive→export→上传即可；旧 build 仍可在 TestFlight 选用。
4. **后续运维注意**：日志查看命令、secrets 轮换方式、域名/证书到期事项、已知限制；iOS 额外标注证书 / provisioning profile / ASC API key 的到期与轮换。
5. **【仅 iOS】提审前待办清单（用户手动）**：把 deploy 步骤里那份 App Store Connect 人工清单原样落进报告——建 App 记录 / 注册 Bundle ID / 填元数据 / 上传各机型截图 / 填隐私清单与数据收集说明 / 配 TestFlight 测试组 / 确认后由用户点「提交审核」。本流水线**到 TestFlight 为止**，提审与发布由用户决策。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/report.md --title "上线交接报告"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 handoff-report --status done
```

## 检查点

阶段收尾按固定顺序执行：

1. `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"` 后再继续。
2. 确认 `artifacts/phase-7/live.png` 与 `artifacts/phase-7/report.md` 均已 artifact 登记（操作台靠登记展示）。
3. `python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status done` + `log "Phase 7 完成：已上线 <URL>"`（iOS 写 `log "Phase 7 完成：TestFlight 构建 <版本号> 已上传，待用户提审"`）。
4. **全流程收尾**：检查 `.productflow/state.json` 确认 7 个阶段全部 done，然后在 CLI 向用户做交付总结——Web 给线上 URL，iOS 给 TestFlight 构建版本号 + 需用户手动完成的提审清单；各阶段关键产物清单（指向 artifacts/phase-N/）、回滚与运维入口（指向 report.md），并告知操作台可回看全部产物。这是流水线终点，无下一阶段确认。
