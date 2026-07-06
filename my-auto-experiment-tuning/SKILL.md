---
name: my-auto-experiment-tuning
description: Autonomous, hypothesis-driven experiment and hyperparameter tuning for ML/research codebases. Use when you need to run many experiments, tune hyperparameters, manage GPU slots, analyze results, maintain benchmark tables or experiment ledgers, resume an interrupted tuning loop, or coordinate subagents for strategy/result analysis. Supports project-specific adapters while keeping the main workflow generic.
---

# Auto Experiment Tuning

## Operating Model

Run an autonomous loop as the experiment orchestrator. Understand the project once, create one durable session, manage run lifecycle commands, check GPU slots, launch work, and coordinate subagents. `results.csv` is the single source of truth for every run and candidate; `session.md` holds the narrative analysis. Do not do inline hyperparameter analysis or candidate strategy.

Analysis and planning are delegated:
- Strategist returns per-HP observations, planned-queue candidates, and Benchmark Review decisions for finished runs.

Launch assigned runs directly. Perform inline result recording (metric parsing, terminal-status classification, `aet.py record`, file writes) after each run completes.

Keep the rolling loop moving **without pausing between planning groups**.

### ⛔ Forbidden Anti-Patterns (CRITICAL — read before anything else)

These are the mistakes that break the autonomous loop. **Never do any of these:**

| # | Anti-Pattern | Why It's Wrong | Correct Behavior |
|---|-------------|---------------|-----------------|
| 1 | **Stopping after a batch completes** — collecting results, writing a summary report, and going idle | A batch completing is NOT a stop condition. The loop continues as long as slots exist and unexplored parameter regions remain. | After collecting results: immediately run `loop-state`, execute any routed Strategist transaction, launch as many ready candidates as current resources allow, THEN give a brief progress note (not a final report). |
| 2 | **Canceling the `CronCreate` keepalive after a sub-phase** — `CronDelete`-ing the job because "this sub-goal is done" | The keepalive is the heartbeat for the ENTIRE tuning objective, not one sub-phase. Canceling it kills the autonomous session. | Create the `CronCreate` keepalive once at session start. Only `CronDelete` it when the user explicitly ends the session, or a valid stop condition has been recorded and the session is being closed. |
| 3 | **Creating new AET sessions for sub-phases** — running `aet.py init` again when exploring a new parameter direction | One tuning objective = one session. Fragmenting sessions destroys the ledger continuity. | Use the same session for the entire tuning objective. Sub-phases are documented in the same `results.csv` and `session.md`. |
| 4 | **Using shell `for` loops to create dirs or launch experiments** — `for d in ...; do ...; done` | Hook interception → manual approval → loop broken. | Use `mkdir -p dir1 dir2 dir3 dir4` to create multiple directories in one command. Claude Code: launch with independent `Bash(run_in_background=True)` calls. Codex: launch with one `exec_command` session per experiment; no shell `&`. |
| 5 | **Presenting a "final report" before checking if more work exists** — summarizing results as if the task is done | Unless a stop condition is met (target achieved, budget exhausted, or plateau confirmed by two independent Strategist instances), the tuning continues. | After results: check slots → launch more → then (and only then) give a brief status update. Do not frame updates as conclusions. |
| 6 | **Keeping only a same-size "next batch" of candidates** — planning exactly as many candidates as current free slots | This creates idle gaps and forces batch-synchronous thinking. | Keep `projected_ready_after_launch` at or above total_capacity whenever unexplored regions remain. |
| 7 | **Self-declaring exhaustion, convergence, or plateau** — concluding from your own reading of results that the search space is exhausted, a ceiling has been reached, or that further tuning is futile, then stopping or skipping Strategist on that basis | You lack the full search-history perspective; such judgments are highly error-prone. Only the Strategist has authority to declare exhaustion. | Never self-evaluate plateau, convergence, or exhaustion. When the planned queue is insufficient, run the Strategist transaction. Only when Strategist returns 0 candidates and explicitly declares exhaustion should you consider stopping — and even then a second independent confirmer must agree. The script owns this: `aet.py strategist-return` sets the handshake, and the next `aet.py strategist-begin` forces a fresh independent confirmer (never a resume). See Default Stopping Rules. **Signal**: if you find yourself about to write "this direction is exhausted", "a ceiling has been reached", or "lcdf is a dead end" — that sentence is the trigger to run the transaction, not to stop. |
| 8 | **Skipping Strategist because it was "recently called" or "has no new data"** — reasoning that calling Strategist is pointless because it just ran, or because the pending set is empty, so there is nothing new for it to analyze | Recency and an empty pending set are not suppression conditions. Strategist always plans from the full session state and can add valuable candidates even immediately after a prior call. The only valid suppression conditions are: explicit user stop, target cleanly met, budget consumed, permission unavailable, or a Strategist call already open (`strategist-begin` refuses a second). | When `projected_ready_after_launch < total_capacity`, run the Strategist transaction. **Signal**: if you find yourself thinking "Strategist was just called so I'll skip it" or "there's nothing new for Strategist to analyze" — that reasoning is invalid. Run it. |
| 9 | **Skipping Strategist on keepalive invocations that found no new completions** — running `aet.py status`, seeing no change since last check, and concluding "nothing to do this invocation, continue waiting" without running `aet.py loop-state` | The loop-state check is unconditional and independent of whether new completions occurred. `aet.py status` showing no change means step (1) has no action; it does NOT mean the loop-state routing can be skipped. | After `aet.py status` shows no new completions: still run `aet.py loop-state`. If it routes a Strategist call, run the transaction immediately — even with 0 new completions, even with all GPU slots occupied. **Signal**: if you find yourself writing "no new completions, continue waiting" — that sentence is the trigger to run `loop-state`, not to stop. |
| 10 | **Reading an OPEN `active_strategist_call` as proof the subagent is still running** — then either busy-waiting on it or `strategist-abort`-ing it as "stale/unreachable" | `loop_state.json` is the state machine YOU update; a call stays OPEN only because you have not yet run `strategist-return`. The script cannot see the subagent at all. Treating its un-updated state as "subagent still running" is circular — and aborting on that basis discards a subagent that already returned, throwing away its candidates AND clearing the resume chain. | Judge the subagent's real state from its completion notification, task panel, or task output. If it returned, run `strategist-return` with its result. On a resume route, use the printed runtime resume call; close with `--resume-failed` only after that call fails. Reserve `strategist-abort` for a failed, unreachable, or cancelled open fresh call. |

