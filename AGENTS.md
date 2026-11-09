# 项目约定（claude/）

本文件约束在 `claude/` 下工作的所有人和编码 Agent。被测的建造 Agent 和学习 Agent 在项目树外的私有目录中运行，看不到本文件。

## 0. 事实来源与留痕

- 方案：`终极方案.md`，包括宏观设计和细节设计。方案变更时同步修改该文件，并在决策记录里登记。
- 决策：`docs/decisions.md`，采用 ADR 格式，编号为 `D-xxx`。只追加不删除；被推翻的条目标注 `Superseded by D-yyy`。
- 工作日志：`docs/worklog.md`。每次工作会话追加一条，写清做了什么、如何验证、验证结果、遗留问题和下一步。
- 过程记录：`docs/process.md`，面向汇报的叙事版本，按阶段写“做了什么、遇到什么问题、依据什么判断、方向怎样调整”，并附证据指针。每次出现方向调整、走了弯路或推翻原计划时都要同步更新；作废的运行目录改名保留，不删除。
- 冲突处理顺序：代码与方案冲突时，先登记决策或修改方案，再改代码。不允许在代码里悄悄偏离方案。

## 1. 目录与依赖边界

```
mlab/catalog     零件、材料、隐藏物性先验；采样 theta_world
mlab/construct   构造 IR、逐步校验、自然语言描述、编译为 MJCF
mlab/sim         按动作程序运行仿真、加噪声、计算结果量
mlab/referee     证书、会话协议、考试、理论评测、说明书、泄漏扫描、报告、信道日志
mlab/agents      Agent 后端（cursor-agent / codex）、冻结的 prompt、
                 builders/（脚本参照建造者）、learners/（与装置无关的脚本学习者）
mlab/sandbox     沙箱策略、自检、canary 审计
mlab/cli         forge（建造者工具）、lab（学习者客户端，只用标准库）、mlab（编排入口）
mlab/analysis    作图、回放、demo 报告
observatory/     观察窗后端（只读事件流、裁判侧重演、静态导出、直播服务）
web/             观察窗前端（TypeScript）
fixtures/        带标签的合格装置与作弊装置，仅用于测试和裁判元评测
tests/           pytest
```

- 依赖方向：`catalog -> construct -> sim -> referee -> agents/cli/analysis`，禁止反向 import。`observatory` 只 import `mlab`，`mlab` 不得 import `observatory`。
- `observatory/` 和 `web/` 必须留在 `mlab/` 之外：建造者的沙箱能读 `mlab/`，观察窗的接口和令牌位置不能进入 Agent 可读的范围（D-023）。观察窗只读运行目录，不得写任何 Agent 可见的位置。
- `mlab/cli/lab.py` 会被复制到学习者工作区，因此只能使用标准库，不得 import `mlab`。
- 本目录自成一体，不 import 工作区里 `codex/`、`gemini/` 或根目录 `src/` 下的任何代码。
- `fixtures/` 与 `tests/` 在运行时必须对两个 Agent 都不可见，由沙箱策略保证。

## 2. 红线（违反即视为 bug）

1. 学习者侧代码（`mlab/agents/learners/`、`mlab/cli/lab.py`）与学习者 prompt 中，不得出现任何具体装置名、装置专属的分支或物理常数。脚本学习者必须与装置无关，只能使用任务卡里的公开信息。脚本参照建造者（`mlab/agents/builders/`）可以包含装置设计，但只用于离线复现，不得作为 demo 的建造者。
2. 禁止编排失败：任何“故意无解的初稿”“预设好的失败”都不允许。demo 里的失败必须来自真实运行。
3. 所有评测指标都由裁判用真值独立计算。Agent 自报的数字只作为被检验的对象，不得钳制或改写指标。
4. 学习者的 prompt 和工具在任何装置产生之前冻结，并把哈希写入 `mlab/agents/prompts/hashes.json`；之后修改必须登记决策并重新计算哈希。
5. 裁判的私有种子、隐藏参数真值、构造记录原文，不得写入任何 Agent 可见的位置。
6. 不得用单个种子、单个实例下结论；统计单元是实例。

## 3. 代码风格

- Python 3.12，必须写类型注解。跨边界的消息用 pydantic v2 模型，内部数据用 dataclass。
- 格式化遵循 `ruff format`，行宽 100；import 一律放在文件顶部。
- 物理量统一用 SI 单位，角度在代码里一律用弧度。
- 随机性必须来自显式的 `numpy.random.Generator` 和种子，禁止使用全局随机状态。
- 注释只写代码本身无法表达的约束，比如物理假设、MuJoCo 的行为细节或安全边界，不写“下一行做什么”。
- 错误信息要可执行：写清实测值、阈值和修改建议，这些信息会直接反馈给建造 Agent。

## 4. 测试与验证

- 运行 `uv run pytest`。默认测试集应在 2 分钟内跑完；更慢的测试标记为 `@pytest.mark.slow`，用 `uv run pytest -m slow` 单独运行。
- 每完成一个里程碑：先跑全部测试，再在 worklog 里记录命令和结果，然后 git 提交。
- 裁判规则的任何改动，都必须让 `tests/test_meta_evaluation.py`（合格集和作弊集）继续通过。

## 5. Git 约定

- 提交信息格式：`<type>(<scope>): <summary>`。
  - type 取值：feat、fix、test、docs、refactor、chore。
  - scope 取值：catalog、construct、sim、referee、agents、sandbox、cli、analysis、docs、repo。
- 小步提交。不提交 `.venv/`、运行产物或缓存；`demo/recorded/` 例外，它是交付物。

## 6. 运行产物

- 私有运行目录为 `~/mlab-runs/<run_id>/`，可用环境变量 `MLAB_RUNS_DIR` 覆盖。项目树内不保存任何一次运行的私有数据。
- 公开产物（报告、图、回放视频）经裁判导出到 `demo/recorded/<run_id>/`。
