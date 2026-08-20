# BibTeX 整理摘要

## Tier 1：已直接应用的格式改动

- 4 个 venue 字段已按文件中逐词对应的 `@String` 定义统一为宏引用：`zhang2017learning` → `CVPR`、`zhang2022practical` → `PAMI`、`ho2020denoising` → `NeurIPS`、`dosovitskiy2021image` → `ICLR`。
- 5 个 title 已改为 sentence case；2 个已知术语已用花括号保护：`{CNN}`、`{Real-ESRGAN}`。本次没有从全小写形式恢复专有名词的大小写。
- 6 个作者列表已统一为 `Last, First` 格式。
- 1 个 `pages` 字段已将单连字符改为双连字符。
- 已删除 1 个 `doi`、1 个 `url`、1 个 `month`、1 个 `address` 及 1 个冗余 `organization` 字段。
- 已从 `wang2021real` 的 `booktitle` 中删除年份；`@INPROCEEDINGS` 已规范为 `@inproceedings`。
- 无对应 `@String` 的 `SIAM Journal on Imaging Sciences` 已保留为其输入中已有的 Title Case 全称。

## Tier 2：经外部核验后应用的改动

无。此次整理仅依据指定 `.bib` 文件中的信息，未引入外部事实。

## Tier 3：需要你的输入

- `zhang2017learning`：`journal = CVPR` 表明其可能应为会议论文，但将 `@article` 改为 `@inproceedings` 需要核验 venue 身份；当前 entry type 保持不变。
- `lim2017enhanced`：`Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops` 与 `CVPR` 宏不逐词对应。其官方 venue 形式及是否应使用宏尚未核验，故保持原值。
- `wang2021real`：`IEEE/CVF International Conference on Computer Vision Workshop (ICCVW)` 与 `ICCV` 宏不逐词对应。其官方 venue 形式及是否应使用宏尚未核验，故除删除年份外保持原值。