### Continuous Rolling Execution (NOT batch-synchronous)

The default operating mode is **asynchronous rolling**: GPU slots are filled continuously, not in synchronized waves. A "batch" is a planning concept, not an execution gate.

> The 8-step protocol below governs the **steady-state cycle** (each completion notification → record → refill). For **session startup queue fill** (before the first launch), see Quick Start step 5.

**The iron rule**: when you receive a completion notification for ANY experiment:
1. Identify the run by its run_id and verify the output/log paths exist
2. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort
3. Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, mismatched output directories, GPU contention, and partial crashes as `failed` or `inconclusive`
4. Call `aet.py record --status <status> --run-id <id> [--primary-metric <v> --metric-name <n> --metrics '<json>'] [--annotation '<note>']`. `aet.py record` writes `results.csv` and adds the terminal run to the pending set in `loop_state.json`.
5. Run `aet.py loop-state` (it counts the planned queue from `results.csv` itself) and follow its `YOU` block — the routing hub right after `record`. It computes free slots and total_capacity (from the stored GPU policy) and prints the exact run_id → GPU pairings to launch plus any Strategist routing.
6. Launch the specific run_ids that loop-state's `LAUNCH runs [...] onto GPU id(s) [...]` line names, onto the GPU ids it names (create-run → launch → record running). Each listed GPU-id occurrence represents one free slot; the same id may appear more than once when stored `max_per_gpu > 1`.
7. When loop-state routes a Strategist call (`projected_ready_after_launch < total_capacity`, where `projected_ready_after_launch = planned_count - min(free_slots, planned_count)`), run the **Strategist transaction** — three beats, every time (full detail in [references/subagents.md](references/subagents.md)):
   - **begin**: `aet.py strategist-begin` snapshots pending runs, finished evidence versions, and pending benchmark markers; computes the branch (fresh / resume / fresh confirmer); opens the call; and prints the exact spawn/resume tool call + payload. It refuses if a call is already open or benchmark-update debt exists.
   - **tool_use**: make the printed call (Claude Code `Agent`/`SendMessage`; Codex `spawn_agent` or `send_message`/`followup_task`). This is your own tool_use, bracketed by begin and return. Between the two you may keep recording other completions; `record` adds them to pending without disturbing the open call.
   - **return**: `aet.py strategist-return --call-id C --candidates-count K --benchmark-promotion-run-ids none|IDS --benchmark-reviewed-run-ids none|IDS [--agent-id A] [--observations-present] [--reusable-rules-present] [--queue-edits-present] [--stop-update-present]` clears version-matched snapshots, records promotion debt in `loop_state.json`, applies the handshake, and prints the `YOU` obligations. `K` must be non-negative. Pass both benchmark selectors on every return and pass `--agent-id` for every fresh invocation, including a confirmer. Apply project table updates from the resulting debt, then acknowledge successful writes with `aet.py benchmark-ack`.
   The script owns fresh-vs-resume-vs-confirmer, the exhaustion handshake, and quiescence — do not hand-derive any of it. Suppression conditions: explicit user stop, target cleanly met, budget consumed, permission unavailable, or a call already open. Plateau, exhaustion, recency, and an empty pending set cannot suppress.
8. Only after steps 1-7: give a brief progress update

**Never wait for all experiments in a batch to finish before acting.** Process each completion as it arrives. Keep all GPU slots occupied at all times.

