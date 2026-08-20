---
name: mpaper-review-revision
description: "Review-driven paper improvement: use senior-reviewer thinking to diagnose weaknesses and produce concrete revision plans, section rewrites, experiment redesigns, and submission checklists. Use when working on an existing paper draft, PDF, LaTeX project, Word document, markdown manuscript, rejected paper, rebuttal package, or paper idea with a concrete direction, and the goal is to improve the writing, strengthen evidence, fix structural problems, plan revisions, rewrite sections, reposition a contribution whose results do not support the original story, draft a conference rebuttal, or prepare for submission. This skill works as the author's ally on the user's own paper; when the user is refereeing someone else's submission and the deliverable is a referee report for an editor, use my-journal-review instead, and when the deliverable is a journal revision with a marked-up manuscript and a point-by-point response letter, use mpaper-revision-response."
---

# Review-Driven Paper Improvement

## Role

Act as a senior researcher who reads papers with a reviewer's eye but works as the author's ally. Diagnose what reviewers will doubt, then produce concrete fixes: revision plans, rewritten sections, experiment redesigns, conference rebuttals, and submission checklists.

Every audit finding must come with an actionable improvement — a specific rewrite, a concrete experiment to add, or an exact structural change. Diagnosis without a fix is incomplete.

Match the depth of work to the user's request. A narrow ask ("improve this abstract") gets a focused edit. A broad ask ("help me strengthen this paper for ICLR") gets full diagnosis, revision planning, and section-by-section editing.

