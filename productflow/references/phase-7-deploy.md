# Phase 7 — 部署上线

进入第七阶段（Phase 6 已 done、用户确认开始部署）时读本文件。本阶段目标：把产品发布出去（Web 上线到可访问 URL；iOS 构建上传到 TestFlight，停在提审前；Android 构建上传 Google Play 内部测试，停在生产提审前；桌面应用打包成安装包，可选上架商店，停在提交商店前）、验证可用、交付运维交接报告，并完成全流程收尾。发布路径先看平台（`primary` = PC/H5 走 Web，APP 走原生移动——按预设走 iOS 或 Android），详见下方 pick-target。

## 阶段启动

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 7 开始：选择部署目标"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 pick-target --status active
```

## Step 1: pick-target — 选择部署路径

发布路径由 Phase 5 选定的预设决定（预设定义见 templates.md），不要临场发明别的形态。**先看平台**——读 `.productflow/wizard.json` 的 `primary`（`PC` / `H5` / `APP`，大写，与 server.py 的 `_read_primary` 一致；缺失则从 brief.json / 产品定位推断）：

- **primary = PC（桌面）** → 按预设走 **Web 路径（A/B/C，桌面 Web 站点）** 或 **路径 d（P-Desktop，桌面应用，预设在 Phase 5 `template-choice.md` 已记录）**。
- **primary = H5（移动 Web）** → 走 Web 路径 A/B/C（按所选预设 T1/T2/T3 对应）。
- **primary = APP（原生移动）** → 按所选预设走 **路径 i（P-iOS → TestFlight）**；Android（P-Android）有两条可选发布渠道，**按用户已填的凭证择一**：填了 Google Play 凭证（`$PLAY_SERVICE_ACCOUNT_JSON`）→ **路径 a（Google Play 内部测试）**；填了蒲公英凭证（`$PGYER_API_KEY`）→ **路径 g（蒲公英内测分发，国内）**；两套都填 → 用 `choice ask` 让用户选；都没填 → 提示去⑦「部署凭证」表单补（预设在 Phase 5 `template-choice.md` 已记录）。

| 路径 | 适用预设 | 形态 | 手段 |
|------|----------|------|------|
| A | T1 | 静态站点 | 默认 Cloudflare Pages（deploy-cf-pages skill）；用户要本机/容器自托管 → nginx:alpine 静态托管（见下方 A 小节） |
| B | T2 | 单 Worker 托管静态资源 + API，配 D1 | wrangler（见 templates.md T2） |
| C | T3 | 全栈带后端进程 | 单机服务器或本地：①裸机 rsync+systemd+caddy 或 ②Docker compose |
| i | P-iOS | 原生 iOS App | `xcodebuild archive` → distribution 签名导出 `.ipa` → 上传 TestFlight（fastlane `pilot` / `xcrun altool` / Transporter），停在提审前（见下方 iOS 小节） |
| a | P-Android | 原生 Android App | `./gradlew bundleRelease` → AAB 签名（upload keystore） → 上传 Google Play 内部测试（停在生产提审前，见下方 Android 小节） |
| g | P-Android | 原生 Android App（国内内测分发） | `./gradlew assembleRelease` → APK 签名 → `curl` 上传蒲公英（`$PGYER_API_KEY`）→ 得扫码安装短链（无审核、上传即用，见下方蒲公英小节） |
| d | P-Desktop | PC 桌面应用 | `cargo tauri build`（或 `electron-builder`）→ 平台安装包（`.dmg`/`.msi`/`.AppImage`）→ 签名/公证 → 直接分发或可选上架商店（停在提交商店前，见下方桌面小节） |

路径与预设一一对应，不再询问用户选哪条（唯一例外：**Android 在路径 a（Google Play）/ 路径 g（蒲公英）两渠道间按用户已填凭证择一，两套都填才用 `choice ask` 让用户选**）；Web 内部选目标形态（本机/CF/服务器、Docker/systemd）有歧义时用 `choice ask` 抛到网页让用户点选（见 SKILL.md）。

**部署凭证（重要）**：服务器地址/SSH 账号/端口/token 等由用户在操作台⑦「部署凭证」表单填，存在项目仓库外的 `~/.productflow/secrets/<项目id>.env`（600，不进 git/留言）。本阶段被触发时这些值**已作为环境变量注入**你的运行环境，直接引用即可：

```bash
ssh -p "$PF_SSH_PORT" "$PF_SSH_USER@$PF_SSH_HOST"   # 用户填的 PF_SSH_* 已是环境变量
# 自定义键（如 CF_API_TOKEN）同样可直接 $CF_API_TOKEN 引用
```

iOS 路径同理：App Store Connect API key（`.p8` 文件路径 + key id + issuer id，以及 distribution 证书 / provisioning profile）也走这套凭证机制注入（用户在⑦「部署凭证」表单填，存项目仓库外 `~/.productflow/secrets/<项目id>.env`），本阶段已作为环境变量注入，直接引用即可。

Android 路径同理：Google Play **service account JSON**（`$PLAY_SERVICE_ACCOUNT_JSON`）+ **upload keystore 及其密码/别名**（`$ANDROID_KEYSTORE` / `$ANDROID_KEYSTORE_PASSWORD` / `$ANDROID_KEY_ALIAS` / `$ANDROID_KEY_PASSWORD`）也走这套凭证机制注入（用户在⑦「部署凭证」表单填，存项目仓库外 `~/.productflow/secrets/<项目id>.env`），本阶段已作为环境变量注入，直接引用即可。

桌面路径同理：桌面签名凭证——Apple **Developer ID** 证书 + 公证用 **ASC API key**（`$ASC_KEY_PATH` / `$ASC_KEY_ID` / `$ASC_ISSUER_ID`）、Windows **code-signing 证书及密码**（`$WIN_CODESIGN_CERT` / `$WIN_CODESIGN_PASSWORD`）——也走这套凭证机制注入（用户在⑦「部署凭证」表单填，存项目仓库外 `~/.productflow/secrets/<项目id>.env`），本阶段已作为环境变量注入，直接引用即可。

安全：**不要把这些值打印进 agent-log / 产物 / 留言**（ASC key 的 .p8 内容、key id、issuer id；Android keystore 密码/别名、service account JSON 内容；桌面签名的 Developer ID 证书/ASC API key/Windows 证书密码一律不打印、不入库）。命令里只引用凭证文件路径（如 `$PLAY_SERVICE_ACCOUNT_JSON`、`$ANDROID_KEYSTORE`、`$ASC_KEY_PATH`、`$WIN_CODESIGN_CERT`），**绝不贴密钥内容**（仓库是公开的）。若 `$PF_SSH_HOST` / ASC 凭证 / Android 凭证 / 桌面签名凭证等为空（用户还没填），用 `choice ask` 或在 CLI 让用户去⑦表单补，别瞎填占位值。涉及自定义域名时先与用户确认 DNS 归属。

### 部署前 checklist（任何路径都先过一遍）

逐项验证，全绿才进入 deploy 步骤（参照 verification-before-completion，不要凭"应该没问题"放行）：

1. **秘密不入库**：`.env`、`*.key`、token 在 `.gitignore` 中；`git grep -iE "api[_-]?key|secret|password" -- ':!*.md'` 无硬编码命中。
2. **构建通过 + 测试门禁**：`npm run build`（或项目等价命令）退出码 0，T1/T2 零构建则跳过构建项；**Phase 6 测试全绿**——确认 `artifacts/phase-6/test-report.md` 已登记，且单元/集成/E2E/回归四类各为「通过」或「显式 N/A」（没有这份产物或有某类静默跳过 → 退回 Phase 6 补齐，不许带病部署）。
3. **端口/域名确认（Web 路径）**：用户已给出目标域名（或接受 *.pages.dev / *.workers.dev 默认域）；路径 C 还需确认端口空闲——Linux `ss -ltnp | grep :PORT`，macOS `lsof -iTCP:PORT -sTCP:LISTEN`。iOS 路径 i 改为确认 **Bundle ID / 凭证就位**：ASC API key（.p8 + key id + issuer id）+ distribution 证书 + provisioning profile 已注入（缺则回⑦表单补），App Store Connect 里目标 App 记录与 Bundle ID 已建好（这步是用户手动，见 iOS 小节）。
4. **部署/构建工具就位**：
   - Web：按选定路径 `command -v wrangler`（CF）/ `command -v docker`（Docker）/ `command -v caddy`（自定义域名）检测，缺失就提示用户安装或改 `npx wrangler`，不要硬跑报 command not found。
   - iOS（路径 i）：`xcodebuild -version`、`xcrun simctl list devices`，上传若用 fastlane 则 `command -v fastlane`；缺了提示用户装 **Xcode / 命令行工具 / fastlane**，别硬跑报 command not found。
   - Android（路径 a）：`./gradlew --version`、`adb --version`、`emulator -list-avds`，上传若用 fastlane 则 `fastlane --version`；缺了提示用户装 **Android Studio / Android SDK / 命令行工具**，别硬跑报 command not found。
   - 桌面（路径 d，Tauri）：`rustc --version`、`cargo --version`、`cargo tauri --version`（macOS 还需 Xcode CLT：`xcode-select -p`；Windows 需 MSVC toolchain）；Electron 备选则 `node --version`、`npx electron --version`；缺了提示用户安装对应工具链，别硬跑报 command not found。
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

**签名凭证分两种情况处理（看用户在⑦「部署凭证」表单填没填，已注入则是环境变量）：**

- **凭证齐全**（ASC API key + distribution 证书 + provisioning profile 都已注入）：走下面 archive → export 签名 `.ipa` → 上传 TestFlight 全程。
- **凭证缺失**：**仍执行第 1 步 `xcodebuild archive` 产出 `.xcarchive`**，并用 artifact 登记到 `artifacts/phase-7/`（让用户先拿到可继续的归档，不至于空手）；随后 `choice ask` / `reply` 提示用户去⑦「部署凭证」表单补齐 ASC API key / distribution 证书 / provisioning profile，补齐后再触发导出 IPA + 上传——**绝不瞎填占位的 team id / 证书硬跑**（会产出废包或报错）。

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

> **.p8 就位**：用户若是在⑦「部署凭证」表单**整段粘贴** AuthKey.p8，服务端会把它落成 `~/.productflow/secrets/<项目id>.p8` 并把路径注入 `$ASC_KEY_PATH`。altool/fastlane 默认从 `~/.appstoreconnect/private_keys/AuthKey_<key id>.p8` 找私钥，所以上传前先把它 cp 到位（不打印内容）：
> ```bash
> mkdir -p ~/.appstoreconnect/private_keys
> cp "$ASC_KEY_PATH" ~/.appstoreconnect/private_keys/AuthKey_"$ASC_KEY_ID".p8
> ```

```bash
# 方式 ① fastlane pilot（推荐：自带重试与处理状态轮询）
fastlane pilot upload \
  --ipa build/export/MyApp.ipa \
  --api_key_path "$ASC_API_KEY_JSON"     # 由凭证机制生成的 key 描述文件，含 .p8 路径/key id/issuer id

