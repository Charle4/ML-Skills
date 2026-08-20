---
name: mpaper-cover-letter
description: >-
  Write a journal cover letter for a finalized manuscript ready for submission.
  Use whenever: writing cover letter, drafting cover letter, coverletter,
  投稿信, 投稿 cover letter, 投 [journal name], preparing submission,
  submitting paper to journal, or the user has a finished manuscript and
  mentions submitting it. Scope: ML, applied/computational math, image
  processing, optimization, inverse problems — journals like Pattern
  Recognition, IEEE TPAMI/TIP/TSP, SIAM journals, Elsevier applied math,
  Springer Numerische Mathematik, JCAM, etc. This skill produces a
  compilable LaTeX .tex file. For revision response letters, use
  mpaper-revision-response instead; for LaTeX typesetting polish, use
  mpaper-latex-typeset-polish.
---

Base directory for this skill: <injected at load time>

You write a concise, confident journal cover letter in LaTeX for a finalized manuscript in ML, applied/computational mathematics, or related fields.

## Core Principles

**One page, four to five paragraphs, zero bibliography.** The editor spends 60 seconds on this letter. Every sentence must earn its place.

**Sell, don't defend.** The letter exists to make the editor want to send the paper out for review. Listing things you did *not* do, datasets you did *not* use, or metrics you chose *not* to report is self-sabotage — it plants doubts the editor never had. If the journal explicitly requires justification for methodological choices (e.g., PR's three-question format), weave the answers into a confident narrative paragraph, never as numbered sub-questions or defensive bullet lists.

**Strategic ambiguity over premature honesty.** When some baselines received full experimental comparison and others were only discussed, use language that is accurate but does not volunteer the distinction unprompted. "Comprehensively evaluated" for the strong comparisons; "discussed as recent advances in complementary settings" for the rest. Every word is technically true; the emphasis falls on strength.

**No self-diminishing signals.** Do not:
- List unused datasets, metrics, or methods
- Write "we omit X because..." or "we do not report Y because..."
- Mention reference count ("this manuscript cites N articles from your journal")
- Include format-compliance sentences ("prepared in the required format within the page limit") — the editor can see the PDF
- Add an explicit bibliography/references section — use inline citations (Author et al., Venue Year) only

## Workflow

### Step 1: Read the manuscript

Read the full paper: title, abstract, introduction (especially contributions), experiments (main tables/figures), and conclusion. Identify:
- The problem and why it matters (application domains where this problem is unavoidable)
- The key technical contribution (one sentence: "we do X via Y, which achieves Z")
- The strongest experimental claim (which baselines, which metrics, what margin)
- The novel angle that distinguishes this from prior work

Also read `refs.bib` or the bibliography to understand which journals/venues the paper already cites — this informs the scope-fit argument.

### Step 2: Research the target journal

Search the target journal's Guide for Authors for:
- Any specific cover letter requirements (e.g., PR's three mandatory questions about SOTA, datasets, metrics)
- Article type terminology (Full Length Article, Regular Paper, Research Article, Letter)
- Scope statement — what the journal says it publishes
- Any declaration requirements (ethics, data availability, conflict of interest)

If the journal has specific required questions, they must be answered — but folded into the letter's natural flow, not as a separate Q&A section.

### Step 3: Draft the letter

Copy the template into the target location, then edit it in place:

```bash
cp <SKILL_DIR>/assets/cover_letter_template.tex <target_path>
```

where `<SKILL_DIR>` is the absolute path from the "Base directory for this skill:" line at the top of this file, and `<target_path>` is the user-specified output path (default: `cover_letter.tex` in the paper directory). Then read the copied file and replace each `[PLACEHOLDER]` according to the guidelines below. If the journal does not require Paragraph 4, delete the `[SOTA PARAGRAPH]` line and its comment.

**Paragraph 1 — Submission statement** (1–2 sentences):
- Title in LaTeX double backticks, journal name in `\textit{}`.
- Article type matching the journal's terminology.
- No filler ("We are pleased to...", "On behalf of all authors...") — get to the point.

**Paragraph 2 — Importance + contribution** (4–6 sentences):
- Open with why the problem matters: name 2–3 application domains where paired data is unavailable / the phenomenon is critical / current methods fail.
- Bridge to the unexploited resource or insight your paper leverages (e.g., "Visual foundation models encode rich semantic structure that remains stable under degradation, offering a previously unexploited source of constraints").
- State the technical contribution: framework/method name, what it derives/produces, key properties.
- Close with the strongest experimental summary: "consistently outperforms all evaluated baselines across all N metrics" or equivalent.

**Paragraph 3 — Scope fit** (2–4 sentences):
- Why THIS journal specifically, not just any journal in the field.
- Connect to the journal's published research lines — cite 1–2 recent articles from the journal that your work extends, complements, or shares methodology with. Use inline citations (Author et al., *Journal Abbrev.*, Year).
- Frame contributions in the journal's own language (e.g., PR's "theory, methodology, and application of pattern recognition").

**Paragraph 4 — SOTA / journal-specific requirements** (only if required):
- If the journal mandates specific information (SOTA comparison, datasets, metrics), provide it in a single flowing paragraph.
- Lead with strength: "We benchmark against N methods spanning [traditional] and [modern] approaches."
- For SOTA article lists: pick 5 articles that represent the **current** state of the art — prioritize the last 2–3 years and the same methodological paradigm as the paper. Do not pad the list with older traditional methods (e.g., a 2014 optimization-based approach is not "state of the art" when 2024–2026 deep-learning methods exist). Distinguish comprehensively-evaluated from discussed-only using strategic ambiguity (see Core Principles).
- For datasets: name only the primary evaluation benchmark, not auxiliary validation sets (e.g., if BSDS300 is only used for assumption verification, it is not a "benchmark" — omit it).
- For metrics: name only what you report, not what you chose not to use.

**Paragraph 5 — Declarations** (2–3 sentences):
- Originality and non-duplication.
- Author approval.
- Add only what's true and relevant: non-conference-extension, data availability, no conflicts. Each as a short clause, not a separate sentence.

**Signature block:**
- "Sincerely," followed by corresponding author only.
- Name, department, university, city + country, email.

### Step 4: Self-check before delivery

Before presenting the draft:
1. **Length**: will it compile to ≤1 page? If borderline, cut scope-fit or tighten the contribution paragraph.
2. **Defensive language audit**: grep for "we do not", "we omit", "we chose not to", "we exclude", "although", "limitation". Delete or reframe every instance.
3. **Specificity check**: every claim must trace to a specific section/table/figure in the manuscript. No vague "significant improvements" without naming the metric or margin. Do not use "for the first time" unless the manuscript itself makes that exact claim.
4. **Consistency check**: data availability statement, author list, title must match the manuscript exactly. If the manuscript says "Data will be made available on request", the cover letter must not say "publicly available".
5. **Citation check**: every article cited in the cover letter must exist in the manuscript's bibliography. Do not introduce citations that are not in the paper.
6. **Salutation**: default to "Dear Editor" or "Dear Editor-in-Chief". Only use a specific name if the user provides it or explicitly asks you to look it up — getting the name wrong is worse than being generic.

### Step 5: Compile and verify

Run `pdflatex` on the edited file to confirm it compiles cleanly and fits on one page. If any information is genuinely missing (corresponding author email, article type), leave `[PLACEHOLDER]` markers and list them for the user.
