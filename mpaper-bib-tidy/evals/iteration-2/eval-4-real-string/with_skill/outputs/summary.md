# BibTeX 整理报告

## Tier 1：已直接应用的格式变更

- 标题统一为 sentence case：8 条。
- 已恢复并用花括号保护的术语：`Deblurgan` → `{DeblurGAN}`、`Dinov2` → `{DINOv2}`、`Siglip` → `{SigLIP}`、`Sam` → `{SAM}`。
- 额外保护的已有专名、技术术语或符号：`{L0}`、`{Bayesian}`、`{Deep Image Prior}`。
- 作者改为 `Last, First` 格式：8 条；原有姓名、连字符和 LaTeX 重音均保留。
- 与 `@String` 定义逐字对应的 venue 已替换为未加花括号的宏 key：`CVPR` 2 条、`TMLR` 1 条、`ICML` 1 条、`ICLR` 1 条、`PAMI` 1 条。
- `pages` 单短横线改为双短横线：4 处。
- 删除可清理字段：`url` 2 处。
- 未定义 `@String` key 的 `Journal of Machine Learning Research` 保留原有完整词序及格式。

## Tier 2：核验后变更

无。本次 venue 宏替换均由文件中 `@String` 定义的逐字匹配决定，属于 Tier 1；没有引入、扩展或替换任何需要外部事实核验的 venue、机构形式或 entry type 信息。

## Tier 3：需要用户输入或保持未改

- `radford2021learning`：作者列表以 `and others` 结束；未补全作者，已按原样保留。
- `oquab2024dinov`：`@article` 缺少 `volume`、`number` 和 `pages`；未补填。
- `wipf2014revisiting`：`@article` 缺少 `volume`、`number` 和 `pages`；未补填。
- `ravi2025sam`：`@inproceedings` 缺少 `pages`；未补填。
- 未经文件内证据或外部核验可确认的书目信息均保持原样；本次未对 entry type、venue 全称或组织机构形式作任何推断性修改。