Do NOT present a summary and go idle after a batch. A batch is not a stop boundary. The only valid stop boundaries are the stop conditions listed below.

### Rolling Queue State Machine

`results.csv` is the single live ledger. Each row's `status` carries its place in the lifecycle:

`planned` (registered candidate, not yet assigned a GPU) → `created` (GPU/output_dir assigned, not yet launched) → `running` → `finished` / `failed` / `inconclusive` / `superseded`. A `planned` candidate invalidated before launch goes `planned → dropped`.

Keep `projected_ready_after_launch` at or above total_capacity whenever useful unexplored regions remain. `projected_ready_after_launch = planned_count - min(free_slots, planned_count)`; total_capacity = configured capacity_per_gpu × number_of_gpus under the stored policy and changes only through `set-policy`. Read slot and capacity values from `aet.py gpu-slots`. `loop-state` routes the Strategist transaction whenever the projected count is below total_capacity.

State transitions:
- Register Strategist-returned candidates with `aet.py queue-add` (each becomes a `planned` row with an auto-assigned run_id). Preserve every returned multi-point or factorial group; do not reduce it to a one-finished-run to one-new-run cadence.
- Launching takes one or more `planned` run_ids that `aet.py loop-state` names, activates each with `aet.py create-run --run-id <id> --gpu-id <gpu>` (planned → created, allocating output_dir/log_path), launches the command, then records each accepted process with `aet.py record --status running`.
- Completion triggers inline recording: verify output files → parse metrics (JSON/CSV/NPZ → TensorBoard → log regex) → determine status → call `aet.py record` (which adds the terminal run to the pending set) → run `aet.py loop-state` (the routing hub) → launch the planned run_ids it names into free slots.
- New evidence may invalidate unlaunched `planned` candidates; after Strategist returns Queue Edits, run `aet.py queue-drop --run-ids <ids> --reason '<why>'` (planned → dropped) and record the reasoning in `session.md`.

### Delegation Protocol

Read [references/subagents.md](references/subagents.md) before spawning the Strategist. Use paths and durable context in prompts; avoid summarizing results for the subagent when it can read the files directly.

| Trigger | Role | Follow-up |
| ------- | ---- | --------- |
| `projected_ready_after_launch < total_capacity` under the stored GPU policy | Strategist | Run the three-beat transaction: `aet.py strategist-begin` → printed tool call → `aet.py strategist-return`. Pass the id for every fresh invocation. Then follow `loop-state`: apply and acknowledge any benchmark-update debt before another Strategist call, apply session/queue updates, and launch planned rows. |

Self-evaluatable conditions that may suppress a Strategist call: explicit user stop, explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable. Plateau and exhaustion are never self-evaluatable — Strategist must declare them. **Recency of the last Strategist call and an empty pending set are not suppression conditions.**

When calling subagents, pass `algorithm_context` as 2-5 sentences covering: metric meaning and direction, tuning target, known comparability risks (GPU contention, channel mode differences, etc.), and key parameter couplings. Use the template in [references/subagents.md](references/subagents.md).

Single-writer rules:
- `results.csv`: only through `aet.py queue-add`, `queue-drop`, `create-run`, and `record`.
- `session.md`: write lifecycle facts and apply the Strategist's returned Current Analysis, Reusable Rules, and Stop/Continue Rule updates.
- `loop_state.json`: script-owned. Fields: pending run set, Strategist identity/open call, exhaustion handshake, agent history, and `pending_benchmark_updates`. Each benchmark debt entry stores `call_id`, approved `terminal_version`, metric name/value, output/log locators, and `added_at`. Read it with `aet.py loop-state`; change it only through AET helper commands. `loop-state` routes benchmark debt before launches or Strategist work.

### One Session Per Objective

Create exactly ONE AET session (`aet.py init`) per user tuning objective. Do NOT create new sessions for sub-phases, new parameter directions, or follow-up explorations. All sub-phases go into the same session's `results.csv` and `session.md`. If you accidentally created multiple sessions, consolidate into the first one and stop creating new ones.

### Loop Lifecycle (Claude Code)

- **When to create**: immediately after `aet.py init`, before launching the first experiment. Call the `CronCreate` tool directly (cron `7 * * * *` for hourly) with interval ≥ 1 hour unless individual runs are very short. Follow [references/claude-code-adapter.md](references/claude-code-adapter.md) "Periodic Keepalive (CronCreate)".
- **When to adjust**: change the interval if runs are short (≤ 20 min → 30m interval) or very long (≥ 2h → 2h interval).
- **When to cancel**: ONLY when (a) the user explicitly says "stop" or "end the tuning", OR (b) a valid stop condition has been recorded and the session is being closed. **Never cancel the loop just because a sub-phase produced good results, reached a local peak, or met one image's target.**
- **The loop is the heartbeat of autonomous tuning.** Canceling it without a valid stop condition kills the session. If in doubt, keep it running.

### Default Autonomy Contract

