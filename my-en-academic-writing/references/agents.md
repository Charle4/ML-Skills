# External Agent Usage Guide

Read this file **only** when at least one of the following MCP tools appears in your tool list:
`mcp__codex__codex`, `mcp__gemini-review__review_start`.

If neither is present and you still want a clean-context second opinion, use the Subagent fallback described at the bottom.

---

## Workflow Selection

External agents review from a cold context — they have not seen your editing process, so they catch issues you normalised away. Choose the workflow based on task scope:

| Task scope | Workflow | Section |
|:-----------|:---------|:--------|
| Substantive writing: section drafting, deep rewrite of a full section, multi-paragraph de-AI, full-paper proofreading, related-work synthesis spanning many references | Coordinated multi-agent workflow | Below |
| Light editing: single-paragraph polish, grammar check, short conservative polish, quick output | Independent single-agent review (or no agent) | "When Single-Agent Review Suffices" |

When both Codex and Gemini MCP tools are available and the task is substantive, use the coordinated workflow. When only one is available, adapt: use it for review or polish, but you still own the draft and final review.

---

## Coordinated Multi-Agent Workflow

This workflow uses three roles — you (the main editor with full context), Codex (logic and structure reviewer), and Gemini (language polisher) — in a staged pipeline. Each role has a distinct strength; the pipeline compensates for each role's known weaknesses.

### Role Summary

| Role | Strength | Known weakness |
|:-----|:---------|:---------------|
| You (main editor) | Fullest context: user intent, plan, existing manuscript, LaTeX conventions, style-guide rules | May normalise your own writing and miss drift |
| Codex | Logic, argument consistency, cross-section coherence, claim-evidence mapping | Conservative and defensive language; raises phantom issues; likes "not X but Y" framing; ignores LaTeX/symbol conventions |
| Gemini | Fluent, human-sounding prose; good at smoothing stitched paragraphs; catches readability issues a linear reader would notice | Prone to florid or exaggerated language; may embellish claims; ignores LaTeX conventions |

### Stage 1 — Draft (you)

1. Read the plan, outline, or revision notes. Identify every piece of content that needs to be written or rewritten.
2. Write the complete draft yourself. Do not delegate drafting to Codex or Gemini — you have the fullest context; skipping the draft means you have not engaged with the details, which undermines your ability to review agent outputs later.
3. Write from the perspective of the finished paper as a linear reader would encounter it. Verify that every concept is introduced before it is referenced and that no argument is circular.
4. Save the draft to a temporary file (e.g., `<project>/draft-<section>.tex` or a scratch path). Include in the file or as a companion:
   - The original text path (so agents can compare)
   - The plan or revision notes path (so agents understand intent)
   - Any constraints the agents must respect (venue, LaTeX conventions, terminology)

### Stage 2 — Codex Logic Review

Assemble the Codex prompt from Blocks A + B + D, plus the review checklist below. Use `model_reasoning_effort: xhigh`. Omit `sandbox` so Codex can edit the draft file directly.

Tell Codex to read the draft file, the original text, and the plan, then review for:

- Concept introduction order: is every term/symbol defined or motivated before first use?
- Claim-evidence mapping: does every claim in the text have a corresponding evidence anchor (theorem, experiment, citation)?
- Cross-section consistency: do quantities, assumptions, and method names used in this section match the rest of the paper?
- Argument logic: are there circular arguments, unsupported leaps, or redundant re-statements?

**Handling Codex output.** Codex routinely produces three types of feedback:

1. **Real structural issues** — a concept genuinely used before introduction, a claim with no evidence anchor, an inconsistency with another section. Act on these.
2. **Phantom issues** — problems that do not actually exist in the text, often caused by Codex reading a snippet out of context. Verify each issue against the actual draft before accepting it. If the text is correct, ignore the issue.
3. **Defensive style suggestions** — adding hedges, disclaimers, "not X but rather Y" framings, weakening direct claims. Ignore these unless they address a genuine evidence-boundary problem.

Sort every Codex finding into one of these three categories. Apply only category 1.

