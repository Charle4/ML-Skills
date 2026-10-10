---
name: mpaper-revision-response
description: "Journal revision and response (R&R) for ML, applied/computational mathematics, optimization, and inverse problems papers. Full-cycle: reviewer comments analysis with multi-agent cross-validation, revision plan, manuscript editing with blue-marking, point-by-point response letter, and response-manuscript consistency verification. Use when the user receives actual reviewer comments / referee reports from a journal and needs to plan revisions, draft response letters, edit the manuscript accordingly, or verify that the response letter matches the actual manuscript changes. Also use when the user says 返修, revision, R&R, rebuttal, response to reviewer, 审稿意见, 修订, 回复, respond to referees, revision plan, or points at a reviewer report / decision letter file. Boundary with sibling skills: mpaper-review-revision is for self-initiated review-perspective diagnosis before submission; this skill is for responding to real reviewer feedback after submission to a journal; a conference rebuttal during the author-response period goes to mpaper-review-revision. For isolated paragraph-level English editing within the revision, the user may additionally invoke mpaper-en-academic-writing."
---

The `Base directory for this skill:` line injected at the top when this skill loads gives its absolute path; replace every `<SKILL_DIR>` below with it.

# Journal Revision & Response (R&R)

Handle the complete revision cycle for journal papers in ML, applied mathematics, computational mathematics, optimization, inverse problems, and related fields.

## Inputs

The user provides some combination of:
- **Reviewer report(s)**: `.txt`, `.pdf`, `.md`, or pasted text (editor decision letter + individual reports)
- **Original manuscript**: `.tex` source and/or compiled `.pdf`
- **Reference response letters** (optional): examples of past responses for format reference

Read all inputs completely before any analysis.

---

## Core Principles

These principles govern every step of the revision. They come from hard-won experience with actual journal revisions.

### Manuscript Integrity

1. **The paper is an organic, self-consistent story, not a Q&A transcript.** Revisions must read as if the content was always there. No seams, no "as suggested by the reviewer" in the manuscript body.

2. **Response and manuscript serve different audiences.** The response letter speaks directly to the reviewer — it can be more specific, include derivations, cite exact values. The manuscript must read fluently to a future reader who never saw the review. The letter argues; the manuscript does not. A manuscript change made in reply is a result, a precise definition, a clearer design statement, or a narrowed claim, not added reassurance or a sentence about what the paper does not claim; what the paper does not cover goes once into the limitations and future-work passage at the end. Wording calibrated to persuade the reviewer (`the remaining factors could not be separated`) stays in the letter; the manuscript states what was varied and what was held constant.

3. **Every modification must preserve global consistency.** After changing any content (initialization, notation, parameter values, algorithm description), grep the entire manuscript for all related mentions and update them consistently. Changes in Algorithm 2 must propagate to Algorithm 3, to the implementation section, to the appendix.

4. **Blue-marking discipline.** Changes inspired by or responsive to reviewers: mark with `\textcolor{blue}{...}` (single expressions) or `{\color{blue} ...}` (multi-line blocks). Self-discovered typos, notation unification, and other improvements the reviewer didn't ask about: fix silently, no blue marking, no mention in the response.

5. **Theoretical-practical gaps stay quiet.** When the code uses a trick (e.g., over-relaxation parameter $\gamma=1.05$) or a theoretical condition is far from the experimental operating point (e.g., $\rho > 2L$ requires $\rho > 0.4$ but experiments use $\rho \sim 10^{-3}$), do not volunteer these gaps unless the reviewer specifically asked. Exposing them risks escalating minor revision to major.

### Response Letter Craft

6. **The reviewer wants three things: you read their comment, you changed the paper, the paper is now better.** Structure every response to deliver exactly these three signals.

7. **Response format: black question, blue answer.** Reproduce each reviewer comment verbatim in black, then respond in blue. Each response references the specific location of the revision (section, page, line, equation, algorithm, figure, table number). Use ``` ``...''\, ``` to quote added or modified text from the manuscript when it helps.

8. **The summary paragraph comes last in writing, first in the document.** Write all point-by-point responses first, then compose the summary ("Dear Editor and Reviewer, ... The main corrections are marked in blue. The revisions are summarized as follows: ..."). This ensures the summary accurately reflects what was actually done.

9. **Response can be more detailed than the manuscript.** Technical details the reviewer needs to see but that would clutter the manuscript (seed values, cudnn settings, exact parameter tables, full derivations) go in the response letter, not the paper.

