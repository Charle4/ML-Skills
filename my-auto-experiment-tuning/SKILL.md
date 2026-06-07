---
name: my-auto-experiment-tuning
description: Autonomous, hypothesis-driven experiment and hyperparameter tuning for ML/research codebases. Use when the agent (Codex or Claude Code) needs to run many experiments, tune hyperparameters, manage GPU slots, analyze results, maintain benchmark tables or experiment ledgers, resume an interrupted tuning loop, or coordinate subagents for strategy/result analysis. Supports project-specific adapters while keeping the main workflow generic.
---

# Auto Experiment Tuning

## Operating Model

Run an autonomous loop as the experiment orchestrator. Understand the project once, create one durable session, maintain `plan.md`, manage run lifecycle commands, check GPU slots, launch work, and coordinate subagents. Do not do inline hyperparameter analysis or candidate strategy when subagent support is available.

Analysis and planning are delegated:
- Strategist returns per-HP observations for recent completed runs and Ready Queue candidates.

Launch assigned runs directly. Perform inline result recording (metric parsing, trust judgment, `aet.py record`, file writes) after each run completes.

Keep the rolling loop moving **without pausing between planning groups**.

### ⛔ Forbidden Anti-Patterns (CRITICAL — read before anything else)

These are the mistakes that break the autonomous loop. **Never do any of these:**

| # | Anti-Pattern | Why It's Wrong | Correct Behavior |
|---|-------------|---------------|-----------------|
| 1 | **Stopping after a batch completes** — collecting results, writing a summary report, and going idle | A batch completing is NOT a stop condition. The loop continues as long as slots exist and unexplored parameter regions remain. | After collecting results: immediately re-check GPU slots, plan next candidates, launch as many ready candidates as current resources allow, THEN give a brief progress note (not a final report). |
| 2 | **Canceling the `/loop` after a sub-phase** — deleting the cron job because "this sub-goal is done" | The loop is the keepalive mechanism for the ENTIRE tuning objective, not one sub-phase. Canceling it kills the autonomous session. | Set the loop once at session start. Only cancel it when the user explicitly ends the session, or a valid stop condition has been recorded and the session is being closed. |
| 3 | **Creating new AET sessions for sub-phases** — running `aet.py init` again when exploring a new parameter direction | One tuning objective = one session. Fragmenting sessions destroys the ledger continuity. | Use the same session for the entire tuning objective. Sub-phases are documented in the same `plan.md` and `observations.md`. |
| 4 | **Using shell `for` loops to create dirs or launch experiments** — `for d in ...; do ...; done` | Hook interception → manual approval → loop broken. | Use `mkdir -p dir1 dir2 dir3 dir4` to create multiple directories in one command. Claude Code: launch with independent `Bash(run_in_background=True)` calls. Codex: launch with one `exec_command` session per experiment; no shell `&`. |
| 5 | **Presenting a "final report" before checking if more work exists** — summarizing results as if the task is done | Unless a stop condition is met (target achieved, budget exhausted, or plateau confirmed by two independent Strategist instances), the tuning continues. | After results: check slots → launch more → then (and only then) give a brief status update. Do not frame updates as conclusions. |
| 6 | **Keeping only a same-size "next batch" table** — planning exactly as many candidates as current free slots | This creates idle gaps and forces batch-synchronous thinking. | Maintain `Completed / Recorded`, `Running`, and `Ready Queue` sections in `plan.md`; keep ready candidates at or above total_capacity (capacity_per_gpu × gpu_count) whenever unexplored regions remain. |
| 7 | **Self-declaring exhaustion, convergence, or plateau** — concluding from your own reading of results that the search space is exhausted, a ceiling has been reached, or that further tuning is futile, then stopping or skipping Strategist on that basis | You lack the full search-history perspective; such judgments are highly error-prone. Only the Strategist has authority to declare exhaustion. | Never self-evaluate plateau, convergence, or exhaustion. When Ready Queue is insufficient, run the Strategist transaction. Only when Strategist returns 0 candidates and explicitly declares exhaustion should you consider stopping — and even then a second independent confirmer must agree. The script owns this: `aet.py strategist-return` sets the handshake, and the next `aet.py strategist-begin` forces a fresh independent confirmer (never a resume). See Default Stopping Rules. **Signal**: if you find yourself about to write "this direction is exhausted", "a ceiling has been reached", or "lcdf is a dead end" — that sentence is the trigger to run the transaction, not to stop. |
| 8 | **Skipping Strategist because it was "recently called" or "has no new data"** — reasoning that calling Strategist is pointless because it just ran, or because the pending set is empty, so there is nothing new for it to analyze | Recency and an empty pending set are not suppression conditions. Strategist always plans from the full session state and can add valuable candidates even immediately after a prior call. The only valid suppression conditions are: explicit user stop, target cleanly met, budget consumed, permission unavailable, or a Strategist call already open (`strategist-begin` refuses a second). | When Ready Queue count < total_capacity, run the Strategist transaction — period. **Signal**: if you find yourself thinking "Strategist was just called so I'll skip it" or "there's nothing new for Strategist to analyze" — that reasoning is invalid. Run it. |
| 9 | **Skipping Strategist on keepalive invocations that found no new completions** — running `aet.py status`, seeing no change since last check, and concluding "nothing to do this invocation, continue waiting" without running `aet.py loop-state` | The loop-state check is unconditional and independent of whether new completions occurred. `aet.py status` showing no change means step (1) has no action; it does NOT mean the loop-state routing can be skipped. | After `aet.py status` shows no new completions: still run `aet.py loop-state`. If it routes a Strategist call, run the transaction immediately — even with 0 new completions, even with all GPU slots occupied. **Signal**: if you find yourself writing "no new completions, continue waiting" — that sentence is the trigger to run `loop-state`, not to stop. |
| 10 | **Reading an OPEN `active_strategist_call` as proof the subagent is still running** — then either busy-waiting on it or `strategist-abort`-ing it as "stale/unreachable" | `loop_state.json` is the state machine YOU update; a call stays OPEN only because you have not yet run `strategist-return`. The script cannot see the subagent at all. Treating its un-updated state as "subagent still running" is circular — and aborting on that basis discards a subagent that already returned, throwing away its candidates AND clearing the resume chain (next begin fresh-spawns). | Judge the subagent's real state from the subagent itself: its completion notification, the agent panel, or its task-output file. If it returned, run `strategist-return` with its result. If you lost the output, resume the SAME agent (`SendMessage` / `send_input`) to re-request it. Use `strategist-abort --reason unreachable` only after that resume itself returns `success:false`. **Signal**: if you are about to call `strategist-abort` because loop-state "still shows it open" — stop; first verify the subagent against reality and `strategist-return` it. |

