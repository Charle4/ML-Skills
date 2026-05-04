---
name: my-auto-experiment-tuning
description: Autonomous, hypothesis-driven experiment and hyperparameter tuning for ML/research codebases. Use when the agent (Codex or Claude Code) needs to run many experiments, tune hyperparameters, manage GPU slots, analyze results, maintain benchmark tables or experiment ledgers, resume an interrupted tuning loop, or coordinate subagents for strategy/result analysis. Supports project-specific adapters while keeping the main workflow generic.
---

# Auto Experiment Tuning

## Operating Model

Run an autonomous loop: understand the project once, create a durable session, keep a rolling candidate queue, launch unique experiment runs, collect metrics, analyze trends, update the project record, then replenish the queue — **without pausing between planning groups**.

### ⛔ Forbidden Anti-Patterns (CRITICAL — read before anything else)

These are the mistakes that break the autonomous loop. **Never do any of these:**

| # | Anti-Pattern | Why It's Wrong | Correct Behavior |
|---|-------------|---------------|-----------------|
| 1 | **Stopping after a batch completes** — collecting results, writing a summary report, and going idle | A batch completing is NOT a stop condition. The loop continues as long as slots exist and unexplored parameter regions remain. | After collecting results: immediately re-check GPU slots, plan next candidates, launch as many ready candidates as current resources allow, THEN give a brief progress note (not a final report). |
| 2 | **Canceling the `/loop` after a sub-phase** — deleting the cron job because "this sub-goal is done" | The loop is the keepalive mechanism for the ENTIRE tuning objective, not one sub-phase. Canceling it kills the autonomous session. | Set the loop once at session start. Only cancel it when the user explicitly ends the session, or a valid stop condition has been recorded and the session is being closed. |
| 3 | **Creating new AET sessions for sub-phases** — running `aet.py init` again when exploring a new parameter direction | One tuning objective = one session. Fragmenting sessions destroys the ledger continuity. | Use the same session for the entire tuning objective. Sub-phases are documented in the same `plan.md` and `observations.md`. |
| 4 | **Using shell `for` loops to create dirs or launch experiments** — `for d in ...; do ...; done` | Hook interception → manual approval → loop broken. | Use `mkdir -p dir1 dir2 dir3 dir4` to create multiple directories in one command. Launch experiments with multiple independent `Bash(run_in_background=True)` calls in the same turn. |
| 5 | **Presenting a "final report" before checking if more work exists** — summarizing results as if the task is done | Unless a stop condition is met (target achieved, budget exhausted, plateau documented), the tuning continues. | After results: check slots → launch more → then (and only then) give a brief status update. Do not frame updates as conclusions. |
| 6 | **Keeping only a same-size "next batch" table** — planning exactly as many candidates as current free slots | This creates idle gaps and forces batch-synchronous thinking. | Maintain `Completed / Recorded`, `Running`, and `Ready Queue` sections in `plan.md`; keep ready candidates strictly greater than current free GPU slots whenever unexplored regions remain. |

### Continuous Rolling Execution (NOT batch-synchronous)

The default operating mode is **asynchronous rolling**: GPU slots are filled continuously, not in synchronized waves. A "batch" is a planning concept, not an execution gate.

**The iron rule**: when you receive a completion notification for ANY experiment:
1. Collect the result immediately
2. Record it
3. Move the run from `Running` to `Completed / Recorded` in `plan.md`
4. Check GPU slots
5. If slots are free AND unexplored parameter regions remain → launch as many `Ready Queue` candidates as current resources allow NOW
6. If ready candidates are not strictly greater than current free slots → analyze results and append as many new candidates as the evidence justifies NOW
7. Only after steps 1-6: give a brief status update

**Never wait for all experiments in a batch to finish before acting.** Process each completion as it arrives. Keep all GPU slots occupied at all times.

Do NOT present a summary and go idle after a batch. A batch is not a stop boundary. The only valid stop boundaries are the stop conditions listed below.

### Rolling Queue State Machine

Use `SESSION/plan.md` as a live execution board with three sections:

- `Completed / Recorded`: terminal runs with metrics, trust status, and the follow-up learned from them.
- `Running`: active runs with run id, GPU, output directory, log path, command/session id if available, and expected signal.
- `Ready Queue`: launchable candidates without assigned run ids yet. Keep this count strictly greater than the current free GPU slots whenever useful unexplored regions remain. If free slots = N, maintain at least N+1 ready candidates; if free slots = 0, keep at least one ready candidate unless a valid stop condition is documented.