If Codex edits the draft file directly, review the diff before accepting. Revert any defensive insertions or LaTeX convention violations.

### Stage 3 — Gemini Language Polish

After applying verified Codex fixes, call Gemini to polish the draft. Gemini starts from the post-Codex-review draft, not the original. Assemble the Gemini prompt from Blocks A + B + E.

Tell Gemini to:

- Read the draft file and smooth any stitched or awkward passages so the text flows naturally for a linear reader.
- Flag any point where, reading linearly, the text becomes unclear or confusing — this likely indicates a genuine clarity problem.
- Polish language for naturalness and readability without adding new claims or embellishing existing ones.

**Handling Gemini output.** Gemini tends to:

- Embellish claims beyond what the evidence supports — revert any amplified language.
- Add florid vocabulary or dramatic phrasing — replace with the plain academic register from the style guide.
- Ignore LaTeX conventions — check all `\cite`, `\ref`, `\eqref`, equation environments, and variable names after Gemini edits.

When Gemini flags a passage as unclear, independently assess whether the passage is actually unclear to a reader. If it is, rewrite it yourself with the full context you have. If it is not (Gemini may be confused by domain-specific content), keep the original.

### Stage 4 — Final Review (you)

You own the final manuscript. After Stages 2 and 3:

1. **Diff check.** Run `git diff` on the modified file. Read every change. Verify:
   - No information loss — rewriting often simplifies away local details. If a detail was present in the original and is substantively important, restore it. After several rewrite iterations, cumulative detail loss becomes severe; the diff is the only reliable safeguard.
   - No unintended additions — no new claims, no fabricated citations, no embellished numbers.
   - Only restructuring, rewording, or intentional deletions remain.
2. **LaTeX and convention check.** Verify that all LaTeX commands, equations, labels, references, and variable names survive intact. Verify formatting conventions match the style guide.
3. **Linear read.** Read the final text as a reviewer who knows only what the paper has said so far. Check concept introduction order, transition coherence, and argument completeness.
4. **Full-text consistency.** Verify terminology, notation, tense, and claim scope are consistent with the rest of the manuscript.

### File-System Exchange Pattern

Codex and Gemini operate through file-system reads and writes rather than prompt/response payloads, because prompt capacity is limited and the draft may be long.

Typical file layout:

```
<project>/
  draft-<section>.tex          ← your Stage 1 draft
  plan-<section>.md            ← plan/revision notes (optional companion)
  original-<section>.tex       ← snapshot of the original text for diff reference
```

When calling Codex: pass file paths in the prompt; Codex reads them directly.

When calling Gemini: pass file paths in the prompt; Gemini reads them directly.

After each agent finishes, read the file to see what changed, then apply Stage 4 review.

---

## When Single-Agent Review Suffices

For lighter tasks, a single independent review pass is enough. Use the appropriate agent:

| Mode | Agent value | Recommended agent |
|:-----|:-----------|:-----------------|
| Deep polish / rewrite (single paragraph) | Readability and fluency check | Codex (or Gemini if Codex absent) |
| De-AI rewrite (single paragraph) | Verify residual AI-like phrasing | Codex |
| Section drafting (short, single section) | Argument logic check from a fresh read | Codex or Gemini |
| Related-work synthesis (few references) | Coverage gaps and positioning errors | Codex or Gemini |

**Do not** call external agents for:
- Short conservative polish (single paragraph, grammar check) — not worth the overhead
- Requests where the user just wants a quick output
- Anything the user explicitly asks you to handle alone

---

## Codex MCP

### Persona Constraint (prepend to every call)

```
Act as a collaborative expert in applied & computational mathematics, optimization theory, machine learning, and image processing. Requirements:
- Form your own independent judgment first, then provide a balanced conclusion. Do not simply agree with presented viewpoints.
- Respond accurately, objectively, and concisely. Avoid exaggeration or unwarranted enthusiasm.
- If you disagree with a point, say so clearly and explain why.
- Maintain professional formality. Focus on substance over encouragement.
```

### Invocation Pattern