### Continuous Rolling Execution (NOT batch-synchronous)

The default operating mode is **asynchronous rolling**: GPU slots are filled continuously, not in synchronized waves. A "batch" is a planning concept, not an execution gate.

> The 10-step protocol below governs the **steady-state cycle** (each completion notification → record → refill). For **session startup queue fill** (before the first launch), see Quick Start step 5.

**The iron rule**: when you receive a completion notification for ANY experiment:
1. Identify the run from `plan.md` `Running` and verify the output/log paths exist
2. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort
3. Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, mismatched output directories, GPU contention, and partial crashes as `failed` or `inconclusive`
4. Call `aet.py record --status <status> --run-id <id> [--primary-metric <v> --metric-name <n> --metrics '<json>'] [--notes '<note>']`
5. If trust note is relevant: append to `runs/<id>/summary.md` (after record, since record rewrites that file)
6. Move run from `Running` to `Completed / Recorded` in `plan.md`. `aet.py record` already added the terminal run to the pending set in `loop_state.json`.
7. Run `aet.py loop-state` (it counts the Ready Queue from `plan.md` itself) and follow its `YOU` block — the routing hub right after `record`; steps 5–6 are order-independent with it, so you may run it first and finish that bookkeeping after. It computes free slots and total_capacity (from the stored GPU policy) and routes the next actions.
8. Launch as many existing `Ready Queue` candidates as current free slots allow NOW (create-run → launch → record running → move row to Running).
9. When loop-state routes a Strategist call (Ready Queue count < total_capacity, total_capacity = capacity_per_gpu × gpu_count from the stored policy), run the **Strategist transaction** — three beats, every time (full detail in `references/subagents.md`):
   - **begin**: `aet.py strategist-begin` snapshots pending, computes the branch (fresh / resume / fresh confirmer), opens the call, and prints the exact spawn/resume tool call + the payload. It refuses if a call is already open.
   - **tool_use**: make the printed call (Claude Code `Agent`/`SendMessage`; Codex `spawn_agent`/`send_input`). This is your own tool_use, bracketed by begin and return. Between the two you may keep recording other completions; `record` adds them to pending without disturbing the open call.
   - **return**: `aet.py strategist-return --call-id C --candidates-count K [--agent-id A] [--observations-present] [--queue-edits-present] [--stop-update-present]` clears the snapshot, records the agent id, derives exhaustion from `K == 0`, applies the handshake, and prints the `YOU` doc-update obligations. Follow them, then launch ready rows into free slots.
   The script owns fresh-vs-resume-vs-confirmer, the exhaustion handshake, and quiescence — do not hand-derive any of it. Suppression conditions: explicit user stop, target cleanly met, budget consumed, permission unavailable, or a call already open. Plateau, exhaustion, recency, and an empty pending set cannot suppress.
10. Only after steps 1-9: give a brief progress update

**Never wait for all experiments in a batch to finish before acting.** Process each completion as it arrives. Keep all GPU slots occupied at all times.

Do NOT present a summary and go idle after a batch. A batch is not a stop boundary. The only valid stop boundaries are the stop conditions listed below.

### Rolling Queue State Machine

Use `SESSION/plan.md` as a live execution board with three sections:

- `Completed / Recorded`: terminal runs with metrics, trust status, and the follow-up learned from them.
- `Running`: active runs with run id, GPU, output directory, log path, command/session id if available, and expected signal.
- `Ready Queue`: launchable candidates without assigned run ids yet. Keep this count at or above total_capacity whenever useful unexplored regions remain. total_capacity = configured capacity_per_gpu × number_of_gpus (constant; read from `aet.py gpu-slots`). Run the Strategist transaction whenever count drops below total_capacity, ensuring the queue is always pre-stocked for upcoming slots.