State transitions:
- Planning adds candidates to `Ready Queue`. Add as many as the analysis justifies, including multi-point grids or factorial groups when useful; do not force a one-finished-run to one-new-run cadence.
- Launching takes one or more `Ready Queue` rows according to current available slots, assigns run id/GPU/output/log fields, registers each with `aet.py create-run`, launches the command, records each accepted process with `aet.py record --status running`, and moves them to `Running`.
- Completion records metrics with `aet.py record`, moves the row to `Completed / Recorded`, updates `observations.md`, re-checks resources, then fills all currently usable slots from `Ready Queue`.
- New evidence may invalidate unlaunched ready rows; rewrite or remove those rows and note the reason in `observations.md`.

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
- Keep a durable ledger before relying on context memory.
- Never overwrite an existing output directory, log file, or shared result JSON.
- Treat failed and bad runs as data. Record the failure pattern and avoid repeating it.
- If a standard baseline is far below expected behavior, pause pure hyperparameter sweeps and audit implementation fidelity, preprocessing, objective terms, schedules, seeds, and metric definitions.
- Prefer project CLI arguments over editing experiment scripts. If edits are required, read first and keep them scoped.
- Use subagents when the user has requested autonomous tuning with subagent support and the environment permits delegation. Otherwise, execute the same roles locally.

### Shell Command Safety (Claude Code — CRITICAL)

Claude Code hooks intercept complex shell structures, requiring manual approval and breaking the autonomous loop. Follow these rules strictly:

**Forbidden — never use these patterns:**
- `for d in ...; do ...; done` — shell for loop (any variant)
- `cd /path && python ... > log.txt` — cd combined with redirection or other commands
- `cmd1; echo "---"; cmd2` — multi-command sequences with separators
- `python -c "..."` with `#` comments inside the quoted Python string

**Safe replacements:**
- Multiple directories: `mkdir -p /abs/path/dir1 /abs/path/dir2 /abs/path/dir3` (space-separated, one command)
- Launch experiments: multiple independent `Bash(run_in_background=True)` tool calls in the same response turn — never a loop. Use the exact command shape:
  ```
  python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1
  ```
  Use plain `python` by default so the command inherits the agent's startup environment; use an explicit interpreter path only when the active environment is wrong. Pass `--gpu_id` explicitly.
- Read logs: `grep -r "pattern" /abs/path/results/` or the Read tool for known paths — never a `for f in ...` loop
- Always use absolute paths — no `cd` needed

Full details in `references/claude-code-adapter.md` (Safe Bash Patterns section).

### Default Stopping Rules

- Stop only for one of these reasons: explicit user stop, explicit metric target met with clean evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable, destructive action required, or a documented plateau/exhaustion decision.
- A plateau/exhaustion decision requires evidence, not intuition: at minimum, record the current best, at least one broadened escape group, at least one local refinement group, and at least one clean confirmation if the best will be used as a benchmark.
- When no explicit target or budget is supplied, assume the user wants continued tuning rather than a final answer. Send progress updates, keep filling available slots, and avoid a final response while useful experiments remain.
- If the agent is about to end while the target is unmet, write the exact reason to the ledger and include the next ready candidates or search group that should run when resources permit.

**A batch completing is never a stop condition. A sub-phase target being met is never a stop condition. The loop must not be canceled for these reasons.**

## Runtime Detection

Determine which agent runtime you are before proceeding:

- **Codex**: Your active instructions identify you as "Codex, a coding agent based on GPT-5". Skill installed at `~/.codex/skills/my-auto-experiment-tuning/`. Shell sessions are the primary execution path; no `run_in_background`, no background notifications, no `/loop`.
- **Claude Code**: Your system prompt says "You are Claude Code, Anthropic's official CLI for Claude." Skill installed at `~/.claude/skills/my-auto-experiment-tuning/`. You have `run_in_background=True` on Bash, background-completion notifications, and the `/loop` timer. Read `references/claude-code-adapter.md` immediately after this file.

Throughout this skill, `SKILL_DIR` means the install root above. Substitute it when running `aet.py` commands.

## Quick Start

