# 仓库布局：公开库与私有库

本项目的代码与论文分置于两个 GitHub 仓库，避免把第三方版权材料与内部过程记录放进公开范围。

## 一、两个仓库

| 仓库 | 可见性 | 用途 |
|---|---|---|
| [YuyYuzz/cumcm-2026](https://github.com/YuyYuzz/cumcm-2026) | **Public** | 论文正文、四问求解与验证代码、结果、图件、绘图脚本、电子支撑材料 |
| [YuyYuzz/cumcm-2026-private](https://github.com/YuyYuzz/cumcm-2026-private) | **Private** | 公开库内容 + 第三方论文原文 + 题目原始压缩包 + 第三方技能仓库 |

## 二、分支约定

| 分支 | 存在于 | 内容 |
|---|---|---|
| `main` | 两个仓库 | 360 个文件；不含任何第三方论文 PDF |
| `internal` | **仅私有库** | `main` + 私有材料（见下） |

### `internal` 分支的私有材料

| 内容 | 体量 | 说明 |
|---|---|---|
| `references/retrieved/`、`references/to-read/` | 19 个 PDF，约 64 MB | 第三方论文原文，本地留存，不公开分发 |
| `CUMCM2026Problems.zip` | 4.2 MB | 竞赛题目与附件原始压缩包 |
| `codex-paper-figure-skill` | 7.5 MB | 以 git submodule 形式引入的第三方图形技能仓库（`pengqianhan/codex-paper-figure-skill`） |

公开库中保留的是团队自写内容：`references.bib`、`a_problem_literature.bib`、`README.md`、`manual_download.md` 与 `excellent-papers/` 下的风格卡与综述。论文原文的获取方式记录在 `references/retrieved/manual_download.md`。

## 三、本地 remote 配置

```bash
git remote -v
# origin    https://github.com/YuyYuzz/cumcm-2026.git          （公开库）
# private   https://github.com/YuyYuzz/cumcm-2026-private.git  （私有库）
# upstream  https://github.com/latexstudio/CUMCMThesis.git     （模板上游，可选）
```

`.gitignore` 中的 `references/**/*.pdf`、`CUMCM2026Problems.zip`、`codex-paper-figure-skill/` 三条规则，确保这些材料**不会**被误提交到公开分支。

## 四、日常操作

### 更新公开内容

```bash
git checkout main
# … 修改论文、代码或结果 …
latexmk main.tex                      # 改动论文后须编译并检查 build/main.pdf
git add -A && git commit -m "…"
git push origin main                  # 只推公开库
```

### 更新私有材料

```bash
git checkout internal
# … 增删参考文献 PDF 等 …
git add -f references/                # 这些路径被 .gitignore 忽略，需 -f
git commit -m "internal: …"
git push private internal             # 只推私有库
```

### 让 `internal` 跟上 `main`

```bash
git checkout internal
git merge main                        # 或 git rebase main
git push private internal
```

### 克隆私有库后初始化子模块

```bash
git clone https://github.com/YuyYuzz/cumcm-2026-private.git
cd cumcm-2026-private
git submodule update --init --recursive
```

## 五、为什么这样拆分（操作记录）

2026-09-13 收尾时，公开准备工作发现三类不宜进入公开范围的内容：

1. **第三方论文 PDF**（19 个，约 64 MB）——下载版论文通常不允许再分发；
2. **历史中的本机路径**——早期误提交的 matplotlib 字体缓存 `fontlist-v390.json` 含 `/Users/<user>/Library/Fonts/...`；
3. **冗余过程产物**——`Q3.zip`、临时草稿、构建缓存等。

同时发现：**GitHub 在强推后会保留不可达对象**，实测强推后旧提交与旧 PDF blob 仍可按 SHA 访问（HTTP 200）。因此仅靠 `git rm` + 强推无法达成「公开仓库不含版权材料」。

最终采用**公开库/私有库分离 + 公开库全新重建**的方案：

1. 旧仓库改名为 `cumcm-2026-private` 并转为私有（保留全部旧对象，但不对外）；
2. 以孤儿提交重建干净历史，新建公开库 `cumcm-2026`；
3. 公开库为全新存储，**旧对象一个都不存在**（实测旧 blob → 404、旧提交 → 422）；
4. 私有材料放在私有库的 `internal` 分支。

验收结果（2026-09-13）：

| 检查 | 结果 |
|---|---|
| 公开库分支 | 仅 `main` |
| 公开库旧 PDF blob | HTTP 404 |
| 公开库旧提交 | HTTP 422 |
| 私有库匿名访问 | HTTP 404（已私有） |

## 六、重建公开库历史的原则

公开库的历史被有意压缩为**单个根提交**，原因是原始开发历史中混有上述三类内容。若日后需要在公开库继续开发，直接在 `main` 上正常提交即可；不要再把 `internal` 分支推送或合并到公开库。

## 七、提交前自查（沿用于 `CONTRIBUTING.md`）

- 新增文献或数据时，确认其**再分发许可**；不确定的一律放 `internal`；
- 不要提交 `.mplconfig/`、`__pycache__/`、`build/`、`tmp/`、`.DS_Store`（均已在 `.gitignore`）；
- 不要把其他协作者的个人信息（姓名、邮箱、本机路径）写入公开文档或提交信息。
