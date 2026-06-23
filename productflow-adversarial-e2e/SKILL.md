---
name: productflow-adversarial-e2e
version: 1.0.0
description: 一键启动 ProductFlow 操作台的「对抗式 e2e 双 loop」验证——从用户视角持续找问题 + 定时自动修复。Loop 1 后台轮换 8 个用户 persona 跑对抗 e2e、只积累问题不改码；Loop 2 定时读问题→复现→修→独立沙箱回归验证→本地提交（不自动 push）。业务用例贴 understand-anything 抽取的领域图，多实例隔离（每跑一个用户=独立进程+独立沙箱 server+独立 browser，绝不碰 :7717）。用户说「跑对抗测试 / adversarial e2e / 启动 e2e 验证 loop / 两个 loop 对抗验证 / 自动找 bug 自动修 ProductFlow」时用本 skill。
---

# ProductFlow 对抗式 e2e 双 loop

把「从用户使用角度对抗验证 ProductFlow 操作台」做成两条并行 loop，**不遗漏**地持续找问题并定时修复。引擎与用例已落在 productflow skill 里：`<productflow>/tests/e2e-adversarial/`（`PLAN.md` 规格、`harness.py` 引擎、`findings.py` 问题库、`loop1-discovery.sh` 发现驱动）。

- **Loop 1（发现）**：后台连续跑，每次轮换一个 user persona（手快乱点 / 超长&注入输入 / 断网慢网 / 多标签 / 纯键盘 / 画布重度 / 空边界 / 不读说明），对一套贴真实业务流的旅程做对抗操作，把问题追加进 `findings/findings.jsonl`（status=open），**绝不改码**。
- **Loop 2（修复）**：定时（默认每 30 分钟）读 open findings → 按严重度 crash>broken>degraded>cosmetic 复现根因 → 外科手术式修 → 在**独立沙箱实例**回归验证 → 跑测试套件 → 标 fixed + **本地 commit**（绝不 push，留人工审核）。
- **Playwright 多实例（关键）**：sync API 非线程安全 → 不靠多线程，靠**多进程**。每次跑 = 独立进程 + 独立沙箱 server（随机端口，复用 `tests/helpers.py`）+ 独立 browser；两 loop 是不同进程，互不抢、都**不碰用户的 :7717**。

## 前置
productflow 已装且 `/productflow-init` 通过（尤其 Playwright + chromium——对抗 e2e 必需）。业务基准领域图：`<productflow>/.understand-anything/domain-graph.json`（缺了可先跑 `/understand-anything:understand-domain`，但 harness 不强依赖它运行）。

## 启动（agent 执行）

**1. 定位 productflow skill 目录**：
```bash
PF="$(python3 -c "import os;print(os.path.realpath(os.path.expanduser('~/.claude/skills/productflow')))" 2>/dev/null)"
[ -d "$PF/tests/e2e-adversarial" ] || PF="$(find ~ /opt -path '*/skills/productflow/tests/e2e-adversarial' 2>/dev/null | head -1 | sed 's#/tests/e2e-adversarial##')"
echo "PF=$PF"
```

**2. 起 Loop 1（后台发现，脱离会话常驻）**：
```bash
nohup sh "$PF/tests/e2e-adversarial/loop1-discovery.sh" >/dev/null 2>&1 &
```
（脚本自带：开跑前清 `.stop`、每次 `harness.py --persona auto` 轮换一个 persona、每轮间 sleep。问题写进 `findings/findings.jsonl`。）

**3. 起 Loop 2（定时修复）**：用 `/loop` skill 起一个 30 分钟周期的修复 loop，提示词如下（逐字）：

```
ProductFlow 对抗 e2e「修复 loop」。每次触发一轮，在 productflow skill 目录的上层仓库下：
1) 读 open findings：python3 <PF>/tests/e2e-adversarial/findings.py open
2) 若无 open：报「本轮无待修问题」，结束本轮等下次。
3) 若有：按 crash>broken>degraded>cosmetic 取最高 1–2 个：看 repro/observed/console_errors 复现根因 → 外科手术式修（React 改 web/src/*、服务端改 productflow/scripts/server.py，只动相关处）→ 若动 React 则 cd web && npm run typecheck && npm run build → 用 harness 在独立沙箱实例重跑该 persona 验证不再复现（多实例隔离，不碰 :7717、不和 Loop1 抢）→ 跑 sh productflow/tests/run.sh 确认无回归 → 修好则 findings.mark('<fid>','fixed','<sha>') + 本地 git commit；改不动/非真问题则 findings.mark('<fid>','wontfix') 说明。
4) 绝不 git push（留人工审核）；本轮只本地 commit + 报修了什么、剩多少 open。
5) 绝不停 Loop 1（不碰 findings/.stop）；两 loop 靠多实例隔离并行。
```
> 注：`/loop 30m …` 是会话级（关会话即停）。要跨会话常驻请改用 `/schedule` 或 `new-workflow`。

## 观察 / 控制
```bash
tail -f "$PF/tests/e2e-adversarial/findings/discovery.log"          # 发现进度
python3 "$PF/tests/e2e-adversarial/findings.py" open                 # 当前 open 问题
python3 "$PF/tests/e2e-adversarial/findings.py"                      # 汇总
```
**收口（停两 loop）**：
```bash
touch "$PF/tests/e2e-adversarial/findings/.stop"                     # 停 Loop 1（下次迭代退出）
```
+ 删 Loop 2 的 cron（`CronDelete <jobid>`，jobid 是起 Loop 2 时返回的）；若 Loop 1 是 nohup 起的，必要时 `pkill -f loop1-discovery; pkill -f harness.py`（注意别误杀 :7717 主进程）。

## 也可不开 loop、单跑一次
```bash
python3 "$PF/tests/e2e-adversarial/harness.py" --persona auto        # 跑一个 persona 一轮
python3 "$PF/tests/e2e-adversarial/harness.py" --persona canvas-power
```

## 扩展对抗深度
发现长期 0（饱和）时，往 `harness.py` 加更狠的 journey（参 `PLAN.md` 的 persona × 旅程 × 探针），Loop 1 下次 fresh 运行会自动吃到（每轮重新 import）。