State transitions:
- Strategist planning adds candidates to `Ready Queue`. Add as many as the evidence justifies, including multi-point grids or factorial groups when useful; do not force a one-finished-run to one-new-run cadence.
- Launching takes one or more `Ready Queue` rows according to current available slots, assigns run id/GPU/output/log fields, registers each with `aet.py create-run`, launches the command, records each accepted process with `aet.py record --status running`, and moves them to `Running`.
- Completion triggers inline recording: verify output files → parse metrics (JSON/CSV/NPZ → TensorBoard → log regex) → determine status → call `aet.py record` (which adds the terminal run to the pending set) → run `aet.py loop-state` (the routing hub; bookkeeping like trust notes, plan.md row moves is order-independent with it) → fill all currently usable slots from `Ready Queue`.
- New evidence may invalidate unlaunched ready rows; rewrite or remove those rows after Strategist returns and note the reason in the session ledger.

### Delegation Protocol

Read `references/subagents.md` before spawning or locally emulating a role. Use paths and durable context in prompts; avoid summarizing results for the subagent when it can read the files directly.

| Trigger | Role | Main-agent follow-up |
| ------- | ---- | -------------------- |
| `Ready Queue` count < total_capacity (capacity_per_gpu × gpu_count, from the stored GPU policy) | Strategist | Run the three-beat transaction: `aet.py strategist-begin` (computes blocking/background and fresh/resume/confirmer, prints payload) → your spawn/resume tool_use → `aet.py strategist-return` (clears the snapshot, records the agent id, applies the handshake). Then follow strategist-return's `YOU`: append `observations_to_append` → observations.md, append candidates → plan.md Ready Queue, update Stop/Continue Rule, launch ready rows. |

Self-evaluatable conditions that may suppress a Strategist call: explicit user stop, explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable. Plateau and exhaustion are never self-evaluatable — Strategist must declare them. **Recency of the last Strategist call and an empty pending set are not suppression conditions.**

When calling subagents, pass `algorithm_context` as 2-5 sentences covering: metric meaning and direction, tuning target, known comparability risks (GPU contention, channel mode differences, etc.), and key parameter couplings. See `references/subagents.md` prompt templates for the full format.

Single-writer rules:
- `plan.md`: you only (semantic board + Ready Queue).
- `observations.md`: append `observations_to_append` returned by Strategist; `aet.py record --notes` may append terminal run notes.
- `results.csv`: only through `aet.py record` (call it directly after inline parsing).
- `runs/<id>/summary.md`: rewritten by `aet.py record`; append trust-check details after record.
- `loop_state.json`: script-owned. Read it with `aet.py loop-state`; change it only through `aet.py record` (pending set) and `aet.py strategist-begin/return/abort` (Strategist state machine).

### One Session Per Objective

Create exactly ONE AET session (`aet.py init`) per user tuning objective. Do NOT create new sessions for sub-phases, new parameter directions, or follow-up explorations. All sub-phases go into the same session's `plan.md` and `observations.md`. If you accidentally created multiple sessions, consolidate into the first one and stop creating new ones.

### Loop Lifecycle (Claude Code)

- **When to create**: immediately after `aet.py init`, before launching the first experiment. Use the `/loop` skill (not CronCreate directly) with interval ≥ 1 hour unless individual runs are very short.
- **When to adjust**: change the interval if runs are short (≤ 20 min → 30m interval) or very long (≥ 2h → 2h interval).
- **When to cancel**: ONLY when (a) the user explicitly says "stop" or "end the tuning", OR (b) a valid stop condition has been recorded and the session is being closed. **Never cancel the loop just because a sub-phase produced good results, reached a local peak, or met one image's target.**
- **The loop is the heartbeat of autonomous tuning.** Canceling it without a valid stop condition kills the session. If in doubt, keep it running.

### Default Autonomy Contract

- Treat the user's initial request as the authorization to pursue the stated tuning objective end to end within the active sandbox and approval policy.
- Do not ask the user to approve each candidate group, each hyperparameter choice, each GPU assignment, or each result update.
- Make local decisions from the written objective, benchmark constraints, project memory, and observed results.
- Ask the user only when the objective is ambiguous, the next action is destructive, required permissions are unavailable, or the run would exceed the user's stated budget/principles.
- Continue filling available slots, collecting results, and planning follow-up candidate groups until a stop condition is reached.
- Do not stop merely because a result improved the current best, looks "good enough", or a local neighborhood has been checked. If the user has not set an explicit budget, keep running until the user intervenes, the explicit target is met, or the plateau/exhaustion rules below are satisfied.
- If the user gives a numeric target such as `PSNR > 25`, treat it as a hard stop condition: continue autonomous rolling execution until a clean run meets or exceeds it, or until the user changes the target or budget.
- If the user says resources are available or asks to "fully tune", actively keep GPUs occupied within the configured contention limits. Prefer launching ready candidates into all currently free slots as soon as resources are available — do not wait for all running experiments to finish.

### Core Rules