### Editing Discipline

10. **Modification scope: only change what has a substantive reason to change.** Do not make cosmetic rewrites, synonym substitutions, or sentence restructurings in areas the reviewer did not ask about and the content does not require. If "The two hyperparameters of X are" works, do not change it to "X has two hyperparameters:" — there is no reason and it creates noise in the diff. Every blue-marked change must trace to a specific concern; every silent change must fix a genuine error or inconsistency.

11. **Restructure for coherence, not just append.** When adding substantial content to a section, consider reorganizing the existing text so the new material flows naturally — the reader should feel the section was always written this way. "Head + tail" additions (new opening paragraph + new closing guidelines, with the existing analysis in the middle) often work better than appending a paragraph at the end.

12. **Consider LaTeX layout impacts.** Algorithm pseudocode has limited line width. When modifying algorithm lines, check that the result fits. Plan for two-line splits, color marking interactions with tikzmark backgrounds, and \Statex continuation lines. Compile and visually inspect algorithm blocks after editing.

### Tone and Language

13. **Courteous but confident, never defensive or submissive.** "We thank the reviewer for noting that..." is better than "We agree that...". Never say the reviewer is wrong — reframe misunderstandings as presentation issues ("We apologize for the lack of clarity"). But do not over-apologize or pre-emptively weaken claims. End a supported answer on the answer and the revision, without a habitual concession such as `However, this does not prove...`. In revised manuscript text, if a sentence serves only to preempt potential objections rather than advance the argument, delete it. In both manuscript and response prose, a connective may label only a relation supported by the cited comment, manuscript fact, equation, or result. Do not turn difference into contradiction or parallel facts into causality with `however`, `whereas`, `still`, or `therefore`; state the facts directly or supply the missing premise.

14. **Verb strength matches evidence strength.** When a reviewer challenges a claim, first check whether the claim's verbs match the available evidence: strong (demonstrate/show/establish) requires direct proof; moderate (indicate/suggest/support) for empirical consistency; limited (are consistent with / may reflect) for indirect evidence. Downgrading overclaimed verbs in the manuscript is often the right first step before drafting the response.

### Venue-Appropriate Style

15. **Match the venue's conventions.** Applied mathematics journals (SIAM, Inverse Problems, JMIV, Numerische Mathematik) differ from ML conferences. Reproducibility in applied math means "all methods share identical degraded observations" and code availability, not enumerating PyTorch/NumPy/cuDNN seed settings in the paper. Use standard phrases from the literature: "we have found that ... usually results in" (Goldstein-Osher), "a good rule of thumb" (SALSA), "though not very much" for insensitivity.

16. **Survey literature writing patterns before drafting.** Before writing parameter guidelines, practical recommendations, or new technical explanations, search how top-venue papers in the same field phrase similar content. Extract exact quotes with citations. Adopt their phrasing patterns rather than inventing new ones. This applies especially to: parameter selection heuristics, reproducibility statements, initialization descriptions, and sensitivity analysis conclusions.

17. **Literature-grounded parameter guidance.** When reviewers ask for parameter selection heuristics, frame as: theoretical interpretation (e.g., MAP scaling) + empirical consistency with that interpretation + recommended search ranges + reference values. No fitting formulas without theoretical basis.

### Cross-Reviewer Awareness

18. **Detect and resolve conflicting reviewer requests.** When two reviewers ask for incompatible changes (e.g., one wants more detail, another wants shorter): surface the conflict in the revision plan, prioritize editor instructions if any, find a minimal revision satisfying both, and explain the balancing choice in both responses. Never make incompatible promises across responses.

---

## Workflow

### Phase 0: Classify and Decompose

