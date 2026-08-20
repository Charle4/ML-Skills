# BibTeX 整理摘要

## Tier 1：已直接应用的格式修改

- 7 个条目的作者姓名改为 `Last, First` 格式。
- 4 个 Title Case 标题改为 sentence case：`candes2006robust`、`chambolle2004algorithm`、`beck2009fast`、`goldstein2009split`。
- 2 个术语已用花括号保护：`{Split Bregman}`、`{L1}`；没有从全小写形式恢复大小写的术语。
- 5 个 `pages` 字段的单连字符改为 BibTeX 页码范围连字符 `--`。
- 删除 1 个 `doi` 字段、1 个 `url` 字段，以及 `boyd2011distributed` 期刊名中的注册商标标记。

## Tier 2：经核验后应用的修改

LTWA 词表规则用于逐词缩写：省略介词和连词，保留 `IEEE`、`SIAM` 等首字母缩略词，并为缩略内容词保留句点。以下期刊的注册标题与独立书目来源均支持目标形式：

- `IEEE Transactions on Information Theory` → `IEEE Trans. Inf. Theory`（ISSN 0018-9448；[ETH Research Collection](https://www.research-collection.ethz.ch/items/f4102446-13be-49c4-b5e6-b89df8b48054)；[Ryukoku University OPAC](https://opac.ryukoku.ac.jp/iwjs0005opc/catdbl.do?hidden_return_link=true&pkey=SB30008113)）。
- `Physica D: Nonlinear Phenomena` → `Phys. D: Nonlinear Phenom.`（ISSN 0167-2789；[RUDN repository](https://repository.rudn.ru/ru/record-sources/record-source/1421/)；[PubMed](https://pubmed.ncbi.nlm.nih.gov/40808756/)）。
- `Journal of Mathematical Imaging and Vision` → `J. Math. Imaging Vis.`（ISSN 0924-9907；[RWTH Aachen publication record](https://publications.rwth-aachen.de/record/19510)；[Springer/DOI record](https://doi.org/10.1007/S10851-008-0118-X)）。
- `SIAM Journal on Imaging Sciences` → `SIAM J. Imaging Sci.`，应用于 `beck2009fast` 和 `goldstein2009split`（ISSN 1936-4954；[UC3M research portal](https://researchportal.uc3m.es/display/rev185741)；[GSI repository](https://repository.gsi.de/record/41532)）。
- `Foundations and Trends in Machine Learning` → `Found. Trends Mach. Learn.`（ISSN 1935-8237；[PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC5913324/)；[PolyU research portal](https://research.polyu.edu.hk/en/publications/a-note-on-the-convergence-of-admm-for-linearly-constrained-convex)）。ISSN 连续出版物记录与出版记录确认其为期刊，故将 `boyd2011distributed` 从 `@inproceedings` 更正为 `@article`。
- `SIAM J. Sci. Comput.` 已是 `SIAM Journal on Scientific Computing` 的核验后 LTWA 形式（ISSN 1064-8275；[NLM Catalog](https://www.ncbi.nlm.nih.gov/nlmcatalog/9888470)；[PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC12987680/)）；仅核验，未改变该字段的文本。

## Tier 3：需要你的输入

- 无。所有条目均保留原有的卷、期、页码和年份信息，未发现缺失必填书目信息或未确认的标题术语。
