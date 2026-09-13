# PR 审计报告：`submission/final-package`

- **PR 分支**：`origin/submission/final-package`
- **作者**：Terbiumhr `<Terbiumhr@gmail.com>`
- **提交**：`b9def88`（submission: add final source code and result workbooks）、`46e0b62`（archive: add Q3 and Q4 development artifacts）
- **合并基点**：`6fb7794`（= `origin/main`，Merge PR #3）
- **规模**：69 个文件，+12511 / −5
- **审计对象**：本地 `main` = `a900bc8`（审计时领先 `6fb7794` 6 个提交；相关成果已随 `10c12a1` 推送到 `origin/main`）
- **结论**：**不建议合并（Reject as-is）**，建议转为「定向取材 + 单独提交」

---

## 一、核心结论

该 PR 不是一次增量交付，而是相对 `origin/main` 的**平行重写**：它新增的 Q3/Q4 开发产物与本地 `main` 中已提交的 Q3/Q4 工作**同题不同源**，且**自身内部代码与数据互不一致**、**交付包无法在仓库布局下运行**，并在交付工作簿上引入一处模板违例——`submission/final/results/result4.xlsx` 违反官方模板列结构（B3）；`result1.xlsx` 的时刻起点需与归档版统一对齐模板（B4）。

被冻结的数值答案本身是可信的、且与已归档版本交叉一致；问题不在数值，而在**版本归属、可复现性与权威来源**。

---

## 二、阻断级发现

### B1. 合并会产生 22 个文件冲突，其中多项为「已提交工作的覆盖回退」

`git merge-tree --write-tree main origin/submission/final-package` 判定冲突：

| 冲突类型 | 数量 | 代表文件 |
|---|---|---|
| add/add | 20 | `code/q3/q3_main.py`、`code/q3/q3_validation.py`、`docs/handoffs/q3/*`、`figures/final/q3,q4/*`、`tables/q3/result3.xlsx` |
| content | 2 | `docs/handoffs/q3/README.md`、`docs/handoffs/q4/README.md` |

### B2. PR 的 Q3 提交文件与其自带结果**不是同一次运行**

直接统计（非 diff 推断）：

| 文件 | `main` | PR |
|---|---|---|
| `code/q3/q3_main.py` 中 `surface_root_branch` | 9 处 | **0 处** |
| `code/q3/q3_validation.py` 中 `root_branch_checks` | 2 处 | **0 处** |
| `code/q3/q3_validation.py` 中 `pending_decision` | 1 处 | 0 处 |
| `code/q3/q3_validation.py` 中 `diagnostic_unresolved` | 0 处 | 1 处 |
| `results/q3/q3_validation.json` 顶层键 | `pending_decision`、`surface_root_branch_check` | `diagnostic_unresolved`、`surface_equation_diagnostic` |
| `results/q3/q3_validation.json` 布尔检查项 | 6 项独有 | 7 项独有 |

两边**互有对方没有的键**，且代码与结果文件的键名对不上号。因此不能按「旧版/新版」简单择一：
**必须先确定权威实现，再让它重新生成结果记录。**

差异细节（PR 侧缺失、本地侧具备）：

- 本地 `q3_validation.py` 有 `pending_decision` 字段，点名 Ca=0.03 情景「离散非线性 Robin 表面方程出现多根及根分支折叠，折叠位置随界面平均方式与网格变化，故不报告唯一精确 `t_end`」；
- 本地 `q3_main.py` 提供 `surface_root_branch: str = "first"` 开关（取值 `first` / `last`，非法值报错）与 `root_branch` 参数，可显式指定根分支；
- 本地 `q3_validation.json` 含 `cases.post_Ca_0.03.options.terminal_event=false`、`post_Ca_0.03.threshold_reached=false`、`ambient_sensitivity.post_14400_Ca.0.03.diagnostic_only=true` 等防线；
- PR 的 `q3_run_summary.json` 缺失本地已有的 `data_number_format: "0.0000"`。

PR 侧具备、本地侧缺失的改进（值得取材）：

