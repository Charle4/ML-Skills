# External Agent Usage Guide

Read this file **only** when at least one of the following MCP tools appears in your tool list:
`mcp__codex__codex`, `mcp__gemini-review__review_start`.

If neither is present and you still want a clean-context second opinion, use the Subagent fallback described at the bottom.

---

## When External Agents Add Value

External agents provide independent review from a cold context — they have not seen your editing process, so they catch things you normalised. Use them in the following situations:

| Mode | Agent value | Recommended agent |
|:-----|:-----------|:-----------------|
| Deep polish / rewrite | Independent readability and fluency check after you finish | Codex (or Gemini if Codex absent) |
| De-AI rewrite | Verify residual AI-like phrasing you may have missed | Codex |
| Section drafting | Check argument logic and academic register from a fresh read | Codex or Gemini |
| Related-work synthesis | Spot coverage gaps and positioning errors | Codex or Gemini |
| Full-paper proofreading | Final surface and logic check before user sends to journal | Codex + Gemini in parallel |

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
  sandbox: read-only
  cwd: <project directory, or /tmp if none>
  config: {"model_reasoning_effort": "high"}
  prompt: |
    <Persona Constraint above>

    <Task block — see Prompt Blocks below>
```

Use `"model_reasoning_effort": "xhigh"` only for complex multi-section drafts or full-paper reviews. Use `"medium"` for quick fluency checks.

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

When both are available and the task is substantial (e.g., deep-polish an entire section, or proofread a near-submission paper), launch both in the same message — they maintain independent threads via their own `threadId` values. Synthesise their outputs yourself: keep points both agree on, verify disagreements against the source text, discard one-sided objections that conflict with the user's stated constraints.

---

## Prompt Blocks

Assemble the relevant blocks for each agent call. Always include Block A.

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

### Block F — Draft Writing from Outline

```
Draft the following section from the outline provided:
- Follow the outline structure exactly; do not add or remove major points.
- Write in academic English suitable for an applied mathematics or CS journal.
- Each paragraph should have a clear topic sentence and logical internal structure.
- Transitions between paragraphs must be explicit.
- Do not introduce claims not implied by the outline.
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
| Deep polish | A + B + D + E |
| Section drafting | A + B + F |
| Related-work synthesis | A + B + G |
| Final proofreading | A + B + D |
| Discussion / idea review | A only |

---

## Agent Invocation Rules

1. **Always provide sufficient context.** State what the task is, what constraints apply (venue, mode, LaTeX preservation), and what specific output is needed. Agents start cold.

2. **Provide file paths and line numbers.** For Codex MCP (sandbox may block local I/O): paste the minimum necessary excerpt directly into the prompt. For Gemini: tell it to read the file path directly.

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
    2. Any logical gaps or unclear transitions between sentences.
    3. Specific suggestions for improvement (quote the original phrase, propose the replacement).

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
