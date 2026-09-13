# Q4 交接与冻结状态说明

## 冻结状态

- Q4 numerical result frozen
- Formal numerical result frozen
- Internal numerical validation passed
- Independent cross-validation is described, but its raw evidence files are not included in this archive
- result4.xlsx passed the supplied workbook audit

Q4 正式主结果、2×2 条件效应分解、网格与时间积分验收、移动域库存平衡、表面根审计、官方工作簿和四类图件均已完成并冻结。正式数值方法采用附录4物性、附件2 PCHIP 移动半径、材料坐标守恒有限体积法和 BDF 同步积分，正式网格 N=2561；q4_validation.json 的 overall_pass=true。

正式终止时刻为 182956.1477926 s，即 50.8211522 h（约 2.1175480 d）；论文建议写约 50.82 h。终点半径 1.2000 cm，全域最大含水率 0.15 位于轴线，表面含水率 0.0524964。

交接材料描述了节点中心材料坐标守恒有限体积、后向欧拉和 Picard 迭代的独立交叉验证，并给出相应对拍数字；但 q4_phase1_report.md、q4_phase2_report.md、q4_phase1_results.json、q4_phase2_compare.json 未随本次 Q4.zip 提供。因此这些数字目前只能作为待补证据的交接信息，正式论文在补齐原始记录前不应把它们写成可独立追溯的验证结论；本轮修订明细见 Q4_REVISION_LOG.md。

## 表6

表6 未舍入数据位于 q4_run_summary.json 的 table6_times_s、table6_moisture 字段，四位小数版本见 q4_results.md 与论文表6。固定位置按当前真实物理距离解释；若某固定位置因药材收缩已位于当前药材表面之外，表中以“—”表示，不填浓度、也不用材料坐标值代替。药材表面列始终取 ξ=1，即实时移动表面 r=R(t) 的水分浓度。

## result4.xlsx 语义

result4.xlsx 为单一 Sheet1，3050 行×22 列。时间从 60 s 至 182940 s、每隔 60 s；表头为固定物理距离 0 至 1.9 cm（步长 0.1 cm）以及“药材表面”。对固定物理距离列，当该位置因药材收缩已位于当前表面之外时，相应单元格留空；最后一列“药材表面”始终记录实时移动表面 r=R(t) 的水分浓度。

精确终止时刻 182956.1478 s 不是 60 s 规则节点，因此工作簿只保存不超过终止时刻的最后一个 60 s 规则节点，末行为 182940 s，不另外加入一行；精确终止时刻在正文、表6和运行摘要中单独报告。工作簿审计记录位于 result4_workbook_audit.json，独立审核判定为 ACCEPT。

## 2×2 效应口径

四工况 C/D/A/B 为条件反事实组合，不是严格因果分解：A−C 记为“固定半径条件下的物性条件效应”，D−C、B−A 分别记为对应物性条件下的收缩效应，I 记为“非加性交互项”；各效应不能简单线性相加。详见 q4_results.md 第 3 节。

## 文件角色

- q4_main.py：正式数学模型、移动半径、有限体积、BDF、全域事件、表6抽取及未舍入结果保存。
- q4_validation.py：正式程序的网格、容差、步长、Robin、积分平衡、终点和 Q3 基准复现验收。
- q4_solution.npz：N=2561 未舍入正式结果及绘图快照。
- q4_run_summary.json：正式设置、终点、表6和交付检查索引。
- q4_validation.json：完整数值验收记录，overall_pass=true。
- q4_effect_decomposition.json：C/D/A/B 四工况和交互项；字段名为历史命名，正文术语以本说明和 q4_results.md 为准。
- q4_surface_root_audit.json：4097 点表面方程根扫描。
- q4_radius_audit.json、q4_radius_interpolation_check.json：附件2与 PCHIP 节点审计及插值敏感性。
- q4_zero_diffusion_test.json：材料坐标结构极限试验。
- result4.xlsx：已接受的正式工作簿；result4_payload.json、result4_workbook_audit.json 为填充载荷与审计记录。
- model_spec_q4.md：冻结数学规格与后处理物理分析。
- q4_results.md：正式结果、表6、条件效应分解、数值验证、独立交叉验证和物理分析小结。
- plot_q4.py：从正式结果独立重绘全部图件。
- q4_phase1_report.md、q4_phase2_report.md、q4_phase1_results.json、q4_phase2_compare.json：交接说明中引用但本次归档缺失的独立数值方法交叉验证证据，待补交。
- Q4_REVISION_LOG.md：本轮文档修订记录。
- diagnostics/：零扩散极限、效应分解、半径插值和工作簿保真检查工具及临时审计材料。