- Optimize by hypotheses, not blind grids. State what each candidate group is testing.
- Analyze hyperparameters as a coupled system. Early candidate groups should deliberately cover interactions among important knobs before local refinement.
- Do not get trapped in single-parameter coordinate tuning. If progress stalls or conclusions conflict, broaden the design space and test interaction hypotheses.
- Default division of labor: you manage the experiment lifecycle (orchestration, launching, inline recording) and the Strategist owns analysis and candidate planning. Delegate observations synthesis and next-candidate strategy to Strategist whenever subagents are available; apply returned decisions and keep managing the lifecycle. Perform analysis and planning inline only as a fallback when subagent delegation is unavailable.
- Keep a durable ledger before relying on context memory.
- Never overwrite an existing output directory, log file, or shared result JSON.
- Treat failed and bad runs as data. Record the failure pattern and avoid repeating it.
- If a standard baseline is far below expected behavior, pause pure hyperparameter sweeps and audit implementation fidelity, preprocessing, objective terms, schedules, seeds, and metric definitions.
- Prefer project CLI arguments over editing experiment scripts. If edits are required, read first and keep them scoped.
- Always ask before destructive or scope-expanding actions, even under auto/bypass approval where no prompt fires: deleting experiment directories or logs, killing processes not started in the current run, installing packages or accessing the network, writing outside the project / `/tmp` / configured writable roots, or destructive git operations. Auto-approval removes the human gate, so enforcing this boundary is yours.

### Shell Command Safety (Claude Code — CRITICAL)

Claude Code hooks intercept complex shell structures, requiring manual approval and breaking the autonomous loop. Follow these rules strictly:

**Forbidden — never use these patterns:**
- `for d in ...; do ...; done` — shell for loop (any variant)
- `cd /path && python ... > log.txt` — cd combined with redirection or other commands
- `cmd1; echo "---"; cmd2` — multi-command sequences with separators
- `python -c "..."` with `#` comments inside the quoted Python string

**Safe replacements:**
- Multiple directories: `mkdir -p /abs/path/dir1 /abs/path/dir2 /abs/path/dir3` (space-separated, one command)
- Launch experiments with the exact command shape below — never a loop:
  ```
  python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1
  ```
  Use plain `python` by default so the command inherits the agent's startup environment; use an explicit interpreter path only when the active environment is wrong. Pass `--gpu_id` explicitly.
  - **Codex**: run that same command as one `exec_command` session per experiment. Do not add shell `&`; if the tool yields a `session_id`, record the `session_id -> run_id/output_dir/log_path` mapping and poll it with `write_stdin`.
  - **Claude Code**: use one independent `Bash(run_in_background=True)` tool call per experiment.
- Read logs: `grep -r "pattern" /abs/path/results/` or the Read tool for known paths — never a `for f in ...` loop
- Always use absolute paths — no `cd` needed

Full details in `references/claude-code-adapter.md` (Safe Bash Patterns section).

### Default Stopping Rules

- Stop only for one of these reasons: explicit user stop, explicit metric target met with clean evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable, destructive action required, or a plateau/exhaustion decision confirmed by two independent Strategist instances per the rules below.
- The plateau/exhaustion stop condition cannot be self-evaluated. You have no authority to conclude the search space is exhausted, a ceiling has been reached, or that further tuning is futile. Only the Strategist may declare plateau or exhaustion, after evaluating the minimum evidence requirements.
- Strategist calling follows one rule throughout: Ready Queue count < total_capacity → run the Strategist transaction. total_capacity is constant (capacity_per_gpu × gpu_count). `aet.py strategist-begin` chooses blocking vs background and fresh vs resume vs confirmer. When a Strategist returns zero candidates the queue stays empty (0 < total_capacity), so every subsequent trigger keeps running the transaction with the standard neutral prompt and complete session state.
- All Strategist prompts must use the standard neutral template from subagents.md. Never add context about previous Strategist conclusions, never ask "is the search exhausted?", never prime the conclusion in any direction.
- Stop condition for plateau/exhaustion: two exhaustion signals from **independent contexts**, both produced while fully quiescent (no experiments running, Ready Queue empty). A Strategist signals exhaustion by **returning zero candidates**. The independence is structural and enforced by the script: when the Primary returns 0 candidates while quiescent, `aet.py strategist-return` sets the handshake so the next `aet.py strategist-begin` is forced to a **fresh confirmer** — a new independent context, never a resume of the Primary, because re-messaging the context that produced the signal gives no independence. If the confirmer returns candidates, the Primary is overturned, the confirmer is promoted to Primary, and the loop continues; only when the fresh confirmer also returns 0 candidates does `strategist-return` print `CONFIRMED_EXHAUSTION`. Any Strategist that returns candidates anywhere resets the handshake to zero. Quiescence (no `created`/`running` runs and an empty Ready Queue) is computed by the script, not self-judged. Full mechanics: `references/subagents.md` and `references/claude-code-adapter.md` step 9.
- When no explicit target or budget is supplied, assume the user wants continued tuning rather than a final answer. Send progress updates, keep filling available slots, and avoid a final response while useful experiments remain.
- If the agent is about to end while the target is unmet, write the exact reason to the ledger and include the next ready candidates or search group that should run when resources permit.

**A batch completing is never a stop condition. A sub-phase target being met is never a stop condition. The loop must not be canceled for these reasons.**

## Runtime Detection

Determine which agent runtime you are before proceeding:

- **Codex**: Your active instructions identify you as "Codex, a coding agent based on GPT-5". Skill installed at `~/.codex/skills/my-auto-experiment-tuning/`. Shell sessions are the primary experiment execution path; no `run_in_background`, no background notifications, no `/loop`. The Strategist agent id lives in `loop_state.json` and `strategist-begin` prints the `send_input` resume call.
- **Claude Code**: Your system prompt says "You are Claude Code, Anthropic's official CLI for Claude." Skill installed at `~/.claude/skills/my-auto-experiment-tuning/`. You have `run_in_background=True` on Bash, background-completion notifications, and the `/loop` timer. Read `references/claude-code-adapter.md` immediately after this file.