- Treat the user's initial request as the authorization to pursue the stated tuning objective end to end within the active sandbox and approval policy.
- Do not ask the user to approve each candidate group, each hyperparameter choice, each GPU assignment, or each result update.
- Make local decisions from the written objective, benchmark constraints, project memory, and observed results.
- Ask the user only when the objective is ambiguous, the next action is destructive, required permissions are unavailable, or the run would exceed the user's stated budget/principles.
- Continue filling available slots, collecting results, and applying Strategist-returned candidate groups until a stop condition is reached.
- Do not stop merely because a result improved the current best, looks "good enough", or a local neighborhood has been checked. If the user has not set an explicit budget, keep running until the user intervenes, the explicit target is met, or the plateau/exhaustion rules below are satisfied.
- If the user gives a numeric target such as `PSNR > 25`, treat it as a hard stop condition: continue autonomous rolling execution until a clean run meets or exceeds it, or until the user changes the target or budget.
- If the user says resources are available or asks to "fully tune", actively keep GPUs occupied within the configured contention limits. Prefer launching ready candidates into all currently free slots as soon as resources are available — do not wait for all running experiments to finish.

### Core Rules

- Optimize by hypotheses, not blind grids. State what each candidate group is testing.
- Preserve the Strategist's coupled-parameter groups when registering and launching candidates.
- When progress stalls or evidence conflicts, run the routed Strategist transaction and apply its broaden/refine decision.
- Division of labor: you manage the experiment lifecycle (orchestration, launching, inline recording) and the Strategist owns analysis and candidate planning. Delegate observations synthesis and next-candidate strategy to the Strategist; apply returned decisions and keep managing the lifecycle.
- Keep a durable ledger before relying on context memory.
- Never overwrite an existing output directory, log file, or shared result JSON.
- Keep credentials out of `results.csv`, `session.md`, commands, params, hypotheses, expected signals, rationales, annotations, and shared logs. Refer to environment-variable names or secret-manager handles, never secret values.
- Treat failed and bad runs as data. Record the failure pattern and avoid repeating it.
- If a standard baseline is far below expected behavior, pause pure hyperparameter sweeps and audit implementation fidelity, preprocessing, objective terms, schedules, seeds, and metric definitions.
- Treat the evaluator as part of the experiment contract. For a new or changed command/evaluator, run project-native validation or a dry run before GPU search; preserve the raw evidence and let the Strategist decide whether baseline fidelity, metric signal, and search headroom are adequate.
- Collect aggregate and diagnostic evidence: primary and secondary metrics, per-case/seed/slice or worst-case metrics when available, failure/stability rates, and best-artifact paths. Do not infer robustness or choose follow-up candidates inline; pass the artifacts to the Strategist.
- Use staged budgets when the project supports them: a short probe validates the end-to-end path and metric signal before expensive full runs. The Strategist chooses probe/full-run candidates; you execute and record them. Record checkpoint provenance whenever a later run resumes earlier state.
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
  Use plain `python` by default so the command inherits the active shell environment; use an explicit interpreter path only when that environment is wrong. Pass `--gpu_id` explicitly.
  - **Codex**: run that same command as one `exec_command` session per experiment. Do not add shell `&`; if the tool yields a `session_id`, record the `session_id -> run_id/output_dir/log_path` mapping and poll it with `write_stdin`.
  - **Claude Code**: use one independent `Bash(run_in_background=True)` tool call per experiment.
- Read logs: `grep -r "pattern" /abs/path/results/` or the Read tool for known paths — never a `for f in ...` loop
- Always use absolute paths — no `cd` needed

Follow [references/claude-code-adapter.md](references/claude-code-adapter.md) for safe Bash patterns.

### Default Stopping Rules

- Stop only for one of these reasons: explicit user stop, explicit metric target met with clean evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable, destructive action required, or a plateau/exhaustion decision confirmed by two independent Strategist instances per the rules below.
- The plateau/exhaustion stop condition cannot be self-evaluated. You have no authority to conclude the search space is exhausted, a ceiling has been reached, or that further tuning is futile. Only the Strategist may declare plateau or exhaustion, after evaluating the minimum evidence requirements.
- Strategist calling follows one rule throughout: `projected_ready_after_launch < total_capacity` → run the Strategist transaction. `aet.py strategist-begin` chooses blocking vs background and fresh vs resume vs confirmer. When a Strategist returns zero candidates the queue stays empty, so every subsequent trigger keeps running the transaction with the standard neutral prompt and complete session state.
- All Strategist prompts must use the standard neutral template from subagents.md. Never add context about previous Strategist conclusions, never ask "is the search exhausted?", never prime the conclusion in any direction.
- Stop condition for plateau/exhaustion: two exhaustion signals from **independent contexts**, both produced while fully quiescent. Quiescence means no `planned`/`created`/`running` rows and no live process matching the stored session process pattern; the script computes it. A Strategist signals exhaustion by **returning zero candidates**. When the Primary returns 0 candidates while quiescent, `aet.py strategist-return` sets the handshake so the next `aet.py strategist-begin` forces a **fresh confirmer**, never a resume of the Primary. Pass the fresh confirmer's id to `strategist-return --agent-id`. If the confirmer returns candidates, it is promoted to Primary and the loop continues; only when the fresh confirmer also returns 0 candidates does `strategist-return` print `CONFIRMED_EXHAUSTION`. Any Strategist that returns candidates resets the handshake. Follow [references/subagents.md](references/subagents.md); under the `claude` runtime also follow [references/claude-code-adapter.md](references/claude-code-adapter.md) step 9.
- When no explicit target or budget is supplied, assume the user wants continued tuning rather than a final answer. Send progress updates, keep filling available slots, and avoid a final response while useful experiments remain.
- Before ending while the target is unmet, write the exact reason to the ledger and include the next ready candidates or search group for the next continuation.

