# Workflow

Use this file when starting or resuming an autonomous tuning job.

## Autonomy Contract

After the user states the tuning target, benchmark setting, constraints, and budget/principles, continue without asking for approval at each iteration. The main agent owns the loop:
- infer the current state
- maintain the rolling execution board in `SESSION/plan.md`
- keep a ready queue of launchable candidates
- launch experiments within allowed permissions
- monitor and collect results
- update ledgers and benchmark docs
- decide which candidates to add, launch, rewrite, or retire

Escalate to the user only for destructive operations, ambiguous goals, missing required permissions, budget changes, or actions outside the active sandbox/approval policy.

Default duration semantics:
- Treat autonomous tuning as a long-running job, not a short investigation. If the user asks for broad tuning, abundant GPU use, or a target such as `PSNR > 25`, expect tens to hundreds of runs and possibly multi-day operation.
- Do not end after 1-3 planning groups just because a plausible local best was found. A local best is a signal for the next queue update, not a stopping reason.
- If no explicit run or wall-clock budget is provided, assume the budget is open-ended until the user intervenes or the target is cleanly met.
- Keep all usable GPU slots occupied within the configured contention limits. When any run finishes, immediately collect it, record metrics, move it from `Running` to `Completed / Recorded`, re-check current resources, and launch as many `Ready Queue` candidates as the now-free slots allow - do not wait for other running experiments to finish first.
- Keep `Ready Queue` count strictly greater than current free GPU slots whenever useful unexplored regions remain. If free slots = N, maintain at least N+1 ready candidates; if free slots = 0, keep at least one ready candidate unless a valid stop condition is documented.
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
- minimum stopping evidence: required broad escape groups, refinements, confirmations, and minimum run count before plateau can be claimed

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
- `record` rewrites `runs/<id>/summary.md` from the template. Add detailed trajectory/trust-check edits after the final terminal `record`, or be prepared to reapply them if status changes later.

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
- current free GPU slots and enough ready candidates so ready_count > free_slots

Do not create separate planning notes such as `aet/YYYY-MM-DD/next.md`, `aet/YYYY-MM-DD/plan.md`, or `aet/plan.md`. If the session `plan.md` is missing or corrupted, restore it from `assets/plan-template.md` into `SESSION/plan.md`.

Prefer candidate groups that distinguish hypotheses. Avoid spending many runs only confirming tiny local changes unless a peak has already been found and needs verification.

Use "batch" only as a search-design label. Execution is rolling: a completion, a resource change, or a changed result can trigger an immediate row transition, slot refill, and queue refill before the rest of the conceptual batch finishes. Analysis may append zero, one, or many ready candidates at once, not exactly one candidate per finished run.

## 4. Launch

Launch every configuration in its own run directory.

Launch rules:
- one experiment per command/session
- explicit GPU id
- unique output directory created before launch, normally with `aet.py unique-dir ... --mkdir`
- log path inside the unique output directory, normally `<output_dir>/train.log`; do not use a separate shared log directory
- standard launch shape: `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`
- use plain `python` by default so the command inherits the agent's startup environment; use an explicit interpreter path only when the active environment is wrong
- simple shell: avoid `cd`, command substitution, loops, pipes, and multi-command launch blocks
- before each launch wave, re-check resources, select as many `Ready Queue` rows as current free slots allow, assign run id/GPU/output/log fields, register each with `aet.py create-run`, record status `running` with `aet.py record --status running` after the process starts, and move each to `Running`

**Codex**: keep the command in a foreground tool session; do not add shell `&`. Poll active sessions with `write_stdin` at reasonable intervals.

**Claude Code**: use `run_in_background=True` on the Bash tool instead of foreground blocking. Multiple experiments can be launched in the same turn. See `references/claude-code-adapter.md`.

When a run finishes, immediately collect and record before launching more if the result changes the plan. Move the row to `Completed / Recorded`, update observations, re-check resources, then fill all currently usable slots from `Ready Queue`.

## 4.1 Task Management by Runtime

**Codex task management:**
- Keep the `Running` table in the session plan before launching: run id, hypothesis, GPU id, output directory, command, and expected metric file. `queue.jsonl` is only a recovery map created by `create-run`.
- After `exec_command` returns a long-running session id, record the mapping from Codex session id to run id. Do not rely on chat memory alone.
- Poll active sessions with `write_stdin` at reasonable intervals. Because stdout/stderr are redirected to the log file, use separate short reads of the log path when progress details are needed.
- Prefer direct commands such as `python -u SCRIPT --gpu_id N --output_dir DIR > DIR/train.log 2>&1`, where `DIR` already exists and was created as a unique run directory. Keep one experiment per tool session. Avoid launching more jobs than can be tracked and analyzed cleanly.
- Use `multi_tool_use.parallel` for independent file reads and status checks, not for launching several long-running experiments unless each launch remains a separate, trackable tool session.
- Use `spawn_agent` for Strategist/Runner/Analyzer roles only when the user explicitly requested subagents or delegation. Keep delegated work bounded and avoid assigning the next critical-path blocker to a subagent.
- Do not leave required experiment sessions running when sending the final answer. Either collect them, report that they are intentionally still running at the user's request, or stop before claiming completion.