Throughout this skill, `SKILL_DIR` means the install root above. Substitute it when running `aet.py` commands.

Identify your runtime once, here. Record it at `init` with `--runtime` (Codex must pass `--runtime codex`; Claude Code defaults to `claude`); it is stored in `meta.json`. Every per-cycle command (`loop-state`, `strategist-begin`) reads it from the session, so do not pass `--runtime` again after `init`.

## Quick Start

1. Read project-local operating context:
   - Read these core references immediately after this file: `references/workflow.md`, `references/subagents.md`, and `references/gpu-policy.md`. `references/workflow.md` carries the full autonomous loop, the durable ledger/state schema, and the per-cycle GPU capacity rules; `references/gpu-policy.md` holds the configurable-parameter and CLI-flag tables for the GPU scheduling you arrange.
   - `AGENTS.md`, `CLAUDE.md`, experiment README files, and existing memory/notes if present.
   - Check `references/project-adapter-*.md` for project-specific adapters. Each adapter should state its match criteria near the top, such as project root paths, repository markers, or required files. If one matches the current project, read it before planning.
   - **Semantic search — don't trust filenames alone**: After reviewing file names, use your available search tool (`grep`, `rg`, `search`, or equivalent) to scan all reference files for keywords from the actual task: project root path fragments, script names, method names, metric names, and parameter names the user mentioned. If any file matches, read it fully. This step takes seconds and prevents missing critical tuning rules that happen to live in a file whose name looks irrelevant.
   - **Claude Code only**: read `references/claude-code-adapter.md` now to understand how your execution model differs from Codex.

2. Create the session — for a fresh objective. If instead the user asked you to resume/continue an existing on-disk session, do NOT `init`: read `references/recovery.md` and follow it (re-attach to the existing session, no new registration).

```bash
python SKILL_DIR/scripts/aet.py init \
  --project-root /path/to/project \
  --name short-task-name \
  --objective "maximize PSNR under benchmark ordering constraints" \
  --goal max \
  --runtime claude   # or codex; stored as the session default
# optionally append GPU policy flags here, or set later: --gpu-ids 2,3 --max-per-gpu 2
```

Use `aet/` inside the project as the canonical state root. This makes the loop recoverable after context compaction.
The `init` command prints the exact session directory, normally `PROJECT/aet/YYYY-MM-DD/HH-MM-SS`; treat that directory as the only session state location.
`init` already creates `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/plan.md` from `assets/plan-template.md` and `observations.md` from `assets/observations-template.md`. Edit those generated files in place. Do not create ad hoc plan or observation files such as `PROJECT/aet/YYYY-MM-DD/*.md` or `PROJECT/aet/*.md`.

**Claude Code only**: set up `/loop` immediately after `init`, before proceeding further (see Loop Lifecycle section). Do this before writing the plan so the keepalive is active from the start.

3. Write a plan before launching:
   - target metric and direction
   - current best/baseline
   - explicit target threshold if the user provided one
   - current stop condition and minimum evidence required before stopping
   - constraints that make a result untrustworthy
   - candidate knobs, ranges, and forbidden regions
   - likely parameter couplings and at least one broad interaction group before narrow sweeps
   - per-GPU capacity, current free slots, total_capacity, and the `Ready Queue` invariant: ready candidates must be at or above total_capacity while useful search remains
   - the live execution board: `Completed / Recorded`, `Running`, and `Ready Queue`

Fill `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/plan.md` before launching. If that file is missing or damaged, read `assets/plan-template.md` only to restore the template into the same session `plan.md`; do not copy the template into any other path.

4. Check capacity:

   GPU scheduling is normally something you arrange explicitly (which GPUs, jobs per GPU, thresholds). `references/workflow.md` section 6 covers the scheduling-source priority chain (user > adapter > README > memory), the runtime slot check, the `total_capacity` definition, and the conservative fallback defaults used only when no scheduling is specified. `references/gpu-policy.md` holds the configurable-parameter table and the `aet.py gpu-slots` CLI-flag mapping for the scheduling you arrange.

```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader
python SKILL_DIR/scripts/aet.py gpu-slots --session PROJECT/aet/YYYY-MM-DD/HH-MM-SS
```

Use raw `nvidia-smi` for human-readable/agent-readable context; use `aet.py gpu-slots` for the normalized slot decision because it parses numeric fields internally and applies the stored policy. Pass `--session` (or `--project-root`) so it reads `meta.gpu_policy`; without a session it falls back to conservative defaults (all GPUs, 1/gpu). Output directory creation happens in Step 6 via `aet.py create-run`.

5. Fill Ready Queue before launching:
   **If `Ready Queue` count < total_capacity, run the Strategist transaction before selecting any candidates.** This is the same invariant as the steady-state cycle — it applies at session start too. Strategist plans candidates from `plan.md`'s objective, hypotheses, and coupled parameters; it does not require completed runs to do so. Do not manually design the initial parameter set yourself; that is Strategist's responsibility.

   Run the three beats: `aet.py strategist-begin` → the spawn call it prints → `aet.py strategist-return ...`. At session start the queue is empty so begin opens a blocking fresh spawn. Because all slots are free, expect Strategist to return at least 2× total_capacity (current_free_slots + total_capacity): if it returns only total_capacity, launching the first wave empties the queue and forces an immediate redundant re-call against the same empty result state. With ≥ 2× total_capacity, the queue still holds ≥ total_capacity after the first launch wave.

   Follow strategist-return's `YOU` block to append returned candidates to Ready Queue, then proceed.