**A batch completing is never a stop condition. A sub-phase target being met is never a stop condition. The loop must not be canceled for these reasons.**

## Runtime Detection

Select the runtime from the available execution primitives:

- **`codex`**: use when long commands run as foreground `exec_command` sessions and yielded sessions are polled with `write_stdin`; background notifications and `CronCreate` are unavailable. The skill root is `~/.codex/skills/my-auto-experiment-tuning/`; the Strategist id lives in `loop_state.json`, and `strategist-begin` prints the Codex spawn/resume call.
- **`claude`**: use when Bash supports `run_in_background=True`, completion notifications, and `CronCreate`. The skill root is `~/.claude/skills/my-auto-experiment-tuning/`; read [references/claude-code-adapter.md](references/claude-code-adapter.md) immediately.

Throughout this skill, `SKILL_DIR` means the install root above. Substitute it when running `aet.py` commands.

Identify your runtime once, here. Record it at `init` with `--runtime` (Codex must pass `--runtime codex`; Claude Code defaults to `claude`); it is stored in `meta.json`. Every per-cycle command (`loop-state`, `strategist-begin`) reads it from the session, so do not pass `--runtime` again after `init`.

## Quick Start

1. Read project-local operating context:
   - Read these core references immediately after this file: [references/workflow.md](references/workflow.md), [references/subagents.md](references/subagents.md), and [references/gpu-policy.md](references/gpu-policy.md). `workflow.md` carries the full autonomous loop, durable ledger/state schema, per-cycle GPU capacity rules, project records, and cross-session knowledge; `gpu-policy.md` holds the configurable-parameter and CLI-flag tables.
   - `AGENTS.md`, `CLAUDE.md`, experiment README files, and existing memory/notes if present.
   - Check the [AI4M](references/project-adapter-ai4m.md) and [CLIP-Deblur](references/project-adapter-clip-deblur.md) adapters. Match by project root, repository markers, or required files, and read only an adapter whose criteria hold.
   - **Semantic search — don't trust filenames alone**: After reviewing file names, use your available search tool (`grep`, `rg`, `search`, or equivalent) to scan all reference files for keywords from the actual task: project root path fragments, script names, method names, metric names, and parameter names the user mentioned. If any file matches, read it fully. This step takes seconds and prevents missing critical tuning rules that happen to live in a file whose name looks irrelevant.
   - **`claude` runtime only**: read [references/claude-code-adapter.md](references/claude-code-adapter.md) now.

2. Create the session for a fresh objective. For an explicit resume/continue request, read [references/recovery.md](references/recovery.md) and re-attach to the existing session.

```bash
python SKILL_DIR/scripts/aet.py init \
  --project-root /path/to/project \
  --name short-task-name \
  --objective "maximize PSNR under benchmark ordering constraints" \
  --goal max \
  --runtime RUNTIME \
  --process-pattern 'experiments/exp_dip_deblur\.py'
# optionally append GPU policy flags here, or set later: --gpu-ids 2,3 --max-per-gpu 2
```

Substitute the runtime selected above: `RUNTIME=codex` for Codex and `RUNTIME=claude` for Claude Code.

`--process-pattern` is required: a regex that uniquely identifies this session's experiment processes in `ps` output. Use the experiment script filename or a distinctive path fragment — specific enough to avoid matching other projects' or sessions' experiments, but broad enough to match all launch variants of the same script. Follow [references/gpu-policy.md](references/gpu-policy.md) for examples and anti-patterns.

Use `aet/` inside the project as the canonical state root. This makes the loop recoverable after context compaction.
The `init` command prints the exact session directory, normally `PROJECT/aet/YYYY-MM-DD/HH-MM-SS`; treat that directory as the only session state location.
`init` already creates `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/session.md` from [assets/session-template.md](assets/session-template.md). Edit that generated file in place. Do not create ad hoc plan or observation files such as `PROJECT/aet/YYYY-MM-DD/*.md` or `PROJECT/aet/*.md`.