```
mcp__codex__codex:
  cwd: <project directory, or /tmp if none>
  config: {"model_reasoning_effort": "high"}
  prompt: |
    $my-en-academic-writing

    <Persona Constraint above>

    <Prompt Blocks — assemble from Block A + task-specific blocks>
```

Start the prompt with `$my-en-academic-writing ` (trailing space or newline) so Codex loads this skill — without whitespace separation from subsequent text, Codex will not recognise the trigger. Use `sandbox: read-only` for review-only tasks; omit `sandbox` when Codex should edit files directly (e.g., coordinated workflow Stage 2).

Use `"model_reasoning_effort": "xhigh"` for the coordinated workflow (Stage 2), complex multi-section drafts, or full-paper reviews. Use `"high"` for single-agent review tasks. Use `"medium"` for quick fluency checks.

### Follow-up

Continue the same thread with `mcp__codex__codex-reply` (pass the `threadId`). Never open a new session for a follow-up — this discards all prior context.

---

## Gemini MCP

### Persona Constraint (prepend to every call — Gemini specifically needs this)

```
Act as a collaborative expert in applied & computational mathematics, optimization theory, machine learning, and image processing. Requirements:
- Form your own independent judgment first, then provide a balanced conclusion. Do not simply agree with presented viewpoints.
- Respond accurately, objectively, and concisely. Avoid exaggeration, embellishment, or unwarranted enthusiasm.
- If you disagree with a point, say so clearly and explain why.
- Maintain professional formality. Focus on substance. Keep responses focused and avoid unnecessary elaboration.
```

### Invocation Pattern (async)

```
1. mcp__gemini-review__review_start → returns jobId
2. mcp__gemini-review__review_status (waitSeconds=30) → poll until done: true, status: "completed"
3. Read response field; threadId for follow-up
```

Follow-up uses `mcp__gemini-review__review_reply_start` with the `threadId`.

---

## Running Codex and Gemini in Parallel

In the coordinated multi-agent workflow, Codex and Gemini run **sequentially** (Codex reviews logic first, then Gemini polishes the post-review draft) — this is intentional because Gemini should polish text that has already been structurally corrected.

For single-agent review tasks where you want both agents' independent opinions (e.g., a quick readability check on a short passage), launch both in the same message — they maintain independent threads via their own `threadId` values. Synthesise their outputs yourself: keep points both agree on, verify disagreements against the source text, discard one-sided objections that conflict with the user's stated constraints.

---

## Prompt Blocks

Assemble the relevant blocks for each agent call — both coordinated workflow stages and single-agent review tasks. Always include Block A.

### Block A — Expert Persona
(Use the persona text for Codex or Gemini as written above.)

### Block B — Academic Writing Style

```
Write in standard academic English. Rules:
- Use clear, scientifically accessible language. Avoid fancy vocabulary.
- Forbidden words: burgeoning, pivotal, in the realm of, keen, adept, endeavor, uphold, imperative, profound, ponder, cultivate, hone, delve, embrace, pave, embark, encompass, monumental, scrutinize, vast, versatile, paramount, foster, necessitates.
- Always use full forms: "it is", "he would" — never contractions.
- No stylistic double quotes or dashes.
- No unverified data or figures. No exaggeration or figurative language.
- Use direct academic claims with concrete scope and evidence boundaries.
- Tense: past tense for what prior authors did and for completed experiment conclusions; present tense for algorithms, methods, and findings that hold generally.
- Non-proper-noun technical terms are not capitalised in running text.
```

### Block D — Minimal Invasive Editing

```
Editing constraints:
- Preserve all structure, argument flow, and meaning. Never remove key information.
- Make only the changes that are genuinely needed. Leave correct text unchanged.
- Do not over-simplify. Keep academic rigor; do not obscure claims.
- Ensure logical connectives between sentences. Do not optimise each sentence in isolation.
- Introduce no new claims.
- Never alter equations, labels, \cite, \eqref, \cref, variable names, or figure/table references.
- Do not introduce unnecessary bullet points.
```

### Block E — Polish / Refinement

