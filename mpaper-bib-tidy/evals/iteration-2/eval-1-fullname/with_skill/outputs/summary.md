# BibTeX 整理摘要

已按 Full Name mode 生成 `result.bib`，citation key 未变。

## Tier 1 — 已直接应用的格式修改

- 8 个 title 调整为 sentence case；恢复并保护 7 处专有术语：`{Plug-and-Play}`（3）、`{SwinIR}`、`{Swin Transformer}`、`{RED}`、`{SinSR}`。
- 5 个完整作者列表统一为 `Last, First`；2 个原本合规的列表未改。
- 1 个完整期刊名改为 Title Case：`SIAM journal on imaging sciences` → `SIAM Journal on Imaging Sciences`。
- 3 个 `booktitle` 删除年份或届次；2 个 `pages` 单连字符转 `--`；1 个 entry type 大小写规范为小写。
- 删除 8 个字段：2 `doi`、1 `url`、1 `organization`、2 `publisher`、1 `address`、1 `month`；`@book` 的 publisher 保留。

## Tier 2 — 经核验后应用的修改

- `IEEE Trans. Pattern Anal. Mach. Intell.` → `IEEE Transactions on Pattern Analysis and Machine Intelligence`（ISSN Portal https://portal.issn.org/resource/ISSN/1939-3539；IEEE https://www.computer.org/digital-library/journals/tp/cfp-ieee-pattern-analysis-machine-intelligence；DBLP https://dblp.org/db/journals/pami/index.html）。
- `venkatakrishnan2013pnp`：确认 GlobalSIP 为会议，`@article` → `@inproceedings`，`journal` → `booktitle`（IEEE program guide https://www.2013.ieeeglobalsip.org/GS13_ProgramGuide_Web.pdf；DBLP https://dblp.dagstuhl.de/rec/conf/globalsip/VenkatakrishnanBW13.html；Proceedings.com https://www.proceedings.com/21201.html）。
- `hurault2022proximal`：确认 PMLR Volume 162 论文为 ICML conference paper，`@article` → `@inproceedings`，`journal` → `booktitle`，保留 PMLR series（PMLR https://proceedings.mlr.press/v162/；paper https://proceedings.mlr.press/v162/hurault22a.html；DBLP https://dblp.org/rec/conf/icml/HuraultLP22）。
- `scholkopf2002learning`：确认 MIT Press 图书，`@article` → `@book`，保留 publisher（MIT Press https://mitpress.mit.edu/9780262536578/learning-with-kernels/；WorldCat https://search.worldcat.org/title/48970254；Google Books https://books.google.com/books/about/Learning_with_Kernels.html?id=y8ORL3DWt4sC）。

## Tier 3 — 需要用户补充或确认

- `wang2024sinsr`：作者字段以 `and others` 结尾，补全需文件外事实，已保持原样。
- `scholkopf2002learning`：源文件写作 `Scholkopf`；恢复姓名变音符号需用户确认，未改。