# 方式 ② xcrun altool（无 fastlane 时）
xcrun altool --upload-app -f build/export/MyApp.ipa -t ios \
  --apiKey "$ASC_KEY_ID" --apiIssuer "$ASC_ISSUER_ID"
# 注：altool 从 ~/.appstoreconnect/private_keys/AuthKey_<key id>.p8 读私钥（上面已 cp 就位），不打印内容
```

上传后用 `notarytool`/`altool` 或 ASC 网页看 build 是否进入「Processing → Ready to Test」。**到此为止**——下列 App Store Connect 步骤是正式提审前的人工动作，**留给用户手动做**，本阶段不替用户点「提交审核」，只在交接报告里列清单：

- 在 App Store Connect 建 **App 记录**、注册 **Bundle ID**（与工程一致）。
- 填 App 元数据：名称、副标题、描述、关键词、分级、分类。
- 上传 App 截图（各机型尺寸；可用 `scripts/appstore_shots.py` 抓的竞品商店截图做版式参考）。
- 填 **隐私清单（App Privacy）/ 数据收集说明**、出口合规、测试账号（如需）。
- 在 TestFlight 配测试组/测试员发内测；确认无误后再由用户点「提交审核」。

iOS 路径无线上 URL / 端口，下方 deploy done 的 log 写「TestFlight build 已上传：<构建版本号>」即可。

### 路径 a：Android 构建 + 上架 Google Play 内部测试（P-Android）—— 停在生产提审前

只用于 `primary = APP` 的 Android App（P-Android 预设，Kotlin + Jetpack Compose + Room + Gradle）。这条不部署到服务器/CF，而是构建 AAB 上传 Google Play Console 的 **内部测试（internal testing）轨道**，**到内部测试为止留用户手动推进正式发布**（理由：生产轨道提审涉及内容合规与发布决策，不替用户拍板）。前置工具检测见上方 checklist 第 4 项（`./gradlew --version` / `adb --version` / `emulator -list-avds` / 可选 `fastlane`，缺了提示装，别硬跑）。

凭证全程走环境变量，**绝不打印、不入库**（service account JSON 内容、keystore 密码/别名一律不进 agent-log / 产物 / 留言）。命令里只引用凭证文件路径，**绝不贴密钥内容**（仓库是公开的）。

```bash
# 1. 构建 Release AAB（Google Play 要求 AAB，不是 APK）
./gradlew bundleRelease
# 产物路径：app/build/outputs/bundle/release/app-release.aab
```

```bash
# 2. 签名（upload keystore；Play App Signing 由 Google 托管最终签名）
#    keystore 路径、密码、别名全部从环境变量读，绝不明文写进命令或仓库
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore "$ANDROID_KEYSTORE" \
  -storepass "$ANDROID_KEYSTORE_PASSWORD" \
  -keypass "$ANDROID_KEY_PASSWORD" \
  app/build/outputs/bundle/release/app-release.aab \
  "$ANDROID_KEY_ALIAS"
