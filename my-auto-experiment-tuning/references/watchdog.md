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
| Native recurring-prompt timer (`CronCreate`) | ✗ | ✓ |
| Wake an idle REPL | ✗ | ✓ (`CronCreate`) |
| Wake a closed conversation | ✗ | ✗ (needs external trigger) |

## Claude Code: Native Keepalive (CronCreate)

Follow [claude-code-adapter.md](claude-code-adapter.md) section "Periodic Keepalive (CronCreate)" immediately after session creation. It is the canonical `CronCreate` call, cadence, lifetime, and cancellation protocol. Run the first cycle immediately after scheduling.

## Claude Code: Background Job Notifications

With `run_in_background=True`, the Bash tool notifies Claude Code when the command finishes. This means:
- You do not need to poll or sleep between experiments.
- On notification, immediately identify the run and record inline: verify output files, parse metrics (JSON/CSV/NPZ → TensorBoard → log regex), determine status, call `aet.py record` (which adds the terminal run to the pending set and writes the terminal row to `results.csv`), then `aet.py loop-state` to re-check resources and route launches/Strategist.
- If multiple experiments run in parallel, each notification triggers an incremental inline-record → queue-refill pass.

See [claude-code-adapter.md](claude-code-adapter.md) for the full background job pattern.

## Codex: External Keepalive (Cron / systemd)

Codex cannot self-wake and has no background completion notification. During an active turn, a long-running `exec_command` may return a `session_id`; the run's `run_id -> output_dir -> log_path` mapping lives in its `results.csv` row (written at `create-run`), and you poll the handle with `write_stdin`. After the turn ends, an external scheduler must send a follow-up prompt if continued supervision is required.

## Keepalive Message

If an external scheduler can send a message to the active conversation, use a short prompt like:

```text
$my-auto-experiment-tuning Continue the existing tuning session. Run `aet.py loop-state` and follow its routing. Apply any durable benchmark-update debt first and acknowledge successful project-table writes with `aet.py benchmark-ack`. Keep GPUs occupied within contention limits and stop only for a recorded valid stop condition.
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
- if processes finished while Codex was idle, reconcile `results.csv`, logs, and output directories on resume, then record each finished-but-unrecorded run inline
- include the project root, session path, target metric, and current target threshold
- continue the explicitly identified existing session; create a new session only for a new tuning objective

Do not rely on the watchdog to replace the skill's normal autonomy. Keep filling available slots and replenishing the ready queue during an active turn.