```
Polish the following passage minimally:
- Simplify verbose or redundant phrasing without losing information.
- Remove repetitive explanations and unnecessary elaboration.
- Smooth awkward transitions; ensure sentence-to-sentence coherence.
- Do not change the overall argument or delete substantive content.
- Preserve all LaTeX commands exactly.
```

### Block F — Draft Writing from Outline or Notes

```
Draft the following section from the outline or notes provided:
- If the input is a structured outline, follow its structure exactly and do not add or remove major points.
- If the input is loose materials or notes without a fixed structure, organize the content into a coherent logical order and explain the reasoning.
- Write in academic English suitable for an applied mathematics or CS journal.
- Each paragraph should have a clear topic sentence and logical internal structure.
- Transitions between paragraphs must be explicit.
- Do not introduce claims not implied by the source materials.
```

### Block G — Literature Review / Related Work

```
Summarise and synthesise the following references for a related work section:
- Identify the key contribution of each work in one or two sentences.
- Group related works thematically, not chronologically.
- Clearly state where each prior approach falls short relative to the user's setting.
- Do not editorialize. State limitations factually with citations.
- Use past tense for what prior authors did; present tense for what their results show.
```

### Typical Block Combinations

| Task | Blocks |
|:-----|:-------|
| Coordinated Stage 2 (Codex logic review) | A + B + D + review checklist from Stage 2 |
| Coordinated Stage 3 (Gemini language polish) | A + B + E |
| Single-agent deep polish | A + B + D + E |
| Section drafting | A + B + F |
| Related-work synthesis | A + B + G |
| Final proofreading | A + B + D |
| Discussion / idea review | A only |

---

## Agent Invocation Rules

1. **Always provide sufficient context.** State what the task is, what constraints apply (venue, mode, LaTeX preservation), and what specific output is needed. Agents start cold.

2. **Provide file paths.** Both Codex and Gemini can read local files by absolute path. Pass file paths in the prompt rather than pasting long excerpts. For short passages (single paragraph), pasting inline is acceptable.

3. **Use reply interfaces for follow-up.** `mcp__codex__codex-reply` (pass `threadId`) or `mcp__gemini-review__review_reply_start` (pass `threadId`). Never start a new session for a follow-up.

4. **You own the final review.** Never copy agent output verbatim into the manuscript or into file edits without independent verification. Check every proposed change against the source text and the style-guide rules. Catching errors is your responsibility, not the external agent's.

5. **Correct wrong answers via reply, not silence.** When an agent response contains factual errors, wrong variable names, or LaTeX that violates the style-guide, use the reply interface: quote the specific wrong passage, state what is incorrect and why, supply the correct content, and ask for a revised answer.

6. **Verify before applying.** An agent saying "this is correct" is not evidence that it is correct. Check proposed changes against the style-guide and the source text before applying.

---

## Subagent Fallback (No MCP Available)

When no Codex or Gemini MCP tool is visible but a clean-context second opinion is genuinely useful (e.g., a full section draft that needs an independent readability check), spawn a same-model subagent:

```
Agent(
  subagent_type="general-purpose",
  prompt="""
    <Persona Constraint — Block A>

    You are reviewing a passage of academic English for a [venue] paper.
    Read the following text carefully and provide:
    1. A list of any phrases that sound unnatural, AI-like, or imprecise.
    2. Any defensive framing that can be replaced by a direct, scoped claim.
    3. Any logical gaps or unclear transitions between sentences.
    4. Specific suggestions for improvement (quote the original phrase, propose the replacement).

    Editing constraints (Block D):
    - Preserve all LaTeX commands exactly.
    - Do not introduce new claims.
    - Make only changes that clearly improve the text.

    Text to review:
    [paste the passage]
  """
)
```

**When to use subagents vs. inline editing:**
- Subagents are useful when the passage is long (>2 paragraphs) and you want a genuinely fresh read without your own editing context contaminating the review.
- For short passages or simple grammar checks, just edit inline — spawning a subagent adds overhead without benefit.

**Synthesise subagent output the same way as MCP output:** verify every suggestion against the source text and style-guide before applying.
