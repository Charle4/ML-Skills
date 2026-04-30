---
name: my-auto-experiment-tuning
description: Autonomous, hypothesis-driven experiment and hyperparameter tuning for ML/research codebases. Use when the agent (Codex or Claude Code) needs to run many experiments, tune hyperparameters, manage GPU slots, analyze results, maintain benchmark tables or experiment ledgers, resume an interrupted tuning loop, or coordinate subagents for strategy/result analysis. Supports project-specific adapters while keeping the main workflow generic.
---

# Auto Experiment Tuning

## Operating Model

Run an autonomous loop: understand the project once, create a durable session, launch unique experiment runs, collect metrics, analyze trends, update the project record, then choose the next batch.

Default autonomy contract:
- Treat the user's initial request as the authorization to pursue the stated tuning objective end to end within the active sandbox and approval policy.
- Do not ask the user to approve each batch, each hyperparameter choice, each GPU assignment, or each result update.
- Make local decisions from the written objective, benchmark constraints, project memory, and observed results.
- Ask the user only when the objective is ambiguous, the next action is destructive, required permissions are unavailable, or the run would exceed the user's stated budget/principles.
- Continue filling available slots, collecting results, and planning follow-up batches until a stop condition is reached.
- Do not stop merely because a result improved the current best, looks "good enough", or a local neighborhood has been checked. If the user has not set an explicit budget, keep running until the user intervenes, the explicit target is met, or the plateau/exhaustion rules below are satisfied.
- If the user gives a numeric target such as `PSNR > 25`, treat it as a hard stop condition: continue autonomous batches until a clean run meets or exceeds it, or until the user changes the target or budget.
- If the user says resources are available or asks to "fully tune", actively keep GPUs occupied within the configured contention limits. Prefer launching the next candidate from the queue as soon as any GPU slot opens — do not wait for all running experiments to finish.

