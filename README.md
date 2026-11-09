# AI_Physist：一个 Agent 造机器，另一个 Agent 学会使用（MuJoCo）

在 MuJoCo 中，建造 Agent 用通用零件和构造即校验的 API 自主设计机械装置并定义任务；学习 Agent 只拿到自动生成的说明书和实验接口，通过“先预测再观测”的实验形成可执行的理论，然后学会使用装置。两个 Agent 由操作系统级沙箱隔离，只通过可信裁判转交的结构化信道相连。裁判为每台装置出具可解性证书，并用孪生互换、外推与改装检验、对照组来证明学习确实来自交互。

- 方案：[`终极方案.md`](终极方案.md)
- 设计记录（隔离、避免无解、证明学会）：[`DESIGN.md`](DESIGN.md)
- 研发过程记录（做法、问题、转向，汇报用）：[`docs/process.md`](docs/process.md)
- 决策记录：[`docs/decisions.md`](docs/decisions.md)；工作日志：[`docs/worklog.md`](docs/worklog.md)
- 项目约定：[`AGENTS.md`](AGENTS.md)

## 环境

- macOS（隔离依赖系统自带的 `sandbox-exec`），Python 3.12，[uv](https://docs.astral.sh/uv/)。
- 真实 LLM 运行需要已登录的 `cursor-agent` CLI（`cursor-agent status`）。
- 一次 5 轮的 LLM 运行约 4 小时，请接通电源、不要合盖。运行期间会阻止空闲睡眠，但笔记本合盖加电池会强制睡眠；跨越睡眠的会话会被标为无效。

```bash
uv sync                      # 安装 mlab 及依赖（mujoco、numpy、scipy、pydantic、matplotlib）
uv run mlab selftest         # 沙箱自检；首次运行会创建学习者专用 venv（不含 mlab）
uv run pytest -q             # 默认测试集，约 1 min
uv run pytest -q -m slow     # FULL 认证元评测，约 10 min
```

## 运行

离线复现（脚本参照建造者 + 与装置无关的脚本学习者，不调用 LLM，约 2 分钟）：

```bash
uv run mlab run --run-id offline --rounds 3 --profile fast --seed 1
uv run mlab verify-log offline         # 校验哈希链信道日志
```

真实 LLM 运行（建造者和学习者都是 cursor-agent 会话，各自在沙箱中运行）：

```bash
uv run mlab run --run-id demo --rounds 3 --profile full \
  --builder cursor --builder-model claude-opus-5-thinking-high \
  --learner cursor --learner-model gpt-5.6-sol-high
```

对照实验（在同一个世界、同样的设计、同样的孪生实例上，换一个学习者重跑）：

```bash
uv run mlab rerun-learner demo --run-id demo-weak --learner-model gpt-5.3-codex   # 较弱的模型
uv run mlab rerun-learner demo --run-id demo-amnesic --learner-model gpt-5.6-sol-high --amnesic
uv run mlab rerun-learner demo --run-id demo-scripted --learner scripted           # 黑盒基线
```

导出演示（时间线、图表、MuJoCo 回放动画、Agent 产物）：

```bash
uv run python -m mlab.analysis.demo_report demo     # 写入 demo/recorded/demo/
```

## 已录制的演示

| 目录 | 内容 |
| --- | --- |
| [`demo/recorded/demo-1/`](demo/recorded/demo-1/index.md) | 正式演示：建造者 claude-opus-5-thinking-high，学习者 gpt-5.6-sol-high，3 轮 |
| [`demo/recorded/demo-1-weak/`](demo/recorded/demo-1-weak/index.md) | 对照：同样的装置和实例，学习者换成 gpt-5.3-codex |
| [`demo/recorded/demo-1-amnesic/`](demo/recorded/demo-1-amnesic/index.md) | 对照：同一强模型，每次会话前清空笔记 |
| [`demo/recorded/demo-2/`](demo/recorded/demo-2/index.md) | 第二次闭环：修复后的裁判、新世界；含两次被拒和修改，4 轮有效 |
| [`demo/recorded/llm-learner-smoke/`](demo/recorded/llm-learner-smoke/index.md) | 补充：参照装置上的 LLM 学习者冒烟运行 |

每份演示包含时间线、图表、MuJoCo 回放动画，以及建造者的设计日志和学习者的笔记、理论代码。结论汇总见 [`DESIGN.md`](DESIGN.md) 第 3 节。

## 观察窗：可视化与直播网页

浏览器里看一次运行：3D 舞台上逐次重演学习者的实验（橙色环是它的预测，半径等于容差），配合证书闸门、信道哈希链、学习过程、跨轮积累、结论页和导览。设计与隔离考虑见 D-023。

```bash
cd web && pnpm install && pnpm build && cd ..        # 构建前端（Node 24，pnpm）
uv run python -m observatory export demo-2           # 为已结束的运行导出静态包到 demo/recorded/demo-2/viz/
uv run python -m observatory serve                   # 本地服务：直播进行中的运行，也能看已录制的
```

- `serve` 会打印一个带令牌的地址 `http://127.0.0.1:<port>/#token=...`，只用浏览器打开它。Agent 的沙箱可以联网，令牌是这个服务唯一的访问控制，不要粘进任何 Agent 会话。
- 直播默认跟随最新事件，可以拖时间轴回看；“上帝视角”显示隐藏真值，直播时默认关闭。
- 不需要服务的静态版：`cd web && pnpm build && pnpm bundle`，把 `web/dist/` 放到任意静态服务器上（例如 `npx vite preview`），只含已导出的运行。

运行目录：`~/mlab-runs/<run_id>/`（可用 `MLAB_RUNS_DIR` 覆盖）。

| 目录 | 内容 | 谁能访问 |
| --- | --- | --- |
| `referee/` | 世界真值、canary、提交原文、证书、会话记录、沙箱策略、summary.json | 仅编排器 |
| `builder/` | 建造者工作区：`device.py`、`design_log.md`、`inbox/`、`outbox/` | 建造者 |
| `learner/main`、`learner/twinNN` | 学习者工作区：`notebook.md`、`theories/`、`data/`、`predict.py` | 各自的学习者会话 |
| `public/` | 哈希链信道日志、任务卡、每轮成绩单 | 公开 |

## 代码结构

```
mlab/catalog     零件、材料、隐藏物性先验
mlab/construct   构造 API（逐步物理校验）、IR、MJCF 编译、改装
mlab/sim         动作程序运行器、结果量、带噪观测
mlab/referee     证书 C0-C3、会话协议、说明书、泄漏扫描、RPC、理论评测、指标、成绩单、信道日志
mlab/agents      cursor-agent 后端、LLM 建造者/学习者、冻结 prompt、脚本学习者、参照建造者
mlab/sandbox     Seatbelt 策略、自检、canary 审计
mlab/cli         mlab（编排）、forge（建造者工具）、lab（学习者客户端，只用标准库）
mlab/analysis    演示报告、MuJoCo 回放、会话记录摘要
observatory/     观察窗后端：运行目录到事件流、裁判侧重演与曲线、静态导出、令牌保护的直播服务
web/             观察窗前端（Vite + React + three.js）
fixtures/        带标签的合格/作弊装置（裁判元评测）
scripts/diagnostics  运维诊断：C3 参考学习者方差、从会话记录还原编辑、在已录制世界中重新认证
tests/           pytest
```
