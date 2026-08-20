# Workflow

Read this file at session start and apply its autonomous loop, ledger schema, and GPU capacity rules.

## 1. Autonomy Contract

After the user states the tuning target, benchmark setting, constraints, and budget/principles, continue without asking for approval at each iteration. You own the loop:
- infer the current state
- keep a queue of launchable candidates as `planned` rows in `results.csv`
- launch experiments within allowed permissions
- monitor and collect results
- update lifecycle ledgers
- delegate result analysis and candidate planning, then apply returned queue changes

Escalate to the user only for destructive operations, ambiguous goals, missing required permissions, budget changes, or actions outside the active sandbox/approval policy.

Default duration semantics:
- Treat autonomous tuning as a long-running job, not a short investigation. If the user asks for broad tuning, abundant GPU use, or a target such as `PSNR > 25`, expect tens to hundreds of runs and possibly multi-day operation.
- Do not end after 1-3 planning groups just because a plausible local best was found. A local best is a signal for the next queue update, not a stopping reason.
- If no explicit run or wall-clock budget is provided, assume the budget is open-ended until the user intervenes or the target is cleanly met.
- Keep all usable GPU slots occupied within the configured contention limits. When any run finishes, immediately identify it, record inline: verify output files, parse metrics in priority order (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record` (which adds the terminal run to the pending set), then `aet.py loop-state` to re-check resources and launch as many `planned` candidates as the now-free slots allow — do not wait for other running experiments to finish first.
- Keep `projected_ready_after_launch = planned_count - min(free_slots, planned_count)` at or above total_capacity (see [6. Capacity Check](#6-capacity-check)) whenever useful unexplored regions remain. `loop-state` routes the Strategist transaction whenever the projected count is below total_capacity.
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
- evaluation contract: primary metric formula/direction, supporting metrics, required per-case/seed/slice or worst-case checks, expected range/headroom, failure behavior, and best-artifact/checkpoint locations
- run trust constraints, such as GPU contention limits
- budget: max runs, wall time, or `open-ended until target/user stop`
- minimum stopping evidence: required broad escape groups, refinements, confirmations, and minimum run count before the Strategist may declare plateau — these are inputs for the Strategist to evaluate, not conditions you check

Use:

```bash
python SKILL_DIR/scripts/aet.py init --project-root PROJECT --name NAME --objective OBJECTIVE --goal max --runtime RUNTIME --process-pattern 'SCRIPT_FILENAME_REGEX'
```

Set `RUNTIME` to `codex` for Codex or `claude` for Claude Code.

`--process-pattern` is required: a regex that uniquely identifies this session's experiment processes in `ps` output (e.g. the script filename `'exp_dip_deblur\\.py'`). Without it, `loop-state` cannot detect experiments that finished without a terminal record. See [gpu-policy.md](gpu-policy.md) for guidance.

Capture the printed session path. `aet.py init` creates `session.md` from [../assets/session-template.md](../assets/session-template.md) in that exact directory; edit that generated file directly.

### Session Files

`aet/YYYY-MM-DD/HH-MM-SS/` contains:
- `meta.json`: objective, metric direction, project root, creation time, `runtime` default, and `gpu_policy`
- `session.md`: the single narrative ledger — `Target & Constraints`, `Evaluation Contract`, `Hypotheses & Coupled Parameters`, `Reusable Rules`, `Current Analysis`, `Stop/Continue Rule`, `Final Analysis`
- `results.csv`: one row per run, including the launchable queue (`planned` rows). Columns: `run_id`, `queue_id`, `status`, `params`, `hypothesis`, `expected_signal`, `rationale`, `priority`, `gpu_id`, `primary_metric`, `metric_name`, `metrics`, `output_dir`, `log_path`, `command`, `start_time`, `end_time`, `annotation`, `benchmark_status`, `goal`. `benchmark_status` is a retained legacy column that `record` no longer writes.
- `loop_state.json`: script-owned Strategist state machine — pending runs, Strategist identity/open call, exhaustion handshake, agent history, and `last_evidence_hash` (the evidence hash used to detect a state-unchanged loop). Read it via `aet.py loop-state`; change it only through AET helper commands.
- `runs/<id>/`: per-run params, command, and metrics

Only this timestamped session directory holds session ledger files. Do not write narrative, observations, or run notes directly under `aet/` or the date-level directory `aet/YYYY-MM-DD/`. If a task needs narrative or observations, update `aet/YYYY-MM-DD/HH-MM-SS/session.md`. The one allowed file at the `aet/` root is the optional cross-session durable-rules file `aet/knowledge.md` (see [12. Project Records and Cross-Session Knowledge](#12-project-records-and-cross-session-knowledge)); it is not session-scoped, so it does not belong inside a timestamped session directory.

### Run Status Values

- `planned`: candidate registered in `results.csv` (the launchable queue) but no GPU assigned and no run directory created yet
- `created`: run directory exists but command has not started
- `running`: process is active
- `finished`: completed and metrics are trustworthy
- `failed`: the run's own settings produced an unusable result — divergence, NaN, or a crash these parameters caused
- `inconclusive`: completed but contaminated, mismatched, or not comparable
- `infra_failed`: died for a reason the parameters had no part in, so they were never actually tested
- `superseded`: no longer relevant because a later clean run replaces it
- `dropped`: a `planned` candidate invalidated before launch (never ran)

### Separating `failed` from `infra_failed`

The question is whether the failure says anything about the parameters. A candidate that diverges, hits NaN, triggers a code bug on the path its own settings take, or OOMs *because its own batch size or model width is too large* has been tested and the answer is no — that is `failed`, and it is real evidence about a forbidden region. A run killed by a sandbox, dependency, CUDA-visibility, permission, or disk failure, by another user filling the card, or by an external kill tells you nothing about the candidate — that is `infra_failed`.

Two cases sit between them. A partial crash (the run died mid-way but left usable metrics) is classified by the same question, and by whether those partial metrics are comparable: parameter-caused and comparable is `failed`, environment-caused with nothing usable is `infra_failed`, usable-but-not-comparable is `inconclusive`. Contention is split the same way: contention that distorted a metric the run did produce is `inconclusive`; contention that killed the run is `infra_failed`.

The distinction is load-bearing because the Strategist treats `failed` and `inconclusive` runs as evidence for forbidden regions, and steers away from them. Filing an infrastructure crash as `failed` therefore fabricates a negative result and makes the search actively avoid a region that was never explored.

`record --status infra_failed` clones the candidate back into the planned queue under a new run_id (queue_id lineage `Q7` → `Q7r1` → `Q7r2`, carrying the attempt count) and keeps the run out of the pending set the Strategist analyzes. That new `planned` row also holds quiescence open until it runs, which is correct — a candidate awaiting retry means the search is not finished. Retries are not capped: repeated `infra_failed` rows on the same lineage mean the environment keeps breaking, and the annotation of each attempt is where you look for the reason. If they accumulate on a memory failure, `min_free_memory_mb` is understating what the job needs — raise it with `set-policy` (see [gpu-policy.md](gpu-policy.md)).

## 4. AET Helper Contract

Use `aet.py` for objective run bookkeeping. Delegate semantic search decisions to the Strategist:
- `results.csv` is the single source of truth for the launchable queue and run status/metrics. `planned` rows are the queue; terminal rows are history. Register the Strategist's candidate choices with `queue-add`/`queue-drop`.
- `loop_state.json` is the source of truth for the Strategist state machine (pending set, agent id, open call, exhaustion handshake). Read it via `aet.py loop-state`; change it only via `aet.py record` and `aet.py strategist-begin/return/abort`.
- Store per-run objective artifacts in `runs/<id>/params.json`, `metrics.json`, and `command.sh`.

Helper call ownership for each run:
- Use `aet.py queue-add` to register one or more Strategist candidates as `planned` rows in `results.csv`. Each gets a `queue_id`, `params`, `hypothesis`, `expected_signal`, `rationale`, and `priority`; GPU and run-directory allocation happen at `create-run`.
- Use `aet.py create-run --run-id <id>` before launching any experiment. It points at an existing `planned` row, creates `runs/<id>/` and `runs/<id>/output/`, writes objective artifacts, activates the row `planned` → `created`, and prints `run_dir`, `run_id`, and `output_dir` as labeled lines.
- Use `aet.py record --status running` after the process starts so `results.csv` records `start_time`.
- Use `aet.py record` again for terminal statuses and metrics. Terminal records update `end_time`, `metrics.json`, and `results.csv`. `record` refuses a terminal status while the run's process is still alive; pass `--force` to override only when you have confirmed the process is actually gone.
- Use `aet.py queue-drop --run-ids <id>` to invalidate a `planned` candidate before it launches (`planned` → `dropped`).
- `record --annotation` stores a trust note in the run's `annotation` column. Use it mainly for terminal statuses or important anomalies; omit it on routine `running` transitions.
- Commands, params, hypotheses, expected signals, rationales, annotations, and logs are durable artifacts. Use environment-variable names or secret-manager handles in place of credential values.

### Evaluator Evidence and Staged-Run Gate

Perform deterministic project validation and evidence collection. Delegate semantic analysis to the Strategist:

- For a new or changed experiment command, evaluator, preprocessing path, or metric definition, run the project's existing contract tests, validator, or dry-run mode before launching GPU work. Do not invent a generic validator when the project already has one.
- Record the primary metric definition and direction, all useful diagnostic metrics, benchmark slices/cases/seeds, constraint thresholds, failure behavior, and the paths of best-program/model/config artifacts. Include finer-grained outputs whenever available.
- Preserve evaluator and candidate failures as failed, inconclusive, or explicitly penalized evidence; preserve environment failures as `infra_failed`, which is not evidence about the candidate.
- When run length or fidelity is configurable, let the Strategist choose short probe/screening candidates or full runs. Execute the returned choice. Classify a probe as end-to-end signal evidence; reserve benchmark claims for clean full runs.
- Resume a probe checkpoint only when the project supports it and the Strategist requests it. Record the source run/checkpoint and whether the resumed result remains comparable with clean full runs.
- Pass raw metrics and artifact paths to the Strategist for headroom, robustness, and per-case regression decisions. Apply returned headroom/saturation assessments through Current Analysis and Stop/Continue Rule.

## 5. Planning and Queue Invariant

The launchable queue is the set of `planned` rows in `results.csv`. Register the Strategist's JSON candidates with `aet.py queue-add`; each row persists `params`, `hypothesis`, `expected_signal`, `rationale`, and `priority`.

Keep enough `planned` rows that `projected_ready_after_launch` stays >= total_capacity after the next launch wave fills the free slots (target planned count ≈ current_free_slots + total_capacity; = 2× total_capacity at session start). The narrative context for the queue — objective, coupled parameters, current analysis, stop/continue rule — lives in `session.md`.

Register the Strategist's hypothesis-distinguishing candidate groups without redesigning them inline.

**Before proceeding to section 7**: if `projected_ready_after_launch < total_capacity`, run the Strategist transaction. The Strategist plans candidates from the objective and coupled parameters in `session.md`; no completed runs are required. At session start all slots are free, so expect at least 2× total_capacity candidates (current_free_slots + total_capacity): only total_capacity would let the first launch wave empty the queue and force a redundant blocking re-call against the same empty result state. Register the returned candidates with `queue-add`, then launch.

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
2. a matching project adapter linked from [../SKILL.md](../SKILL.md)
3. project README or experiment notes
4. project memory (`aet/knowledge.md` or the project's memory system)

When the arrangement names specific GPU indices, launch only on those GPUs; do not use unlisted GPUs without asking. Persist it once with `aet.py set-policy` (e.g., "use GPU 2 and 3, up to 2 jobs each" → `--gpu-ids 2,3 --max-per-gpu 2`); it is stored in `meta.json` `gpu_policy` and `gpu-slots`/`loop-state`/`strategist-begin` all read it. See the flag table in [gpu-policy.md](gpu-policy.md).

Apply the arrangement per dimension. For each scheduling dimension a higher-priority source does not fix, fall back to its conservative default — so if the user names GPUs 2 and 3 but not jobs-per-GPU, those GPUs still take the default 1 job each. The per-dimension defaults: 1 experiment per GPU, utilization ceiling 95%, no per-slot memory cap, all GPUs that `nvidia-smi` reports. These defaults guard against GPU contention that can contaminate metrics; they are a floor, not the expected operating point. The hard cap of 3 experiments per GPU holds regardless of arrangement — never exceed it without an explicit user instruction naming a higher number.

A GPU's slot count is `min(max_per_gpu - running, free_memory // min_free_memory_mb)`, and drops to zero when utilization reaches the applicable ceiling or used memory reaches `max_memory_used_mb`. `min_free_memory_mb` is the memory **one** job needs, so a card with 6 GB free offers one 5 GB slot even when `max_per_gpu` is 2; the next `loop-state` re-measures and may open a second. If all allowed GPUs are at capacity, wait for the next completion rather than forcing a launch.

`total_capacity` = capacity_per_gpu × gpu_count across all allowed GPUs under the stored policy. `aet.py gpu-slots` and `aet.py loop-state` compute and print it. It remains stable until `set-policy` changes that policy and drives the planned-row queue invariant in section 5.

For the configurable parameters (`gpu_ids`, `max_per_gpu`, `max_memory_used_mb`, `min_free_memory_mb`, `max_util`), the `aet.py gpu-slots` CLI flag mapping, and the conditions under which more than one experiment per GPU is allowed, read [gpu-policy.md](gpu-policy.md).

Use `pgrep -af` only as a sanity check. It may match the `pgrep` command itself and does not prove which output directory belongs to a process. Prefer precise patterns such as `experiments/exp_` or the exact script name; broad patterns like `exp_` can match unrelated system threads.

## 7. Launch

Launch every configuration in its own run directory.

Launch rules:
- one experiment per command/session
- explicit GPU id
- unique output directory created before launch. Call `aet.py create-run --run-id <id>` against an existing `planned` row; it prints three labeled lines (`run_dir`, `run_id`, `output_dir`) and creates `run_dir/output/` automatically — use the printed `output_dir` directly. Use `aet.py unique-dir` only when `output_dir` must live outside the session directory (rare).
- log path inside the unique output directory, normally `<output_dir>/train.log`; do not use a separate shared log directory
- standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`
- use plain `python` by default so the command inherits the active shell environment; use an explicit interpreter path only when that environment is wrong
- simple shell: avoid `cd`, command substitution, loops, pipes, and multi-command launch blocks
- before each launch wave, re-check resources, select as many `planned` rows as current free slots allow, and use the run-id → GPU-slot pairings from `aet.py loop-state`. Each listed GPU-id occurrence is one free slot; repeated ids are valid when `max_per_gpu > 1`. Never add an unlisted occurrence or exceed that GPU's cap. Activate each run with `aet.py create-run --run-id <id>`, then record status `running` after the process starts

**Codex**: keep the command in a foreground tool session; do not add shell `&`. Poll active sessions with `write_stdin` at reasonable intervals.

**Claude Code**: use `run_in_background=True` on the Bash tool instead of foreground blocking. Multiple experiments can be launched in the same turn. See [claude-code-adapter.md](claude-code-adapter.md).

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
- Invoke the Strategist only inside the three-beat transaction (`aet.py strategist-begin` → printed `spawn_agent` or `send_message`/`followup_task` tool_use → `aet.py strategist-return`). `strategist-begin` prints the fresh/resume route and target id.
- Do not leave required experiment sessions running when sending the final answer. Either collect them, report that they are intentionally still running at the user's request, or stop before claiming completion.

**Claude Code task management:**
- Before launching, activate each `planned` row with `aet.py create-run --run-id <id>`; the run's `results.csv` row carries the live state (GPU id, output directory, command).
- Launch all independent jobs in the same turn with `run_in_background=True`. You will receive a completion notification for each.
- After each background launch is accepted, call `aet.py record --status running` without a routine annotation so `results.csv` has a start time.
- On notification: identify the run; record inline (verify output files, parse metrics, determine status, call `aet.py record` — which adds the terminal run to the pending set); then `aet.py loop-state` to re-check resources and route launches/Strategist.
- Do not wait for all jobs in a candidate group to finish before recording the ones that completed first — incremental recording reduces exposure to context compaction loss.

## 9. Collection and Result Integrity

For each finished run:
1. Verify output directory, metrics JSON/CSV/NPZ, images, and the in-output-dir log file exist.
2. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort (and record that it was manual).
3. Determine terminal status: `finished`, `failed`, `inconclusive`, or `infra_failed`, per [Separating `failed` from `infra_failed`](#separating-failed-from-infra_failed). Code bugs the candidate's own settings trigger, divergence, and NaN are `failed`; contaminated but comparable-looking results are `inconclusive`; sandbox, dependency, CUDA-visibility, disk, and external-kill failures are `infra_failed` and re-queue the candidate automatically.
4. Call `aet.py record --status <status> --run-id <id> [--primary-metric <v> --metric-name <n> --metrics '<json>'] [--annotation '<note>']`
5. Run `aet.py loop-state` to re-check GPU slots and route the next launch/Strategist action. It is the rolling hub: run it right after `record` and before any create-run or launch.

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
- per-case, per-seed, per-slice, and worst-case metrics when the evaluator emits them
- best artifact/config/checkpoint paths and resume provenance when applicable
- annotation explaining trustworthiness

### Optional Per-Run Fields (record when available)

- per-HP rationale: brief evidence for each non-default value. Persist it in the candidate's `rationale` field and include structured value-specific notes in `params` when needed.
- trust evidence: concise notes on metric source, output/log path match, GPU contention, code/data comparability, and any anomaly that affects benchmark use.

### Contamination and Code Changes

- Record sandbox, dependency, CUDA visibility, and permission failures as `infra_failed`; they say nothing about the candidate and must not be folded into method performance.
- If a candidate group used a later-discovered implementation bug, wrong color conversion, wrong crop, stale metric, or mismatched output directory, mark the affected runs `inconclusive`.
- If an aggregate improvement hides a required slice/case regression, record both the aggregate and the regression; do not promote the run as benchmark-quality until the Strategist evaluates it against the written constraints.
- When adding CLI knobs or changing experiment code during tuning, record the code-diff summary, default behavior, and whether older benchmark rows remain comparable.
- Keep raw logs under each run's output directory for bad, failed, and contaminated runs. They are often the only evidence that prevents repeating the same mistake.

If a run is contaminated, record it as `inconclusive` rather than deleting it; if it never ran far enough to test its parameters, record it as `infra_failed`.

## 10. Analysis

Recording is inline (see [9. Collection and Result Integrity](#9-collection-and-result-integrity)). Analysis is delegated, not done inline: synthesizing per-HP influence patterns across runs is the Strategist's job.
- Strategist returns `observations_to_append` (per-HP influence patterns, boundary hits, forbidden regions) when called.
- Write returned observations into `session.md`'s Current Analysis section (overwrite). `aet.py strategist-return` clears the pending-run snapshot for you (version-guarded), so runs that completed during analysis stay pending for the next call.

Do not wait for a whole conceptual batch before recording. Record each run inline immediately as it completes.

## 11. Next Queue and Stopping Handshake

Do not perform inline strategy derivation. After inline recording:

1. Check whether a self-evaluatable stop condition is met: explicit user stop ("stop"/"end tuning"), explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, or required permission/resource unavailable. These you can evaluate inline. Do NOT evaluate plateau or exhaustion here — that is Strategist's job.
2. Run `aet.py loop-state` (it counts planned rows from `results.csv`). It reports free slots, total_capacity, pending runs, and the routed NEXT action.
3. If it routes a Strategist call (`projected_ready_after_launch < total_capacity`, section 6), run the three-beat transaction:
   - `aet.py strategist-begin` — snapshots pending runs; computes the branch and blocking/background; opens the call; prints the spawn/resume tool call and payload. It refuses if a call is already open.
   - your spawn/resume tool_use (the printed call). For Claude Code resume, output the `SendMessage` tool call directly — it always works; do NOT skip it (anti-pattern #12). On a background Claude Code resume, keep processing other completions meanwhile; each `record` adds to pending without disturbing the open call.
   - when the Strategist returns, **read its full output** — candidates, observations, rules, stop update, queue edits — and count the actual candidates. This is `K` for the next step. Skipping this and closing with fabricated `K=0` is anti-pattern #11.
   - `aet.py strategist-return --call-id C --candidates-count K [--agent-id A] [--observations-present] [--reusable-rules-present] [--queue-edits-present] [--stop-update-present]` — requires non-negative `K` (the actual count from the Strategist) and an id for every fresh invocation. It applies the handshake. Pure resume cleanup requires `K=0`, no id, and no presence flags; it consumes no snapshot.
   No other suppression is valid. Do not skip because Strategist was recently called or because the pending set is empty. Full protocol: [subagents.md](subagents.md).
4. Apply the Strategist return per its YOU block, then run `aet.py loop-state`.
5. Immediately launch planned rows into free slots with `aet.py create-run --run-id <id> --gpu-id <gpu>`.

Plateau/exhaustion is an **independent-context handshake owned by the script**. Quiescence means no `planned`/`created`/`running` rows and no live process matching the stored session process pattern. A Strategist signals exhaustion by returning zero candidates. When the Primary returns 0 candidates while quiescent, `strategist-return` sets the handshake so the next `strategist-begin` is forced to a **fresh confirmer** in a new context. Pass that fresh confirmer's id to `strategist-return --agent-id`. If the confirmer returns candidates, it is promoted to Primary and the loop continues. Only when the fresh confirmer also returns 0 candidates does `strategist-return` print `CONFIRMED_EXHAUSTION`. Any Strategist returning candidates resets the handshake.

Candidate-selection principles are built into the `experiment-strategist` subagent.

Before stopping, verify the applicable condition:

**Explicit stop** (target/budget/permission): the target is cleanly met with evidence, or the budget is consumed, or continuation is blocked by unavailable permission or resource. No further checks required.

**Plateau/exhaustion stop**: all of the following must hold:
- plateau or exhaustion has been confirmed by two independent-context Strategist signals: both produced while fully quiescent (no `planned`/`created`/`running` rows and no matching live process), both returning zero candidates. Signal (2) comes from a fresh confirmer whose id was passed to `strategist-return --agent-id`
- at least one broad alternative regime has been tested after the current best was found
- the current best has been confirmed if it is surprising or produced under different load
- the ledger records why further experiments are unlikely to change the user's decision

When a valid stop condition is met, produce a **Session Final Analysis** before closing:

1. **Best configuration found**: full parameter table of the best run, primary metric, and the run id.
2. **Per-HP influence summary**: for each tuned hyperparameter, state what was learned — which values worked, which failed, observed trends (monotone, peaked, interaction-dependent), and any coupling with other HPs. Draw from `session.md` and the session ledger. Keep entries concise (1–2 sentences each).
3. **Future exploration directions**: list 2–5 specific directions that were not exhausted — unexplored regions, untested couplings, alternative schedules, or method-level changes that might help.

Write the final analysis to `session.md`'s `## Final Analysis` section, and include it in the response to the user. Run `aet.py summarize` alongside it for the quantitative run-count and metric statistics.

## 12. Project Records and Cross-Session Knowledge

If a project has a memory system, store durable rules there. If not, append rules to `session.md`'s Reusable Rules section and optionally create `aet/knowledge.md` (the only file allowed at the `aet/` root; it is cross-session, not session-scoped).