Core rules:
- Optimize by hypotheses, not blind grids. State what each batch is testing.
- Analyze hyperparameters as a coupled system. Early batches should deliberately cover interactions among important knobs before local refinement.
- Do not get trapped in single-parameter coordinate tuning. If progress stalls or conclusions conflict, broaden the design space and test interaction hypotheses.
- Keep a durable ledger before relying on context memory.
- Never overwrite an existing output directory, log file, or shared result JSON.
- Treat failed and bad runs as data. Record the failure pattern and avoid repeating it.
- If a standard baseline is far below expected behavior, pause pure hyperparameter sweeps and audit implementation fidelity, preprocessing, objective terms, schedules, seeds, and metric definitions.
- Keep command execution simple: one experiment per command/session. Never use shell `&`, `nohup`, `screen`, or `tmux` unless the user explicitly requests external process management. **Claude Code exception**: use the Bash tool's `run_in_background=True` parameter instead of shell backgrounding — this gives native completion notifications with no shell hacks.
- Never batch multiple experiments in a single `for` loop or shell script. Use one tool call per experiment. To launch several experiments in parallel, issue multiple independent tool calls in the same response turn, not a loop.
- Never use `cd` combined with redirection, pipes, or multi-command chains in a single shell command. Use absolute paths throughout and keep each tool call to a single, unconditional operation. **Claude Code**: `for` loops, `cd`+redirect combos, and multi-command sequences trigger hook interception and require manual approval, breaking the autonomous loop. See `references/claude-code-adapter.md` (Safe Bash Patterns section) for the explicit forbidden/safe list.
- When reading multiple result files or logs, prefer the Read tool for known paths or `grep -r` / `rg` with an explicit directory — not a `for` loop iterating over filenames.
- Launch experiment scripts with a consistent log-managed command shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`. Use plain `python` by default so the command inherits the agent's startup environment; use an explicit interpreter path only when the active environment is wrong.
- Prefer project CLI arguments over editing experiment scripts. If edits are required, read first and keep them scoped.
- Use subagents when the user has requested autonomous tuning with subagent support and the environment permits delegation. Otherwise, execute the same roles locally.

Default stopping rules:
- Stop only for one of these reasons: explicit user stop, explicit metric target met with clean evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable, destructive action required, or a documented plateau/exhaustion decision.
- A plateau/exhaustion decision requires evidence, not intuition: at minimum, record the current best, at least one broadened escape batch, at least one local refinement batch, and at least one clean confirmation if the best will be used as a benchmark.
- When no explicit target or budget is supplied, assume the user wants continued tuning rather than a final answer. Send progress updates, keep launching batches, and avoid a final response while useful experiments remain.
- If the agent is about to end while the target is unmet, write the exact reason to the ledger and include the next batch that should run.

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
   - likely parameter couplings and at least one broad interaction batch before narrow sweeps
   - batch size and per-GPU capacity

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
   - Use the `aet.py unique-dir ... --mkdir` output as the run's `output_dir`.
   - Set `log_path` to a file inside that `output_dir`, normally `output_dir/train.log`; do not use a separate shared log directory.
   - Before each launch, register the run with `aet.py create-run` so the session has a run id, params, command, GPU, output directory, and log path.
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
   - `aet.py create-run` creates `SESSION/runs/<id>/summary.md` from `assets/run-summary-template.md`; update that per-run file for important runs. If the file is missing, restore the template into `SESSION/runs/<id>/summary.md`, not a date-level note.
   - Update the benchmark table or experiment README in the project-required format.
   - Update durable failure/success notes when a reusable rule emerges.
   - Unless a stop condition is satisfied, replenish the queue and launch into any free GPU slots immediately.
   - Stop only when the objective is met, budget is exhausted, resources/permissions block continuation, or plateau/exhaustion has been documented with the evidence required above.

## AET Helper Calls

Use `scripts/aet.py` as the durable state and safety helper for the tuning loop:

- `init`: create `aet/YYYY-MM-DD/HH-MM-SS/` with `meta.json`, `results.csv`, `queue.jsonl`, `observations.md`, `plan.md`, and `runs/`, then print that session path. `plan.md` is rendered from `assets/plan-template.md`; `observations.md` is rendered from `assets/observations-template.md`. These generated files are the canonical files to edit. Required: `--project-root`, `--name`, `--objective`. Optional: `--goal max|min` (default `max`).
- `create-run`: register a run before launch and create `runs/<id>/`. Optional: `--session` or `--project-root` (latest session lookup), `--run-id`, `--name`, `--params` (JSON string or JSON file), `--command`, `--gpu-id`, `--output-dir`, `--log-path`, `--notes`. Prefer explicit `--run-id` when coordinating multiple agents.
- `record`: update a run whenever status or results change. Required: `--run-id`, `--status created|running|finished|failed|inconclusive|superseded`. Optional: `--session` or `--project-root`, `--name`, `--primary-metric`, `--metric-name`, `--metrics` (JSON string or JSON file), `--gpu-id`, `--output-dir`, `--log-path`, `--notes`. Use `running` to record `start_time`; terminal statuses record `end_time`.
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
- `assets/plan-template.md`: source template rendered by `aet.py init` into the session's `plan.md`; read it only to understand or restore the generated plan format.
- `assets/observations-template.md`: source template rendered by `aet.py init` into the session's `observations.md`; read it only to understand or restore observation sections.
- `assets/run-summary-template.md`: source template rendered by `aet.py create-run` into `SESSION/runs/<id>/summary.md`; read it only to understand or restore per-run summary format.
- `agents/experiment-strategist.md`: role prompt for a strategist subagent that plans the next queue of candidate experiments.
- `agents/experiment-runner.md`: role prompt for a runner subagent that launches assigned experiment commands.
- `agents/result-analyzer.md`: role prompt for an analyzer subagent that parses runs, records metrics, and extracts conclusions.
- `agents/openai.yaml`: UI metadata only; do not treat it as operational instructions.

Load only the reference file needed for the current decision.

## Subagent Pattern

For autonomous tuning requests that include subagent support, use these roles when they can run in parallel without blocking the main thread:
- Strategist: reads current ledger and proposes a queue of candidate experiments (plan more than available GPU slots so there is always a ready candidate when a slot opens). Includes per-HP rationale for non-obvious value choices, cited from prior run results. Planning happens whenever the queue runs low, not at synchronous batch boundaries.
- Runner: launches disjoint run commands and reports process/session IDs.
- Analyzer: parses finished runs, updates ledger, extracts failure rules, extracts optimization trajectories (key checkpoints), diagnoses convergence behavior, and accumulates per-HP influence notes in `observations.md`. Main agent receives only the recorded metric and a one-line convergence note — delegate the detailed work to Analyzer to keep main-agent context clean.

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