## 仓库内运行路径

从仓库根目录运行（需先安装交接说明中列出的 Python 依赖）：

    python code/q4/q4_main.py
    python code/q4/diagnostics/q4_effect_decomposition.py
    python code/q4/diagnostics/q4_zero_diffusion_test.py
    python code/q4/q4_validation.py
    python code/q4/diagnostics/q4_radius_interpolation_check.py
    python scripts/plotting/q4/plot_q4.py

以上命令仅在需要重建时使用；本轮归档和审计没有重新运行正式求解，也没有重算任何数值结果。

模板填充采用 code/q4/diagnostics/result4_template_tool.mjs 读取 results/q4/result4_payload.json 后导出；code/q4/diagnostics/validate_result4.py 对导出文件复读核验。

q4_main.py 已包含仓库布局识别：从 data/raw/problems/ 只读附件，并把数值结果写入 results/q4/；plot_q4.py 从 results/q4/ 读取并输出到 figures/final/q4/。

## 输入与依赖

只读输入：

- data/raw/problems/A题/A题.pdf
- data/raw/problems/A题/附件/附件1.xlsx
- data/raw/problems/A题/附件/附件2.xlsx
- data/raw/problems/A题/附件/附件3/result4.xlsx
- Q3 冻结的 q3_run_summary.json，仅用于固定半径附录3复现对照。

本次实际环境：Python 3.13.5，NumPy 2.1.3，SciPy 1.15.3，openpyxl 3.1.5，Matplotlib 3.10.0。工作簿模板保真构建另使用 Node.js 脚本；该脚本只扩展官方占位区域、填入四位小数并输出预览，未重设计样式。

## 图件说明

| 图件 | 数据来源 | 横轴 | 纵轴/颜色 | 支持内容 |
|---|---|---|---|---|
| q4_radius_time | 附件2、PCHIP、正式终点 | 时间/h | 半径/cm | 半径节点、收缩过程及终点位置 |
| q4_moving_profiles | q4_solution.npz 胞心快照 | 实际半径/cm | 水分浓度/(kg/kg) | 不同时刻剖面及移动右端 |
| q4_moisture_spacetime | q4_solution.npz 60 s固定位置输出 | 实际半径/cm | 时间/h；颜色为水分浓度 | 水分场随时间和移动边界演化 |
| q4_effect_decomposition | q4_effect_decomposition.json | C/D/A/B工况 | 终止时间/h | 物性条件与收缩的2×2比较 |

每张图均提供 PDF 和 320 DPI PNG，可由 plot_q4.py 重现。

## 已知假设与待审核点

1. 附录4未给新边界系数，沿用 \(h=25\ \mathrm{W/(m^2\cdot K)}\)、\(h_m=8\times10^{-7}\ \mathrm{m/s}\)。
2. 附件2只给半径，补充假设轴向长度25 cm不变，仅径向收缩。
3. 14400 s后固定环境为附件1末值 \(T_a=50.165^\circ\mathrm C,C_a=0.04986\)。
4. result4.xlsx 将模板省略号展开为0至1.9 cm固定位置和一个实时表面列；体外固定位置留空。该解释符合题面和表6，但建议论文负责人最终确认官方阅卷系统是否接受空单元格。
5. 能量方程未显式加入蒸发潜热，因为题目未给完整相变能量参数；这是模型局限，不作“影响可忽略”的断言。

## 交付与人工核验说明

本轮正式求解、独立交叉验证、工作簿填充和图件生成均在人工审核流程下完成。人工核验建议包括：逐式对照附录4；复核附件2 PCHIP 和体外空值规则；复跑 q4_validation.py；抽查 q4_solution.npz、表6 和 result4.xlsx 的一致性；由论文负责人决定最终模型假设、表格口径和入库文件。本说明仅用于项目交付，不应直接写入数学建模正文。

## 2026-09-12 论文冻结补记

按论文负责人最终确认：仅径向收缩、长度不变；附件2 PCHIP定义几何，密度不反推几何；域外固定位置留空，表面列随实时半径移动。正文采用临界事件182956.15 s（约50.82 h），最后60 s规则节点182940 s。正式检验为数值收敛性、守恒性、结构性与代表时刻边界稳定性；独立Phase1/Phase2材料不进入正文，也不要求补入。累计相对残差只报告终点2.02×10^-4。上文交付说明保留为历史记录，正文使用范围以本补记及 `docs/writing-reviews/q4_paper_review.md` 为准。