6. Launch experiments:
   - Select candidates from `plan.md` `Ready Queue`, highest priority first, for as many free slots as current resource checks allow.
   - Launch each job onto a GPU id named in `aet.py loop-state`'s `LAUNCH ... onto GPU id(s) [...]` line. Those are the only free GPUs; do not hand-pick a GPU, reuse a finished run's id, or round-robin. If you need the free ids outside a launch routing, run `aet.py gpu-slots` and use the GPUs it reports `free>0`.
   - Register each run with `aet.py create-run --name ... --params '...' --gpu-id G` (no `--run-id`), where `G` is one of those named ids. It auto-assigns the next safe ID, creates `runs/<id>/output/`, and prints three labeled lines: `run_dir`, `run_id`, `output_dir`. Use the printed `output_dir` directly — do not call `aet.py unique-dir` for session-internal output directories.
   - Redirect stdout/stderr to `output_dir/train.log` in the launch command (`> output_dir/train.log 2>&1`); do not use a separate shared log directory. `create-run` records this as the default `log_path`; no need to pass `--log-path` unless overriding.
   - `create-run` appends a recovery row to `queue.jsonl`; do not treat `queue.jsonl` as the live `Ready Queue`.
   - After the process starts, call `aet.py record --status running` without routine notes so `results.csv` records `start_time`.
   - Move each launched row from `Ready Queue` to `Running` in `plan.md`.
   - **Codex**: run the same launch command in one `exec_command` session per experiment. Do not use shell backgrounding. When Codex returns a long-running `session_id`, record `session_id -> run_id/output_dir/log_path` in `plan.md` and poll with `write_stdin`.
   - **Claude Code**: use `run_in_background=True` on the Bash tool; you will be notified on completion and do not need to poll. See `references/claude-code-adapter.md` for the full pattern.
   - Set `workdir` instead of shell `cd`.
   - Use the standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`.
   - Use plain `python` unless the active environment is wrong; then use the correct interpreter path, for example `/path/to/venv/bin/python -u ...`.
   - Pass `--gpu_id`/equivalent explicitly.
   - Use a unique `--output_dir` for every configuration and never reuse an existing output directory.

7. Record results inline on completion:
   - Verify output directory and metric files exist (runs/<id>/ artifacts).
   - Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort.
   - Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, GPU contention, and partial crashes as `failed` or `inconclusive`.
   - Call `aet.py record` with status and metrics (terminal records add the run to the pending set in `loop_state.json`). Append trust details to `runs/<id>/summary.md` if relevant (after record, since record rewrites that file).
   - Move run row from `Running` to `Completed / Recorded` in `plan.md`.

```bash
python SKILL_DIR/scripts/aet.py record \
  --session /path/to/project/aet/YYYY-MM-DD/HH-MM-SS \
  --run-id 3 \
  --status finished \
  --primary-metric 23.42 \
  --metric-name PSNR \
  --metrics '{"PSNR": 23.42, "SSIM": 0.71}' \
  --notes "lk=0.05 clean run; candidate peak"