1. Read project-local operating context:
   - Read these core references immediately after this file: `references/workflow.md`, `references/search-strategies.md`, `references/experiment-ledger.md`, and `references/gpu-policy.md`.
   - `AGENTS.md`, `CLAUDE.md`, experiment README files, and existing memory/notes if present.
   - Check `references/project-adapter-*.md` for project-specific adapters. Each adapter should state its match criteria near the top, such as project root paths, repository markers, or required files. If one matches the current project, read it before planning.
   - **Semantic search — don't trust filenames alone**: After reviewing file names, use your available search tool (`grep`, `rg`, `search`, or equivalent) to scan all reference files for keywords from the actual task: project root path fragments, script names, method names, metric names, and parameter names the user mentioned. If any file matches, read it fully. This step takes seconds and prevents missing critical tuning rules that happen to live in a file whose name looks irrelevant.
   - **Claude Code only**: read `references/claude-code-adapter.md` now to understand how your execution model differs from Codex.

2. Create or resume a session:

```bash
python SKILL_DIR/scripts/aet.py init \
  --project-root /path/to/project \
  --name short-task-name \
  --objective "maximize PSNR under benchmark ordering constraints" \
  --goal max
```

Use `aet/` inside the project as the canonical state root. This makes the loop recoverable after context compaction.
The `init` command prints the exact session directory, normally `PROJECT/aet/YYYY-MM-DD/HH-MM-SS`; treat that directory as the only session state location.
`init` already creates `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/plan.md` from `assets/plan-template.md` and `observations.md` from `assets/observations-template.md`. Edit those generated files in place. Do not create ad hoc plan or observation files such as `PROJECT/aet/YYYY-MM-DD/*.md` or `PROJECT/aet/*.md`.

3. Write a plan before launching:
   - target metric and direction
   - current best/baseline
   - explicit target threshold if the user provided one
   - current stop condition and minimum evidence required before stopping
   - constraints that make a result untrustworthy
   - candidate knobs, ranges, and forbidden regions
   - likely parameter couplings and at least one broad interaction group before narrow sweeps
   - per-GPU capacity, current free slots, and the `Ready Queue` invariant: ready candidates must be strictly greater than free slots while useful search remains
   - the live execution board: `Completed / Recorded`, `Running`, and `Ready Queue`

Fill `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/plan.md` before launching. If that file is missing or damaged, read `assets/plan-template.md` only to restore the template into the same session `plan.md`; do not copy the template into any other path.

4. Check capacity and create unique run output directories:

   Read `references/gpu-policy.md` for slot defaults and configurable parameters. Default: 1 experiment per GPU, hard cap 3, utilization ceiling 95%. Override via user instruction, project adapter, README, or project memory — in that priority order.

```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader
python SKILL_DIR/scripts/aet.py gpu-slots
python SKILL_DIR/scripts/aet.py unique-dir /path/to/project/experiments/results/dse_example/run_name --mkdir
```

Use raw `nvidia-smi` for human-readable/agent-readable context; use `aet.py gpu-slots` for the normalized slot decision because it parses numeric fields internally and applies configured filters.