- `acceptance` 多出 5 项判定：`terminal_maximum_at_axis`、`grid_end_time_change_below_60s`、`grid_table_change_below_5e-5`、`cumulative_temperature_final_below_1e-4`、`cumulative_moisture_final_below_1e-3`；
- 把表面根诊断从验收项中**结构性剥离**，并以 `diagnostic_unresolved.included_in_overall_pass = false` 保证未解诊断不进入 `overall_pass`。这比本地单列一个 `surface_root_bracket_found` 验收项更干净。

### B3. Quantity（数值答案）全部一致——这是最强的一致性证据

对 4 份提交工作簿与已归档工作簿做逐单元格比对：

| 工作簿 | 比对结果 |
|---|---|
| `result2.xlsx` | 237622 + 237622 单元格，**零差异** |
| `result3.xlsx` | 75482 单元格，**零差异** |
| `result4.xlsx` | 交集 67100 单元格**零差异**（差异仅为 PR 多插一列，见下） |
| `result1.xlsx` | `tables/q1/` 版与 `main` 逐字节相同；`submission/final/results/` 版删 `t=0` 对齐官方模板，见 B4 |

`result4.xlsx` 的比对必须按官方模板语义解读（**此处更正了本报告初版的一处错误判断**）。

官方模板 `data/raw/problems/A题/附件/附件3/result4.xlsx` 的表头为
`('时间\到药材中心的距离', 0, 0.1, 0.2, '…', '药材表面')`，即 `0~1.9` 共 20 个固定位置 + `药材表面`，展开后为 **A + 21 = 22 列**。

| 文件 | 列数 | 表头 | 与模板一致 |
|---|---|---|---|
| 本地归档 `tables/q4/result4.xlsx` | 22 | … `1.9`、`药材表面` | ✅ 一致 |
| PR 交付 `submission/final/results/result4.xlsx` | 23 | … `1.9`、**`2`（空列）**、`药材表面` | ❌ 不一致 |

PR 版在第 21 位插入了一个表头为 `2`、内容全空的列（`V1 = 2`、`V2 = None`，共 3050 个空单元格），把 `药材表面` 挤到第 22 位。

**结论：PR 交付版工作簿违反官方模板列结构，不可采纳。** 本地归档版已正确包含实时表面列（`W3050 = 0.0525`，与本地 README 记载的「表面含水率 0.0524964」一致），**不存在「缺列」缺陷**；本报告初版据此提出的「以 PR 版为准补列」的建议作废。

### B4. `result1.xlsx` 时刻起点：submission 版删 `t=0` 对齐官方模板，归档版多一行

**经与产出方确认，`submission/final/results/result1.xlsx` 删除 `t=0` 是「有意为之」；核对官方模板后，该做法成立，本报告初版「缺陷」判定撤销。**

**先澄清两份文件**：

| 文件 | SHA256 前 12 位 | 行数 | 第 2 行 A 列 |
|---|---|---|---|
| `main:tables/q1/result1.xlsx` | `69bf683cca23` | 1802（表头+1801 时刻） | `0` |
| `PR:tables/q1/result1.xlsx` | `69bf683cca23`（与 `main` 逐字节相同） | 1802 | `0` |
| `PR:submission/final/results/result1.xlsx` | `d83af8cfcac6` | **1801（表头+1800 时刻）** | `1` |

**官方模板证据（判定依据）**——四个 `result*.xlsx` 模板的「第一个数据时刻」全部等于步长值、且不含 `t=0`：

| 模板 | 步长 | 第一个数据时刻 |
|---|---|---|
| `result1.xlsx` | 1 s | `1` |
| `result2.xlsx` | 1 s | `1` |
| `result3.xlsx` | 60 s | `60` |
| `result4.xlsx` | 60 s | `60` |

因此官方约定为「结果表从第一个非零采样时刻开始，不含 `t=0` 初值行」。据此：

- **`submission/final/results/result1.xlsx`（`t=1…1800`，1800 时刻）对齐官方模板，正确；**
- **归档版 `tables/q1/result1.xlsx`（`t=0…1800`，1801 时刻）多出 `t=0` 一行，偏离模板；**
- `docs/handoffs/q1/model_spec_q1.md:106`「`t=0` 一行严格按题给初值写为 `T=28、C=2.55`」与本模板约定**冲突**，需修订。

**待裁定项（需团队决定）**：

