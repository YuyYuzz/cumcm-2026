
# CUMCM 2026 论文工作区

本仓库是全国大学生数学建模竞赛论文写作与绘图工作区，使用 XeLaTeX 编译。
当前直接采用 [Sustainable-Enjoyment/CUMCM-LaTeX-Template](https://github.com/Sustainable-Enjoyment/CUMCM-LaTeX-Template)
的文档类与图表样式，保留其原有视觉设计。根目录类文件只增加字体回退；旧模板散文件已移至
`archive/legacy-template-files/`，不参与编译。
上游原文件及 MIT 许可证保存在 `vendor/sustainable-enjoyment/`，来源和官方要求见 `docs/template-reference.md`。

团队协作采用“按问题提交材料、论文负责人统一整合”的方式。首次参与请先阅读
[`CONTRIBUTING.md`](CONTRIBUTING.md)，每次提交材料时同步更新 `docs/handoffs/qN/README.md`。

如需检查排版效果，运行 `latexmk preview.tex` 生成独立样张。样张只用于版式检查，不能作为参赛内容提交。

## 快速编译

```bash
latexmk main.tex
latexmk preview.tex
```

正式骨架生成在 `build/main.pdf`，样张生成在 `build/preview.pdf`。提交前至少检查摘要页、页码、匿名信息、图表清晰度、
参考文献引用和 AI 工具使用声明。

## 目录说明

```text
.
├── main.tex                 # 唯一正式入口：2026 全国规范电子版
├── preview.tex              # 独立排版样张入口
├── preview/                 # 样张插图与程序
├── vendor/                  # 上游原文件、许可证
├── archive/                 # 更换前的模板与内容备份
├── output/                  # 本地导出文件，不提交 Git
├── config/                  # 宏包、图片路径和自定义命令
├── contents/
│   ├── abstract.tex         # 摘要和关键词
│   ├── info.tex             # 论文标题
│   ├── ai_usage.tex         # AI 工具使用声明
│   ├── references.tex       # 参考文献入口
│   ├── sections/            # 正文分章节文件
│   └── appendix/            # 附录和支撑材料清单
├── references/              # BibTeX 文献库
│   ├── retrieved/           # 已获取全文和待人工下载清单
│   └── to-read/             # 待读全文
├── figures/
│   ├── source/              # 可编辑图源和绘图中间材料
│   └── final/               # 论文实际引用的最终图片
├── scripts/plotting/q1..q4/ # 分问题保存可复现绘图脚本
├── data/raw/problems/       # 原始赛题和附件，只读保存
├── results/q1..q4/          # 分问题保存模型输出和绘图输入
├── tables/q1..q4/           # 分问题保存表格数据或 TeX 片段
├── code/q1..q4/             # 分问题保存建模求解代码
├── docs/
│   └── handoffs/q1..q4/     # 同学交付说明和论文写作证据入口
├── cumcmthesis.cls          # 国赛文档类
├── archive/
│   └── legacy-template-files/ # 旧样式、旧示例及其配套图片
└── build/                   # 编译产物，不提交 Git
```

## 写作约定

- `contents/` 供分章节写作；可以按赛题增删合并，不强制四个问题或十一章。官方不指定固定章数。
- 同学主要修改自己负责的 `qN` 目录，论文负责人统一维护 `main.tex`、`contents/` 和公共排版配置。
- 每次提交代码、结果、表格或图片时，同步更新 `docs/handoffs/qN/README.md`。
- 最终图只放 `figures/final/`，对应脚本放 `scripts/plotting/`。
- 原始数据保持不改；清洗或计算后的数据写入 `results/`。
- 图题置于图下，表题置于表上；LaTeX 插图优先 PDF，SVG 先转换为 PDF；栅格图建议至少 300 DPI。
- 每个关键数字应能追溯到 `results/` 或建模代码输出。
- AI 声明必须按比赛期间的真实使用情况维护。
- 附录应收录全部完整可运行代码与支撑材料列表，不能仅收录关键代码片段。
- 本项目当前只维护电子版；`main.tex` 是唯一正式入口。
- 电子版摘要页为第1页，不含承诺书、编号页、目录；正文不超过30页，附录页数不限。
- 2026全国规范未统一规定字体、字号、行距、摘要字数或最少页数；所在赛区若有额外规定，再按规定调整。
- 上游内置纸质承诺页仍是2025内容，当前默认禁用；纸质提交应另用当年官方专用页。

更换前完整备份：`archive/before-template-switch-20260910.tar.gz`；根目录遗留的旧模板散文件另存于
`archive/legacy-template-files/`。二者均不参与正式编译。

## 项目内 Skills

- `mathmodel-figure`：论文级科研绘图和多格式导出。
- `mathmodel-paper`：摘要、LaTeX/PDF/Word 排版工具链和不可见字符检查。

它们位于 `.agents/skills/`，只对本项目生效。
技能中关于固定字号、摘要字数、25-30页等属于建议，不能覆盖官方原文或用户要求的原模板样式。