**Claude Code only**: set up the `CronCreate` keepalive immediately after `init`, before proceeding further (see Loop Lifecycle section). Do this before filling session.md so the keepalive is active from the start.

3. Fill `session.md` before launching:
   - Target & Constraints: target metric and direction, current best/baseline, explicit target threshold, constraints that make a result untrustworthy
   - Evaluation Contract: record available project facts for the primary metric, supporting metrics, per-case/seed/slice or worst-case constraints, documented baseline/range, failure handling, best-artifact location, and checkpoint comparability; write `unknown` where evidence is absent. Apply ongoing headroom/saturation assessments through the Strategist's Current Analysis and Stop/Continue Rule updates.
   - Hypotheses & Coupled Parameters: candidate knobs, ranges, forbidden regions, likely parameter couplings

Fill `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/session.md` before launching. If that file is missing or damaged, read [assets/session-template.md](assets/session-template.md) only to restore the template; do not copy the template into any other path.

4. Check capacity:

   Arrange GPU scheduling explicitly: GPUs, jobs per GPU, and thresholds. Follow [references/workflow.md](references/workflow.md) section 6 for the source priority chain (user > adapter > project docs > memory), runtime slot checks, `total_capacity`, and conservative per-dimension defaults; follow [references/gpu-policy.md](references/gpu-policy.md) for flags.

```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader
python SKILL_DIR/scripts/aet.py gpu-slots --session PROJECT/aet/YYYY-MM-DD/HH-MM-SS
```

Use raw `nvidia-smi` for readable context; use `aet.py gpu-slots` for the normalized slot decision because it parses numeric fields internally and applies the stored policy. Pass `--session` (or `--project-root`) so it reads `meta.gpu_policy`; without a session it falls back to conservative defaults (all GPUs, 1/gpu). Output directory creation happens in Step 6 via `aet.py create-run`.

5. Fill the planned queue before launching:
   **If `projected_ready_after_launch < total_capacity`, run the Strategist transaction before launching.** This is the steady-state invariant and applies at session start. Strategist plans candidates from `session.md`'s objective, hypotheses, and coupled parameters; it does not require completed runs to do so. Do not manually design the initial parameter set yourself.

   Run the three beats: `aet.py strategist-begin` → the spawn call it prints → `aet.py strategist-return ...`. At session start the queue is empty so begin opens a blocking fresh spawn. Because all slots are free, expect Strategist to return at least 2× total_capacity (current_free_slots + total_capacity). Follow strategist-return's `YOU` block to `aet.py queue-add` the returned candidates and update `session.md`, then proceed.

6. Launch experiments:
   - Run `aet.py loop-state` to get the specific run_id → GPU-slot pairings. Its `LAUNCH runs [...] onto GPU id(s) [...]` line names the exact run_ids and GPUs. Treat each GPU-id occurrence as one slot; repeated ids are valid when `max_per_gpu > 1`.
   - Activate each with `aet.py create-run --run-id <id> --gpu-id <gpu>`. It transitions planned → created, creates `runs/<id>/output/`, and prints three labeled lines: `run_dir`, `run_id`, `output_dir`. Use the printed `output_dir` directly.
   - Redirect stdout/stderr to `output_dir/train.log` in the launch command (`> output_dir/train.log 2>&1`).
   - After the process starts, call `aet.py record --status running` so `results.csv` records `start_time`.
   - **Codex**: run the same launch command in one `exec_command` session per experiment. Do not use shell backgrounding.
   - **Claude Code**: use `run_in_background=True` on the Bash tool; you will be notified on completion. Follow [references/claude-code-adapter.md](references/claude-code-adapter.md).
   - Use the standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`.
   - Use plain `python` unless the active environment is wrong. Pass `--gpu_id` explicitly. Use a unique `--output_dir` for every configuration.

7. Record results inline on completion:
   - Verify output directory and metric files exist (runs/<id>/ artifacts).
   - Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort.
   - Determine terminal status: `finished`, `failed`, or `inconclusive`.
   - Call `aet.py record` with status and metrics (terminal records add the run to the pending set in `loop_state.json`).

```bash
python SKILL_DIR/scripts/aet.py record \
  --session /path/to/project/aet/YYYY-MM-DD/HH-MM-SS \
  --run-id 3 \
  --status finished \
  --primary-metric 23.42 \
  --metric-name PSNR \
  --metrics '{"PSNR": 23.42, "SSIM": 0.71}' \
  --annotation "lk=0.05 clean run; candidate peak"