5. Launch experiments:
   - Select candidates from `plan.md` `Ready Queue`, highest priority first, for as many free slots as current resource checks allow. Assign run id/GPU/output/log fields only when launching.
   - Use the `aet.py unique-dir ... --mkdir` output as the run's `output_dir`.
   - Set `log_path` to a file inside that `output_dir`, normally `output_dir/train.log`; do not use a separate shared log directory.
   - Before each launch, register the run with `aet.py create-run` so the session has a run id, params, command, GPU, output directory, and log path.
   - `create-run` appends a recovery row to `queue.jsonl`; do not treat `queue.jsonl` as the live `Ready Queue`.
   - After the process starts, call `aet.py record --status running` without routine notes so `results.csv` records `start_time`.
   - Move each launched row from `Ready Queue` to `Running` in `plan.md`.
   - **Codex**: one foreground command per long-running experiment so Codex receives one session per run.
   - **Claude Code**: use `run_in_background=True` on the Bash tool; you will be notified on completion and do not need to poll. See `references/claude-code-adapter.md` for the full pattern.
   - Set `workdir` instead of shell `cd`.
   - Use the standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`.
   - Use plain `python` unless the active environment is wrong; then use the correct interpreter path, for example `/path/to/venv/bin/python -u ...`.
   - Pass `--gpu_id`/equivalent explicitly.
   - Use a unique `--output_dir` for every configuration and never reuse an existing output directory.
   - Register the in-output-dir log path with `aet.py create-run --log-path`.

6. Record results immediately:
   - If the project produced structured metrics, pass them directly to `aet.py record --metrics`.
   - If only logs contain metrics, run `aet.py parse-log <log>` first, inspect the extracted JSON, then pass clean metrics to `aet.py record`.

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

7. Analyze, update project records, and continue:
   - Summarize the session with `aet.py summarize`.
   - `aet.py create-run` creates `SESSION/runs/<id>/summary.md` from `assets/run-summary-template.md`, and `aet.py record` rewrites it when metrics/status change. Update that per-run file for important runs after the terminal `record`. If the file is missing, restore the template into `SESSION/runs/<id>/summary.md`, not a date-level note.
   - Update the benchmark table or experiment README in the project-required format.
   - Update durable failure/success notes when a reusable rule emerges.
   - Move completed runs from `Running` to `Completed / Recorded`; append several new `Ready Queue` candidates when analysis exposes useful regions. The number added can be 0, 1, or many.
   - Unless a stop condition is satisfied, keep `Ready Queue` count strictly greater than current free GPU slots and launch into any free GPU slots immediately.
   - Stop only when the objective is met, budget is exhausted, resources/permissions block continuation, or plateau/exhaustion has been documented with the evidence required above.

## AET Helper Calls

Use `scripts/aet.py` as the durable state and safety helper for the tuning loop:

- `init`: create `aet/YYYY-MM-DD/HH-MM-SS/` with `meta.json`, `results.csv`, `queue.jsonl`, `observations.md`, `plan.md`, and `runs/`, then print that session path. `plan.md` is rendered from `assets/plan-template.md`; `observations.md` is rendered from `assets/observations-template.md`. These generated files are the canonical files to edit. Required: `--project-root`, `--name`, `--objective`. Optional: `--goal max|min` (default `max`).
- `create-run`: register a run before launch, create `runs/<id>/`, and append a recovery snapshot to `queue.jsonl`. Optional: `--session` or `--project-root` (latest session lookup), `--run-id`, `--name`, `--params` (JSON string or JSON file), `--command`, `--gpu-id`, `--output-dir`, `--log-path`, `--notes`. Prefer explicit `--run-id` when coordinating multiple agents. `queue.jsonl` is not the live `Ready Queue`; manage ready candidates in `plan.md`.
- `record`: update a run whenever status or results change. Required: `--run-id`, `--status created|running|finished|failed|inconclusive|superseded`. Optional: `--session` or `--project-root`, `--name`, `--primary-metric`, `--metric-name`, `--metrics` (JSON string or JSON file), `--gpu-id`, `--output-dir`, `--log-path`, `--notes`. Use `running` to record `start_time`; terminal statuses record `end_time`. `--notes` appends to `observations.md`, so omit it for routine `running` updates and use it for terminal trust/failure notes.
- `unique-dir`: choose a non-existing output directory. Positional: `path`. Optional: `--mkdir`; use it before launching so shell redirection to `<output_dir>/train.log` succeeds.
- `gpu-slots`: estimate available GPU slots. Optional: `--kind default|light|heavy` (default `default`), `--capacity N`, `--saturated-util N` (default `95`), `--process-pattern REGEX` (default `python`), `--gpu-ids 0,1,3`, `--max-memory-used-mb N`, `--min-free-memory-mb N`, `--allow-over-cap`, `--json`. It internally queries `nvidia-smi` with machine-readable numeric output, then reports utilization, memory used/total/free, running process count, capacity, and free slots.
- `parse-log`: extract metrics from a log only when structured metrics are unavailable. Positional: `log`. Optional: repeat `--pattern REGEX`; each pattern should have named groups `name` and `value`, or one numeric group. Treat regex output as a draft and inspect it before recording.
- `status` / `summarize`: print session path, objective, run counts, status counts, and current best finished result. Optional: `--project-root`, `--session`, `--goal max|min`.

Session-aware commands (`create-run`, `record`, `status`, and `summarize`) accept `--session`; if omitted, they use the latest session under `--project-root/aet`. Prefer explicit `--session` when multiple sessions may exist or when delegating work to subagents.

## Resource Map

- `references/workflow.md`: core; read at session start for the full autonomous loop and recovery protocol.
- `references/search-strategies.md`: core; read at session start for choosing grids, coordinate descent, boundary expansion, confirmation runs, and stopping rules.
- `references/experiment-ledger.md`: core; read at session start for durable state schema and what to record after each run.
- `references/project-adapter-*.md`: optional project adapters. Each adapter should state match criteria at the top and point to the authoritative project README, benchmark docs, launch conventions, and known tuning constraints.
- `references/gpu-policy.md`: core; read at session start. GPU slot defaults (1 per GPU, cap 3, util ceiling 95%), configurable parameters (`gpu_ids`, `max_per_gpu`, memory headroom, `max_util`), helper CLI mappings, and override priority (user > adapter > README > memory).
- `references/permissions.md`: read if a command is blocked by sandbox policy, or before starting a long Codex autonomous run. Covers approved command-prefix patterns and what always requires confirmation.
- `references/watchdog.md`: read when setting up a keepalive for a long session (Claude Code `/loop` or external cron for Codex). Not needed for short runs.
- `references/subagents.md`: read before spawning or coordinating Strategist/Runner/Analyzer subagents. Contains the role prompts to include in each subagent task.
- `references/claude-code-adapter.md`: **Claude Code only** — read at session start (already listed in Quick Start step 1). Covers `run_in_background`, completion notifications, `/loop`, and subagent differences vs Codex.
- `scripts/aet.py`: session creation, run scaffolding, normalized GPU slot inspection (`gpu-slots`), unique directory creation, log parsing, result recording, and summaries.
- `assets/plan-template.md`: source template rendered by `aet.py init` into the session's `plan.md`; it defines the live execution board (`Completed / Recorded`, `Running`, `Ready Queue`) and rolling queue invariant. Read it only to understand or restore the generated plan format.
- `assets/observations-template.md`: source template rendered by `aet.py init` into the session's `observations.md`; read it only to understand or restore observation sections.
- `assets/run-summary-template.md`: source template rendered by `aet.py create-run` into `SESSION/runs/<id>/summary.md`; read it only to understand or restore per-run summary format.
- `agents/experiment-strategist.md`: role prompt for a strategist subagent that plans the next queue of candidate experiments.
- `agents/experiment-runner.md`: role prompt for a runner subagent that launches assigned experiment commands.
- `agents/result-analyzer.md`: role prompt for an analyzer subagent that parses runs, records metrics, and extracts conclusions.
- `agents/openai.yaml`: UI metadata only; do not treat it as operational instructions.

Load only the reference file needed for the current decision.

## Subagent Pattern

For autonomous tuning requests that include subagent support, use these roles when they can run in parallel without blocking the main thread:
- Strategist: reads current ledger and proposes `Ready Queue` candidates (keep ready count strictly greater than current free GPU slots, and generally no more than about 2x configured capacity unless the method tolerates a larger queue). Includes per-HP rationale for non-obvious value choices, cited from prior run results. Planning happens whenever the queue runs low, not at synchronous batch boundaries.
- Runner: launches disjoint run commands, moves assigned ready rows to `Running` when given write ownership, and reports process/session IDs.
- Analyzer: parses finished runs, updates ledger, moves rows to `Completed / Recorded` when given write ownership, extracts failure rules, extracts optimization trajectories (key checkpoints), diagnoses convergence behavior, and accumulates per-HP influence notes in `observations.md`. Main agent receives only the recorded metric and a one-line convergence note — delegate the detailed work to Analyzer to keep main-agent context clean.

Before spawning a subagent, read the matching `agents/*.md` role prompt and include its instructions in the subagent task. If delegation is useful but no subagent tool is available, use the matching role prompt as a local checklist.

**Codex**: use `spawn_agent` only when the user explicitly requested subagents, delegation, or parallel agent work. Give each subagent a bounded write scope and tell it that other agents may be working in the same codebase. Do not assign the critical-path blocker to a subagent if the main agent needs the result immediately. Use `send_input`, `wait_agent`, and `close_agent` to coordinate; `multi_tool_use.parallel` is for parallel tool calls, not subagent creation.

**Claude Code**: use the `Agent` tool to spawn subagents. Multiple independent agents can be launched in the same message. Claude Code subagents also support `run_in_background=True`; see `references/claude-code-adapter.md` for coordination patterns.

If delegation is not authorized, perform the same three roles sequentially in the main thread.

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
