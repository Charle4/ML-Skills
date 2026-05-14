---
name: my-auto-experiment-tuning
description: Autonomous, hypothesis-driven experiment and hyperparameter tuning for ML/research codebases. Use when the agent (Codex or Claude Code) needs to run many experiments, tune hyperparameters, manage GPU slots, analyze results, maintain benchmark tables or experiment ledgers, resume an interrupted tuning loop, or coordinate subagents for strategy/result analysis. Supports project-specific adapters while keeping the main workflow generic.
---

# Auto Experiment Tuning

## Operating Model

Run an autonomous loop with the main agent as an experiment orchestrator. The main agent understands the project once, creates one durable session, maintains `plan.md`, manages run lifecycle commands, checks GPU slots, launches work, and coordinates subagents. It does not do inline hyperparameter analysis or candidate strategy when subagent support is available.

Analysis and planning are delegated:
- Analyzer parses finished runs, judges trust, and accumulates per-HP observations. It returns structured data (status, metrics, trust notes, per-HP notes) for the main agent to record and write.
- Strategist reads the durable ledger and proposes the next `Ready Queue` rows.
- Runner is optional; use it only when launch execution benefits from context isolation. By default, the main agent launches assigned runs itself.

Keep the rolling loop moving **without pausing between planning groups**.

### ⛔ Forbidden Anti-Patterns (CRITICAL — read before anything else)

These are the mistakes that break the autonomous loop. **Never do any of these:**

| # | Anti-Pattern | Why It's Wrong | Correct Behavior |
|---|-------------|---------------|-----------------|
| 1 | **Stopping after a batch completes** — collecting results, writing a summary report, and going idle | A batch completing is NOT a stop condition. The loop continues as long as slots exist and unexplored parameter regions remain. | After collecting results: immediately re-check GPU slots, plan next candidates, launch as many ready candidates as current resources allow, THEN give a brief progress note (not a final report). |
| 2 | **Canceling the `/loop` after a sub-phase** — deleting the cron job because "this sub-goal is done" | The loop is the keepalive mechanism for the ENTIRE tuning objective, not one sub-phase. Canceling it kills the autonomous session. | Set the loop once at session start. Only cancel it when the user explicitly ends the session, or a valid stop condition has been recorded and the session is being closed. |
| 3 | **Creating new AET sessions for sub-phases** — running `aet.py init` again when exploring a new parameter direction | One tuning objective = one session. Fragmenting sessions destroys the ledger continuity. | Use the same session for the entire tuning objective. Sub-phases are documented in the same `plan.md` and `observations.md`. |
| 4 | **Using shell `for` loops to create dirs or launch experiments** — `for d in ...; do ...; done` | Hook interception → manual approval → loop broken. | Use `mkdir -p dir1 dir2 dir3 dir4` to create multiple directories in one command. Claude Code: launch with independent `Bash(run_in_background=True)` calls. Codex: launch with one `exec_command` session per experiment; no shell `&`. |
| 5 | **Presenting a "final report" before checking if more work exists** — summarizing results as if the task is done | Unless a stop condition is met (target achieved, budget exhausted, plateau documented), the tuning continues. | After results: check slots → launch more → then (and only then) give a brief status update. Do not frame updates as conclusions. |
| 6 | **Keeping only a same-size "next batch" table** — planning exactly as many candidates as current free slots | This creates idle gaps and forces batch-synchronous thinking. | Maintain `Completed / Recorded`, `Running`, and `Ready Queue` sections in `plan.md`; keep ready candidates strictly greater than current free GPU slots whenever unexplored regions remain. |

### Continuous Rolling Execution (NOT batch-synchronous)

The default operating mode is **asynchronous rolling**: GPU slots are filled continuously, not in synchronized waves. A "batch" is a planning concept, not an execution gate.

**The iron rule**: when you receive a completion notification for ANY experiment:
1. Identify the run from `plan.md` `Running` and verify the output/log paths exist
2. Spawn Analyzer immediately, passing `session_path`, `run_ids`, script paths, and algorithm context
3. After Analyzer returns: call `aet.py record` from returned data; append returned per-HP notes to `observations.md` and trust details to `summary.md`; then move the run from `Running` to `Completed / Recorded` in `plan.md`
4. Check GPU slots
5. If slots are free, launch as many existing `Ready Queue` candidates as current resources allow NOW
6. If ready candidates are not strictly greater than current free slots and no stop condition is met, spawn Strategist and write its returned candidates into `plan.md`
7. Only after steps 1-6: give a brief progress update

**Never wait for all experiments in a batch to finish before acting.** Process each completion as it arrives. Keep all GPU slots occupied at all times.

Do NOT present a summary and go idle after a batch. A batch is not a stop boundary. The only valid stop boundaries are the stop conditions listed below.

### Rolling Queue State Machine

Use `SESSION/plan.md` as a live execution board with three sections:

- `Completed / Recorded`: terminal runs with metrics, trust status, and the follow-up learned from them.
- `Running`: active runs with run id, GPU, output directory, log path, command/session id if available, and expected signal.
- `Ready Queue`: launchable candidates without assigned run ids yet. Keep this count strictly greater than the current free GPU slots whenever useful unexplored regions remain. If free slots = N, maintain at least N+1 ready candidates; if free slots = 0, keep at least one ready candidate unless a valid stop condition is documented.

State transitions:
- Strategist planning adds candidates to `Ready Queue`. Add as many as the evidence justifies, including multi-point grids or factorial groups when useful; do not force a one-finished-run to one-new-run cadence.
- Launching takes one or more `Ready Queue` rows according to current available slots, assigns run id/GPU/output/log fields, registers each with `aet.py create-run`, launches the command, records each accepted process with `aet.py record --status running`, and moves them to `Running`.
- Completion triggers Analyzer (read-only); Analyzer returns structured data (status, metrics, trust note, per-HP notes); the main agent calls `aet.py record`, appends returned notes to `observations.md` and `summary.md` as needed, moves the row to `Completed / Recorded`, re-checks resources, then fills all currently usable slots from `Ready Queue`.
- New evidence may invalidate unlaunched ready rows; the main agent rewrites or removes those rows after Analyzer/Strategist returns and notes the reason in the session ledger.

### Delegation Protocol

Read `references/subagents.md` before spawning or locally emulating a role. Use paths and durable context in prompts; avoid summarizing results for the subagent when it can read the files directly.

| Trigger | Role | Main-agent follow-up |
| ------- | ---- | -------------------- |
| Any run completes | Analyzer | Call `aet.py record` from returned data, append returned notes to `observations.md`/`summary.md`, move row to `Completed / Recorded`, update benchmark if needed |
| `Ready Queue` count <= free slots, or queue is empty, and no stop condition is met | Strategist | Append returned rows to `plan.md`, update Stop/Continue Rule, launch ready rows |
| Launch execution needs context isolation | Runner, optional | Confirm registration/running status, write `Running` row, then handle completion through Analyzer |

When calling subagents, pass `algorithm_context` as 2-5 sentences covering: metric meaning and direction, tuning target, known comparability risks (GPU contention, channel mode differences, etc.), and key parameter couplings. See `references/subagents.md` prompt templates for the full format.

Single-writer rules:
- `plan.md`: main agent only.
- `observations.md`: main agent appends Analyzer-returned per-HP notes; `aet.py record --notes` may append terminal run notes.
- `results.csv`: only through `aet.py record` (main agent calls it based on Analyzer return).
- `runs/<id>/summary.md`: rewritten by `aet.py record`; main agent appends trust-check details from Analyzer return after record.

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
- Delegate detailed trend analysis and next-candidate strategy to Analyzer/Strategist when subagents are available; the main agent applies returned decisions and maintains the lifecycle.
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
   - Read these core references immediately after this file: `references/workflow.md`, `references/subagents.md`, `references/experiment-ledger.md`, `references/gpu-policy.md`, and `references/permissions.md`.
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
   - **Codex**: run the same launch command in one `exec_command` session per experiment. Do not use shell backgrounding. When Codex returns a long-running `session_id`, record `session_id -> run_id/output_dir/log_path` in `plan.md` and poll with `write_stdin`.
   - **Claude Code**: use `run_in_background=True` on the Bash tool; you will be notified on completion and do not need to poll. See `references/claude-code-adapter.md` for the full pattern.
   - Set `workdir` instead of shell `cd`.
   - Use the standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`.
   - Use plain `python` unless the active environment is wrong; then use the correct interpreter path, for example `/path/to/venv/bin/python -u ...`.
   - Pass `--gpu_id`/equivalent explicitly.
   - Use a unique `--output_dir` for every configuration and never reuse an existing output directory.
   - Register the in-output-dir log path with `aet.py create-run --log-path`.

6. Record results immediately through Analyzer:
   - On completion, spawn Analyzer with the session path, run id, project root, script paths, and algorithm context.
   - Analyzer reads files, parses metrics, and returns structured data (status, metrics, trust note, per-HP notes). Analyzer does not call `aet.py record` or write files.
   - The main agent calls `aet.py record` based on Analyzer's returned fields, appends returned notes to `observations.md` and `summary.md`, and moves the run row in `plan.md`.

```bash
# Main agent calls aet.py record after Analyzer returns:
python SKILL_DIR/scripts/aet.py record \
  --session /path/to/project/aet/YYYY-MM-DD/HH-MM-SS \
  --run-id 3 \
  --status finished \
  --primary-metric 23.42 \
  --metric-name PSNR \
  --metrics '{"PSNR": 23.42, "SSIM": 0.71}' \
  --notes "lk=0.05 clean run; candidate peak"