1. 归档版 `tables/q1/result1.xlsx` 是否删除 `t=0` 行、对齐官方模板（`t=1…1800`）？
2. 若删，`docs/handoffs/q1/model_spec_q1.md:106` 的「`t=0` 写初值」条款须同步修改。

**附带风险（与 t=0 无关，独立存在）**：绘图脚本 `scripts/plotting/q1/make_q1_spatiotemporal_figures.py` 的 `load_field()` 按数组下标取数（`rows[0]` 当坐标轴、`rows[1:]` 当数据），不做时间值校验。任何「行数与表头约定不一致」的工作簿喂入都会**静默**丢末点并整体左移。建议后续改为按时间值定位或加 `time_s[0]==0` 断言（加固项，见第五节第 4 条）。

> 说明：本报告初版先后将此处描述为「表头丢失 + 整体错位一行」→「删除 t=0 整行（缺陷）」。前者因误用 `sharedStrings.xml` 判据（该工作簿用 inline string）所致；后者经与产出方确认意图、并核对官方模板起始时刻后撤销。

### B5. 同题两套（乃至三套）求解器并存，违反仓库唯一实现约定

PR 引入 `submission/final/Q{1..4}/` 与既有 `code/q{1..4}/` 并存，且互不引用（`git grep 'submission/final'` 在 `code/ docs/ AGENTS.md CONTRIBUTING.md` 中无任何命中）：

| 题号 | `submission/final/` | `code/` |
|---|---|---|
| Q1 | 620 行 | 499 行 |
| Q2 | 930 行 | 895 行 |
| Q3 | 1068 行 | 1046 行 |
| Q4 | 1082 行 | 903 行 |

更严重的是 Q3 形成**三个变体**：`code/q3/`（本地权威）、PR 的 `submission/final/Q3/`、PR 重写的 `code/q3/`（`46e0b62` 注入）。`AGENTS.md` 要求「每个定量结论必须可追溯到唯一来源」、`CONTRIBUTING.md` 要求「结果可由已提交的代码和输入复现」，三套变体会直接破坏可追溯性。

### B6. 交付包在仓库布局下无法运行

`submission/final/Q3/q3_main.py` 设置：

```
SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent          # → submission/final
RESULTS_DIR  = SCRIPT_DIR                 # → submission/final/Q3
TABLES_DIR   = SCRIPT_DIR
Q2_MODULE_PATH  = PROJECT_ROOT / "Q2" / "q2_main.py"        # → submission/final/Q2（不存在）
Q2_SOLUTION_PATH = PROJECT_ROOT / "Q2" / "results" / "q2_solution.npz"  # 不存在
```

实际布局是 `submission/final/Q2/`，因此该路径解析**指向不存在的目录**；`submission/final/` 下也没有任何 README 说明运行方式与依赖。同类问题出现在 PR 新增的 Q3 诊断脚本：它们把 `q3_solution.npz` 解析到 `code/q3/q3_solution.npz`（脚本父目录的父目录），而该文件实际位于 `results/q3/`，直接运行必然 `FileNotFoundError`。

### B7. 缺失 `submission/final` 所依赖的独立交叉验证证据

PR 的 `docs/handoffs/q4/README.md` 声称「独立数值方法交叉验证已完成…证据文件为 `q4_phase1_report.md`、`q4_phase2_report.md`、`q4_phase1_results.json`、`q4_phase2_compare.json`」，但这 4 个文件在 `main` 与 PR 中**均不存在**（`git ls-tree` 命中数 0）。

本地 `main` 对此的表述遵循更严格的证据标准：「这些数字目前只能作为待补证据的交接信息，正式论文在补齐原始记录前不应把它们写成可独立追溯的验证结论」。PR 反而放宽了该限制（改为 "Independent cross-validation passed"）。**这是把未具证据的结论写入交接文档，与 `AGENTS.md` 的「不得编造实验或模型性能」直接冲突。**

### B8. PR 使现有仓库内容净减少

PR 未包含本地已有的：

