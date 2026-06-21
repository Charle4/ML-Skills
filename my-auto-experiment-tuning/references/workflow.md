# Workflow

Read this file at session start. It covers the full autonomous loop, the durable ledger/state schema, and the GPU capacity rules needed every cycle.

## 1. Autonomy Contract

After the user states the tuning target, benchmark setting, constraints, and budget/principles, continue without asking for approval at each iteration. You own the loop:
- infer the current state
- keep a queue of launchable candidates as `planned` rows in `results.csv`
- launch experiments within allowed permissions
- monitor and collect results
- update lifecycle ledgers and benchmark docs
- delegate result analysis and candidate planning, then apply returned queue changes

Escalate to the user only for destructive operations, ambiguous goals, missing required permissions, budget changes, or actions outside the active sandbox/approval policy.

Default duration semantics:
- Treat autonomous tuning as a long-running job, not a short investigation. If the user asks for broad tuning, abundant GPU use, or a target such as `PSNR > 25`, expect tens to hundreds of runs and possibly multi-day operation.
- Do not end after 1-3 planning groups just because a plausible local best was found. A local best is a signal for the next queue update, not a stopping reason.
- If no explicit run or wall-clock budget is provided, assume the budget is open-ended until the user intervenes or the target is cleanly met.
- Keep all usable GPU slots occupied within the configured contention limits. When any run finishes, immediately identify it, record inline: verify output files, parse metrics in priority order (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record` (which adds the terminal run to the pending set), then `aet.py loop-state` to re-check resources and launch as many `planned` candidates as the now-free slots allow — do not wait for other running experiments to finish first.
- Keep the `planned` row count at or above total_capacity (see section 6) whenever useful unexplored regions remain. Run the Strategist transaction whenever count drops below total_capacity.
- If the system forces a final response before the target is met, report the next planned candidates or search group and the reason continuation is blocked; do not present a local best as final.

## 2. Context Pass

Read the minimum files that define the experiment contract:
- repository agent instructions
- experiment README or benchmark docs
- target script argparse/config definitions
- existing run ledgers, result tables, or project memory

Do not repeatedly reread large files after extracting stable rules. Write durable summaries to `session.md` or the project's memory mechanism.

## 3. Session Setup and Ledger Schema

Keep a durable ledger as the ground truth. Do not rely on chat context for completed runs.

Create one `aet/YYYY-MM-DD/HH-MM-SS/` session per tuning objective.
This two-level timestamped directory is the canonical session root. Store session files inside it, not directly under `aet/` or `aet/YYYY-MM-DD/`.

Required session fields:
- objective and metric direction
- explicit target threshold, if any
- project root
- target scripts/commands
- known baselines and current best results
- run trust constraints, such as GPU contention limits
- budget: max runs, wall time, or `open-ended until target/user stop`
- minimum stopping evidence: required broad escape groups, refinements, confirmations, and minimum run count before the Strategist may declare plateau — these are inputs for the Strategist to evaluate, not conditions you check

Use:

```bash
python SKILL_DIR/scripts/aet.py init --project-root PROJECT --name NAME --objective OBJECTIVE --goal max --process-pattern 'SCRIPT_FILENAME_REGEX'
```

`--process-pattern` is required: a regex that uniquely identifies this session's experiment processes in `ps` output (e.g. the script filename `'exp_dip_deblur\\.py'`). Without it, `loop-state` cannot detect experiments that finished without a terminal record. See `references/gpu-policy.md` for guidance.

Capture the printed session path. `aet.py init` creates `session.md` from `assets/session-template.md` in that exact directory; edit that generated file directly.

### Session Files

`aet/YYYY-MM-DD/HH-MM-SS/` contains:
- `meta.json`: objective, metric direction, project root, creation time, `runtime` default, and `gpu_policy`
- `session.md`: the single narrative ledger — `Target & Constraints`, `Hypotheses & Coupled Parameters`, `Reusable Rules`, `Current Analysis`, `Stop/Continue Rule`, `Final Analysis`
- `results.csv`: one row per run, including the launchable queue (`planned` rows). Columns: `run_id`, `queue_id`, `status`, `params`, `hypothesis`, `priority`, `gpu_id`, `primary_metric`, `metric_name`, `metrics`, `output_dir`, `log_path`, `command`, `start_time`, `end_time`, `annotation`, `goal`
- `loop_state.json`: script-owned Strategist state machine — pending run set, `strategist_agent_id`, `active_strategist_call`, `pending_exhaustion_confirmation`, `exhaustion_confirmed`, `agent_history`. Read it via `aet.py loop-state`; changed only by `aet.py record` and `aet.py strategist-begin/return/abort`. `exhaustion_confirmed` is set to `true` by `strategist-return` on `CONFIRMED_EXHAUSTION`; `loop-state` then routes `SESSION EXHAUSTED` instead of a new Strategist call. `strategist-begin` resets it to `false` if you explicitly continue.
- `runs/<id>/`: per-run params, command, and metrics

Only this timestamped session directory holds session ledger files. Do not write narrative, observations, or run notes directly under `aet/` or the date-level directory `aet/YYYY-MM-DD/`. If a task needs narrative or observations, update `aet/YYYY-MM-DD/HH-MM-SS/session.md`. The one allowed file at the `aet/` root is the optional cross-session durable-rules file `aet/knowledge.md` (see section 12); it is not session-scoped, so it does not belong inside a timestamped session directory.

### Run Status Values

- `planned`: candidate registered in `results.csv` (the launchable queue) but no GPU assigned and no run directory created yet
- `created`: run directory exists but command has not started
- `running`: process is active
- `finished`: completed and metrics are trustworthy
- `failed`: command failed or output is unusable
- `inconclusive`: completed but contaminated, mismatched, or not comparable
- `superseded`: no longer relevant because a later clean run replaces it
- `dropped`: a `planned` candidate invalidated before launch (never ran)

## 4. AET Helper Contract

Use `aet.py` for objective run bookkeeping, not for semantic search decisions:
- `results.csv` is the single source of truth for both the launchable queue and run status/metrics. `planned` rows are the queue; terminal rows are history. Do not expect `aet.py` to choose, prioritize, or retire candidates — that is the Strategist's semantic decision, registered via `queue-add`/`queue-drop`.
- `loop_state.json` is the source of truth for the Strategist state machine (pending set, agent id, open call, exhaustion handshake). Read it via `aet.py loop-state`; change it only via `aet.py record` and `aet.py strategist-begin/return/abort`.
- `runs/<id>/params.json`, `metrics.json`, and `command.sh` are per-run objective artifacts. Do not create parallel run-note files.

Helper call ownership for each run:
- Use `aet.py queue-add` to register one or more Strategist candidates as `planned` rows in `results.csv`. Each gets a `queue_id`, its `params`, `hypothesis`, and `priority`; no GPU or run directory yet.
- Use `aet.py create-run --run-id <id>` before launching any experiment. It points at an existing `planned` row, creates `runs/<id>/` and `runs/<id>/output/`, writes objective artifacts, activates the row `planned` → `created`, and prints `run_dir`, `run_id`, and `output_dir` as labeled lines.
- Use `aet.py record --status running` after the process starts so `results.csv` records `start_time`.
- Use `aet.py record` again for terminal statuses and metrics. Terminal records update `end_time`, `metrics.json`, and `results.csv`.
- Use `aet.py queue-drop --run-ids <id>` to invalidate a `planned` candidate before it launches (`planned` → `dropped`).
- `record --annotation` stores a trust note in the run's `annotation` column. Use it mainly for terminal statuses or important anomalies; omit it on routine `running` transitions.

## 5. Planning and Queue Invariant

The launchable queue is the set of `planned` rows in `results.csv`. The Strategist owns candidate selection and returns JSON candidates; you register them with `aet.py queue-add` (each becomes a `planned` row carrying `params`, `hypothesis`, and `priority`). You do not hand-author the queue and there is no plan file to edit.

Keep enough `planned` rows that their count stays >= total_capacity after the next launch wave fills the free slots (target ≈ current_free_slots + total_capacity; = 2× total_capacity at session start). The narrative context for the queue — objective, coupled parameters, current analysis, stop/continue rule — lives in `session.md`.

Prefer candidate groups that distinguish hypotheses. The Strategist owns detailed candidate selection.

**Before proceeding to section 7**: if the `planned` row count < total_capacity, run the Strategist transaction (same trigger as the rolling cycle). The Strategist plans candidates from the objective and coupled parameters in `session.md`; no completed runs are required. At session start all slots are free, so expect at least 2× total_capacity candidates (current_free_slots + total_capacity): only total_capacity would let the first launch wave empty the queue and force a redundant blocking re-call against the same empty result state. Register the returned candidates with `queue-add`, then launch.

Use "batch" only as a search-design label. Execution is rolling: a completion, a resource change, or a changed result can trigger an immediate launch, slot refill, and queue refill before the rest of the conceptual batch finishes. The Strategist may return zero, one, or many candidates at once, not exactly one candidate per finished run.

## 6. Capacity Check

Before every launch wave, check available GPU slots. Memory alone is insufficient; high utilization can contaminate metrics for some methods.

```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader
python SKILL_DIR/scripts/aet.py gpu-slots
```

Raw `nvidia-smi` keeps units for readable context; `aet.py gpu-slots` queries `--format=csv,noheader,nounits` internally so it can parse memory and utilization reliably, then prints per-GPU free slots plus a `TOTAL free_slots/total_capacity` footer. `aet.py loop-state` also reports both — read them from there.

GPU scheduling is normally arranged explicitly — which GPU indices to use, how many jobs per GPU, memory and utilization thresholds. Take that arrangement from the highest-priority source available, in this order:
1. user instruction in the current session — honor immediately
2. project adapter (`references/project-adapter-*.md`)
3. project README or experiment notes
4. project memory (`aet/knowledge.md` or the project's memory system)

When the arrangement names specific GPU indices, launch only on those GPUs; do not use unlisted GPUs without asking. Persist it once with `aet.py set-policy` (e.g., "use GPU 2 and 3, up to 2 jobs each" → `--gpu-ids 2,3 --max-per-gpu 2`); it is stored in `meta.json` `gpu_policy` and `gpu-slots`/`loop-state`/`strategist-begin` all read it. See the flag table in `references/gpu-policy.md`.

Apply the arrangement per dimension. For each scheduling dimension a higher-priority source does not fix, fall back to its conservative default — so if the user names GPUs 2 and 3 but not jobs-per-GPU, those GPUs still take the default 1 job each. The per-dimension defaults: 1 experiment per GPU, utilization ceiling 95%, no per-slot memory cap, all GPUs that `nvidia-smi` reports. These defaults guard against GPU contention that can contaminate metrics; they are a floor, not the expected operating point. The hard cap of 3 experiments per GPU holds regardless of arrangement — never exceed it without an explicit user instruction naming a higher number.

A GPU slot is **available** when all hold: utilization is below the applicable util ceiling, active experiments on that GPU are below the applicable `max_per_gpu`, and any configured memory limit is satisfied (used memory below `max_memory_used_mb` and/or free memory at least `min_free_memory_mb`). If all allowed GPUs are at capacity, wait for the next completion rather than forcing a launch.

`total_capacity` = capacity_per_gpu × gpu_count across all allowed GPUs. `aet.py gpu-slots` (TOTAL footer) and `aet.py loop-state` compute and print it. It is constant for the session and drives the planned-row queue invariant in section 5.

For the configurable parameters (`gpu_ids`, `max_per_gpu`, `max_memory_used_mb`, `min_free_memory_mb`, `max_util`), the `aet.py gpu-slots` CLI flag mapping, and the conditions under which more than one experiment per GPU is allowed, read `references/gpu-policy.md`.

Use `pgrep -af` only as a sanity check. It may match the `pgrep` command itself and does not prove which output directory belongs to a process. Prefer precise patterns such as `experiments/exp_` or the exact script name; broad patterns like `exp_` can match unrelated system threads.

## 7. Launch

Launch every configuration in its own run directory.

Launch rules:
- one experiment per command/session
- explicit GPU id
- unique output directory created before launch. Call `aet.py create-run --run-id <id>` against an existing `planned` row; it prints three labeled lines (`run_dir`, `run_id`, `output_dir`) and creates `run_dir/output/` automatically — use the printed `output_dir` directly. Use `aet.py unique-dir` only when `output_dir` must live outside the session directory (rare).
- log path inside the unique output directory, normally `<output_dir>/train.log`; do not use a separate shared log directory
- standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`
- use plain `python` by default so the command inherits the agent's startup environment; use an explicit interpreter path only when the active environment is wrong
- simple shell: avoid `cd`, command substitution, loops, pipes, and multi-command launch blocks
- before each launch wave, re-check resources (section 6), select as many `planned` rows as current free slots allow, assign each to a GPU id that `aet.py loop-state` (its `LAUNCH ... onto GPU id(s)` line) or `aet.py gpu-slots` reports free — one job per free id, never a hand-picked or reused id and never a GPU already at its cap — activate each with `aet.py create-run --run-id <id>` (take `run_id` and `output_dir` from its output), and record status `running` with `aet.py record --status running` after the process starts

**Codex**: keep the command in a foreground tool session; do not add shell `&`. Poll active sessions with `write_stdin` at reasonable intervals.

**Claude Code**: use `run_in_background=True` on the Bash tool instead of foreground blocking. Multiple experiments can be launched in the same turn. See `references/claude-code-adapter.md`.

When a run finishes, immediately identify the run, then record inline: verify output files, parse metrics (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record` (which adds the terminal run to the pending set), then `aet.py loop-state` to re-check resources and fill all currently usable slots from the `planned` rows.

## 8. Task Management by Runtime

**Codex task management:**
- The live state of each run is its `results.csv` row (`created`/`running` status, GPU id, output directory, command). `create-run` and `record` keep it current; do not maintain a parallel table.
- Launch each experiment by passing the standard command directly to `exec_command`; this is a foreground tool session, not shell backgrounding. Use the same command shape as Claude Code, but without `run_in_background=True` and without shell `&`.
- If `exec_command` yields before completion and returns a long-running `session_id`, treat that session as the managed run. Map `codex_session_id -> run_id` via the run's `annotation` immediately. Do not rely on chat memory alone.
- Poll active sessions with `write_stdin` at reasonable intervals. Because stdout/stderr are redirected to the log file, use separate short reads of the log path when progress details are needed.
- Prefer direct commands such as `python -u SCRIPT --gpu_id N --output_dir DIR > DIR/train.log 2>&1`, where `DIR` already exists and was created as a unique run directory. Keep one experiment per tool session. Avoid launching more jobs than can be tracked and analyzed cleanly.
- Use `multi_tool_use.parallel` for independent file reads and status checks, not for launching several long-running experiments unless each launch remains a separate, trackable tool session.
- Delegate analysis and planning to the Strategist. Keep delegated work bounded.
- Invoke the Strategist only inside the three-beat transaction (`aet.py strategist-begin` → `spawn_agent`/`send_input` tool_use → `aet.py strategist-return`). `strategist-begin` prints whether to fresh-spawn or `send_input`-resume and the target id.
- Do not leave required experiment sessions running when sending the final answer. Either collect them, report that they are intentionally still running at the user's request, or stop before claiming completion.

**Claude Code task management:**
- Before launching, activate each `planned` row with `aet.py create-run --run-id <id>`; the run's `results.csv` row carries the live state (GPU id, output directory, command).
- Launch all independent jobs in the same turn with `run_in_background=True`. You will receive a completion notification for each.
- After each background launch is accepted, call `aet.py record --status running` without a routine annotation so `results.csv` has a start time.
- On notification: identify the run; record inline (verify output files, parse metrics, determine status, call `aet.py record` — which adds the terminal run to the pending set); then `aet.py loop-state` to re-check resources and route launches/Strategist.
- Do not wait for all jobs in a candidate group to finish before analyzing and recording the ones that completed first — incremental recording reduces exposure to context compaction loss.

## 9. Collection and Result Integrity

For each finished run:
1. Verify output directory, metrics JSON/CSV/NPZ, images, and the in-output-dir log file exist.
2. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort (and record that it was manual).
3. Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, mismatched output directories, GPU contention, and partial crashes as `failed` or `inconclusive`.
4. Call `aet.py record --status <status> --run-id <id> [--primary-metric <v> --metric-name <n> --metrics '<json>'] [--annotation '<note>']`
5. Run `aet.py loop-state` to re-check GPU slots and route the next launch/Strategist action. It is the rolling hub: run it right after `record` and before any create-run, launch, or candidate planning.

### Required Per-Run Fields

Record:
- run id and queue id
- command
- output directory
- log path under the output directory, normally `train.log`
- GPU id
- parameters as JSON
- seed or initialization source, if the method is initialization-sensitive
- preprocessing/channel mode, postprocessing mode, and metric definition when these can affect comparability
- schedule/switch sentinel values, especially when they are intended to disable a behavior
- status
- primary metric and metric name
- all useful secondary metrics
- annotation explaining trustworthiness

### Optional Per-Run Fields (record when available)

- per-HP rationale: brief justification (from prior results) for the specific value chosen for each non-default hyperparameter in this run. Stored in the run's `params.json` or `session.md`, not necessarily the CSV row.
- trust evidence: concise notes on metric source, output/log path match, GPU contention, code/data comparability, and any anomaly that affects benchmark use.

### Contamination and Code Changes

- Record sandbox, dependency, CUDA visibility, and permission failures as failures or inconclusive runs; do not fold them into method performance.
- If a candidate group used a later-discovered implementation bug, wrong color conversion, wrong crop, stale metric, or mismatched output directory, mark the affected runs `inconclusive`.
- When adding CLI knobs or changing experiment code during tuning, record the code-diff summary, default behavior, and whether older benchmark rows remain comparable.
- Keep raw logs under each run's output directory for bad, failed, and contaminated runs. They are often the only evidence that prevents repeating the same mistake.

If a run is contaminated, record it as `inconclusive` rather than deleting it.

## 10. Analysis

Recording is inline (see section 9). Analysis is delegated, not done inline: synthesizing per-HP influence patterns across runs is the Strategist's job.
- Strategist returns `observations_to_append` (per-HP influence patterns, boundary hits, forbidden regions) when called.
- Write returned observations into `session.md`'s Current Analysis section (overwrite). `aet.py strategist-return` clears the pending snapshot for you (version-guarded), so runs that completed during analysis stay pending for the next call.

Do not wait for a whole conceptual batch before recording. Record each run inline immediately as it completes.

## 11. Next Queue and Stopping Handshake

Do not perform inline strategy derivation. After inline recording:

1. Check whether a self-evaluatable stop condition is met: explicit user stop ("stop"/"end tuning"), explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, or required permission/resource unavailable. These you can evaluate inline. Do NOT evaluate plateau or exhaustion here — that is Strategist's job.
2. Run `aet.py loop-state` (it counts planned rows from `results.csv`). It reports free slots, total_capacity, pending runs, and the routed NEXT action.
3. If it routes a Strategist call (planned count < total_capacity, section 6), run the three-beat transaction:
   - `aet.py strategist-begin` — snapshots pending, computes the branch (fresh / resume / fresh confirmer) and blocking/background, opens the call, prints the spawn/resume tool call + payload. It refuses if a call is already open.
   - your spawn/resume tool_use (the printed call). On a background Claude Code resume, keep processing other completions meanwhile; each `record` adds to pending without disturbing the open call.
   - `aet.py strategist-return --call-id C --candidates-count K [--agent-id A] [--observations-present] [--queue-edits-present] [--stop-update-present]` — clears the snapshot (version-guarded), records the agent id, derives exhaustion from `K == 0`, applies the handshake, prints the YOU obligations.
   No other suppression is valid. Do not skip because Strategist was recently called or because the pending set is empty. Full protocol: `references/subagents.md`.
4. Apply the Strategist return per its YOU block: run `aet.py queue-add` with the returned candidates JSON, run `aet.py queue-drop` for any invalidated candidates, and update `session.md` (Current Analysis, Reusable Rules, Stop/Continue Rule).
5. Immediately launch planned rows into free slots with `aet.py create-run --run-id <id> --gpu-id <gpu>`.

Plateau/exhaustion is an **independent-context handshake owned by the script**. A Strategist signals exhaustion by returning zero candidates. When the Primary returns 0 candidates while fully quiescent (no `planned`/`created`/`running` runs — computed by the script, not self-judged), `strategist-return` sets the handshake so the next `strategist-begin` is forced to a **fresh confirmer** in a new context — never a resume of the Primary, because re-messaging the context that produced the signal gives no independence. If the confirmer returns candidates, the Primary is overturned, the confirmer is promoted to Primary, and the loop continues. Only when the fresh confirmer also returns 0 candidates does `strategist-return` print `CONFIRMED_EXHAUSTION`. Any Strategist returning candidates resets the handshake to zero.

Candidate-selection principles are built into the `experiment-strategist` subagent.

Before stopping, verify the applicable condition:

**Explicit stop** (target/budget/permission): the target is cleanly met with evidence, or the budget is consumed, or continuation is blocked by unavailable permission or resource. No further checks required.

**Plateau/exhaustion stop**: all of the following must hold:
- plateau or exhaustion has been confirmed by two independent-context Strategist signals (not self-evaluated): both produced while fully quiescent (no experiments running, no planned candidates), both returning zero candidates (zero candidates is the exhaustion signal). Signal (2) must come from a fresh confirmer, not a resume of the Primary: Claude Code uses fresh `Agent`; Codex uses fresh `spawn_agent` (see Next Queue handshake above)
- at least one broad alternative regime has been tested after the current best was found
- the current best has been confirmed if it is surprising, benchmark-facing, or produced under different load
- the ledger records why further experiments are unlikely to change the user's decision

When a valid stop condition is met, produce a **Session Final Analysis** before closing:

1. **Best configuration found**: full parameter table of the best run, primary metric, and the run id.
2. **Per-HP influence summary**: for each tuned hyperparameter, state what was learned — which values worked, which failed, observed trends (monotone, peaked, interaction-dependent), and any coupling with other HPs. Draw from `session.md` and the session ledger. Keep entries concise (1–2 sentences each).
3. **Future exploration directions**: list 2–5 specific directions that were not exhausted — unexplored regions, untested couplings, alternative schedules, or method-level changes that might help.

Write the final analysis to `session.md`'s `## Final Analysis` section, and include it in the response to the user. Run `aet.py summarize` alongside it for the quantitative run-count and metric statistics.

## 12. Project Records and Cross-Session Knowledge

If a project has a benchmark table, update it immediately when a clean result improves the current best. Keep detailed comparisons in `session.md` or the project's result notes; keep the benchmark table as a current-best quick lookup.

If a project has a memory system, store durable rules there. If not, append rules to `session.md`'s Reusable Rules section and optionally create `aet/knowledge.md` (the only file allowed at the `aet/` root; it is cross-session, not session-scoped).