**Claude Code task management:**
- Before launching, register each run with `aet.py create-run` so `queue.jsonl` receives the recovery map, and write the live row to `plan.md`: run id, hypothesis, GPU id, output directory, command, expected metric file.
- Launch all independent jobs in the same turn with `run_in_background=True`. You will receive a completion notification for each.
- After each background launch is accepted, call `aet.py record --status running` without routine notes so `results.csv` has a start time.
- On notification: identify the run from `Running`, collect results, record immediately, move it to `Completed / Recorded`, update `observations.md`, re-check resources, then launch as many `Ready Queue` candidates as current slots allow.
- Do not wait for all jobs in a candidate group to finish before recording the ones that completed first — incremental recording reduces exposure to context compaction loss.

**Both runtimes:**
- Check `nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader` before launching and during suspicious slowdowns. Memory alone is insufficient; high utilization can contaminate metrics for some methods. Use `references/gpu-policy.md` and `aet.py gpu-slots` to determine available slots (default: 1 per GPU, cap 3, util ceiling 95%); the helper normalizes the same fields for numeric filtering.
- Use `pgrep -af` only as a sanity check. It may match the `pgrep` command itself, and it does not prove which output directory belongs to a process. Prefer precise patterns such as `experiments/exp_` or the exact script name; broad patterns like `exp_` can match unrelated system threads.

## 5. Collection

For each finished run:
1. Verify output directory, metrics JSON/CSV/NPZ, images, and the in-output-dir log file exist.
2. Parse structured outputs first; use log regex only as fallback.
3. Record terminal status and metrics with `aet.py record`; include a concise `--notes` only after trust status is known.
4. Move the row from `Running` to `Completed / Recorded` in `plan.md`.
5. Append a short observation: what changed, whether it improved, and whether the run is trustworthy.
6. Update project benchmark tables immediately if the project requires it.

## 6. Analysis

Analyze after each completed run, not only at the end of the session:
- rank finished runs by the primary metric
- compare against baseline and previous best
- identify monotonic trends, discrete peaks, boundary hits, collapses, and contamination
- mark regions as promising, exhausted, forbidden, or inconclusive

Write reusable conclusions as rules. Example: "lambda=0.205 is an isolated peak; do not dense-scan 0.202-0.219 again."

Delegate detailed per-run analysis to the Analyzer subagent (see `agents/result-analyzer.md`). The Analyzer extracts optimization trajectories and convergence diagnostics and writes per-HP influence notes to `observations.md`. The main agent receives only the recorded primary metric and a one-line convergence note — this keeps main-agent context clean across a long multi-run session.

## 7. Next Queue

Choose candidates to add to `Ready Queue` using the search strategy reference:
- expand if best is on a boundary
- refine if a stable local peak is bracketed
- confirm if the result is surprising or affected by contention
- broaden if all recent runs are local variants and no escape group has been run
- stop only if a valid stop condition is met and the required evidence has been recorded

After every analysis pass:
- remove or rewrite unlaunched ready rows invalidated by the new evidence
- append as many informative candidates as the evidence justifies, including grids or interaction groups when appropriate, not necessarily one
- keep ready_count > current_free_slots while useful search remains
- immediately move ready rows into `Running` for any free slots

Before stopping, verify:
- explicit target is met, or an explicit budget is exhausted, or continuation is blocked
- at least one broad alternative regime has been tested after the current best was found
- the current best has been confirmed if it is surprising, benchmark-facing, or produced under different load
- the ledger records why further experiments are unlikely to change the user's decision

When a valid stop condition is met, produce a **Session Final Analysis** before closing:

1. **Best configuration found**: full parameter table of the best run, primary metric, and the run id.
2. **Per-HP influence summary**: for each tuned hyperparameter, state what was learned — which values worked, which failed, observed trends (monotone, peaked, interaction-dependent), and any coupling with other HPs. Draw from `observations.md` and the session ledger. Keep entries concise (1–2 sentences each).
3. **Future exploration directions**: list 2–5 specific directions that were not exhausted — unexplored regions, untested couplings, alternative schedules, or method-level changes that the trajectory diagnostics suggest might help.

Write the final analysis to the session's `observations.md` under a `## Final Analysis` heading, and include it in the response to the user. Run `aet.py summarize` alongside it for the quantitative run-count and metric statistics; the two serve different purposes and complement each other.

## 8. Recovery

After context compaction or interruption:
1. Locate latest session with `aet.py status --project-root PROJECT`.
2. Read `meta.json`, `plan.md`, `results.csv`, and `observations.md`.
3. Check active processes and GPU slots.
4. Reconcile any finished-but-unrecorded runs.
5. Resume from the next untested hypothesis.

If the recovered session has no active processes and the target is unmet, do not summarize and stop. Treat the idle state as a failure to continue: read the last observations, refill `Ready Queue` so it exceeds free slots, and relaunch.