- `Q3.zip`（2060177 字节原始交付包）；
- `docs/writing-reviews/q3_materials_audit.md`（6319 字节）、`docs/writing-reviews/q4_paper_review.md`（5188 字节）审计记录；
- 12 个图件：`q3_ambient_sensitivity.{pdf,png,svg}`、`q3_spatiotemporal_field.{pdf,png,svg}`、`q3_summary.{pdf,png,svg}`、`q3_cmax_threshold.svg`、`q3_moisture_profiles.svg` 及 4 个 Q4 `.svg`；
- `figures/final/q3/source_zip/`（8 个可编辑图源）与绘图脚本 `scripts/plotting/q3/make_q3_figures.py`；
- `docs/handoffs/q4/diagnostics/`（7 个诊断截图与 `q4_validation_cache.json`）。

PR 也确实**没有删除**任何文件（`--diff-filter=D` 为空），但合并后这些既有产物仍面临被冲突解决误覆盖的风险。

---

## 三、通过项

| 检查项 | 结果 |
|---|---|
| 原始数据未被修改 | ✅ `data/` 无改动 |
| 无密钥/令牌/个人身份信息 | ✅ 未命中；作者邮箱为个人邮箱，属正常协作信息 |
| 无绝对个人路径 | ✅ 未发现 `/Users/`、`/home/`、`C:\` 等硬编码 |
| 无 `.venv/`、`build/`、`tmp/`、`__pycache__`、`.DS_Store` 混入 | ✅ |
| 图片/工作簿按 binary 标记 | ✅ 与 `.gitattributes` 一致 |
| 论文负责人专属区域 | ✅ 未触碰 `main.tex`、`contents/`、`config/`、`cumcmthesis.cls`、`preview.tex` |
| 提交信息可读 | ✅ 注明题号与内容 |
| 数值答案可交叉验证 | ✅ Q2/Q3/Q4 与已归档逐单元格一致（见 B3） |
| PR 新增 Q3 诊断脚本可复现 | ✅ 实测通过（见下） |

### 可复现性实测

在冻结数据 `results/q3/q3_solution.npz` 上实跑 PR 新增的两个诊断脚本：

- `q3_low_ca_diagnostic.py`：产出与 PR 提交的 `results/q3/diagnostics/q3_low_ca_diagnostic.json` **逐字节一致**。
  记录到 `t = 43200 s` 时外层控制体表面方程有 **3 个根**（0.163889、0.037094、0.030557），`t = 108000 s` 后回到 1 个根——复现了 B2 所述的根分支折叠现象。
- `q3_long_time_decay_check.py`：产出与 PR 提交的 `q3_long_time_decay_check.json` 仅有**最后一位浮点差异**（`slope_per_s` 尾数 `…346` vs `…351`），结论一致（`supports_near_exponential_late_decay: true`）。

结论：这两个新增诊断脚本**逻辑正确、值得取材**，仅需修正数据路径（B6）。

---

## 四、取材过程中发现的数值可复现性问题（独立发现）

为移植上述 5 项判据，在**当前机器**（Python 3.14.6 / NumPy 2.5.3）上实跑了 `code/q3/q3_validation.py`（耗时 46.2 s，原归档记录为 188.5 s）。与该分支归档版 `results/q3/q3_validation.json` 对比：

| 项目 | 结果 |
|---|---|
| `formal` 正式结果 `end_time_s` | `205818.35096859455` → **完全一致** ✓ |
| 5 个算例的 `t_end` | 相对差 `1.6e-11` ~ `1.7e-8`（浮点噪声级） |
| `post_Ca_0.03` 末态最大水分 | `0.17644898938869652` → `0.18470611470830603`（**+4.68%**） |
| 16 项 `acceptance` 判定 | 两版全部为 `true` |

**判定：**

- `formal` 逐位一致，说明**论文正式引用的结果可复现**，这是最关键的一点；
- `post_Ca_0.03` 的 4.68% 变化**不是数值噪声**，而是 B2 所述「离散非线性 Robin 表面方程根分支折叠」的直接后果——该情景的结果本就依赖离散化与求解路径，**不具备唯一性**。这反向印证了当初「不为其报告精确终止时刻、仅作离散敏感性局限」的决定是正确的；
- 该数值**未被正文或文档引用**（`grep '0.1764\|0.1847' contents/ docs/` 无命中），因此不影响现有论证；
- **处置**：不提交重跑结果，保留归档版并仅并入 5 项派生判据。若日后需要重跑验证，应先确认 `formal` 是否仍逐位一致，并接受病理情景可能给出不同数值。

**遗留建议**：`q3_validation.py` 的病理情景数值不确定性宜在 `docs/handoffs/q3/README.md` 中显式声明（例如「Ca=0.03 情景的末态量随环境浮动，不得作为结论引用」），以免后续被误当作稳定结果写入论文。

**副产物**：验证脚本在重跑时会顺带改写 `results/q3/q3_run_summary.json`（仅去掉文件末尾换行）。重跑后需检查并还原该文件。

---

## 五、建议处置

**不要合并该 PR。** 改为按以下顺序定向取材：

1. **删除 PR 对 `code/q3/`、`code/q4/`、`results/`、`figures/`、`tables/`、`docs/handoffs/` 的重写**——这些内容相对本地 `main` 已经是过时或被取代的版本，合并即回退。
2. **单独提交 PR 新增的两个 Q3 诊断脚本**，并修正数据路径为 `results/q3/q3_solution.npz`：
   - `code/q3/diagnostics/q3_low_ca_diagnostic.py`
   - `code/q3/diagnostics/q3_long_time_decay_check.py`
   附对应 `results/q3/diagnostics/*.json`（已实测可复现）。
3. **Q4 工作簿维持本地归档版，不采纳 PR 版**：本地 `tables/q4/result4.xlsx` 为模板正确的 22 列（含实时表面列），PR 版为违反模板的 23 列（第 21 位多出表头 `2` 的全空列）。**无需改动 `tables/q4/result4.xlsx`。**
4. **`result1.xlsx` 时刻起点已统一为模板口径**（B4）：`submission/final/results/result1.xlsx`（`t=1…1800`）对齐官方模板；归档版 `tables/q1/result1.xlsx` 已删除 `t=0` 整行（1802 → 1801 行），删后与提交版时刻口径一致。**待同步的连带项**：(a) `docs/handoffs/q1/model_spec_q1.md:105-106` 的「`t=0` 写初值」与「A 列 `0…1800 s`」条款；(b) `docs/handoffs/q1/q1_results.md:86-87`、`docs/writing-reviews/q1_materials_review.md:11` 的范围描述；(c) **论文正文 `contents/sections/05_problem_1.tex:9,91` 仍称「输出文件中的 `t=0` 行严格保留题给初值」，与本次删行及 `contents/sections/06_problem_2.tex:101`（「题目指定结果表从 `t=1 s` 开始填写」）矛盾，需论文负责人修订**；(d) 绘图脚本 `load_field()` 按下标取数、无时间值校验，建议改为按时间值定位或加断言（加固项，独立于 t=0）；(e) 本地 `code/q1/q1_main.py` 硬编码 Windows 路径、依赖未入库的 `tmp/q1_artifact/q1_build_workbook.mjs`，导致 `result1.xlsx` 无法从仓库复现导出，须一并处理。
5. **保留本地 `code/q3/` 为权威实现，移植 PR 的 5 项验收判别**（已完成）：这 5 项均为既有输出的纯派生式，无需重算。为避免覆盖冻结记录，只把派生结果并入归档版 `results/q3/q3_validation.json`，其余数值逐字未动（见第四节）。
6. **恢复交接文档的严格表述**：`docs/handoffs/q4/README.md` 应保留「独立交叉验证证据缺失、补齐前不得写成可独立追溯结论」的限定（B7）；同时保留本地 README 中的精确数值与图文对应关系。
7. **就 `submission/final/` 是否入库做出决策**。若要保留，必须：(a) 明确它是唯一权威来源，并同步退役 `code/qN/` 或改为引用它；(b) 修正 `PROJECT_ROOT` 路径解析；(c) 补写运行说明与依赖清单（B5、B6）。
8. 若上述修订完成，应**重新发起一个基于最新 `main` 的 PR**，而不是继续在 `submission/final-package` 上追加提交——该分支的基点已落后 6 个提交，继续叠加只会扩大冲突面。

---

## 六、复现本审计的命令

```bash
git fetch origin --prune
git log --oneline origin/main..origin/submission/final-package
git diff --stat origin/main...origin/submission/final-package
git merge-tree --write-tree --name-only main origin/submission/final-package   # 冲突清单
git diff main origin/submission/final-package -- code/q3/ results/q3/ docs/handoffs/
```

工作簿逐单元格比对见本报告 B3/B4 两节；诊断脚本复现见第三节末尾。