1. Read the editor decision letter and all reviewer reports completely.
2. When this is revision round 2 or later, read the previous round's response letter (`Response_R<round-1>.tex`) and revision plan (`revision_plan_R<round-1>.md`) completely. For each comment that follows up an earlier one ("my comment 3 was not addressed", "the new Section 4.2 still does not..."), find the earlier concern's ID and open the current manuscript at the location the previous letter claimed for it; a claimed revision that is not there is part of the new concern. The new responses stay consistent with every statement the previous letter made: a value, a claimed change, a stated scope, a reason for deferring.
3. Identify the decision type: major revision / minor revision / R&R.
4. Decompose each reviewer's comments into atomic concerns. One reviewer comment containing multiple distinct points must be split into separate concerns. Assign stable IDs: `R1.1`, `R1.2`, `R2.1`, etc. For editor-level comments: `E.1`, `E.2`.
5. For each concern, record:
   - **ID**: `R{n}.{m}`
   - **Previous-round ID** (round 2 or later, follow-up comments only): the earlier concern's ID, written as `round 1 R1.3`
   - **Verbatim quote**: the key sentence(s)
   - **Category**: one of — language/format, information gap, scientific logic, beyond scope
   - **Severity**: major / minor / typographic (as the reviewer frames it)
   - **Response strategy**: Accept+Revise / Defend+Clarify / Defer+Acknowledge / Redirect
   - **One-line summary** in your own words
6. Check for cross-reviewer conflicts: if two reviewers' requests are incompatible, flag explicitly.

Present the decomposition to the user as a table before proceeding.

### Phase 1: Multi-Agent Analysis

Launch parallel independent analyses of the reviewer comments. All agents receive the reviewer reports, the original manuscript (PDF/tex path), and relevant code paths.

In a single message, spawn:
- **SubAgent** (background): deep analysis including code verification, literature search for writing patterns, mathematical cross-checks
- **Gemini** (async via `review_start`): independent assessment with focus on the reviewer's perspective
- **Codex** (`approval-policy: "never"`, `model_reasoning_effort: "xhigh"`): independent analysis with code-level verification

Persona for all external agents, passed as `developer-instructions` for Codex and as `system` for Gemini (for Gemini, append the read-only command constraints from your global instructions):
```
Act as a collaborative expert in applied & computational mathematics, optimization theory, machine learning, and image processing. Requirements:
- Form your own independent judgment first, then provide a balanced conclusion. Do not simply agree with presented viewpoints.
- Respond accurately, objectively, and concisely. Avoid exaggeration or unwarranted enthusiasm.
- If you disagree with a point, say so clearly and explain why.
- Maintain professional formality. Focus on substance over encouragement.
```

After Round 1 results arrive, conduct Round 2: send your synthesis (agreements, disagreements, your independent judgment) back to all agents via their reply interfaces. Iterate until convergence on all substantive points.

**Your judgment is final.** Codex tends toward excessive defensiveness — its suggestions for additional validation, extra experiments, and pre-emptive disclaimers would produce a cluttered technical report, not a focused paper. Gemini tends toward overenthusiasm and imprecision. SubAgent is usually the most balanced. Cross-check all claims against the actual manuscript and code before accepting.

### Phase 2: Revision Plan

Create the revision plan from the template, with `<round>` the revision round (1 for the first revision):

```bash
test -e <user-specified-path>/revision_plan_R<round>.md || cp <SKILL_DIR>/assets/revision_plan_template.md <user-specified-path>/revision_plan_R<round>.md
```

Read the copied file, then Edit it to fill in every section. The template defines the full structure: overall assessment, concern tracking matrix, per-concern analysis with the previous-round link (round 2 or later) and modification plan (tex line numbers), proposed manuscript and response text (dual drafting), consistency checklist, self-discovered issues, exclusion list, literature writing patterns, and edit execution order.

**Literature patterns**: for concerns requiring new text in the manuscript (parameter guidelines, reproducibility statements, initialization descriptions), delegate literature survey to SubAgent/Codex — they search for how published papers in the same venue phrase similar content, download PDFs to scratchpad for full-text extraction, and report exact quotes with citations. This informs the phrasing in both the manuscript revision and the response letter.

**Dual drafting**: proposed new text must be drafted separately for the response letter and for the manuscript. The manuscript draft reads as natural prose for a future reader who never saw the review; the response draft speaks directly to the reviewer with more technical specificity.

**Exclusion list**: explicitly record what you will NOT do and why (e.g., "will not add fitting formula — no theoretical basis", "will not expose γ=1.05 — theory-practice gap the reviewer didn't ask about"). This prevents scope creep and documents decisions.

Present the plan to the user. Iterate based on their feedback. Do not proceed to editing until the plan is confirmed.

Once the plan is confirmed, create the response letter:

```bash
test -e <user-specified-path>/Response_R<round>.tex || cp <SKILL_DIR>/assets/response_template.tex <user-specified-path>/Response_R<round>.tex
```

