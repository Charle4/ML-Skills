---
name: mpaper-bib-tidy
description: BibTeX .bib file cleanup and normalization — entry types (with cross-validation), venue names (full-name / abbreviated with verified LTWA or ISO 4 / @String macro), title sentence-casing with brace protection, author Last-First format, field pruning, pages double-dash. Use whenever the user mentions tidying, cleaning, formatting, normalizing, or unifying a .bib file; fixing inconsistent journal/conference names, title casing, or author names in BibTeX; or mentions that their references.bib or main.bib has formatting issues. Also trigger when the user says "bib 格式不统一", "整理 bib", "统一参考文献格式", "bib 大小写保护", "期刊名缩写", "LTWA", "ISO 4", or asks to clean up bibliography entries for a LaTeX paper. This skill handles .bib source files only — for LaTeX body text use mpaper-en-academic-writing; for typesetting (page/hbox) use mpaper-latex-typeset-polish.
---

# BibTeX Bibliography Cleanup

## Workflow

1. Read the entire .bib file.
2. Determine venue name format mode.
3. Classify every needed change into Tier 1 / Tier 2 / Tier 3 (see [Modification Boundary](#modification-boundary)).
4. Apply all Tier 1 edits directly.
5. Route every Tier 2 item through the verification workflow before editing.
6. Collect every Tier 3 item for the report.
7. Report in the three sections described under [Reporting](#reporting).

## Modification Boundary

Every change falls into exactly one tier. The tier determines whether you may edit directly, must verify first, or must only report. Classify before editing — a change whose tier you cannot determine is Tier 2.

### Tier 1 — Format transformations (edit directly)

These rewrite the file's existing words without importing any fact about which venue, paper, or person an entry refers to:

- Title recasing to sentence case, including post-colon capitalization.
- Brace protection of acronyms, eponyms, and named methods/models/datasets, **restoring conventional capitalization the source lost** (`cnn` → `{CNN}`, `swinir` → `{SwinIR}`, `fourier` → `{Fourier}`).
- Venue name recasing **when the word sequence is unchanged** (`SIAM journal on imaging sciences` → `SIAM Journal on Imaging Sciences`).
- Author reordering into `Last, First` from names already present.
- Deleting tokens: year/ordinal from `booktitle`, trademark symbols, `doi`/`url`/`month`/`address` and other prunable fields.
- `pages` single dash → double dash.
- Whitespace, indentation, field ordering.

### Tier 2 — Facts from outside the file (verify first, never improvise)

These require a fact the file does not contain. Read [references/abbreviation-verification.md](references/abbreviation-verification.md) and follow its protocol for each one. Do not answer them from your own knowledge, do not infer them from the citation key, and do not run ad-hoc searches outside that protocol:

- Expanding an abbreviation into a full name, or contracting a full name into an abbreviation — except the word-by-word `@String` key match described under [@String mode](#string-mode), which stays Tier 1.
- Any venue name change that **adds, removes, or substitutes words** rather than only recasing them.
- Whether a venue is a journal or a conference — the fact that decides an entry type change.
- Which organizational form applies to the paper's year (e.g., `IEEE` vs `IEEE/CVF`).
- Whether the official title carries a `Proceedings of ...` prefix.
- Whether a venue corresponds to a defined `@String` key when the correspondence is not a plain word-by-word match.

Apply the change only for venues the protocol confirms. Downgrade anything it leaves unconfirmed to Tier 3 and leave the entry untouched.

### Tier 3 — Report only (never fill in, never guess)

Leave the entry as-is and list it in the report:

- Missing `volume`, `number`, `pages`, or `year`.
- `and others` / `et~al.` in an author list.
- Venue identity that the Tier 2 protocol could not confirm.
- A suspected wrong entry type whose venue identity is unconfirmed.
- A word that may be a flattened proper noun but reads equally well as an ordinary word in that title.
- Anything that looks wrong where the correct value is unknown.

## Venue Name Format Detection

Three modes. Determine which applies before editing.

### Detection procedure

1. If the user's prompt names a format ("use @String keys", "use LTWA abbreviations", "use full names"), that is the mode. It outranks what the file happens to contain — a file full of `@String` definitions does not mean the user wants macros this time.
2. Otherwise, if the .bib file contains `@String` definitions, or the user supplies a list of `@String` key→value mappings → **@String mode**.
3. Otherwise, if the user or the target venue style explicitly requires abbreviated journal names (LTWA / ISO 4, or another standard) → **Abbreviated mode**.
4. Otherwise → **Full Name mode** (default).
5. If the prompt asks for `@String` keys but the file defines none and the user supplied none, ask once via AskUserQuestion — inventing keys would change how every entry renders.

### Full Name mode (default)

Target form is the venue's official full name in Title Case (content words capitalized).

```bibtex
journal = {IEEE Transactions on Image Processing},
booktitle = {IEEE/CVF Conference on Computer Vision and Pattern Recognition},
```

An entry whose venue is already spelled out in full needs only recasing — Tier 1. An entry whose venue is abbreviated needs the full name looked up — Tier 2.

### @String mode

Target form is the `@String` key for venues that have one. Do not wrap the key in braces — it is a macro reference.

```bibtex
journal = PAMI,
booktitle = CVPR,
```

Map a venue to a key when its name and the key's value correspond word by word (`IEEE Transactions on Pattern Analysis and Machine Intelligence` ↔ `IEEE Trans. Pattern Anal. Mach. Intell.`) — Tier 1. Any looser correspondence is Tier 2.

Venues with no defined key keep a braced full name in Title Case, subject to the same Tier 1 / Tier 2 split as Full Name mode. Do not invent new `@String` definitions unless the user asks.

### Abbreviated mode

Target form is the abbreviated venue name under the required standard (LTWA/ISO 4, or another).

```bibtex
journal = {IEEE Trans. Image Process.},
journal = {SIAM J. Imaging Sci.},
```

Every venue name in this mode is Tier 2 — including ones already abbreviated in the source, since the existing form may be wrong. Verify each unique venue through the protocol, then apply only the confirmed forms.

## Formatting Rules

### Entry types and cross-validation

- Journal paper → `@article`. Required: `author`, `title`, `journal`, `year`. Recommended: `volume`, `number`, `pages`.
- Conference paper → `@inproceedings`. Required: `author`, `title`, `booktitle`, `year`. Recommended: `pages`. Optional: `series`, `volume` (for LNCS/PMLR-style).
- Preserve `@misc`, `@book`, `@phdthesis`, `@techreport` and other types as-is; apply title/author/field rules but do not change entry type.

**Cross-validate entry type against venue identity.** Many bib files carry mismatched entry types. Scan every entry for these mismatch shapes:

- `@article` whose `journal` field holds a conference name (`journal = {IEEE Conference on ...}`, `journal = CVPR`) → belongs in `@inproceedings` with the value moved to `booktitle`.
- `@inproceedings` whose venue sits in a `journal` field with no `booktitle` → belongs in `@article`.
- `@article` with no `volume`/`number` whose venue is a proceedings series (`Proceedings of Machine Learning Research`) → belongs in `@inproceedings` with `booktitle` and `series`.

A mismatch shape marks the entry as a candidate; it does not settle the entry type. What settles it is the venue's identity as a journal or a conference, which is a Tier 2 fact — verify it through the protocol, then rewrite the confirmed entries and report the unconfirmed ones.

### Venue names (all modes)

Tier 1, apply to every entry:

- Remove year, edition number, or ordinal (`37th`, `2024`) from `booktitle`. Year belongs only in the `year` field.
- Remove trademark / registration symbols (`{\textregistered}`, `\texttrademark`).

Tier 2, verify before touching:

- The `Proceedings of ...` prefix. Keep what the source has until the protocol confirms the official title's form — some conferences (e.g., ICLR, NeurIPS) do not use it.
- The organizational form for the paper's year (`IEEE` vs `IEEE/CVF`, which shifted for CVPR and ICCV in recent years). In `@String` mode, a key that does not distinguish year-specific variants is used as-is and needs no verification.

### Title

**Sentence case**: Only the first letter of the title is uppercase. All other words lowercase, except:

- After a colon `:` — capitalize the first letter of the next word (treat as new sentence). No brace protection needed for this; it is a source-level convention.
- Terms that must keep their internal capitals — wrap them in braces `{}` so the bibliography style cannot flatten them.

**Judge each word by what the term is, not by how the source spelled it.** Reference managers and database exports routinely flatten titles to sentence case without brace protection, so `{CNN}` arrives as `cnn` and `{SwinIR}` as `swinir`. Treating the source casing as authoritative would leave exactly those titles — the most common kind — unprotected. Restore the term's conventional capitalization and brace it; the flattening was a lossy transform, and undoing it asserts nothing the entry did not already say.

Apply these cues to every content word regardless of its current case:

- **Acronym** — expands to a phrase in the field: `{CNN}`, `{GAN}`, `{ADMM}`, `{SVD}`, `{MRI}`, `{PnP}`, `{LoRA}` (`admm` → `{ADMM}`, `svd` → `{SVD}`).
- **Proper noun / eponym** — derived from a person's name: `{Fourier}`, `{Poisson}`, `{Bayesian}`, `{Gaussian}`, `{Bregman}`, `{Euler}` (`fourier` → `{Fourier}`, `bregman` → `{Bregman}`, `bayesian` → `{Bayesian}`).
- **Named artifact** — a model, method, dataset, or system introduced under that name, usually mixed-case: `{ResNet}`, `{CLIP}`, `{FedADMM}`, `{DarkIR}`, `{ImageNet}` (`resnet` → `{ResNet}`, `imagenet` → `{ImageNet}`, `real-esrgan` → `{Real-ESRGAN}`).
- **Product / language / format** — `{LaTeX}`, `{MATLAB}`, `{Python}`.
- **Mixed-case compound** — `{hyper-Laplacian}`, `{plug-and-play}`.

Where the source **has** kept non-initial capitals, that is corroborating evidence: protect the term and keep the author's own hyphenation and internal casing (`hyper-Laplacian`, `sharpness-aware` vs `sharpness aware` — match the source, do not normalize across entries).

A word that reads equally well as an ordinary word in that title is Tier 3: leave it lowercase and report it, naming both readings. `red` in a denoising title may be the RED method or the color; `sam` may be the SAM model or a given name; `adam` may be the optimizer or a person. Guessing here silently changes what the title claims.

### Author names

- Format: `LastName, FirstName MiddleName` separated by `and`.
  - Example: `author = {Zhang, Kai and Liang, Jianqing and Zuo, Wangmeng}`
- List all authors; do not use `and others` or `et~al.`. An author list ending in `and others` is Tier 3: leave it as found and report it, since completing it means adding names the file does not contain.
- Preserve diacritics: `Sch{\"o}lkopf`, `Gonz{\'a}lez`, `Cand{\`e}s`.
- Preserve hyphens in names: `Fotheringham-Smythe`.
- Name particles (`van`, `de`, `von`, `Le`): follow BibTeX convention, optionally braced to stay attached (e.g., `{van de Berg}, Jan`).

### Field cleanup

**Remove silently** (if present):
- `doi`, `url`, `abstract`, `keywords`, `month`, `address`

**Conditionally remove:**
- `organization`: remove it when `booktitle` already names the organizer (drop `organization = {IEEE}` when the booktitle says IEEE); keep it otherwise, since it is then the only record of who ran the event.
- `publisher`: keep it for `@book` / `@incollection`, and for any entry carrying a `series` field (LNCS, PMLR and other publisher-run series, where the publisher identifies the series). Remove it from every other `@inproceedings`.

**Preserve:**
- `note` (often contains "to appear", arXiv IDs, supplemental material references).
- `series` (e.g., `Lecture Notes in Computer Science`).

**Format fixes** (apply directly):
- `pages`: use double dash `--` (e.g., `pages = {123--456}`). Convert single dash to double.
- Numeric fields (`volume`, `number`, `year`): preserve the file's existing convention (bare number vs. braced). Do not convert between `year = 2024` and `year = {2024}`.

### Citation keys

Do not change citation keys — they are referenced in `.tex` files throughout the paper.

## Reporting

Report in three sections mirroring the tiers, so the user can see at a glance what changed on the file's own evidence, what changed on outside evidence, and what is left for them:

1. **Format changes applied** (Tier 1): counts by kind — e.g. "23 titles recased to sentence case, 31 terms brace-protected, 8 `pages` fields fixed, `doi`/`url` removed from 12 entries". List separately any term whose capitalization you **restored** rather than merely protected (`cnn` → `{CNN}`), so the user can spot-check the restorations.
2. **Verified changes applied** (Tier 2): one line per venue with its verdict and sources — e.g. "`SIAM J. Imaging Sci.` — Confirmed (ISSN 1936-4954; DBLP, MathSciNet)".
3. **Needs your input** (Tier 3): one line per entry, naming the citation key, what is missing or unconfirmed, and what was left untouched — e.g. "`wang2024sinsr` — author list ends in `and others`; entry left as-is", "`smith2019foo` — venue identity unconfirmed, `@article` vs `@inproceedings` undecided; entry left as-is", "`chen2021red` — title word `red` may be the RED method or the color; left lowercase". Include Constructed-only venue forms here with the missing independent corroboration.