```

8. Update project records and continue:
   - Run `aet.py loop-state` and follow its `YOU` — the routing hub after every record.
   - If `loop-state` prints `APPLY BENCHMARK UPDATES`, update project tables for the listed debt ids, run `aet.py benchmark-ack --run-ids IDS` only after successful writes, then re-run `loop-state`. Partial acknowledgement is allowed.
   - If loop-state routes a Strategist call (`projected_ready_after_launch < total_capacity`), run the transaction and follow its `YOU` to `queue-add` returned candidates. Suppress only for explicit self-evaluatable stop conditions.
   - Unless a stop condition is satisfied, keep `projected_ready_after_launch` at or above total_capacity and launch into free GPU slots immediately.
   - Stop only when the objective is met, budget is exhausted, resources/permissions block continuation, or plateau/exhaustion has been confirmed by two independent Strategist instances per the Default Stopping Rules above.

## AET Helper Calls

Use `scripts/aet.py` as the durable state and safety helper for the tuning loop:

- `init`: create `aet/YYYY-MM-DD/HH-MM-SS/` with `meta.json`, `results.csv`, `session.md`, `loop_state.json`, and `runs/`. `session.md` is rendered from [assets/session-template.md](assets/session-template.md); `loop_state.json` is script-owned. Required: `--project-root`, `--name`, `--objective`, `--process-pattern`. Optional: `--goal max|min` (default `max`), `--runtime claude|codex` (default `claude`), and any GPU policy flags (see `set-policy`).
- `set-policy`: persist the GPU policy into `meta.json` so `gpu-slots`/`loop-state`/`strategist-begin` all compute capacity from one source. Optional: `--session` or `--project-root`, `--gpu-ids`, `--max-per-gpu`, `--max-util`, `--max-memory-used-mb`, `--min-free-memory-mb`, `--process-pattern`. Set it once at/after `init`; re-run only when the policy genuinely changes mid-session.
- `queue-add`: batch-register Strategist candidates as `planned` rows in `results.csv`. Required: `--candidates` (JSON array or file path). Each candidate gets an auto-assigned `run_id`; `queue_id`, `params`, `hypothesis`, `expected_signal`, `rationale`, and `priority` are persisted.
- `queue-drop`: mark `planned` candidates as `dropped` (they never ran). Required: `--run-ids` (comma-separated). Optional: `--reason`.
- `queue-list`: list all `planned` rows sorted by priority. Optional: `--json`.
- `create-run`: activate a `planned` row: create `runs/<id>/` and `runs/<id>/output/`, transition planned → created, and print `run_dir`, `run_id`, `output_dir`. Required: `--run-id` (pointing to a planned row). Optional: `--command`, `--gpu-id`, `--output-dir`, `--log-path`.
- `record`: update a run whenever status or results change. Required: `--run-id`, `--status created|running|finished|failed|inconclusive|superseded`. Optional: `--session` or `--project-root`, `--primary-metric`, `--metric-name`, `--metrics` (JSON string or JSON file), `--gpu-id`, `--output-dir`, `--log-path`, `--annotation`. Use `running` to record `start_time`; terminal statuses record `end_time` and add the run to the pending-run set. Every `finished` record sets `benchmark_status=pending`; other statuses clear it.
- `unique-dir`: choose a non-existing path and optionally create it. Use only when `output_dir` must live outside the session directory. For session-internal run output, use `aet.py create-run` instead.
- `gpu-slots`: estimate available GPU slots. With `--session`/`--project-root` it reads the stored `meta.gpu_policy`; flags override per call. It queries `nvidia-smi`, then prints per-GPU free slots plus a `TOTAL free_slots/total_capacity` footer.
- `loop-state`: the decision panel — call each cycle and each keepalive tick. Counts the planned queue from `results.csv`. Optional: `--session`/`--project-root`, `--runtime` (override only). Prints OK/STATE plus a routed `YOU`/NEXT with specific run_id → GPU pairings, Strategist routing, or wait.
- `strategist-begin`: open a Strategist transaction (Beat 1). Optional: `--session`/`--project-root`, `--runtime` (override only). Snapshots every finished run's evidence version and every pending benchmark marker's version, computes fresh/resume/confirmer + blocking/background, opens `active_strategist_call`, and prints the exact spawn/resume tool call + payload. Refuses if a call is open or benchmark-update debt exists.
- `strategist-return`: close the transaction (Beat 3). Required: `--call-id C`, non-negative `--candidates-count K`, `--benchmark-promotion-run-ids none|IDS`, `--benchmark-reviewed-run-ids none|IDS`. Every fresh invocation also requires `--agent-id`. Promotion ids may reference any unchanged finished evidence captured at begin; reviewed/rejected ids must reference unchanged pending markers captured at begin. Either decision clears that run's unchanged CSV pending marker when present; unlisted markers remain deferred. Promotion also creates durable `pending_benchmark_updates` debt. `--resume-failed` is valid only for a resume call with `K=0`, both selectors `none`, no id, and no presence flags; it consumes neither snapshot.
- `benchmark-ack`: clear durable benchmark-update debt only after the corresponding project table writes succeed. Required: `--run-ids` (unique comma-separated ids from `pending_benchmark_updates`). It verifies the current finished evidence against the debt's `terminal_version`; changed evidence causes refusal, removes the stale debt, and re-marks the current finished run `benchmark_status=pending` for review. Acknowledge successful subsets independently, then re-run `loop-state`.
- `strategist-abort`: last resort to abandon an open call. Required: `--call-id C`, `--reason spawn_failed|unreachable|cancelled`. Clears `active_strategist_call` and, for `unreachable`/`spawn_failed`, the agent id.
- `parse-log`: extract metrics from a log only when structured metrics are unavailable. Positional: `log`. Optional: repeat `--pattern REGEX`.
- `status` / `summarize`: print session path, objective, run counts, status counts, current best, pending benchmark markers, and pending benchmark-update debt.

Session-aware commands (`create-run`, `record`, `status`, and `summarize`) accept `--session`; if omitted, they use the latest session under `--project-root/aet`. Prefer explicit `--session` when multiple sessions may exist or when delegating work to subagents.

## Resource Map

- [references/workflow.md](references/workflow.md): core; read at session start. Carries the full autonomous loop, durable ledger/state schema, run-status and contamination rules, per-cycle GPU capacity rules, project records, and cross-session knowledge.
- Optional project adapters: [AI4M](references/project-adapter-ai4m.md) and [CLIP-Deblur](references/project-adapter-clip-deblur.md). Match by each file's criteria, then follow its project README/benchmark authority, launch conventions, and tuning constraints.
- [references/gpu-policy.md](references/gpu-policy.md): core; read at session start. Holds GPU policy flags and multi-per-GPU conditions; scheduling-source priority, runtime slot checks, `total_capacity`, and defaults remain in `workflow.md` section 6.
- [references/permissions.md](references/permissions.md): read under an approval-gated sandbox or after a sandbox-related block. Covers command-shape/prefix hygiene, narrow pre-approval prefixes, and escalation.
- [references/recovery.md](references/recovery.md): read when re-attaching to an existing on-disk session after a keepalive tick, context compaction, or an explicit continue request. Covers same-context and new-context recovery.
- [references/watchdog.md](references/watchdog.md): read when setting up a keepalive for a long session; skip for short runs.
- [references/subagents.md](references/subagents.md): core; read at session start. Contains the Strategist trigger, transaction, prompt template, and return protocol.
- [references/claude-code-adapter.md](references/claude-code-adapter.md): read at session start under the `claude` runtime. Covers background launches, completion notifications, `CronCreate`, and runtime-specific Strategist calls.
- `scripts/aet.py`: session creation, run scaffolding, GPU policy persistence (`set-policy`) and slot inspection (`gpu-slots`), the loop decision panel (`loop-state`), the Strategist state machine (`strategist-begin`/`strategist-return`/`strategist-abort` over `loop_state.json`), log parsing, result recording, and summaries. The loop commands (`init`, `create-run`, `record`, `set-policy`, `loop-state`, `strategist-begin/return/abort`) print the three-zone `OK/STATE/YOU`; `gpu-slots`, `parse-log`, `unique-dir`, `status`/`summarize` print plain data.
- [assets/session-template.md](assets/session-template.md): source template rendered by `aet.py init` into the session's `session.md`. Read it only to restore a missing or damaged generated file.
- Subagent `experiment-strategist`: returns evidence-linked observations, reusable rules, the next candidate queue, stop/continue updates, queue edits, escape/confirmation need, and Benchmark Review. On the initial call it plans from `session.md` without completed runs. Invoke it inside the three-beat transaction described in [references/subagents.md](references/subagents.md).
- `agents/openai.yaml`: UI metadata only; do not treat it as operational instructions.

Load only the reference file needed for the current decision.

## Subagent Pattern

Delegate analysis and planning to the Strategist so you stay focused on orchestration:
- Strategist: returns seven sections (evidence-linked observations, reusable rules, Ready Queue candidates, stop/continue updates, queue edits, escape/confirmation need, Benchmark Review). Does not write any session file; apply all returned outputs via `aet.py queue-add` / `queue-drop`, `session.md` edits, and promoted benchmark updates.

Invoke it only inside the three-beat transaction (`aet.py strategist-begin` → tool_use → `aet.py strategist-return`). `strategist-begin` prints the exact call to make and the payload; it owns fresh-vs-resume-vs-confirmer and the Strategist agent id.

- **Claude Code**: the printed call is `Agent(subagent_type="experiment-strategist", prompt=..., run_in_background=...)` for a fresh spawn/confirmer, or `SendMessage` targeting the stored id for a resume. Pass the returned id for every fresh invocation. If a resume returns `success:false` without a replacement result, close only with `--candidates-count 0 --resume-failed --benchmark-promotion-run-ids none --benchmark-reviewed-run-ids none` and no id or presence flags.
- **Codex**: for a fresh spawn/confirmer, use the printed `spawn_agent` call and pass its id on return. For a resume, inspect the target with `list_agents`, use `send_message` while running or `followup_task` while idle, then `wait_agent`. If the resume call fails without a replacement result, use the same strict cleanup arguments as Claude Code.

Use the prompt template in [references/subagents.md](references/subagents.md).

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