```

7. Update project records and continue:
   - Summarize the session with `aet.py summarize`.
   - `aet.py create-run` creates `SESSION/runs/<id>/summary.md` from `assets/run-summary-template.md`, and `aet.py record` rewrites it when metrics/status change. Update that per-run file for important runs after the terminal `record`. If the file is missing, restore the template into `SESSION/runs/<id>/summary.md`, not a date-level note.
   - Update the benchmark table or experiment README in the project-required format.
   - Move completed runs from `Running` to `Completed / Recorded`.
   - If `Ready Queue` count is not strictly greater than current free GPU slots and no stop condition is met, spawn Strategist and append its returned candidates. The number added can be 0, 1, or many.
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
- `references/experiment-ledger.md`: core; read at session start for durable state schema and what to record after each run.
- `references/project-adapter-*.md`: optional project adapters. Each adapter should state match criteria at the top and point to the authoritative project README, benchmark docs, launch conventions, and known tuning constraints.
- `references/gpu-policy.md`: core; read at session start. GPU slot defaults (1 per GPU, cap 3, util ceiling 95%), configurable parameters (`gpu_ids`, `max_per_gpu`, memory headroom, `max_util`), helper CLI mappings, and override priority (user > adapter > README > memory).
- `references/permissions.md`: core; read at session start. Covers sandbox permission model, approved command-prefix patterns, recommended pre-approvals, and what always requires confirmation.
- `references/watchdog.md`: read when setting up a keepalive for a long session (Claude Code `/loop` or external cron for Codex). Not needed for short runs.
- `references/subagents.md`: core; read at session start (already listed in Quick Start step 1). Contains trigger rules, prompt templates for Analyzer/Strategist/Runner, and the post-return protocols the main agent must follow after each subagent call.
- `references/claude-code-adapter.md`: **Claude Code only** — read at session start (already listed in Quick Start step 1). Covers `run_in_background`, completion notifications, `/loop`, and subagent differences vs Codex.
- `scripts/aet.py`: session creation, run scaffolding, normalized GPU slot inspection (`gpu-slots`), unique directory creation, log parsing, result recording, and summaries.
- `assets/plan-template.md`: source template rendered by `aet.py init` into the session's `plan.md`; it defines the live execution board (`Completed / Recorded`, `Running`, `Ready Queue`) and rolling queue invariant. Read it only to understand or restore the generated plan format.
- `assets/observations-template.md`: source template rendered by `aet.py init` into the session's `observations.md`; read it only to understand or restore observation sections.
- `assets/run-summary-template.md`: source template rendered by `aet.py create-run` into `SESSION/runs/<id>/summary.md`; read it only to understand or restore per-run summary format.
- Subagent `experiment-strategist`: plans the next queue of candidate experiments. Claude Code: invoke via `Agent(subagent_type="experiment-strategist", prompt="...")`; Codex: invoke via `spawn_agent(agent_type="experiment-strategist", message="...")`.
- Subagent `experiment-runner`: launches assigned experiment commands. Claude Code: invoke via `Agent(subagent_type="experiment-runner", prompt="...")`; Codex: invoke via `spawn_agent(agent_type="experiment-runner", message="...")`.
- Subagent `result-analyzer`: parses runs, judges trust, and returns structured record data for the main agent to write. Claude Code: invoke via `Agent(subagent_type="result-analyzer", prompt="...")`; Codex: invoke via `spawn_agent(agent_type="result-analyzer", message="...")`.
- `agents/openai.yaml`: UI metadata only; do not treat it as operational instructions.

Load only the reference file needed for the current decision.

## Subagent Pattern

For autonomous tuning requests that include subagent support, use these roles to keep the main thread focused on orchestration:
- Strategist: reads current ledger and proposes `Ready Queue` candidates. It does not write `plan.md`; the main agent applies its returned rows.
- Runner: optionally launches disjoint run commands when context isolation is useful. It receives preassigned run ids, GPU ids, output directories, and commands.
- Analyzer: parses finished runs, judges trust, and accumulates per-HP notes. Read-only — does not call `aet.py record` or write files. Returns structured data (status, metrics, trust note, per-HP notes, benchmark-update flag) for the main agent to record and write.

**Claude Code**: spawn via the `Agent` tool using the registered subagent types — `result-analyzer`, `experiment-strategist`, `experiment-runner`. Use Claude Code syntax such as `Agent(subagent_type="experiment-strategist", prompt="...")`. Pass only session-specific context in the `prompt` parameter; the subagent's role instructions are already loaded from its own system prompt. See `references/subagents.md` for the prompt template for each role.

**Codex**: spawn via `spawn_agent` using the registered custom agent types — `result-analyzer`, `experiment-strategist`, `experiment-runner`. Use Codex syntax such as `spawn_agent(agent_type="experiment-strategist", message="...")`. Pass only session-specific context in the `message` parameter; the subagent's role instructions are already loaded from its registered Codex custom agent file. Use `send_input`, `wait_agent`, and `close_agent` to coordinate; `multi_tool_use.parallel` is for parallel tool calls, not subagent creation.

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