```

上传 Google Play 内部测试（任选其一，凭 service account JSON 认证，**只引用 JSON 路径，不贴内容**）：

```bash
# 方式 ① Google Play Developer API + service account JSON（推荐自动化场景）
# 使用官方 python 客户端或 gradle play publisher 插件，JSON 路径由 $PLAY_SERVICE_ACCOUNT_JSON 提供
# 示例：bundletool / gradle-play-publisher
./gradlew publishReleaseBundle \
  --track internal
# 前提：build.gradle 配置了 play { serviceAccountCredentials = file(System.getenv("PLAY_SERVICE_ACCOUNT_JSON")) }

# 方式 ② fastlane supply（有 fastlane 时推荐：自带重试与状态轮询）
fastlane supply \
  --aab app/build/outputs/bundle/release/app-release.aab \
  --track internal \
  --json_key "$PLAY_SERVICE_ACCOUNT_JSON"   # JSON 路径，不是内容

# 方式 ③ 手动在 Play Console 上传 AAB（无自动化工具时）
# 进 Google Play Console → 选应用 → 测试 → 内部测试 → 新建版本 → 上传 AAB
```

上传后在 Google Play Console 确认版本进入内部测试轨道状态。**到此为止**——下列 Play Console 步骤是正式发布前的人工动作，**留给用户手动做**，本阶段不替用户点「发布到生产」，只在交接报告里列清单：

- 在 Google Play Console **建应用记录**（package name 与 applicationId 一致）。
- 填**商店信息**：标题、简介、完整说明、截图（手机/平板各尺寸）、图标、功能图片。
- 完成**内容分级问卷**（IARC 分级）。
- 填写**隐私政策链接**。
- 填写**目标受众与内容**说明。
- 完成**数据安全表单**（收集了哪些用户数据、是否分享给第三方）。
- 在内部测试轨道确认测试员可安装、冒烟通过后，由用户手动在 Play Console 点「发布到生产」（或先升级到封测/开放测试轨道）。

Android 路径无线上 URL / 端口，下方 deploy done 的 log 写「Google Play 内部测试 build 已上传：versionCode <n> / versionName <x>」即可。

### 路径 g：Android 蒲公英内测分发（P-Android · 国内渠道）—— 上传即出可装链接，真端到端闭环

用于 `primary = APP` 的 Android App，且用户填了蒲公英凭证（`$PGYER_API_KEY`）。蒲公英是国内 App 内测分发平台：上传成品 APK 即生成扫码安装短链，**无审核、上传即用**——和 Google Play 内部测试（路径 a）相比，它不卡在提审，是这几条 App 路径里唯一能当场端到端跑通的。适用：面向国内的安卓内测分发（国内访问 Google Play 困难）。前置工具检测见上方 checklist 第 4 项（`./gradlew --version` 就位，缺了提示装，别硬跑）。

凭证全程走环境变量，**绝不打印、不入库**（`PGYER_API_KEY` 不进 agent-log / 产物 / 留言）。

```bash
# 1. 构建可安装的 Release APK（注意：蒲公英要 APK，不是 Google Play 的 AAB）
./gradlew assembleRelease
# 产物：app/build/outputs/apk/release/app-release.apk
# 若该 build 未配 release 签名，可用 assembleDebug 出 debug 签名 APK 也能装；
# 有 upload keystore 时优先 release 签名（apksigner/jarsigner，方式同路径 a，密钥从 $ANDROID_KEYSTORE 等环境变量读，绝不明文）。
```

```bash
# 2. 上传蒲公英（单步 upload API，凭 $PGYER_API_KEY 认证；buildType=android，文件字段 file）
RESP=$(curl -s -F "_api_key=$PGYER_API_KEY" \
  -F "buildType=android" \
  -F "buildInstallType=1" \
  -F "file=@app/build/outputs/apk/release/app-release.apk" \
  https://www.pgyer.com/apiv2/app/upload)
```

```bash
# 3. 自检：解析返回、确认拿到安装短链（这步能真验证「上线成功」，不像提审前那样无凭据）
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('code')==0, d; b=d['data']; print('蒲公英安装短链: https://www.pgyer.com/'+b['buildShortcutUrl'], '| buildKey:', b['buildKey'])"
# 大包（>100MB）单步若超时，改用新版两步 API（getCOSToken → PUT 到 COS → buildInfo 轮询），见蒲公英官方文档。
```

蒲公英无线上 Web URL，deploy done 的 log 写「蒲公英安装短链已生成：https://www.pgyer.com/<短链> · versionName <x>」即可；可选把二维码/安装页截图登记为 `artifacts/phase-7/live.png`（扫码即装的等价「线上截图」）。

**与 Google Play（路径 a）的区别**：蒲公英直接收成品 APK、无审核、当场可装、不依赖 Google 账号（国内友好），且**真能端到端闭环**（不停在提审前）；但它是**内测分发**不是**应用商店上架**——正式上架国内各大安卓商店（华为/小米/应用宝等）仍需各自渠道，本路径不覆盖。iOS 走蒲公英需 ad-hoc（UDID 白名单）或企业签名，本路径只覆盖 Android。

### 路径 d：桌面应用打包 + 分发（P-Desktop）—— 停在提交商店前

只用于 `primary = PC` 且预设为 P-Desktop 的桌面应用。这条不部署到服务器/CF，而是构建平台安装包并签名/公证，**到产出已签名安装包为止**（直接分发给用户下载，或可选上架 Mac App Store / Microsoft Store，**停在提交商店前**——上架审核涉及内容合规与发布决策，不替用户拍板）。前置工具检测见上方 checklist 第 4 项（路径 d）。

桌面应用一般无云后端，无线上 URL/端口；若带云后端则后端按 Web 路径另外部署。

凭证全程走环境变量，**绝不打印、不入库**（Apple Developer ID 证书/ASC API key .p8 内容/key id/issuer id；Windows 证书及密码一律不进 agent-log / 产物 / 留言）。命令里只引用凭证文件路径，**绝不贴密钥内容**（仓库是公开的）。

```bash
# 1. 构建（Tauri，推荐）
cargo tauri build
# 产物目录：src-tauri/target/release/bundle/
#   macOS: src-tauri/target/release/bundle/dmg/*.dmg  或  bundle/macos/*.app
#   Windows: src-tauri/target/release/bundle/msi/*.msi  或  bundle/nsis/*.exe
#   Linux: src-tauri/target/release/bundle/appimage/*.AppImage  或  bundle/deb/*.deb

# Electron 备选（无 Rust 时）
npx electron-builder --mac --win --linux
# 产物目录：dist/ 下各平台子目录
```

签名与公证（macOS）：

```bash
# macOS — Developer ID 证书 codesign（路径 d 用 Developer ID，不是 App Store Distribution）
# codesign 由 cargo tauri build 在 APPLE_SIGNING_IDENTITY 环境变量就位时自动执行；
# 手动触发示例（Tauri 构建后对 .app 补签）：
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: <Team Name> ($APPLE_TEAM_ID)" \
  src-tauri/target/release/bundle/macos/MyApp.app

# macOS — notarytool 公证（凭证从环境变量读，绝不明文）
xcrun notarytool submit src-tauri/target/release/bundle/dmg/MyApp.dmg \
  --key "$ASC_KEY_PATH" \
  --key-id "$ASC_KEY_ID" \
  --issuer "$ASC_ISSUER_ID" \
  --wait
# 公证通过后 staple
xcrun stapler staple src-tauri/target/release/bundle/dmg/MyApp.dmg
```

签名（Windows）：

```bash
# Windows — code-signing 证书签名（证书路径/密码从环境变量读）
signtool sign /fd SHA256 /a \
  /f "$WIN_CODESIGN_CERT" \
  /p "$WIN_CODESIGN_PASSWORD" \
  dist\MyApp-Setup.exe
# Tauri 可在 tauri.conf.json windows.certificateThumbprint + beforeBuildCommand 自动签名
```

Linux 一般免签，`.AppImage` / `.deb` 直接分发。

分发：

```bash
# 分发方式 ① 直接提供安装包下载链接（如 GitHub Releases）
# 到此为止——把安装包上传到 Release / 商店留用户手动

# 分发方式 ② 可选上架 Mac App Store / Microsoft Store
# 本流水线到产出已签名安装包为止，上架提交留用户手动（见下方人工清单）
```

上架前，下列步骤是正式提交商店前的人工动作，**留给用户手动做**，本阶段不替用户提交商店，只在交接报告里列清单：

- **GitHub Releases**：在 GitHub 仓库 Releases 页面新建 Release，上传 `.dmg` / `.msi` / `.AppImage` 安装包，填写版本说明。
- **Mac App Store（可选）**：在 App Store Connect 建 macOS App 记录 / 注册 Bundle ID，改用 App Store Distribution 证书重新构建（`APPLE_SIGNING_IDENTITY` 换成 App Store 分发证书），上传到 Transporter 或 `xcrun altool`，填 App 元数据/截图/隐私清单，确认后由用户点「提交审核」。
- **Microsoft Store（可选）**：在 Partner Center 建应用记录，打包为 `.msix`（可用 `electron-builder` 或 MSIX Packaging Tool），填商店信息/截图，确认后由用户提交认证。

桌面应用路径无线上 URL / 端口，**不写 `.productflow/deploy.json`**（无 url 可健康监测，与 iOS/Android 一致）。deploy done 的 log 写「桌面安装包已构建：<版本> / <平台>(dmg/msi/AppImage)，待用户上传 Release/商店」。

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

**Android 路径 a**：没有线上 URL、没有 curl/E2E 打线上——验证对象是「上传的 AAB 能被 Play Console 接收，并可经内部测试链接在 Emulator/真机安装运行」：

1. 确认 AAB 在 Google Play Console 内部测试轨道进入 **已发布** 状态（fastlane supply 输出 / Play Console 网页确认；上传失败按 systematic-debugging 看上传日志找根因）。
2. 安装态截图作为线上截图的等价物：在 Emulator 或真机经内部测试链接安装 App，跑一遍冒烟旅程，用 `adb` 截关键屏，登记为 `artifacts/phase-7/live.png`：

```bash
# 启动 Emulator（如有 AVD）或接真机，然后截图
adb exec-out screencap -p > artifacts/phase-7/live.png
```

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/live.png --title "Google Play 内部测试构建预览截图"
```

Android **不写** `.productflow/deploy.json`（无 url 可健康监测——操作台的 5 分钟探测只对 Web 线上 URL 有意义，与 iOS 一致），直接收尾：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 smoke-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 handoff-report --status active
```

**路径 d（P-Desktop）**：没有线上 URL、没有 curl/E2E 打线上——验证对象是「构建出的安装包能在本机正常安装并运行」：

1. 在本机安装/运行产出的安装包，验证主要功能（macOS：打开 `.dmg` 拖入 Applications 再运行 `.app`，或直接运行 `src-tauri/target/release/bundle/macos/MyApp.app`；Windows：运行 `.msi`/`.exe` 安装后启动；Linux：`chmod +x MyApp.AppImage && ./MyApp.AppImage`）。
2. 跑一遍冒烟旅程（关键用户流程），截图存为 `artifacts/phase-7/live.png` 作为线上截图等价物。

```bash
# 安装包产物位置（Tauri 构建后）：
# macOS: src-tauri/target/release/bundle/dmg/*.dmg 或 bundle/macos/*.app
# Windows: src-tauri/target/release/bundle/msi/*.msi 或 bundle/nsis/*.exe
# Linux: src-tauri/target/release/bundle/appimage/*.AppImage 或 bundle/deb/*.deb

python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/live.png --title "桌面安装包冒烟截图"
```

桌面路径 d **不写** `.productflow/deploy.json`（无 url 可健康监测——桌面应用无线上服务，与 iOS/Android 一致），直接收尾：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 smoke-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 handoff-report --status active
```

## Step 4: handoff-report — 交接报告

写 `artifacts/phase-7/report.md`，这是用户日后运维的唯一入口文档，必含四节：

1. **线上地址**：Web 给所有可访问地址（默认域 + 自定义域 + API base）；iOS 给 TestFlight 构建版本号 + App Store Connect App 链接（无 web URL）；Android 给 Google Play 内部测试链接 + versionCode / versionName（无 web URL）；桌面应用给安装包/Release 下载链接 + 版本号 + 平台列表（macOS/Windows/Linux，说明哪些已构建）（无 web URL）。
2. **部署/发布方式**：走了哪条路径、关键资源名（CF 项目名 / D1 库名 / 服务器路径与 unit 名；iOS 为 scheme / Bundle ID / 上传方式 fastlane|altool；Android 为 applicationId / 签名 keystore 别名 / 内部测试轨道上传方式 fastlane supply|gradle play publisher|手动；桌面为 Tauri 或 Electron / 签名证书类型（Developer ID / code-signing 证书）/ 分发渠道（GitHub Releases / Mac App Store / Microsoft Store））、重新部署或重新出包上传的完整命令。
3. **回滚步骤**：
   - A：`wrangler pages deployment list` 找上一版，在 CF dashboard 一键回滚，或重发上一 commit 构建产物。
   - B：`wrangler rollback`；D1 schema 变更不可自动回滚，需反向 SQL。
   - C：`ssh <user>@SERVER "rm -rf /opt/<product> && mv /opt/<product>.bak /opt/<product> && systemctl restart <product>"`。
   - i（iOS）：TestFlight 无「回滚」概念——出新 build 提升 build number 重新 archive→export→上传即可；旧 build 仍可在 TestFlight 选用。
   - a（Android）：Google Play 内部测试无传统「回滚」——出新版提升 versionCode 重新 `bundleRelease`→签名→上传；可在 Play Console 停用某版本或回退到前一个已发布版本。
   - d（桌面）：桌面应用无服务器「回滚」——出新版提升版本号重新 `cargo tauri build`→签名/公证→分发；已分发版本由用户在 Release/商店下架或替换。
4. **后续运维注意**：日志查看命令、secrets 轮换方式、域名/证书到期事项、已知限制；iOS 额外标注证书 / provisioning profile / ASC API key 的到期与轮换；Android 额外标注 keystore 备份位置与密码安全存储 / service account JSON 权限最小化 / 目标 API level 年度升级要求 / Google Play 政策合规事项；桌面额外标注 Developer ID 证书 / ASC API key / Windows code-signing 证书到期与轮换 / 公证需效期内有效证书 / 目标 OS 最低版本要求（macOS/Windows 年度变化）。
5. **【仅原生 App / 桌面应用】提审/上架前待办清单（用户手动）**：
   - **iOS（App Store Connect）**：把 deploy 步骤里那份人工清单原样落进报告——建 App 记录 / 注册 Bundle ID / 填元数据 / 上传各机型截图 / 填隐私清单与数据收集说明 / 配 TestFlight 测试组 / 确认后由用户点「提交审核」。本流水线**到 TestFlight 为止**，提审与发布由用户决策。
   - **Android（Google Play Console）**：把 deploy 步骤里那份人工清单原样落进报告——在 Play Console 建应用记录（package name 与 applicationId 一致）/ 填商店信息（标题、简介、截图、图标）/ 完成内容分级问卷（IARC）/ 填写隐私政策链接 / 填写目标受众与内容说明 / 完成数据安全表单 / 内部测试冒烟通过后由用户手动在 Play Console 点「发布到生产」。本流水线**到 Google Play 内部测试为止**，生产轨道发布由用户决策。
   - **桌面应用（P-Desktop）**：把 deploy 步骤里那份人工清单原样落进报告——上传已签名安装包到 GitHub Releases（附版本说明）；若可选上架 Mac App Store，改用 App Store Distribution 证书重新构建并通过 Transporter/altool 提交，在 App Store Connect 填元数据/截图/隐私清单后由用户点「提交审核」；若可选上架 Microsoft Store，打包 `.msix` 并在 Partner Center 填商店信息后由用户提交认证。本流水线**到产出已签名安装包为止**，上传 Release 及商店提交由用户决策。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/report.md --title "上线交接报告"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 handoff-report --status done
```

## 检查点

阶段收尾按固定顺序执行：

1. `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"` 后再继续。
2. 确认 `artifacts/phase-7/live.png` 与 `artifacts/phase-7/report.md` 均已 artifact 登记（操作台靠登记展示）。
3. `python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status done` + `log "Phase 7 完成：已上线 <URL>"`（iOS 写 `log "Phase 7 完成：TestFlight 构建 <版本号> 已上传，待用户提审"`；Android 写 `log "Phase 7 完成：Google Play 内部测试 build 已上传：versionCode <n> / versionName <x>，待用户推生产"`；桌面写 `log "Phase 7 完成：桌面安装包已构建：<版本> / <平台列表(dmg/msi/AppImage)>，待用户上传 Release/商店"`）。
4. **全流程收尾**：检查 `.productflow/state.json` 确认 7 个阶段全部 done，然后在 CLI 向用户做交付总结——Web 给线上 URL；iOS 给 TestFlight 构建版本号 + 需用户手动完成的 App Store Connect 提审清单；Android 给 Google Play 内部测试链接 + versionCode/versionName + 需用户手动完成的 Play Console 发布清单；桌面给安装包/Release 下载链接（或构建产物路径）+ 版本号 + 平台列表 + 需用户手动完成的 Release 上传/商店提交清单；各阶段关键产物清单（指向 artifacts/phase-N/）、回滚与运维入口（指向 report.md），并告知操作台可回看全部产物。这是流水线终点，无下一阶段确认。
