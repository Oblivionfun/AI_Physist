# AI_Physist：一个 Agent 造机器，另一个 Agent 学会使用（MuJoCo）

在 MuJoCo 中，建造 Agent 用通用零件和构造即校验的 API 自主设计机械装置并定义任务；学习 Agent 只拿到自动生成的说明书和实验接口，通过“先预测再观测”的实验形成可执行的理论，然后学会使用装置。两个 Agent 由操作系统级沙箱隔离，只通过可信裁判转交的结构化信道相连。裁判为每台装置出具可解性证书，并用孪生互换、外推与改装检验、对照组来证明学习确实来自交互。

- 方案：[`终极方案.md`](终极方案.md)
- 设计记录（隔离、避免无解、证明学会）：[`DESIGN.md`](DESIGN.md)
- 决策记录：[`docs/decisions.md`](docs/decisions.md)；工作日志：[`docs/worklog.md`](docs/worklog.md)
- 项目约定：[`AGENTS.md`](AGENTS.md)

## 环境

- macOS（隔离依赖系统自带的 `sandbox-exec`），Python 3.12，[uv](https://docs.astral.sh/uv/)。
- 真实 LLM 运行需要已登录的 `cursor-agent` CLI（`cursor-agent status`）。

```bash
uv sync                      # 安装 mlab 及依赖（mujoco、numpy、scipy、pydantic、matplotlib）
uv run mlab selftest         # 沙箱自检；首次运行会创建学习者专用 venv（不含 mlab）
uv run pytest -q             # 默认测试集，约 20 s
uv run pytest -q -m slow     # FULL 认证元评测，约 4 min
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
fixtures/        带标签的合格/作弊装置（裁判元评测）
tests/           pytest
```
