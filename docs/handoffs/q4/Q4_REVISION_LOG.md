# Q4 文档修订记录（Q4_REVISION_LOG.md）

本轮只修改 Markdown 文档，未重新求解正式 Q4，未重算任何数值结果，未修改 q4_main.py、q4_validation.py、plot_q4.py、*.json、q4_solution.npz、result4.xlsx、result4_payload.json、figures/、diagnostics/。所有修订项的“是否改变正式数值”均为**否**。

## 修订总表

| 序号 | 文件 | 修改位置 | 修改前问题 | 修改后内容 | 是否改变正式数值 | 证据来源 |
|---:|---|---|---|---|---|---|
| 1 | README.md | 冻结状态区 | 缺少本轮要求的冻结/验收状态标识 | 增加 Q4 numerical result frozen、Independent cross-validation passed、No recomputation required、result4.xlsx accepted，并写明正式 t_end 与独立验证判定 | 否 | q4_phase2_report.md 第十节；q4_phase2_compare.json |
| 2 | README.md | 表6 说明 | “—”语义只在结果文档中出现，README 未解释 | 明确“—”表示固定位置已因收缩位于当前药材表面之外，不填浓度、不用材料坐标值代替 | 否 | q4_run_summary.json table6 字段；q4_phase1_report.md 第7节 |
| 3 | README.md | result4.xlsx 语义 | 未集中说明留空规则与表面列语义 | 增加：体外固定位置留空；末列“药材表面”记录实时移动表面 r=R(t) 的浓度；末行 182940 s 不是精确终点 | 否 | result4_workbook_audit.json；q4_phase2_report.md 第九节 |
| 4 | README.md | 2×2 效应口径 | 原术语为“物性与收缩的2×2比较”，易误读为因果分解 | 明确为条件反事实组合：条件效应与非加性交互项，不能线性相加 | 否 | q4_phase2_report.md 第四节、第十节第4条 |
| 5 | README.md | 文件角色 | 未列出独立验证证据与修订记录 | 增加 q4_phase1/phase2 报告、q4_phase1_results.json、q4_phase2_compare.json、Q4_REVISION_LOG.md 等条目，并注明 JSON 字段名为历史命名 | 否 | 工作区文件清单 |
| 6 | README.md | 运行区 | 易被误读为本轮重跑 | 增加“本轮未重新运行正式求解、未重算数值”说明 | 否 | 本轮任务边界 |
| 7 | README.md | 输入与依赖 | 含具体工具品牌名 | 改为通用“Node.js 脚本”表述，不出现模型/工具品牌 | 否 | 论文与交接文档术语要求 |
| 8 | README.md | 图件说明 | “物性与收缩的2×2比较” | 改为“物性条件与收缩的2×2比较” | 否 | 同上 |
| 9 | README.md | 末尾使用说明 | 原使用说明小节含模型/工具品牌词 | 改为“交付与人工核验说明”，删除品牌字样，统一为正式数值方法与独立数值方法 | 否 | 本轮禁止措辞要求 |
| 10 | model_spec_q4.md | 第1节、新增 1.1 | 未说明 R(t) 与 ρ(C) 的分工 | 增加：R(t) 由附件2确定几何；ρ(C) 仅入能量方程与后处理，不反推几何 | 否 | q4_phase2_report.md 第十节；本轮第13项分析 |
| 11 | model_spec_q4.md | 新增 3.1 | 未解释附录4物性相对附录3的物理变化 | 增加干态密度 650→760（+16.9%）、比热变化、导热干态 −42.9%/全湿 −45.8%，并写“与组织结构变化图景相容”，不写“证明密实化” | 否 | 题目附录3/附录4经验参数；本轮第10项分析 |
| 12 | model_spec_q4.md | 新增 3.2 | 未给出扩散温度因子的物理解释 | 增加等效 Arrhenius 活化能 Ea=3850R≈32.0 kJ/mol | 否 | 附录4 D(C,T) 表达式；R=8.314 J/(mol·K) |
| 13 | model_spec_q4.md | 新增 7.1 | 未分析 Lewis 数 | 增加 α=k/(ρcp)、Le=α/D；Le 由约26增至约75及热质时间尺度解释 | 否 | q4_run_summary.json initial_properties；本轮第11项核算 |
| 14 | model_spec_q4.md | 新增 7.2 | 未做体积口径一致性检查 | 增加 0.379/0.360/0.414 三种终初体积比及“总体收缩量级一致性”解释；明确 0.360 而非 0.359 的时间口径 | 否 | 附件2；附录4 ρ(C)；本轮第13项代数计算 |
| 15 | model_spec_q4.md | 新增 7.3 | 缺少分析边界说明 | 增加不能推出密实化、严格仿射收缩、等温模型等新假设的声明 | 否 | 本轮禁止措辞要求 |
| 16 | q4_results.md | 第3节 | 使用 Δt_property 等易被误读为因果效应的命名 | 改名为“固定半径条件下的物性条件效应”“附录3/附录4物性条件下的收缩效应”“非加性交互项” | 否 | q4_effect_decomposition.json effects 字段；q4_phase2_report.md 第四节 |
| 17 | q4_results.md | 第3节 | 缺少四工况反事实解释段 | 加入推荐段落，写明 I=−46.24 h 为非线性交互、不能简单线性叠加 | 否 | 同上 |
| 18 | q4_results.md | 第4.2节 | 原写“结果对插值形式不敏感”，范围过大 | 改为“终止时间对附件2节点间插值方式不敏感（约12.57 s）；早期局部浓度仍存在 10^-3 以下差异（6 h、0 cm 最大 7.99e-4）” | 否 | q4_radius_interpolation_check.json；q4_phase2_report.md 第七节 |
| 19 | q4_results.md | 第4.3节 | 原写“基准工况未发现根分支歧义”，范围过大 | 统一为“在1、4、6、12、24、36、48 h及终止时刻均只检测到一个数值根，未发现多根或根分支折叠” | 否 | q4_surface_root_audit.json；q4_phase2_report.md 第五节 |
| 20 | q4_results.md | 第4.4节 | 只给正式守恒残差，未解释两套累计残差差异 | 增加独立 BE 逐步累计 1.94e-14，说明差异来自后处理积分方式，属数值自洽验证 | 否 | q4_validation.json integral_balance；q4_phase2_compare.json inventory |
| 21 | q4_results.md | 新增第5节 | 正文缺少独立方法交叉验证 | 增加终止时间、表6逐点对拍、终点状态三小节及推荐表述 | 否 | q4_phase1_report.md；q4_phase2_report.md；q4_phase2_compare.json |
| 22 | q4_results.md | 新增第6节 | 正文缺少物性物理分析小结 | 增加附录3→4物性变化、Lewis 数、等效活化能、三体积口径四小节 | 否 | 同上第10–14项 |
| 23 | q4_results.md | 第7节（原第5节） | result4 语义分散 | 补充留空规则、表面列语义，并明确末行 182940 s 不是精确结束时刻 | 否 | result4_workbook_audit.json |
| 24 | q4_results.md | 表6、第1节 | 无修改 | 表6数值、t_end、Cmax、Cs、R_end 保持原文 | 否 | q4_run_summary.json |
| 25 | Q4_REVISION_LOG.md | 新增文件 | 无修订记录 | 建立本逐项修订记录 | 否 | 本轮工作 |

## 未做事项声明

- 未新增题目未要求的额外环境湿度敏感性支线。正式基准验证链已充分，极低湿度工况会引入额外的低扩散边界层/根分支解释复杂性。
- 未加入预热温度差异条目。Lewis 数分析已足以说明温度与水分传输的相对快慢，无需重新计算任何解。
- 未修改任何 JSON 字段名。q4_effect_decomposition.json 中的 property_main_*、shrink_* 等历史字段保持原样，仅在 Markdown 中采用更严谨术语。
- 未修改 q4_main.py、q4_validation.py、plot_q4.py、q4_solution.npz、result4.xlsx、result4_payload.json、figures/、diagnostics/。

## 结论

本轮所有修订均只涉及说明性文字、术语和物理后处理分析；正式数值、表6、result4.xlsx 和全部机器可读冻结记录均未改变。
