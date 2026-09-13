# 致 PR `submission/final-package` 作者的问题汇总

- **对象 PR**：`origin/submission/final-package`（作者 Terbiumhr）
- **审计依据**：`docs/writing-reviews/pr_submission_final_package_audit.md`
- **用途**：可直接转发给对方；已核实的条目均附证据位置
- **生成日期**：2026-09-12

---

## 一、已核实、无需作者行动的（告知结论）

### 1. `result1.xlsx` 的 `t=0` 行

已确认作者**有意删除**。核对官方模板后该做法成立：

| 官方模板 | 步长 | 第一个数据时刻 |
|---|---|---|
| `result1.xlsx` | 1 s | `1` |
| `result2.xlsx` | 1 s | `1` |
| `result3.xlsx` | 60 s | `60` |
| `result4.xlsx` | 60 s | `60` |

四个模板一致约定「结果表从第一个非零采样时刻开始，不含 `t=0` 初值行」。我方已按此统一归档版 `tables/q1/result1.xlsx`（删除 `t=0`，1802 → 1801 行）。

→ 如作者有不同依据，请说明。

### 2. 数值答案可信

Q2/Q3/Q4 工作簿与归档版逐单元格比对：

| 工作簿 | 比对结果 |
|---|---|
| `result2.xlsx` | 237622 + 237622 单元格，零差异 |
| `result3.xlsx` | 75482 单元格，零差异 |
| `result4.xlsx` | 交集 67100 单元格零差异（差异仅为多插一列，见第 3 条） |

数值本身没有问题。

---

## 二、需要作者修复的交付缺陷

### 3. `submission/final/results/result4.xlsx` 列数与官方模板不符

- 该版本 **23 列**，在第 21 位插入了表头为 `2`、内容全空的列（`V1 = 2`、`V2 = None`，共 3050 个空单元格）；
- 官方模板为 **22 列**：`时间\到药材中心的距离` + `0…1.9`（20 个固定位置）+ `药材表面`；
- 该版本把 `药材表面` 挤到第 22 位。

→ 请重新导出为 22 列。

### 4. `submission/final/Q3/q3_main.py` 路径解析错误

- 第 25 行 `PROJECT_ROOT = SCRIPT_DIR.parent`，使 `Q2_MODULE_PATH` / `Q2_SOLUTION_PATH` 解析为 `submission/final/Q2/...`；
- 实际目录为 `submission/final/Q2/`，`PROJECT_ROOT / "Q2"` 不存在；
- 后果：交付包在仓库布局下无法运行。

→ 请修正路径解析。

---

## 三、需要作者补充的材料

### 5. `code/q1/q1_main.py` 依赖的构建脚本未入库

- 第 441 行硬编码 `C:\Users\Terbium\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`；
- 第 33 行 `WORKBOOK_BUILDER = TMP_DIR / "q1_build_workbook.mjs"`，而 `tmp/` 已被 `.gitignore` 排除，**该文件不在仓库中**；
- 第 35 行 `DEFAULT_XLSX` 指向 `outputs/01a08acb-8a5a-72b0-bcf4-bfb4860a6dcd/result1.xlsx`，同样不存在；
- 后果：`tables/q1/result1.xlsx` **无法从仓库复现**。

→ 请把 `q1_build_workbook.mjs` 补交到非 `tmp/` 目录，并把 node 路径改为可配置或环境变量。

### 6. Q4 独立交叉验证的 4 个证据文件缺失

- `docs/handoffs/q4/README.md` 称「独立数值方法交叉验证已完成」，并引用：
  `q4_phase1_report.md`、`q4_phase2_report.md`、`q4_phase1_results.json`、`q4_phase2_compare.json`；
- 这 4 个文件在 `main` 与该 PR 分支中**均不存在**（`git ls-tree` 命中数为 0）。

→ 请补交原件；若短期无法补齐，请把该段表述改回「待补证据，暂不作为可独立追溯的结论」。

### 7. `submission/final/` 没有运行说明

该目录下没有任何 README，未写运行环境、入口命令、输入输出路径与依赖。

→ 请补 `submission/final/README.md`。

---

## 四、需要作者澄清的设计问题

### 8. `submission/final/Q{1..4}/` 与 `code/q{1..4}/` 是两套平行实现，互不引用

| 题号 | `submission/final/` | `code/` |
|---|---|---|
| Q1 | 620 行 | 499 行 |
| Q2 | 930 行 | 895 行 |
| Q3 | 1068 行 | 1046 行 |
| Q4 | 1082 行 | 903 行 |

`git grep 'submission/final'` 在 `code/`、`docs/`、`AGENTS.md`、`CONTRIBUTING.md` 中**零命中**，两套代码彼此不知情。

→ 请说明职责关系：哪一套是权威？`submission/final/` 是要**取代** `code/qN/`，还是仅作提交快照？

### 9. `code/q3/q3_validation.py` 与其结果 JSON 的键名对不上

| | 代码产出的键 | 结果 JSON 中的键 |
|---|---|---|
| PR 版本 | `diagnostic_unresolved`、`surface_equation_diagnostic` | 同左 |
| `main` 版本 | `pending_decision`、`surface_root_branch_check` | 同左 |

两边的代码与结果**各自配对**，但 PR 版与 `main` 版互有对方没有的键。

→ 请确认 PR 提交的这份 JSON 是由哪份代码产出，以便判定权威实现。

---

## 五、无需作者补充（我方归档更全）

PR 相对归档版缺少以下内容，但 `main` 上已有，无需作者提供：

- `Q3.zip`（2060177 字节原始交付包）
- `docs/writing-reviews/q3_materials_audit.md`、`docs/writing-reviews/q4_paper_review.md`
- 12 个图件：`q3_ambient_sensitivity.{pdf,png,svg}`、`q3_spatiotemporal_field.{pdf,png,svg}`、`q3_summary.{pdf,png,svg}`、`q3_cmax_threshold.svg`、`q3_moisture_profiles.svg` 及 4 个 Q4 `.svg`
- `figures/final/q3/source_zip/`（8 个可编辑图源）与 `scripts/plotting/q3/make_q3_figures.py`
- `docs/handoffs/q4/diagnostics/`（7 个诊断截图与 `q4_validation_cache.json`）

---

## 六、后续流程建议

1. 原 PR 基点 `6fb7794` 已落后 `main` 6 个提交，试合并产生 22 个文件冲突。建议**关闭该 PR**，待作者修复上述问题后，**重新同步 `main` 并按单一交付项重开**。
2. 我方已从其分支定向取材并单独提交（详见审计报告第五节），不受本清单影响。
