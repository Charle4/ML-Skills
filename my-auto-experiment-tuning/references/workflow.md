# Workflow

Use this file when starting or resuming an autonomous tuning job.

## Autonomy Contract

After the user states the tuning target, benchmark setting, constraints, and budget/principles, continue without asking for approval at each iteration. You own the loop:
- infer the current state
- maintain the rolling execution board in `SESSION/plan.md`
- keep a ready queue of launchable candidates
- launch experiments within allowed permissions
- monitor and collect results
- update lifecycle ledgers and benchmark docs
- delegate result analysis and candidate planning, then apply returned queue changes

Escalate to the user only for destructive operations, ambiguous goals, missing required permissions, budget changes, or actions outside the active sandbox/approval policy.

Default duration semantics:
- Treat autonomous tuning as a long-running job, not a short investigation. If the user asks for broad tuning, abundant GPU use, or a target such as `PSNR > 25`, expect tens to hundreds of runs and possibly multi-day operation.
- Do not end after 1-3 planning groups just because a plausible local best was found. A local best is a signal for the next queue update, not a stopping reason.
- If no explicit run or wall-clock budget is provided, assume the budget is open-ended until the user intervenes or the target is cleanly met.
- Keep all usable GPU slots occupied within the configured contention limits. When any run finishes, immediately identify it, record inline: verify output files, parse metrics in priority order (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record`, append trust details to `runs/<id>/summary.md`, move to `Completed / Recorded`, add to `runs_since_last_strategist`, re-check current resources, and launch as many `Ready Queue` candidates as the now-free slots allow — do not wait for other running experiments to finish first.
- Keep `Ready Queue` count at or above total_capacity (capacity_per_gpu × gpu_count, constant from `aet.py gpu-slots`) whenever useful unexplored regions remain. Call Strategist whenever count drops below total_capacity.
- If the system forces a final response before the target is met, report the next ready candidates or search group and the reason continuation is blocked; do not present a local best as final.

## 1. Context Pass

Read the minimum files that define the experiment contract:
- repository agent instructions
- experiment README or benchmark docs
- target script argparse/config definitions
- existing run ledgers, result tables, or project memory

Do not repeatedly reread large files after extracting stable rules. Write durable summaries to the session observations or the project's memory mechanism.

## 2. Session Setup

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
python SKILL_DIR/scripts/aet.py init --project-root PROJECT --name NAME --objective OBJECTIVE --goal max
```

Capture the printed session path. `aet.py init` creates `plan.md` from `assets/plan-template.md` and `observations.md` from `assets/observations-template.md` in that exact directory; edit those generated files directly.

## 2.1 AET Helper Contract

Use `aet.py` for objective run bookkeeping, not for semantic search decisions:
- `plan.md` is the human/agent-managed rolling execution board. `Ready Queue` lives there.
- `queue.jsonl` is an append-only recovery map written by `create-run` for registered runs. It is not the live `Ready Queue` and it does not reflect later status updates.
- `results.csv` is the status/metric source of truth. Use `aet.py record` for every transition to `running`, `finished`, `failed`, `inconclusive`, or `superseded`.
- `runs/<id>/params.json`, `metrics.json`, `command.sh`, and `summary.md` are per-run objective artifacts. Do not create parallel run-note files.
- `record --notes` appends a run note to `observations.md`; use notes mainly for terminal statuses or important anomalies. For routine `running` transitions, omit `--notes` to avoid noisy duplicate observations.
- `record` rewrites `runs/<id>/summary.md` from the template. Add detailed trust-check edits after the final terminal `record`, or be prepared to reapply them if status changes later.

## 3. Planning

Before launching, write and maintain the live plan in `SESSION/plan.md`:
- hypothesis being tested
- parameter dimensions and values
- expected signal if the hypothesis is true
- risk that could invalidate the candidate group
- exact launch commands or command template
- expected follow-up if the candidate group improves, fails, or lands on a boundary
- remaining stop blockers, such as unmet target, missing escape group, missing confirmation, or unused plausible parameter families
- the rolling execution board with `Completed / Recorded`, `Running`, and `Ready Queue`
- current free GPU slots and enough ready candidates that ready_count stays >= total_capacity after the next launch wave fills the free slots (target ≈ current_free_slots + total_capacity; = 2× total_capacity at session start)

Do not create separate planning notes such as `aet/YYYY-MM-DD/next.md`, `aet/YYYY-MM-DD/plan.md`, or `aet/plan.md`. If the session `plan.md` is missing or corrupted, restore it from `assets/plan-template.md` into `SESSION/plan.md`.

Prefer candidate groups that distinguish hypotheses. The Strategist owns detailed candidate selection when delegation is available; write the returned candidates into `plan.md`.

**Before proceeding to section 4**: if `Ready Queue` count < total_capacity, call Strategist (same trigger as the rolling cycle). Strategist plans candidates from `plan.md`'s objective and coupled parameters; no completed runs are required. At session start all slots are free, so expect at least 2× total_capacity candidates (current_free_slots + total_capacity): only total_capacity would let the first launch wave empty the queue and force a redundant blocking re-call against the same empty result state. Only then launch from the returned queue.

Use "batch" only as a search-design label. Execution is rolling: a completion, a resource change, or a changed result can trigger an immediate row transition, slot refill, and queue refill before the rest of the conceptual batch finishes. Strategist may return zero, one, or many ready candidates at once, not exactly one candidate per finished run.

## 4. Launch

Launch every configuration in its own run directory.

Launch rules:
- one experiment per command/session
- explicit GPU id
- unique output directory created before launch. Default: call `aet.py create-run` (no `--run-id`); it prints three labeled lines (`run_dir`, `run_id`, `output_dir`) and creates `run_dir/output/` automatically — use the printed `output_dir` directly. Use `aet.py unique-dir` only when `output_dir` must live outside the session directory (rare).
- never pass `--run-id` to `create-run`; always let it auto-assign. Manual IDs cause FileExistsError collisions when `plan.md` is stale after context compaction.
- log path inside the unique output directory, normally `<output_dir>/train.log`; do not use a separate shared log directory
- standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`
- use plain `python` by default so the command inherits the agent's startup environment; use an explicit interpreter path only when the active environment is wrong
- simple shell: avoid `cd`, command substitution, loops, pipes, and multi-command launch blocks
- before each launch wave, re-check resources, select as many `Ready Queue` rows as current free slots allow, assign GPU, register each with `aet.py create-run` (no `--run-id`; take `run_id` and `output_dir` from its output), record status `running` with `aet.py record --status running` after the process starts, and move each to `Running`

**Codex**: keep the command in a foreground tool session; do not add shell `&`. Poll active sessions with `write_stdin` at reasonable intervals.

**Claude Code**: use `run_in_background=True` on the Bash tool instead of foreground blocking. Multiple experiments can be launched in the same turn. See `references/claude-code-adapter.md`.

When a run finishes, immediately identify the run, then record inline: verify output files, parse metrics (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record`, append trust details to `summary.md`, move the row to `Completed / Recorded`, add to `runs_since_last_strategist`, re-check resources, and fill all currently usable slots from `Ready Queue`.

## 4.1 Task Management by Runtime

**Codex task management:**
- Keep the `Running` table in the session plan before launching: run id, hypothesis, GPU id, output directory, command, and expected metric file. `queue.jsonl` is only a recovery map created by `create-run`.
- Launch each experiment by passing the standard command directly to `exec_command`; this is a foreground tool session, not shell backgrounding. Use the same command shape as Claude Code, but without `run_in_background=True` and without shell `&`.
- If `exec_command` yields before completion and returns a long-running `session_id`, treat that session as the managed run. Record `codex_session_id -> run_id/output_dir/log_path` in `plan.md` immediately. Do not rely on chat memory alone.
- Poll active sessions with `write_stdin` at reasonable intervals. Because stdout/stderr are redirected to the log file, use separate short reads of the log path when progress details are needed.
- Prefer direct commands such as `python -u SCRIPT --gpu_id N --output_dir DIR > DIR/train.log 2>&1`, where `DIR` already exists and was created as a unique run directory. Keep one experiment per tool session. Avoid launching more jobs than can be tracked and analyzed cleanly.
- Use `multi_tool_use.parallel` for independent file reads and status checks, not for launching several long-running experiments unless each launch remains a separate, trackable tool session.
- Delegate analysis and planning to the Strategist by default whenever subagents are available; fall back to inline analysis and planning only when delegation is unavailable. Keep delegated work bounded.
- After the first Codex Strategist spawn, save `strategist_agent_id` and prefer `send_input(target=strategist_agent_id, ...)` for later Strategist calls. Use a fresh `spawn_agent` only for the first call, an unreachable/resume-failed agent, or the exhaustion confirmer.
- Do not leave required experiment sessions running when sending the final answer. Either collect them, report that they are intentionally still running at the user's request, or stop before claiming completion.

**Claude Code task management:**
- Before launching, register each run with `aet.py create-run` so `queue.jsonl` receives the recovery map, and write the live row to `plan.md`: run id, hypothesis, GPU id, output directory, command, expected metric file.
- Launch all independent jobs in the same turn with `run_in_background=True`. You will receive a completion notification for each.
- After each background launch is accepted, call `aet.py record --status running` without routine notes so `results.csv` has a start time.
- On notification: identify the run from `Running`; record inline (verify output files, parse metrics, determine status, call `aet.py record`, append trust details to `summary.md`, move to `Completed / Recorded`, add to `runs_since_last_strategist`); re-check resources and launch as many `Ready Queue` candidates as current slots allow.
- Do not wait for all jobs in a candidate group to finish before analyzing and recording the ones that completed first — incremental recording reduces exposure to context compaction loss.

**Both runtimes:**
- Check `nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader` before launching and during suspicious slowdowns. Memory alone is insufficient; high utilization can contaminate metrics for some methods. Use `references/gpu-policy.md` and `aet.py gpu-slots` to determine available slots (default: 1 per GPU, cap 3, util ceiling 95%); the helper normalizes the same fields for numeric filtering.
- Use `pgrep -af` only as a sanity check. It may match the `pgrep` command itself, and it does not prove which output directory belongs to a process. Prefer precise patterns such as `experiments/exp_` or the exact script name; broad patterns like `exp_` can match unrelated system threads.

## 5. Collection

For each finished run:
1. Verify output directory, metrics JSON/CSV/NPZ, images, and the in-output-dir log file exist.
2. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort.
3. Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, mismatched output directories, GPU contention, and partial crashes as `failed` or `inconclusive`.
4. Call `aet.py record --status <status> --run-id <id> [--primary-metric <v> --metric-name <n> --metrics '<json>'] [--notes '<note>']`
5. If trust note is relevant: append to `runs/<id>/summary.md` (after record, since record rewrites that file).
6. Move the row from `Running` to `Completed / Recorded` in `plan.md`; add run_id to the `runs_since_last_strategist` tracking list.
7. Re-check GPU slots and continue the rolling queue protocol.

## 6. Analysis

Recording is inline (see section 5). Analysis is delegated, not done inline: synthesizing per-HP influence patterns across runs is the Strategist's job.
- Strategist returns `observations_to_append` (per-HP influence patterns, boundary hits, forbidden regions) when called.
- Append returned observations to `observations.md` and clear only the run_ids that were passed at call time from the tracking list.

Do not wait for a whole conceptual batch before recording. Record each run inline immediately as it completes.

## 7. Next Queue

Do not perform inline strategy derivation. After inline recording:

1. Check whether a self-evaluatable stop condition is met: explicit user stop ("stop"/"end tuning"), explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, or required permission/resource unavailable. These you can evaluate inline. Do NOT evaluate plateau or exhaustion here — that is Strategist's job.
2. Count current `Ready Queue` rows and current free GPU slots.
3. If `Ready Queue` count < total_capacity (capacity_per_gpu × gpu_count from `aet.py gpu-slots`):
   - Queue empty: blocking call; wait for results before launching. Claude Code: if `strategist_agent_id` is set in plan.md Loop State, use `SendMessage` instead — it runs in background; set `background_strategist_in_flight: true` and do not launch while waiting. Codex: if `strategist_agent_id` is set, use `send_input(target=strategist_agent_id, ...)`, then `wait_agent`.
   - Queue non-empty: background spawn where supported. Claude Code: use `SendMessage` if `strategist_agent_id` is set, otherwise `Agent(..., run_in_background=True)`; set `background_strategist_in_flight: true`. Codex: blocking `send_input` if `strategist_agent_id` is set, otherwise blocking `spawn_agent`. Record which run_ids were passed; on return, clear only those IDs from `runs_since_last_strategist`.
   - **Claude Code exhaustion-confirmation exception**: if `pending_exhaustion_confirmation` is true, ignore `strategist_agent_id` and spawn a fresh confirmer (`Agent`, blocking) instead of a SendMessage resume — the exhaustion handshake requires an independent context (see the exhaustion handling below and adapter step 9).
   - **Codex exhaustion-confirmation exception**: if `pending_exhaustion_confirmation` is true, ignore `strategist_agent_id` and spawn a fresh confirmer (`spawn_agent`, blocking) instead of a `send_input` resume — the exhaustion handshake requires an independent context.
   - Codex `send_input` edge cases: if the target agent is still running, input queues by default; use `interrupt=true` only when intentionally replacing the current task. If the agent was closed, `resume_agent(id=...)` before sending when continuity is still useful; if resume/send fails, fresh-spawn and update `strategist_agent_id`.
   - No other suppression is valid. Do not skip because Strategist was recently called or because `runs_since_last_strategist` is empty.
   - Full continuation protocols: Codex in `references/subagents.md`; Claude Code in `references/subagents.md` and `references/claude-code-adapter.md` (step 9).
4. Apply the Strategist return: append `observations_to_append` to `observations.md`, clear only the `runs_since_last_strategist` entries that were passed at call time; append Ready Queue rows to `plan.md`, update Stop/Continue Rule text, and remove or rewrite invalidated ready rows.
5. Immediately move ready rows into `Running` for any free slots.

If the Strategist returns zero Ready Queue candidates and declares plateau or exhaustion:
- Continue the same rule: Queue is still empty (0 < total_capacity), so the Strategist keeps being invoked with the standard neutral prompt and the complete current result state. No mention of any prior verdict.
- Stop condition is an **independent-context handshake**: the exhaustion verdict must be confirmed by a different context, both produced while fully quiescent (no experiments running, Ready Queue empty), both returning zero candidates and declaring exhaustion.
  - **Claude Code**: verdict (1) is the continuous-context Primary; set `pending_exhaustion_confirmation: true` so verdict (2) is a **fresh confirmer spawn** (never a SendMessage resume of the Primary). If the confirmer returns candidates instead, overturn the Primary, append candidates, continue, and **promote the confirmer to Primary** (`strategist_agent_id` ← confirmer `agentId`); reset the handshake.
  - **Codex**: verdict (1) is the continuous-context Primary resumed via `send_input`; set `pending_exhaustion_confirmation: true` so verdict (2) is a **fresh confirmer spawn** (never a `send_input` resume of the Primary). If the confirmer returns candidates instead, overturn the Primary, append candidates, continue, and **promote the confirmer to Primary** (`strategist_agent_id` ← confirmer agent id); reset the handshake.
  - Any Strategist returning candidates discards all prior exhaustion declarations and resets the handshake to zero.

Candidate-selection principles are built into the `experiment-strategist` subagent.

Before stopping, verify the applicable condition:

**Explicit stop** (target/budget/permission): the target is cleanly met with evidence, or the budget is consumed, or continuation is blocked by unavailable permission or resource. No further checks required.

**Plateau/exhaustion stop**: all of the following must hold:
- plateau or exhaustion has been confirmed by two independent-context Strategist verdicts (not self-evaluated): both produced while fully quiescent (no experiments running, Ready Queue empty), both returning zero candidates and declaring exhaustion. Verdict (2) must come from a fresh confirmer, not a resume of the Primary: Claude Code uses fresh `Agent`; Codex uses fresh `spawn_agent` (see Next Queue handshake above)
- at least one broad alternative regime has been tested after the current best was found
- the current best has been confirmed if it is surprising, benchmark-facing, or produced under different load
- the ledger records why further experiments are unlikely to change the user's decision

When a valid stop condition is met, produce a **Session Final Analysis** before closing:

1. **Best configuration found**: full parameter table of the best run, primary metric, and the run id.
2. **Per-HP influence summary**: for each tuned hyperparameter, state what was learned — which values worked, which failed, observed trends (monotone, peaked, interaction-dependent), and any coupling with other HPs. Draw from `observations.md` and the session ledger. Keep entries concise (1–2 sentences each).
3. **Future exploration directions**: list 2–5 specific directions that were not exhausted — unexplored regions, untested couplings, alternative schedules, or method-level changes that might help.

Write the final analysis to the session's `observations.md` under a `## Final Analysis` heading, and include it in the response to the user. Run `aet.py summarize` alongside it for the quantitative run-count and metric statistics.

## 8. Recovery

After context compaction or interruption:
1. Locate latest session with `aet.py status --project-root PROJECT`.
2. Read `meta.json`, `plan.md`, `results.csv`, and `observations.md`.
3. Check active processes and GPU slots.
4. Reconcile any finished-but-unrecorded runs.
5. Resume from the next untested hypothesis.

If the recovered session has no active processes and the target is unmet, do not summarize and stop. Treat the idle state as a failure to continue: read the last observations, refill `Ready Queue` to at least total_capacity, and relaunch.
