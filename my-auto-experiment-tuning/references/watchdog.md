Read this file only when setting up a keepalive or external watchdog for a long tuning session.

# Keepalive / Watchdog

Use this file to set up periodic self-reminders that prevent an autonomous tuning session from going idle.

## Capabilities by Runtime

| Capability | Codex | Claude Code |
|---|---|---|
| Keep working during active turn | ✓ | ✓ |
| Long-running experiment handle | `exec_command` may yield a `session_id`; poll with `write_stdin` | `Bash(run_in_background=True)` job notification |
| `run_in_background=True` (Bash tool) | ✗ | ✓ |
| Notification on background job completion | ✗ | ✓ |
| Native `/loop` timer for periodic wakeup | ✗ | ✓ |
| Wake a closed/idle conversation | ✗ | ✗ (needs external trigger) |

## Claude Code: Native `/loop` Keepalive

Claude Code has a `/loop` command that sends a recurring prompt at a fixed interval within the same session. Use this at skill init time to ensure the tuning loop is re-checked even if the current turn ends or the agent is waiting on background jobs.

**When to set it up**: immediately after creating the AET session, before launching the first runs.

**Command to run** (in conversation, not in shell):

```
/loop 1h /my-auto-experiment-tuning Continue fine-tuning. Target: PSNR > XX (substitute actual target, or omit if none). Keep GPUs occupied. At the start of each invocation: (1) run `aet.py status` — if results.csv finished count exceeds plan.md Completed entries, reconcile plan.md from results.csv first; (2) run `aet.py loop-state` (it counts the Ready Queue from plan.md itself) and follow its YOU block — it routes any launches and the Strategist transaction (begin -> subagent tool_use -> return) for you; the script owns the Strategist routing and exhaustion handshake. Skip this prompt only if you are currently mid-execution of these steps in this exact conversation turn.
```

If the user provided a numeric target (e.g., `PSNR > 25`), embed it in the prompt. If not, omit the target clause. The escape clause prevents re-entry only when you are already mid-execution in the same turn — it does NOT apply just because experiments are running or no new completions occurred.

**Interval guideline**: 1 h is appropriate for long tuning sessions. Use 30 m if runs are short and you want tighter keep-alive. Do not set shorter than 20 m — it creates noise.

**When to stop the loop**: invoke `/loop stop` only when the user ends the session or a valid stop condition has been recorded and the session is being closed. Do not stop the loop merely because one run hit a local or provisional target.

## Claude Code: Background Job Notifications

With `run_in_background=True`, the Bash tool notifies Claude Code when the command finishes. This means:
- You do not need to poll or sleep between experiments.
- On notification, immediately identify the run and record inline: verify output files, parse metrics (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record` (which adds the terminal run to the pending set), append trust details to `summary.md`, move to `Completed / Recorded`, then `aet.py loop-state` to re-check resources and route launches/Strategist.
- If multiple experiments run in parallel, each notification triggers an incremental inline-record → queue-refill pass.

See `references/claude-code-adapter.md` for the full background job pattern.

## Codex: External Keepalive (Cron / systemd)

Codex cannot self-wake and has no background completion notification. During an active turn, a long-running `exec_command` may return a `session_id`; record `session_id -> run_id/output_dir/log_path` in `plan.md` and poll it with `write_stdin`. After the turn ends, an external scheduler must send a follow-up prompt if continued supervision is required.

## Keepalive Message

If an external scheduler can send a message to the active conversation, use a short prompt like:

```text
$my-auto-experiment-tuning Continue the existing tuning session. Keep GPUs occupied within contention limits. Do not stop unless a valid stop condition is recorded: clean target evidence, exhausted budget, user stop, or blocked continuation. If the Ready Queue is insufficient or a stop condition is not clearly met, run `aet.py loop-state` and follow its routing (it runs the Strategist transaction with the standard neutral prompt). Record results and update the benchmark ledger.
```

If the objective has a numeric target, include it:

```text
$my-auto-experiment-tuning Continue the existing tuning session. Target: PSNR > 25 on the benchmark metric. Keep filling available GPU slots from the ready queue until a clean run reaches the target or the user stops the job. If no active experiments are running, inspect the ledger, replenish ready candidates, and launch as resources allow immediately.
```

## Watchdog Behavior

A good external watchdog should:
- run every 30-60 minutes for multi-day tuning
- check whether GPU jobs for the session are active
- if the session is idle and the target is unmet, send the keepalive prompt
- if processes finished while Codex was idle, the resumed agent should reconcile `plan.md`, `results.csv`, logs, and output directories, then record each finished-but-unrecorded run inline
- include the project root, session path, target metric, and current target threshold
- avoid starting duplicate sessions unless the previous one is unrecoverable

Do not rely on the watchdog to replace the skill's normal autonomy. Keep filling available slots and replenishing the ready queue during an active turn.