Read the copied file, then Edit it to fill in the manuscript title and adjust the reviewer block count to match the actual number of reviewers (see [Response Letter Setup](#response-letter-setup) for structure rules).

### Phase 3: Execute Revisions

Process concerns one at a time, in the Edit Execution Order of the confirmed revision plan. For each concern:

1. **Discuss** the modification strategy and response with the user — present the specific text changes and response draft before executing
2. **Edit the manuscript** using the Edit tool (not sed/scripts). Mark reviewer-inspired changes in blue. When adding substantial content to an existing section, restructure the section for coherence rather than appending at the end — the result must read as if the content was always there
3. **Write the response** for this concern in the `Response_R<round>.tex` file, filling its verbatim-comment and response slots. Reference specific locations (section, page, equation, algorithm line number). When quoting added manuscript text, use ``` ``...''\, ```. The response can include details that would clutter the manuscript (exact parameter values, seed settings, full derivations)
4. **Check consistency** across all related locations — grep every concept that was modified and verify uniform notation, parameter values, algorithm descriptions across all instances
5. **Compile** and visually inspect any modified algorithm blocks, figures, or layout-sensitive areas in the PDF
6. **Present** the completed modification for the user's review before moving to the next concern. Accept the user's micro-adjustments (wording, spacing, tone) and learn from them
7. **Classify** the concern: set its Classification in the Concern Tracking Matrix of the revision plan

After all concerns are processed:
- Fix self-discovered issues silently (no blue, no mention in response)
- Fix any notation inconsistencies found during the process (e.g., subscript vs superscript unification) — these are silent corrections
- Write the summary paragraph for the response letter **last**, after all point-by-point responses are finalized, so it accurately reflects what was actually done
- Compile and check for LaTeX errors/warnings introduced by the changes

### Phase 4: Verification

After all edits are complete, run these checks in order. Each check may trigger corrections; re-run affected checks after corrections.

1. **Post-flight verification of locations, numbers, and quotations** (most critical — the highest-risk hallucination in R&R is a response claiming a revision exists at a location where it doesn't):
   - Compile the manuscript to get the final PDF with stable page numbers
   - Extract three kinds of claim from the response letter: every location claim of the form "we have added/modified/revised X in Section Y / page Z / Line N / equation (M)"; every number the letter states about the revised manuscript (a table value, a parameter value, a count, a margin); and every span of manuscript text quoted with ``` ``...''\, ```
   - For each location claim, open the compiled PDF at the cited page and confirm the revision exists at the stated location. For each number, find the table cell, equation, or sentence it comes from in the compiled PDF and confirm the value; recompute every derived number (a difference, a percentage, a ratio) with a script. For each quotation, confirm it matches the final manuscript verbatim: wording the user adjusted in Phase 3 after the letter quoted it no longer matches
   - Spawn SubAgent and Codex in parallel to independently verify the same claims against the PDF (give them the extracted list of all three kinds and the original and revised PDF paths, not the response letter)
   - Fix any discrepancies: wrong page number → correct it; wrong section → correct it; a number or quotation that differs from the manuscript → correct the letter to the manuscript; missing revision → flag to user
   - Every hardcoded reference (page, section, equation, figure, algorithm line) must be verified because the response letter cannot use `\cref` — all numbers are manual

2. **Cross-reference consistency**: grep the entire manuscript for every concept that was modified. Verify uniform notation, consistent parameter values, aligned algorithm descriptions across all instances. Pay special attention to symbols that appear in both algorithms and running text.

3. **Mathematical verification**: for any new equations, derivations, or corrected formulas, invoke Codex (`model_reasoning_effort: "xhigh"`) and Gemini in parallel for independent mathematical verification. Only verify factual correctness — ignore their defensive suggestions for additional validation or disclaimers.

4. **Blue-marking audit**: verify that all reviewer-responsive changes are marked blue, and no self-discovered fixes are marked blue.

5. **Concern lifecycle check**: review the Concern Tracking Matrix in the revision plan. Every concern must have a classification in the Classification column (Addressed / Partially addressed / Deferred / Disagreement). Any concern without a classification is flagged as **UNADDRESSED** and reported to the user.

Report the verification results to the user. If the post-flight verification found any discrepancies, note whether they were corrected.

---

## Response Letter Setup

The response template is copied and initialized in Phase 2. The template contains `{{ placeholder }}` variables and commented-out blocks for additional reviewers.

### Structure rules

- **Multiple reviewers** (common case): each reviewer gets a `\textbf{\large Comments of Reviewer \#N:}` header. Comments are numbered independently starting from 1 within each reviewer section. The revision summary at the top references both reviewer number and comment number: `(Reviewer~\#R, Comment~N)`.
- **Single reviewer**: drop the `Comments of Reviewer \#N:` header and number comments flat (Comment 1, Comment 2, ...). The revision summary references just `(Comment~N)`.
- **Comment text**: reproduce each reviewer comment verbatim in black.
- **Response text**: in `{\color{blue} ... }`, referencing specific locations (section, page, equation, algorithm, figure, table). Quote added manuscript text with ``` ``...''\, ``` when it helps.

- **Response density scales with severity**: major/scientific-logic concerns get full prose responses (acknowledge → explain change → cite location → quote new text). Language/format and typographic concerns can be grouped into a compact table (Comment / Action / Location), with the verbatim comment in the Comment column, to avoid bloating the response letter with trivial items.

Adapt formatting (enumerate style, spacing, font) to match any reference response letters the user provides.

---

## Concern Classification and Lifecycle

Each concern carries two orthogonal labels throughout the revision:

**Classification** (what happened):

| Classification | Meaning | In the response |
|---|---|---|
| **Addressed** | Revision directly resolves it with a specific, locatable change | Point to exact location (section, page, line, equation, algorithm) |
| **Partially addressed** | Revision moves in the right direction but doesn't fully resolve | Explain what was done and what remains |
| **Deferred** | No change in the paper body, at most a sentence in the closing limitations and future-work passage; response explains why (scope, separate paper, conflicting reviewers) | Acknowledge value, explain boundary using study-design or scope reasons — never time, budget, or convenience |
| **Disagreement** | Author respectfully disagrees with premise | Reframe as presentation issue — a misunderstanding means the text was genuinely unclear (this is a substantive reason to revise, not a cosmetic change); explain reasoning |

**Response strategy** (how to handle):

| Strategy | When to use |
|---|---|
| **Accept+Revise** | Concern is valid; make the change |
| **Defend+Clarify** | The reviewer disputes a claim or result that stays unchanged; revise the presentation and argue the substance in the letter (usually ends Disagreement) |
| **Defer+Acknowledge** | Valid but out of scope; acknowledge value, add it once to the limitations and future-work passage at the end of the paper (a Limitations section or the limitations part of the Conclusion) |
| **Redirect** | The reviewer misread what the paper says and no claim is at stake; revise the section for genuine clarity (usually ends Addressed) |

---

## Handling Common Reviewer Request Types

### "Provide practical guidelines for parameter X"
Frame as: theoretical interpretation → empirical consistency → search range → reference values. Use standard phrasing from the literature (see [Core Principles #15-16](#venue-appropriate-style)). Never provide fitting formulas without theoretical basis.

### "Specify initialization / default values"
Check consistency with: (a) any privacy/data-locality claims in the paper, (b) existing narrative about why results look a certain way (e.g., "random initialization explains low starting PSNR"), (c) what the code actually does. Algorithm descriptions must be self-consistent even if they differ slightly from implementation details.

### "Clarify randomness / reproducibility"
For applied math venues: "all methods share identical degraded observations generated with a fixed random seed" + enumerate stochastic components briefly. Detailed seed values and framework-specific settings (cudnn.deterministic) go in the response letter, not the manuscript.

### "Add/supplement experiments"
If feasible: do it. If not feasible (time, equipment, scope): acknowledge the value of the suggested experiment, explain the research boundary, point to existing evidence that partially addresses the concern, and note it once in the limitations and future-work passage at the end of the paper. Never write "we cannot do this" — write "the current study focuses on X; the suggested experiment would be a valuable extension that we plan to pursue."

### Reviewer misunderstood the paper
Do not say the reviewer is wrong. Write: "We apologize for the lack of clarity in the original manuscript. We have revised Section X to more clearly explain..." Then actually revise the section so the explanation is genuinely clearer. A misunderstanding is a signal about the manuscript's presentation, not about the reviewer's competence. Describe the revision as what it is: a clarified presentation, not a corrected result.

### Two reviewers request incompatible changes
Surface the conflict explicitly in the revision plan. Prioritize editor instructions if any. Find a minimal revision satisfying both (e.g., add detail in a remark rather than the main text, satisfying "more detail" without violating "too long"). In each response, explain the balancing choice without blaming the other reviewer. Never make incompatible promises across responses.
