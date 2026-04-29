# Workflow

Use this file when starting or resuming an autonomous tuning job.

## Autonomy Contract

After the user states the tuning target, benchmark setting, constraints, and budget/principles, continue without asking for approval at each iteration. The main agent owns the loop:
- infer the current state
- plan the next batch
- launch experiments within allowed permissions
- monitor and collect results
- update ledgers and benchmark docs
- decide the next batch

Escalate to the user only for destructive operations, ambiguous goals, missing required permissions, budget changes, or actions outside the active sandbox/approval policy.

Default duration semantics:
- Treat autonomous tuning as a long-running job, not a short investigation. If the user asks for broad tuning, abundant GPU use, or a target such as `PSNR > 25`, expect tens to hundreds of runs and possibly multi-day operation.
- Do not end after 1-3 batches just because a plausible local best was found. A local best is a signal for the next batch, not a stopping reason.
- If no explicit run or wall-clock budget is provided, assume the budget is open-ended until the user intervenes or the target is cleanly met.
- Keep all usable GPU slots occupied within the configured contention limits. When any run finishes, immediately collect it, record metrics, and launch the next candidate from the queue into the freed slot — do not wait for other running experiments to finish first.
- If the system forces a final response before the target is met, report the next batch and the reason continuation is blocked; do not present a local best as final.

## 1. Context Pass

Read the minimum files that define the experiment contract:
- repository agent instructions
- experiment README or benchmark docs
- target script argparse/config definitions
- existing run ledgers, result tables, or project memory

Do not repeatedly reread large files after extracting stable rules. Write durable summaries to the session observations or the project's memory mechanism.

## 2. Session Setup

Create one `aet/YYYY-MM-DD/HH-MM-SS/` session per tuning objective.

Required session fields:
- objective and metric direction
- explicit target threshold, if any
- project root
- target scripts/commands
- known baselines and current best results
- run trust constraints, such as GPU contention limits
- budget: max runs, wall time, or `open-ended until target/user stop`
- minimum stopping evidence: required broad escape batches, refinements, confirmations, and minimum run count before plateau can be claimed

Use:

```bash
python SKILL_DIR/scripts/aet.py init --project-root PROJECT --name NAME --objective OBJECTIVE --goal max
```

## 3. Planning

Before launching a batch, write the next-step plan:
- hypothesis being tested
- parameter dimensions and values
- expected signal if the hypothesis is true
- risk that could invalidate the batch
- exact launch commands or command template
- expected follow-up if the batch improves, fails, or lands on a boundary
- remaining stop blockers, such as unmet target, missing escape batch, missing confirmation, or unused plausible parameter families

Prefer batches that distinguish hypotheses. Avoid spending many runs only confirming tiny local changes unless a peak has already been found and needs verification.

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

**Codex**: keep the command in a foreground tool session; do not add shell `&`. Poll active sessions with `write_stdin` at reasonable intervals.

**Claude Code**: use `run_in_background=True` on the Bash tool instead of foreground blocking. Multiple experiments can be launched in the same turn. See `references/claude-code-adapter.md`.

When a run finishes, immediately collect and record before launching more if the result changes the plan.

## 4.1 Task Management by Runtime

**Codex task management:**
- Keep a small run map in the session plan or queue before launching: run id, hypothesis, GPU id, output directory, command, and expected metric file.
- After `exec_command` returns a long-running session id, record the mapping from Codex session id to run id. Do not rely on chat memory alone.
- Poll active sessions with `write_stdin` at reasonable intervals. Because stdout/stderr are redirected to the log file, use separate short reads of the log path when progress details are needed.
- Prefer direct commands such as `python -u SCRIPT --gpu_id N --output_dir DIR > DIR/train.log 2>&1`, where `DIR` already exists and was created as a unique run directory. Keep one experiment per tool session. Avoid launching more jobs than can be tracked and analyzed cleanly.
- Use `multi_tool_use.parallel` for independent file reads and status checks, not for launching several long-running experiments unless each launch remains a separate, trackable tool session.
- Use `spawn_agent` for Strategist/Runner/Analyzer roles only when the user explicitly requested subagents or delegation. Keep delegated work bounded and avoid assigning the next critical-path blocker to a subagent.
- Do not leave required experiment sessions running when sending the final answer. Either collect them, report that they are intentionally still running at the user's request, or stop before claiming completion.

**Claude Code task management:**
- Before launching a batch, write the run map to `queue.jsonl` in the session directory: run id, hypothesis, GPU id, output directory, command, expected metric file. This is the recovery record if the session is interrupted.
- Launch all independent jobs in the same turn with `run_in_background=True`. You will receive a completion notification for each.
- On notification: identify the run from the queue, collect results, record immediately, update `observations.md`, then decide the next step.
- Do not wait for all jobs in a batch to finish before recording the ones that completed first — incremental recording reduces exposure to context compaction loss.

**Both runtimes:**
- Check `nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader` before launching and during suspicious slowdowns. Memory alone is insufficient; high utilization can contaminate metrics for some methods. Use `references/gpu-policy.md` and `aet.py gpu-slots` to determine available slots (default: 1 per GPU, cap 3, util ceiling 95%); the helper normalizes the same fields for numeric filtering.
- Use `pgrep -af` only as a sanity check. It may match the `pgrep` command itself, and it does not prove which output directory belongs to a process. Prefer precise patterns such as `experiments/exp_` or the exact script name; broad patterns like `exp_` can match unrelated system threads.

## 5. Collection

For each finished run:
1. Verify output directory, metrics JSON/CSV/NPZ, images, and the in-output-dir log file exist.
2. Parse structured outputs first; use log regex only as fallback.
3. Record metrics with `aet.py record`.
4. Append a short observation: what changed, whether it improved, and whether the run is trustworthy.
5. Update project benchmark tables immediately if the project requires it.

## 6. Analysis

Analyze after each completed run, not only at the end of the session:
- rank finished runs by the primary metric
- compare against baseline and previous best
- identify monotonic trends, discrete peaks, boundary hits, collapses, and contamination
- mark regions as promising, exhausted, forbidden, or inconclusive

Write reusable conclusions as rules. Example: "lambda=0.205 is an isolated peak; do not dense-scan 0.202-0.219 again."

Delegate detailed per-run analysis to the Analyzer subagent (see `agents/result-analyzer.md`). The Analyzer extracts optimization trajectories and convergence diagnostics and writes per-HP influence notes to `observations.md`. The main agent receives only the recorded primary metric and a one-line convergence note — this keeps main-agent context clean across a long multi-batch session.

## 7. Next Batch

Choose the next batch using the search strategy reference:
- expand if best is on a boundary
- refine if a stable local peak is bracketed
- confirm if the result is surprising or affected by contention
- broaden if all recent runs are local variants and no escape batch has been run
- stop only if a valid stop condition is met and the required evidence has been recorded

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

If the recovered session has no active processes and the target is unmet, do not summarize and stop. Treat the idle state as a failure to continue: read the last observations, design the next batch, and relaunch.