```

8. Update project records and continue:
   - Summarize the session with `aet.py summarize`.
   - `aet.py create-run` creates `SESSION/runs/<id>/summary.md` from `assets/run-summary-template.md`, and `aet.py record` rewrites it when metrics/status change. Update that per-run file for important runs after the terminal `record`. If the file is missing, restore the template into `SESSION/runs/<id>/summary.md`, not a date-level note.
   - Update the benchmark table or experiment README in the project-required format.
   - If `Ready Queue` count < total_capacity, run the Strategist transaction (`strategist-begin` → tool_use → `strategist-return`) and follow its `YOU` to append returned candidates. The number added can be 0, 1, or many. Suppress only for explicit self-evaluatable stop conditions (explicit user stop, explicit target met with evidence, explicit budget consumed, permission/resource unavailable). Plateau and exhaustion cannot suppress it — Strategist must declare them.
   - Unless a stop condition is satisfied, keep `Ready Queue` count at or above total_capacity and launch into any free GPU slots immediately.
   - Stop only when the objective is met, budget is exhausted, resources/permissions block continuation, or plateau/exhaustion has been confirmed by two independent Strategist instances per the Default Stopping Rules above.

## AET Helper Calls

Use `scripts/aet.py` as the durable state and safety helper for the tuning loop:

- `init`: create `aet/YYYY-MM-DD/HH-MM-SS/` with `meta.json`, `results.csv`, `queue.jsonl`, `observations.md`, `plan.md`, `loop_state.json`, and `runs/`, then print the session path + the YOU startup steps. `plan.md`/`observations.md` are rendered from the templates and are the canonical files to edit; `loop_state.json` is script-owned. Required: `--project-root`, `--name`, `--objective`. Optional: `--goal max|min` (default `max`), `--runtime claude|codex` (default `claude`; stored as the session default for verb rendering), and any GPU policy flags (see `set-policy`).
- `set-policy`: persist the GPU policy into `meta.json` so `gpu-slots`/`loop-state`/`strategist-begin` all compute capacity from one source. Optional: `--session` or `--project-root`, `--gpu-ids`, `--max-per-gpu`, `--max-util`, `--max-memory-used-mb`, `--min-free-memory-mb`, `--process-pattern`. Set it once at/after `init`; re-run only when the policy genuinely changes mid-session.
- `create-run`: register a run before launch, create `runs/<id>/` and `runs/<id>/output/`, append a recovery snapshot to `queue.jsonl`, and print three labeled lines: `run_dir`, `run_id`, `output_dir`. The printed `output_dir` is already created — use it directly as the experiment output directory. Optional: `--session` or `--project-root` (latest session lookup), `--name`, `--params` (JSON string or JSON file), `--command`, `--gpu-id`, `--output-dir`, `--log-path`, `--notes`. Never pass `--run-id`; always let it auto-assign to avoid collisions when `plan.md` is stale. `queue.jsonl` is not the live `Ready Queue`; manage ready candidates in `plan.md`.
- `record`: update a run whenever status or results change. Required: `--run-id`, `--status created|running|finished|failed|inconclusive|superseded`. Optional: `--session` or `--project-root`, `--name`, `--primary-metric`, `--metric-name`, `--metrics` (JSON string or JSON file), `--gpu-id`, `--output-dir`, `--log-path`, `--notes`. Use `running` to record `start_time`; terminal statuses record `end_time`, add the run to the pending set in `loop_state.json`, and flag `NEW BEST` in the output when the run becomes the best finished result. `--notes` appends to `observations.md`, so omit it for routine `running` updates and use it for terminal trust/failure notes.
- `unique-dir`: choose a non-existing path and optionally create it. Positional: `path`. Optional: `--mkdir`. Use only when `output_dir` must live outside the session directory (e.g., a project-level `[PROJECT]/tun_res/` tree). For session-internal run output, use `aet.py create-run` instead — it creates `runs/<id>/output/` automatically.
- `gpu-slots`: estimate available GPU slots. With `--session`/`--project-root` it reads the stored `meta.gpu_policy`; flags override per call: `--kind default|light|heavy`, `--capacity N`, `--max-util N`, `--process-pattern REGEX`, `--gpu-ids 0,1,3`, `--max-memory-used-mb N`, `--min-free-memory-mb N`, `--allow-over-cap`, `--json`. It queries `nvidia-smi`, then prints per-GPU utilization/memory/running/capacity/free plus a `TOTAL free_slots/total_capacity` footer.
- `loop-state`: the decision panel — call each cycle and each `/loop` tick. The script counts the `### Ready Queue` rows in `plan.md` itself. Optional: `--session`/`--project-root`, `--runtime` (override only; defaults to the session's stored runtime — normally omit), `--ready-count` (override only; normally omit — a value differing from the plan.md count is flagged stale and ignored). Prints OK/STATE plus a routed `YOU`/NEXT (launch K rows, run the Strategist transaction via a specific branch, or wait).
- `strategist-begin`: open a Strategist transaction (Beat 1). Optional: `--session`/`--project-root`, `--runtime` (override only), `--ready-count` (override only; the script counts the Ready Queue from `plan.md`). Snapshots pending, computes fresh/resume/confirmer + blocking/background, opens `active_strategist_call`, and prints the exact spawn/resume tool call + payload. Refuses if a call is already open.
- `strategist-return`: close the transaction (Beat 3). Required: `--call-id C`, `--candidates-count K` (how many candidates the Strategist returned; the script derives exhaustion from `K == 0`). Optional: `--agent-id A`, `--resume-failed`, `--observations-present`, `--queue-edits-present`, `--stop-update-present`, `--ready-count` (override only; the script counts the Ready Queue from `plan.md` before you append the returned candidates). Clears the snapshot (version-guarded), records the agent id, applies the exhaustion handshake, prints the gated `YOU` doc obligations.
- `strategist-abort`: last resort to abandon an open call when the subagent is genuinely gone (spawn failed / resume returned `success:false` / cancelled). Required: `--call-id C`, `--reason spawn_failed|unreachable|cancelled`. Clears `active_strategist_call` and (for `unreachable`/`spawn_failed`) the agent id — losing the resume chain and any work the subagent already produced. An open call alone is NOT evidence the subagent died: if it returned, use `strategist-return`; if its output is merely lost, resume it to re-request first.
- `parse-log`: extract metrics from a log only when structured metrics are unavailable. Positional: `log`. Optional: repeat `--pattern REGEX`; each pattern should have named groups `name` and `value`, or one numeric group. Treat regex output as a draft and inspect it before recording.
- `status` / `summarize`: print session path, objective, run counts, status counts, and current best finished result. Optional: `--project-root`, `--session`, `--goal max|min`.

Session-aware commands (`create-run`, `record`, `status`, and `summarize`) accept `--session`; if omitted, they use the latest session under `--project-root/aet`. Prefer explicit `--session` when multiple sessions may exist or when delegating work to subagents.

## Resource Map