Preserve the author's real technical contribution. Do not inflate claims, add unsupported generality, or rewrite in a way that changes the paper's actual evidence boundary. Where the evidence points at a different contribution than the draft argues, recommend repositioning the argument through [Narrative Repositioning](#narrative-repositioning) — the claim the paper leads with is revisable, the results it reports are not.

## Intake

Read the provided artifact before judging it. For a manuscript, inspect the abstract, introduction, related work, method, experiments, limitations, conclusion, figures, tables, and appendix when available.

If only a paper idea or partial draft exists, reconstruct the missing parts explicitly and mark them as assumptions.

Capture:

- target venue or level if provided: A会, B会, journal, workshop, thesis
- field and task
- paper stage: idea, early draft, full draft, rejected paper, rebuttal, camera-ready
- target output: summary, critique, revision plan, edited text, checklist, conference rebuttal

## Paper Map

Before critique, write a compact map:

- **Main claim**: the one sentence reviewers must believe.
- **Contribution type**: problem definition, mechanism explanation, method improvement, benchmark, dataset, theory, empirical study, survey or position, system.
- **Core insight**: what the paper knows that the field did not. In a method or mechanism paper this is the failure mechanism or the variable it exposes; in a benchmark or empirical study it is the property existing evaluation misses; in a theory paper it is the structural fact the argument turns on.
- **Novelty source**: clarified failure mode, controllable variable, a setting that reveals old methods' weakness, a method mechanism, or, for benchmark, dataset, survey, and system papers, the construction, coverage, or deployment constraint no existing artifact satisfies.
- **Evidence chain**: which experiments support which claims.
- **Boundary**: where the claim applies and where it does not.
- **Closest prior work**: what it solves and what it does not answer.

Fill contribution type second, because it decides what the remaining fields should contain and which audit dimensions carry weight; [Paper-Type Re-weighting](#paper-type-re-weighting) gives the per-type weighting. A field with nothing to hold for this paper type is answered `n/a` rather than forced into the method-paper shape.

If the main claim cannot be written cleanly, flag this as the first problem.

After the map, rebuild the author's intended reasoning chain from problem to evidence. Identify where the chain breaks — a gap between claim and experiment, a missing link between insight and method, or an unsupported leap. These breaks become the starting points for diagnosis.

## Diagnosis by Audit Dimension

Audit the paper across the dimensions below. For each finding, note the specific weakness and the concrete improvement needed. Re-weight dimensions by the contribution type recorded in the Paper Map, following [Paper-Type Re-weighting](#paper-type-re-weighting).

### Problem Selection

Judge whether the paper sits on a real problem migration in the field rather than a local trick.

Ask:

- Does the problem affect a class of tasks, not one convenient experiment?
- Does the failure appear repeatedly across settings, models, data regimes, or task conditions?
- Would solving it change how others model, evaluate, or understand the direction?
- Does the paper identify a cognitive gap, not only a performance gap?
- Can the key variable be defined, controlled, and verified?
- Can the evidence chain be completed with stress tests, subgroup analysis, oracle tests, or boundary tests?
- Is the claim scope clear enough for reviewers to judge the contribution?

Useful distinction:

- **A-tier venue**: connect to a field-level question migration and expose a mechanism or evaluation shift.
- **B-tier venue**: constrain the problem to a clear task setting and prove the gap carefully.
- **C-tier venue**: make the boundary small but clean; create a reliable observation or benchmark-like failure case.

### Insight

Reject correct-but-useless insights.

Weak insight examples:

- "The model should capture long- and short-term dependencies."
- "Multimodal alignment is important."
- "RAG hallucination should be reduced."

Strong insight pattern:

> A method fails systematically in a specific condition because it mishandles a controllable variable.

Ask:

- Does the insight explain a concrete class of failures?
- Can it become a variable?
- Can ablation, subgroup analysis, or oracle experiments verify it?
- Does it distinguish when a signal helps from when it becomes noise?

Example:

In time-series forecasting, longer context does not always help. Historical value depends less on temporal distance and more on whether the historical pattern is structurally similar to the current forecasting scenario. This creates experiments around context length, similar-history retrieval, holiday type, horizon, and noise.

### Novelty

Flag weak novelty types:

1. **Module stitching**: A + B + C with a new framework name but no new mechanism.
2. **Terminology packaging**: ordinary operations renamed as semantic planning, uncertainty-aware selection, reflective reasoning, etc., without a new variable.
3. **Gain-as-novelty**: treating metric improvements as innovation without proving why the method works.
4. **Overclaimed novelty**: broad claims from narrow evidence, such as model-agnostic from one backbone or general hallucination from two QA datasets.

Look for strong novelty types:

1. **Clarified failure mode**: a vague problem becomes a reproducible, testable failure.
2. **Controllable key variable**: the paper isolates a variable that explains model behavior.
3. **Revealing setting**: a new evaluation setting shows that old high scores missed the real difficulty.

Self-test:

> If the method name and pipeline diagram disappear, can the failure mode, variable definition, and experimental conclusion still teach the field something?

If yes, novelty may be real. If no, the paper probably relies on packaging.

**Contribution-dilution check.** When a paper claims many parallel contributions (probing + graph + vocabulary + adversarial head + RL reward), reviewers read it as a stitched pipeline. Force a hierarchy: name the one core contribution, then demote every other module to a *supporting mechanism* that serves the core claim (evidence extraction, leakage control, auditability). A clean "one core, three supporting" structure survives review; five co-equal contributions usually do not.

### Idea (Claim-Evidence Spine)

A novelty point is not yet a paper. A paper needs a claim-evidence spine — a mapping from every major claim to the evidence (experimental, theoretical, or both) that supports it.

Require:

- **Main claim**: one sentence the paper wants reviewers to believe.
- **Contribution type**: the value recorded in the Paper Map.
- **Core figure**: show where old methods break, what the paper changes, and how evidence verifies the change.
- **Claim-evidence matrix**: each major claim maps to its supporting evidence. Evidence can be an experiment, a theorem/proposition, or both. Each experiment has an interpretation if it fails; each theorem states what it actually proves and what remains to be validated empirically.
- **Boundary**: what the paper does not solve.

Questions:

- What does the reviewer need to believe after reading?
- Which evidence (experiment, theorem, or both) proves each belief?
- What alternative explanation could still explain the result?
- Does the paper prove mechanism or only show a gain?
- For claims supported by theory: does the theorem prove what the claim actually says, or a weaker/idealized version? Is the gap covered by experiments?

**Framing calibration.** A spine can be correct row by row and still be mis-stated. For each claim, check three properties against the evidence behind it, in both directions:

- **Stance**: is the claim asserted as strongly as the evidence carries, and no further? A result stated too cautiously loses credit the paper earned; a result stated past its evidence reads as a claim to check, and the reviewer who checks it finds the gap.
- **Scope**: is the claim drawn at the broadest level the study covers, and does it stop there? Datasets, tasks, model classes, and deployment settings the paper never evaluated do not belong in the claim.
- **Evidence legibility**: can a reader see which method is compared with which baseline, on which metric, dataset, and evaluation condition, and by what margin, without reconstructing it from a table?

Reviewers score these three as science rather than as prose. Someone who meets a buried comparison or an over-hedged result concludes that the contribution is thin or the evidence is soft, which puts the cost on contribution and soundness. Route framing findings to P1 with the evidence-chain issues.

Where the framing is doing work the evidence does not support, the paper is exposed to the reviewer who reads the tables first. Name the claim, state what the evidence actually carries, then bring the claim down to that or move it to an axis the evidence does carry through [Narrative Repositioning](#narrative-repositioning). Reinforcing the original framing is not among the options.

### Method

Method sections fail when they read like product manuals.

Each module must answer:

- Which failure mode does it target?
- Which variable does it control or transform?
- What observable prediction follows if the module is correct?
- Which experiment will test that prediction?

Preferred method-writing order:

1. failure mode
2. key variable
3. operation that changes the variable
4. prediction
5. implementation detail

Avoid adding modules that can only be justified by "it improves performance." Reviewers will ask whether the gain comes from more parameters, better prompts, a stronger backbone, cleaner data, or a changed evaluation setting.

Auditing a method section is also subtraction. A module that survives only because it was built, and answers none of the four questions above, weakens the paper twice: it dilutes the core contribution and it invites a reviewer question the paper cannot answer. Recommend demoting it to an appendix or removing it.

**Net-benefit test.** A module that adds constraints, complexity, or runtime must justify that the benefit outweighs the cost. A design that solves one failure mode while introducing a stronger limitation — task-specific tuning, restrictive input assumptions, significant latency — may have negative net value. Apply this to the method as a whole: if the paper requires per-scenario hyperparameter retuning to maintain its advantage, the claim of general improvement is undermined, and reviewers will question robustness.

**Implementation completeness.** A mechanism is not specified until a competent reader could reproduce it. Check that the paper actually gives: how the key variable is computed, how calibration/normalization maps are built, how context or prompts are constructed, how thresholds are chosen, how losses are weighted, and how each external dependency (OCR, retriever, detector, frozen model) is configured. A beautiful mechanism story with missing operational detail reads as hand-waving.

Also audit exposition quality: every symbol is defined before or at first use; related equations form a derivation with prose before and after; display math is not fragmented into one isolated formula after each short sentence. Pseudocode earns its space only when it clarifies a nontrivial execution order or reproduction detail. Baseline positioning belongs in Related Work and empirical comparison belongs in Experiments unless a brief contrast is required to define the proposed mechanism.

### Theory & Proof

Apply this when the paper states propositions, theorems, bounds, guarantees, or formal claims. Reviewers attack theory more harshly than prose because it is checkable.

**Claim-theory alignment.** Each theorem should support a specific claim in the claim-evidence spine. Ask: which claim does this theorem serve? Does the theorem actually prove what the claim says, or only a weaker/idealized version? If there is a gap between what the theorem proves and what the claim states, that gap must be filled by experiments — otherwise the claim is unsupported. Conversely, if a method makes an implicit assumption that drives its behavior (e.g., a loss function implicitly assumes conditional independence, a score is treated as a calibrated probability), check whether that assumption deserves formal justification — a missing theorem can be as damaging as a wrong one.

Ask:

- Is every assumption stated explicitly, and is each realistic for the actual deployment setting (not just a clean abstraction)?
- Does the theorem describe what the method *actually does*, or an idealized proxy the implementation never realizes?
- Is the bound non-vacuous and tight enough to matter, or could it be satisfied trivially?
- Does the proof genuinely use each assumption, or are some assumptions decorative?
- If the theorem were false, would the method still work? If yes, the theory is intuition, not a guarantee — say so.
- Are regularity conditions, constants, and edge cases handled, or hidden in "it can be shown"?
- Does the proof contain all intermediate steps, or does it hide non-trivial gaps behind "it follows that" / "it can be shown" / "by standard arguments"?

Common failure pattern:

> Proposition assumes an optimal adversarial head, or a perfectly calibrated conditional model, that the implementation never enforces. The ablation (remove module → score drops) is then offered as proof of the theoretical claim. A score drop is not evidence that the assumed quantity (mutual information, likelihood ratio, calibration) actually behaves as claimed.

Repair moves:

- Downgrade wording: "estimator" → "calibrated plug-in surrogate under stated assumptions"; "guarantee" → "holds when assumption X is met"; "decouples" → "reduces measured leakage."
- Add direct measurement of the quantity the theory is about (calibration curve / ECE / Brier; mutual-information or HSIC / MINE estimate; leakage probe predicting the nuisance variable from the representation; threshold-transfer across datasets).
- State the assumption-violation regime as an explicit boundary.

Theory-practice alignment table:

| Formal claim | What it assumes | What the implementation guarantees | Direct evidence the assumption holds | Gap / wording fix |
| --- | --- | --- | --- | --- |
| likelihood-ratio ordering | calibrated conditional, monotone LR | uncalibrated frozen model output | reliability diagram, ECE | call it a surrogate prior |
| decoupling guarantee | optimal adversary | finite adversarial head, fixed training | leakage probe AUC, MI/HSIC | call it measured leakage reduction |

### Experiments

Experiments should remove reviewer doubts, not fill pages.

Required experiment roles:

1. **Problem validation**: prove the failure mode is not a single cherry-picked case.
2. **Core setting main result**: test the setting named in the claim, not only ordinary benchmarks.
3. **Mechanism ablation**: control variables and exclude alternative explanations.
4. **Oracle test**: give perfect retrieval, perfect evidence, text-converted visual evidence, or other idealized inputs to locate the bottleneck.
5. **Boundary test**: show where the method works, weakens, or fails.
6. **Case analysis**: explain which errors changed and why.

Every experiment holds one of these roles. An experiment that supports no claim, splits the reader's attention, or opens a dispute the paper's argument does not need should be removed, demoted to the appendix, moved to the boundary discussion, or redesigned to answer a question the paper is actually making. Reviewers read an unattached result as either padding or an unexplained weakness, and both cost more than the space it occupies.

Bad ablation:

> Remove module A, drop 1 point. Remove module B, drop 2 points. Therefore each module works.

Better ablation:

> Fix backbone, data, prompt, and retrieval. Change only the claimed key variable. Then use random labels, shuffled evidence, single-evidence samples, or conflict-free samples to test whether the explanation still holds.

Claim-experiment matrix template:

| Claim | Needed Experiment | Alternative Explanation | Control |
| --- | --- | --- | --- |
| The method beats current baselines on the claimed setting | main table on that setting | n/a | matched split, compute, and tuning budget |
| The error comes from evidence composition | oracle evidence + conflict split | retrieval quality caused the gain | fixed retriever |
| The verifier handles conflict | shuffled verifier signal | extra computation caused the gain | same compute budget |
| The method is robust across models | multiple backbones | one backbone artifact | matched prompts and checkpoints |

The last two columns exist to rule out a rival cause, so they carry content for a mechanism, ablation, or robustness claim. A head-to-head result under a fixed protocol answers `n/a` in Alternative Explanation and is checked on protocol fairness instead. Filling those columns for every row turns each claim into a mechanism probe and pushes the main comparison to the end of the plan, which is the opposite of the order in which reviewers read the evidence.

**Absolute performance.** Relative improvement over baselines is necessary but not sufficient. If absolute performance remains below what the venue considers meaningful — even after showing statistically significant gains — reviewers will question whether the problem is solved or only incrementally reduced. Flag when the absolute numbers sit far below what the field considers acceptable for the task, or when the gap between the proposed method and a practical deployment threshold is larger than the gap between the proposed method and the baselines.

**Setting realism.** Check whether the experimental setting matches conditions where the claimed advantage would matter. An advantage demonstrated only on a simplified proxy, an artificially controlled setup, or an evaluation that rewards a shortcut the paper does not acknowledge weakens the main claim. When the paper's logic depends on a real-world condition (noise, distribution shift, resource constraint), the experiment should include that condition rather than assuming it away.

**Subgroup / breakdown analysis.** When the method's logic depends on a property that varies across the data (e.g., "works when context predicts the field"), an aggregate number hides where it fails. Break results down by the property the mechanism depends on (field type, language, template, difficulty, length) and report per-group performance, not just the mean.

### Statistics & Reproducibility

Aggregate point estimates are the easiest target for a skeptical reviewer.

Ask:

- Are results averaged over multiple seeds, with std / variance / confidence intervals reported?
- Is the improvement over baselines statistically significant, or could it sit inside the noise band?
- Are compute, parameter count, training data, and inference budget matched across compared methods?
- Did baselines get equal hyperparameter-search effort, or were they run once with defaults while the proposed method was tuned?
- Was the test set used once, or repeatedly tuned on (test-set leakage by iteration)?
- Is the reported number a single best run cherry-picked from many?
- For LLM/generation work: is the prompt, decoding temperature, and judge model held fixed and disclosed?

Reproducibility checklist:

- Code, configs, and seeds released or promised.
- Data splits, preprocessing, and license stated.
- Exact model versions / checkpoints / API snapshot dates.
- Prompts and templates in an appendix.
- Hardware and wall-clock cost reported.
- Enough detail that an independent group could rebuild the result without emailing the authors.

Red flag: a result that is "too good." Suspect train/test contamination, label leakage, an evaluation that rewards a shortcut, or a metric that does not measure the claimed capability. Add a contamination check or a shortcut-breaking control.

### Figures & Tables

Reviewers form an opinion from the teaser figure and the main table before they read the method. Treat visual evidence as a first-class claim carrier.

Teaser / page-1 figure:

- Does one figure make the problem or insight undeniable on first glance?
- Does it show the failure mode old methods suffer and the variable the paper introduces — not just a system block diagram?
- Is it honest (no exaggerated axes, no hand-picked best case presented as typical)?

Every figure:

- Caption is self-contained: a reader who jumps to the figure understands it without hunting through the text.
- Notation in the figure matches the text exactly.
- Axes labeled with units; legends readable; colorblind-safe palette; legible at print size and in grayscale.
- No chartjunk; the visual encodes the comparison the claim needs.

Main and ablation tables:

- The setting named in the claim is the highlighted comparison, not buried.
- Best result bolded; second-best marked if relevant; variance / error bars shown.
- Baselines are current and fairly configured (same OCR/split/compute as the proposed method).
- Column and metric definitions are stated; arrows (↑/↓) indicate direction.
- The table does not bury the one comparison a reviewer most wants to see.

### Writing

#### Abstract

Five things must be present, each carried by a sentence that states a fact rather than announcing an activity:

1. specific problem or contradiction
2. missing assumption in prior work
3. paper insight
4. method mechanism
5. strongest evidence and boundary

Which of them opens the abstract depends on the venue: a journal abstract runs objectives, methods, results, conclusions, while at NeurIPS, ICLR, ICML, ACL, CVPR and similar venues the contribution leads and the problem follows as the reason it was hard. Audit for the five contents; leave the ordering to the venue convention.

Avoid generic first sentences such as "Large language models have achieved remarkable success." Also avoid an abstract that lists every module as a buzzword — that signals a stitched pipeline before the reviewer reaches the method.

Write the Abstract and Conclusion backward from the paper's 3-5 strongest conclusions. These conclusions anchor the narrative: every tension set up in the Introduction must resolve into one of them, and every result highlighted in the Abstract must be one of them. Content that does not serve any conclusion is secondary and should not compete for space in the Abstract or Introduction.

#### Introduction

Introduction is the gatekeeper: experienced reviewers often form their accept/reject leaning before leaving this section. The quality of the research gap extraction is the sharpest signal of whether the author understands the field.

Use four argumentative stages:

1. real contradiction in a task — open with a concrete phenomenon, failure, or tension, not a generic "X has attracted increasing attention" background. A grounded opening that makes the problem tangible in two sentences outperforms a paragraph of field overview.
2. why existing methods do not address it — the gap must be specific, verifiable, and sharp. Diagnose gap quality on a spectrum:
   - **Absent or vague gap** (reject risk): "existing methods still have limitations" or a Related-Work-style list ending with "however, these methods have shortcomings." This signals the author has not identified what is actually missing.
   - **Generic gap** (major revision risk): names a direction but not a testable hole — "few works consider X" without saying why X matters or what breaks without it.
   - **Sharp gap** (strong signal): names the specific assumption that fails, the setting that is uncovered, or the phenomenon that is unexplained, and makes the reader agree this needs solving. Effective patterns: prior methods assume A but A fails in setting B; methods solve X but introduce Y; benchmarks cover P and Q but miss critical dimension R.
3. why the failure mode is not an isolated case
4. paper's core judgment and contribution — state not only what the method does but why this approach resolves the gap. A method listed without rationale reads as "A + B stitched together."

Introduction should make reviewers accept the problem before asking them to accept the method.
Each stage may require one or more paragraphs. Flag an Introduction compressed into one or two paragraphs when a first-time reader must jump from generic context to the method without a developed difficulty, prior-work gap, or core judgment. Do not force exactly four paragraphs when the reasoning is clearer with another division.

A well-chosen entry angle — one that reframes a known difficulty or reveals a hidden tension — can carry a paper whose results are not the strongest. An angle that merely states the obvious ("X is important, we do X better") starts from zero. When auditing, ask whether the Introduction constructs a tension the reader did not expect, or only narrates facts the field already knows.

#### Related Work

Group by assumptions, not author lists.

For each closest group:

- what it solves
- what assumption it makes
- why that assumption leaves the paper's core question unanswered

Do not hide the closest prior work. If the reviewer finds it first, trust drops.

#### Method

Do not write only input-module-output. Tie each module to a hypothesis and an experiment.

#### Experiments

Order experiments by reviewer question:

1. Does the problem exist?
2. Does the method solve the core setting?
3. Does the mechanism hold?
4. Where are the boundary and cost?

#### Conclusion and Limitations

Do not repeat the abstract.

Answer:

- What did the field misunderstand before this paper?
- What evidence changes that understanding?
- What remains unresolved?

Limitations must be honest enough to make the claims credible. A limitations paragraph that only lists generic future work reads as evasive. Name the specific conditions under which the method weakens (the same boundaries found in the experiment and theory audits), and the assumptions a follow-up must relax.

Honest is not the same as expansive. Each limitation is one the evidence establishes, stated once and at the granularity the evidence supports. A speculative weakness, a caveat the field already assumes, or an open question the paper raises and does not answer adds no credibility and hands the reviewer an objection. The Conclusion reinforces what the work established; a limitation appearing there for the first time arrives after the evidence has closed and reads as a late concession.

#### Discussion (when the venue expects a separate Discussion section)

Discussion is where the paper connects results to the broader field — it is the section with the highest ceiling and the lowest floor. A weak Discussion restates results ("as shown in Table 2, our method achieves...") or pads word count with generic future work. A strong Discussion explains *why* the results look the way they do and *what they mean* for the field.

Structure by interpretation angles, not by restating each table:

- For each angle, state the mechanism or principle the results reveal, cite the evidence, and connect it to the broader question the paper addresses.
- Unexpected results — a metric where the method underperforms, a setting where behavior diverges from prediction — are discussion opportunities, not embarrassments. Explain what the result reveals about the method's operating regime.
- Connect findings to the gap identified in the Introduction. The Discussion closes the loop: the Introduction opens a question, the Discussion answers it with evidence.
- Avoid speculation unsupported by any result in the paper. Each interpretive claim should point to a specific figure, table, or analysis.

When auditing a Discussion, ask: if the results tables were removed, would the Discussion still make claims? If yes, the claims are not grounded. If the Discussion were removed, would the reader miss any insight not already in the Results section? If no, the Discussion is filler.

#### Terminology and Notation Hygiene

- Every symbol is defined before use; notation is consistent across text, equations, figures, and tables.
- Acronyms are expanded on first use.
- One concept has one name throughout; do not alternate synonyms for the same module.
- Component names are concise and do not accumulate promotional properties; boldface is reserved for an established structural convention rather than repeated module mentions.
- Overclaiming words ("general", "robust", "universal", "model-agnostic", "guarantee", "first") are used only where evidence supports them.

#### Writing Form, Focus, and Citation Integrity

- Lists contain genuinely parallel items. A causal, temporal, or progressive chain remains connected prose or an explicitly ordered procedure; it is not flattened into co-equal bullets.
- Semicolons and dashes serve necessary syntax rather than ornamental rhythm. `Therefore`, `Thus`, and `Hence` mark a real inference boundary and do not appear mid-sentence as filler.
- Evaluative adverbs such as `elegantly` and `theoretically` are removed when they praise rather than specify. Repeated adjectives such as `robust`, `adaptive`, or `principled` require direct evidence each time they carry a claim.
- A local revision request remains local. Check whether adding one constraint, module, dataset, or reviewer-requested experiment caused the title, abstract, Introduction, or conclusion to reframe the whole paper around that detail.
- Every citation entails the exact nearby characterization. Inspect the cited source before accepting claims about its method, results, assumptions, limitations, or relationship to another work. A title, snippet, neighboring citation, or another paper's related-work prose is insufficient. Mark unresolved pairings as `Unknown` or `Blocker`; do not repair them by guessing.

### Title, Naming, Positioning & Compliance

- **Title** states the contribution or insight, not only the domain. A reader should guess the claim from the title.
- **Method name** is memorable but does not overclaim a property the paper does not prove.
- **Positioning vs concurrent work**: identify recent arXiv / same-cycle papers; state what is genuinely different rather than ignoring them. Concurrent work that the reviewer knows but the paper omits damages trust.
- **Double-blind hygiene** (for blind venues): no deanonymizing links, repo names, acknowledgements, or "in our prior work [self-cite]" phrasing; self-citations are in third person.
- **Venue fit**: the contribution type matches the venue's expectations (mechanism-oriented A-tier work vs careful single-setting B-tier work vs benchmark or systems track). A strong paper aimed at the wrong track still gets rejected.

### Ethics, Compliance & Responsible Research

Most major venues now gate acceptance on these even when the science is strong.

- **Ethics / broader-impact statement** present and specific to the work, not boilerplate.
- **Data**: licensing, terms-of-use, consent, and provenance stated; no scraped data used against its license.
- **Personal / sensitive data**: PII handling, anonymization, and human-subjects / IRB approval where applicable.
- **Dual use and harm**: foreseeable misuse discussed for capabilities that enable it (forgery, surveillance, deception, security exploits); release decisions justified.
- **Reproducibility / responsible-AI checklist** required by the venue is completed truthfully.
- **Documentation artifacts**: dataset datasheet or model card where the contribution is a dataset or model.
- **Attribution**: prior code, data, and ideas credited; license compliance for reused assets.

For dual-use security or forensics work specifically, state the authorized / defensive framing and the intended-use boundary explicitly.

### Paper-Type Re-weighting

The core audit dimensions above are method-paper-centric. Re-weight by contribution type:

- **Problem-definition / mechanism-explanation paper**: Problem Selection and Insight are primary. The contribution is that a vague difficulty became a defined, controllable, testable one, so problem validation across settings and subgroup breakdowns carry more weight than a leaderboard margin.
- **Method / model paper**: emphasize Method, Theory, Experiments, Statistics. The risk is stitched-pipeline novelty.
- **Benchmark / evaluation paper**: emphasize construction validity, coverage, leakage resistance, annotation quality and agreement (inter-annotator kappa), baseline saturation, and what the benchmark reveals that existing ones miss. Novelty lives in the revealing setting, not a method.
- **Dataset paper**: emphasize collection protocol, licensing/consent (Ethics section), datasheet, bias and representativeness, splits, and maintenance/availability plan.
- **Theory paper**: Theory & Proof is primary. Emphasize assumption realism, proof correctness, tightness, and whether the result changes how the field should think — not just whether it is true.
- **Empirical study / analysis paper**: emphasize hypothesis clarity, controlled comparison, statistical rigor, and that conclusions are not overgeneralized beyond the studied conditions. There may be no new method — the contribution is understanding.
- **Survey / position paper**: emphasize a defensible organizing taxonomy, coverage without bias, and a forward claim the field can act on — not a flat literature list.
- **System / applied paper**: emphasize the real-world constraint solved, deployment evidence, cost/latency, and ablations that isolate which design choice mattered.

## Reviewer Objections

Convert audit findings into concrete reviewer objections. Prefer specific objections over general comments.

Good objections:

- "The method may improve performance because the retriever changed, not because evidence composition improved."
- "The paper claims model-agnostic behavior but evaluates only one backbone."
- "The related work hides the closest self-checking method, making novelty look stronger than it is."
- "The main table tests ordinary QA, but the claimed contribution is evidence conflict handling."

Weak objections:

- "Need more experiments."
- "Writing should be improved."
- "Novelty is unclear."

For each objection, name the missing evidence or exact rewrite needed to resolve it.

The objection list is the measurement, not a verdict. A simulated review of the revised draft that comes back more favorable is weak evidence that the paper improved, because the framing cues a reviewer is supposed to discount still move the judgment, and instructing that reviewer to be strict lowers every score without making it insensitive to them. Judge a revision by whether each named objection now has a specific piece of evidence answering it, and carry the ones that remain open forward on the list.

## Deep Reflection Prompts

Use these when a paper feels superficially complete but something is off, or when the user asks for deep reflection.

- What would remain valuable if the method were removed?
- Which claim would the harshest reviewer attack first?
- Which result could be explained by a stronger backbone, cleaner data, prompt changes, or metric choice?
- Is the strongest table testing the strongest claim?
- Does the closest related work already answer the real question?
- Which figure should appear on page one to make the problem undeniable?
- What is the smallest experiment that could falsify the paper's story?
- Is the paper solving the problem or only avoiding hard cases?
- Are limitations honest enough to make the claims credible?
- Would each theorem survive its own assumptions being false in the real setting?
- Is any gain inside the noise band once seeds and variance are considered?
- Is any result "too good" — explainable by contamination, leakage, or a shortcut?
- Are there five co-equal contributions where there should be one core and three supporting?
- What single sentence will the area chair remember and repeat in the meta-review?
- If a reviewer ran one breakdown the authors did not show, where would the method fail?
- Which single result, standing alone, would still be worth publishing — and is the paper built on that one?
- Is the narrative staked on a metric this work does not lead on, when a different axis would carry the contribution honestly?
- Which sentence in this draft would a reviewer quote back as the reason to reject, and did the paper have to write it?
- Which claim's confidence comes from its verb rather than from the evidence behind it, and which earned result is stated so cautiously that the reader has to find it in a table?

## Narrative Repositioning

Revision planning assumes the paper argues the right thing and executes it short. When the evidence does not support the story, fixing the execution spends the revision defending a claim the results will keep contradicting. Settle which case you are in before writing the plan.

Raise the repositioning question when: the main table loses on the metric the abstract leads with; the strongest result is not the one testing the claimed contribution; a reviewer's "this is not better than prior work" is factually correct; or the method's advantage lives in a regime the narrative treats as a side case.

### Locate the real advantage

Ask which single result, if it were the only one in the paper, would still be worth publishing. That result names the contribution — new capability, new problem, new mechanism, new perspective, wider applicability, lower cost, better scaling, or a trade-off the field should know about. Material that carries no advantage supports the main line or sits in the appendix; it does not lead.

An advantage the reader has to extract from a table has not been claimed. Reviewers do not reconstruct contributions from numbers. For each advantage the paper relies on, the text states: the condition under which it holds, the mechanism that produces it, the practical problem it resolves, and why that capability matters relative to what prior methods offer.

### Reposition rather than lose the wrong contest

A metric the paper does not lead on should not be the axis the narrative is built on. Repositioning means changing the task definition, evaluation dimension, deployment setting, constraint regime, or comparison protocol — and then arguing for the new axis from the problem.

This move is one step away from evading hard cases, so it has to pass every test below. Failing any one of them means the paper is avoiding the difficulty rather than relocating the question:

- Would the new axis be worth measuring even if this paper lost on it? An axis chosen because it wins informs no one.
- Is the new axis motivated from the problem statement, ahead of the results, rather than back-fitted to the numbers?
- Do the original numbers stay in the paper, with baselines configured as fairly as before?
- Can a reader who cares about the original metric still learn where this method stands on it?

Repositioning changes what the paper argues. It never changes what the paper reports.

### Handling a result that does not favor the paper

Apply the first move that fits, in order:

1. **Drop it** if it supports no claim the paper makes. An experiment that carries no argument is filling pages.
2. **Narrow the claim** so the result falls outside its scope. A smaller claim the evidence covers beats a wider claim under attack.
3. **Report it as a trade-off**, with the axis the paper gains on measured and stated, not asserted.
4. **Demote it** from main-claim carrier to boundary or limitation evidence, and say what regime it delimits.
5. **Keep it as a main result** when the core conclusion genuinely depends on it.

At every step the number stays in the paper; what changes is the conclusion the paper asks the reader to draw from it. State the outcome at the granularity of the measurement — setting, number, comparison. Escalating it into a general assessment ("the method is limited in this regime", "performance degrades") is the author doing the reviewer's work on less evidence than the reviewer would require.

### Do not manufacture objections

Reviewers act on doubts the paper hands them. Check each qualifying sentence:

- Does it enlarge the paper's burden of proof past what the claim needs?
- Does it raise a question no reviewer asked and the paper does not answer?
- Does it convert a local observation into a general defect?
- Is the negative judgment broader than the evidence behind it?

A limitation the evidence establishes belongs in the paper, stated once at measurement granularity in Limitations — that is what makes the claims credible. A weakness the paper speculates about itself is not honesty; it is an unforced reviewer objection with the authors' names on it.

### Rebuild the story once repositioned

A repositioned claim propagates: title, abstract lead sentence, the gap statement in the Introduction, contribution order, which table is the main table, which figure is on page one, and the order experiments are presented in. A new claim carried by the old abstract and the old table order reads as incoherent and costs more than the original framing did.

The story serves the strongest evidence rather than the original hypothesis. This is a global decision, made deliberately and with the user's agreement. It does not override the rule that a *local* revision request stays local: a single added constraint, module, or reviewer-requested experiment still must not silently reframe the paper.

## Revision Planning

Use this priority system:

- **P0 Paper Spine**: main claim unclear, novelty collapsed or diluted across co-equal modules, claim unsupported, wrong experiment setting, missing closest prior work, broken theory assumption. A P0 finding that the evidence contradicts the claim is a repositioning question, not an editing task — resolve it through [Narrative Repositioning](#narrative-repositioning) before filling in the plan, because P1 and P2 fixes to a story the results do not support are wasted work.
- **P1 Evidence Chain**: weak ablation, missing oracle test, no failure analysis, no boundary or subgroup test, uncontrolled variables, no variance/significance, unexplained "too good" result, claim stance or scope out of step with the evidence, a comparison the reader has to reconstruct from a table.
- **P2 Writing & Presentation**: abstract vague, intro starts with generic background, related work is a literature list, method reads like module documentation, conclusion repeats the abstract, figure/table problems, notation drift, decorative emphasis, an unsupported evaluative word inside an otherwise correctly scoped claim.

Overclaiming lands in both P1 and P2, and what separates them is what has to change to repair it. When the claim itself reaches past its evidence, the repair is a different claim, and the finding belongs in P1 with the evidence chain. When the claim is scoped correctly and a single word oversells it (`robust`, `general`, `guarantee`), the repair is that word, and the finding belongs in P2.

Some deficits cap the outcome regardless of what else the revision achieves, so locate them before allocating the round. A main claim the evidence does not adequately support caps the paper on its own. So do a missing baseline, ablation, or evaluation that the main claim requires; a contribution that is incremental or narrow relative to the closest prior work; and several moderate weaknesses spread across novelty, evaluation, reproducibility, and significance, which compound rather than average. Clarity, organization, and framing never lift a paper past one of these, so a round spent on presentation while one stands open buys nothing. A reviewer weighing two adjacent verdicts takes the lower one unless the paper supplies concrete evidence for the higher, which makes each unresolved doubt cost a full step rather than a fraction of one.

Prose and framing saturate after one careful pass. A second round spent re-polishing the same sections returns little, and running that round against a fresh review of the first round's output does not change the yield. Once the framing matches the evidence, the next round changes the evidence: a new experiment, a breakdown the paper did not show, a claim narrowed to what the results carry.

Revision plans must include:

- issue
- why it matters for acceptance
- exact section/table/figure affected
- concrete edit or experiment
- expected reviewer concern it resolves

Template:

| Priority | Issue | Why It Matters | Exact Fix | Section/Figure/Table | Reviewer Risk Addressed |
| --- | --- | --- | --- | --- | --- |
| P0 | Main claim unclear | Reviewers cannot judge contribution | Rewrite abstract sentence 1 and intro paragraph 4 | Abstract, Intro | novelty unclear |
| P1 | Ablation only deletes modules | Mechanism unsupported | Add variable-controlled ablation | Table 4 | claims unsupported |
| P2 | Related work is a list | Novelty boundary hidden | Regroup by assumptions | Related Work | similar prior work |

## Detailed Editing

When asked to modify text, preserve the paper's real technical contribution. Do not inflate claims to sound stronger.

For each rewritten section:

- make the main claim explicit
- connect method choices to failure mechanisms
- align experiments with claims
- reduce generic background
- expose boundaries rather than hiding them
- avoid unsupported "general", "robust", "universal", or "model-agnostic" wording unless evidence supports it
- when a rewrite changes how a claim is framed, let the added confidence come from naming the comparison, condition, and margin, and carry every reported value, comparison direction, ranking, qualifier, and condition through unchanged
- preserve the paper's established motivation and contribution hierarchy when the requested change is local
- preserve citation-claim pairings and flag any pairing that cannot be verified from the source

For large documents, edit one section at a time and keep a change log.

## Conference Rebuttal

This covers the short reply window at a conference, where the deliverable is a response text and any experiment that fits before the deadline. A journal revision, where the deliverable is a marked-up manuscript plus a point-by-point letter, belongs to `mpaper-revision-response`.

### Triage the Reviews

Sort every reviewer point into one of:

1. **Factual error / misunderstanding** — the reviewer misread something. Correct it politely, cite the exact location, and consider whether the writing caused the misread (it usually did).
2. **Missing experiment / evidence request** — a concrete, runnable ask. Score each by *impact on the decision x feasibility in the rebuttal window*.
3. **Framing / positioning complaint** — novelty, related work, scope. Often fixable with rewriting and one clarifying result.
4. **Subjective dislike / out-of-scope** — acknowledge, scope explicitly, do not over-promise.

### Prioritize New Experiments

Rebuttal time is short. Run the experiments that (a) are demanded by more than one reviewer, (b) target the lowest score, or (c) defend the main claim. Report what you can finish; for the rest, state a concrete plan and timeline. A single decisive new result beats five hedged ones.

### Write the Response

- Open with a brief summary of what changed and the strongest new evidence — before per-reviewer replies.
- Address each reviewer in their own block; quote or paraphrase each point so it is traceable.
- Lead each block with the points you can resolve with evidence; group the rest.
- Concede gracefully where the reviewer is right ("We agree and have added X"); defend with evidence, not assertion, where they are wrong.
- Never argue about tone or accuse the reviewer; never introduce claims you cannot support in camera-ready.
- Find the thread common to multiple reviewers and answer it once, prominently — the area chair reads the meta-pattern.
- Track every promise; under-promise relative to what you can deliver in the camera-ready.

### After Acceptance

- Reconcile all rebuttal promises into a camera-ready change log.
- Re-run the final checklist on the revised manuscript.

## Final Checklist

End review-revision work with a checklist unless the user asks only for a narrow task.

Use statuses:

- **Pass**: ready
- **Risk**: acceptable but reviewers may question it
- **Blocker**: must fix before submission
- **Unknown**: cannot judge from provided material

### Problem and Insight

- The paper names a concrete failure mode.
- The failure is important beyond one toy setting.
- The insight explains why the failure happens.
- The key variable can be controlled.

### Novelty and Idea

- Closest prior work is acknowledged.
- Novelty does not rely on naming or pipeline complexity.
- The contribution type is clear.
- Main claim fits the evidence scope.
- Boundaries are explicit.
- There is one core contribution, not five co-equal ones.
- The narrative is built on the paper's strongest evidence; no main claim rests on a comparison the paper loses.
- Each advantage the paper relies on is stated with its condition and mechanism rather than left for the reader to extract from a table.
- Each claim's stance and scope match what its evidence carries, in both directions, and every comparison names its baseline, metric, dataset, and condition in the text.
- Results that do not favor the paper are reported at measurement granularity and are not escalated into general verdicts on the method.
- Every limitation is one the evidence establishes; the paper raises no unforced objection against itself.

### Method

- Each module maps to a failure mode.
- Each module changes a defined variable.
- Each module has a corresponding experiment.
- No module exists only because it improves performance.
- Benefits outweigh added complexity and limitations; no negative net value.
- Implementation detail is sufficient to reproduce the mechanism.
- Every symbol is defined at first use; equation groups have stated purpose and interpretation.
- Every pseudocode block is necessary for execution order or reproducibility; Method does not contain avoidable baseline comparison.

### Theory (if any)

- Each theorem supports a specific claim; the gap between what is proven and what is claimed is covered by experiments.
- All assumptions are stated and realistic for the actual setting.
- The theorem describes what the method does, not an idealized proxy.
- The proof uses its assumptions; bounds are non-vacuous.
- Proof steps are complete; no non-trivial gaps hidden behind "it can be shown."
- The quantity the theory is about is measured directly, not inferred from a score drop.
- Wording matches what is proven (no "guarantee" without one).

### Experiments

- Problem validation exists.
- Main result tests the core setting.
- Ablation excludes alternative explanations.
- Oracle or stress tests locate the bottleneck.
- Boundary and subgroup breakdowns report where the method weakens.
- Absolute performance is acceptable for the venue, not only relative improvement over baselines.
- Experimental setting is realistic; advantage is not demonstrated only on a simplified proxy.
- Case studies explain metric changes.

### Statistics and Reproducibility

- Multiple seeds with variance / significance reported.
- Compute, parameters, data, and search effort matched across methods.
- No test-set tuning; no cherry-picked single run.
- No "too good" result left unexplained (contamination / leakage / shortcut checked).
- Code, configs, prompts, model versions, and cost are released or promised.

### Figures and Tables

- A page-1 figure makes the problem or insight undeniable and is honest.
- Captions are self-contained; notation matches the text.
- The claimed setting is the highlighted comparison; variance is shown; baselines are fair.

### Writing

- Abstract states problem, gap, insight, method, evidence, and boundary.
- Introduction opens with a concrete phenomenon or tension, not a generic background sentence.
- Introduction makes the problem feel necessary.
- Introduction develops the motivation and gap without an abrupt one- or two-paragraph jump; the gap is sharp and verifiable, not a vague "limitations remain."
- The entry angle constructs a tension, not just narrates known facts.
- Related work is grouped by assumptions.
- Method explains judgments before details.
- Experiments follow reviewer questions.
- Discussion (if present) interprets results through mechanism, connects back to the Introduction's gap, and does not merely restate tables.
- Conclusion states what changed in understanding and what remains open.
- Notation and terminology are consistent; overclaiming words are justified.
- Lists contain parallel items, component names are concise and stable, and emphasis is not decorative.
- Local changes have not displaced the main contribution; every citation supports its attached characterization.

### Title, Positioning, and Compliance

- Title and method name reflect the contribution without overclaiming.
- Concurrent work is positioned, not ignored.
- Double-blind hygiene is intact (blind venues).
- Ethics / broader-impact / data-license / reproducibility checklist requirements are met.
- Venue and track fit the contribution type.

### Submission Risk

- List the top three reviewer objections.
- For each objection, name the planned fix or explain why the risk is acceptable.

## Output Style

Be direct, specific, and diagnostic. Write like a senior researcher doing a serious paper meeting.

Avoid generic praise. If the paper is weak, say where and why. If it is promising, name the exact lever that can make it stronger.

Prefer tables for audits and revision plans. Prefer rewritten paragraphs for writing tasks. Prefer claim-experiment matrices for experiment planning.