- `references/workflow.md`: core; read at session start. Carries the full autonomous loop, the durable ledger/state schema (session files, run-status values, per-run fields, contamination rules), the per-cycle GPU capacity rules, and project-record and cross-session-knowledge handling.
- `references/project-adapter-*.md`: optional project adapters. Each adapter should state match criteria at the top and point to the authoritative project README, benchmark docs, launch conventions, and known tuning constraints.
- `references/gpu-policy.md`: core; read at session start. Holds the configurable-parameter table, the `aet.py gpu-slots` CLI-flag mapping, and the multi-per-GPU conditions for the GPU scheduling you arrange. The scheduling-source priority chain, the runtime slot check, `total_capacity`, and the conservative fallback defaults live in `workflow.md` section 6.
- `references/permissions.md`: conditional; read only when running under an approval-gated sandbox (not full auto/bypass) or when a command is blocked and you need a narrowly scoped escalation. Covers command-shape/prefix hygiene, recommended pre-approval prefixes, and the escalation pattern.
- `references/recovery.md`: conditional; read only when re-attaching a runtime to an existing on-disk session — a `/loop` keepalive tick, a post-compaction continuation, or a user request to continue a prior loop. Not read on a fresh start. Covers the two recovery kinds and the no-self-scan rule.
- `references/watchdog.md`: read when setting up a keepalive for a long session (Claude Code `/loop` or external cron for Codex). Not needed for short runs.
- `references/subagents.md`: core; read at session start (already listed in Quick Start step 1). Contains trigger rules, the Strategist prompt template, and the post-return protocol to follow after each Strategist call.
- `references/claude-code-adapter.md`: **Claude Code only** — read at session start (already listed in Quick Start step 1). Covers `run_in_background`, completion notifications, `/loop`, and subagent differences vs Codex.
- `scripts/aet.py`: session creation, run scaffolding, GPU policy persistence (`set-policy`) and slot inspection (`gpu-slots`), the loop decision panel (`loop-state`), the Strategist state machine (`strategist-begin`/`strategist-return`/`strategist-abort` over `loop_state.json`), log parsing, result recording, and summaries. The loop commands (`init`, `create-run`, `record`, `set-policy`, `loop-state`, `strategist-begin/return/abort`) print the three-zone `OK/STATE/YOU`; `gpu-slots`, `parse-log`, `unique-dir`, `status`/`summarize` print plain data.
- `assets/plan-template.md`: source template rendered by `aet.py init` into the session's `plan.md`; it defines the live execution board (`Completed / Recorded`, `Running`, `Ready Queue`) and rolling queue invariant. Read it only to understand or restore the generated plan format.
- `assets/observations-template.md`: source template rendered by `aet.py init` into the session's `observations.md`; read it only to understand or restore observation sections.
- `assets/run-summary-template.md`: source template rendered by `aet.py create-run` into `SESSION/runs/<id>/summary.md`; read it only to understand or restore per-run summary format.
- Subagent `experiment-strategist`: analyzes recent completed runs (generates observations) and plans the next queue of candidate experiments. When no runs have completed yet, skips observations and plans initial candidates from `plan.md` directly. Invoke it inside the three-beat transaction: `aet.py strategist-begin` prints the exact call to make (Claude Code `Agent`/`SendMessage`; Codex `spawn_agent`/`send_input`), then close with `aet.py strategist-return`. See `references/subagents.md`.
- `agents/openai.yaml`: UI metadata only; do not treat it as operational instructions.

Load only the reference file needed for the current decision.

## Subagent Pattern

By default, delegate analysis and planning to the Strategist so you stay focused on orchestration:
- Strategist: returns per-HP observations for recent runs and Ready Queue candidates. Does not write `plan.md` or `observations.md`; apply returned rows and observations.

Invoke it only inside the three-beat transaction (`aet.py strategist-begin` → tool_use → `aet.py strategist-return`). `strategist-begin` prints the exact call to make and the payload; it owns fresh-vs-resume-vs-confirmer and the Strategist agent id.

- **Claude Code**: the printed call is `Agent(subagent_type="experiment-strategist", prompt=..., run_in_background=...)` for a fresh spawn/confirmer, or the literal `SendMessage` tool (invoked by name, not `Agent`) targeting the existing agent id for a resume. A resume reuses the existing strategist with its context — Agent-spawning a new one on a resume route throws that context away; fall back to a fresh `Agent` spawn only if `SendMessage` returns `success:false`, then pass `--resume-failed` to `strategist-return`. Pass only session-specific context; the role instructions load from the subagent's own system prompt.
- **Codex**: the printed call is `spawn_agent(message=..., fork_context=true)` with the registered custom agent `experiment-strategist` for a fresh spawn/confirmer, or `send_input(target=..., message=...)` then `wait_agent` for a resume. If a resume target is still running, `send_input` queues; if it was closed, `resume_agent(id=...)` first. If resume fails, fall back to a fresh `spawn_agent` and pass the new id to `strategist-return --agent-id` plus `--resume-failed`. `multi_tool_use.parallel` is for parallel tool calls, not subagent creation.

See `references/subagents.md` for the prompt template. If delegation is not authorized, perform strategy and planning inline yourself.

## Result Integrity

Before accepting a result as benchmark-quality:
- Verify the output files exist.
- Verify the log belongs to the intended command and output directory.
- Check whether GPU contention or early crashes make the run untrustworthy.
- Compare against the current benchmark with the same metric definition.
- Confirm that no later-discovered code/data conversion bug contaminates the run.
- Record seed, preprocessing mode, objective terms, schedule/switch values, and any code changes needed to reproduce the result.
- Preserve raw logs and metrics paths in the ledger.

If a run is contaminated, record it as `inconclusive` rather than deleting it.
