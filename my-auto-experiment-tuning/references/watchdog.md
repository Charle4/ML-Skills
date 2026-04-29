# Keepalive / Watchdog

Use this file to set up periodic self-reminders that prevent an autonomous tuning session from going idle.

## Capabilities by Runtime

| Capability | Codex | Claude Code |
|---|---|---|
| Keep working during active turn | ✓ | ✓ |
| `run_in_background=True` (Bash tool) | ✗ | ✓ |
| Notification on background job completion | ✗ | ✓ |
| Native `/loop` timer for periodic wakeup | ✗ | ✓ |
| Wake a closed/idle conversation | ✗ | ✗ (needs external trigger) |

## Claude Code: Native `/loop` Keepalive

Claude Code has a `/loop` command that sends a recurring prompt at a fixed interval within the same session. Use this at skill init time to ensure the tuning loop is re-checked even if the current turn ends or the agent is waiting on background jobs.

**When to set it up**: immediately after creating the AET session, before launching the first batch.

**Command to run** (in conversation, not in shell):

```
/loop 1h /my-auto-experiment-tuning Continue fine-tuning parameters; target PSNR > XX (if specified when enabled); expand the range if trapped in a local optimum; maintain GPU usage; ignore if working normally.
```

If the user provided a numeric target (e.g., `PSNR > 25`), embed it in the prompt. If not, omit the target clause. The "ignore if working normally" tail means the loop does nothing when the session is already busy, making it safe to leave running.

**Interval guideline**: 1 h is appropriate for long tuning sessions. Use 30 m if runs are short and you want tighter keep-alive. Do not set shorter than 20 m — it creates noise.

**When to stop the loop**: invoke `/loop` again with `stop` or adjust the interval when the target is met or the user ends the session.

## Claude Code: Background Job Notifications

With `run_in_background=True`, the Bash tool notifies Claude Code when the command finishes. This means:
- You do not need to poll or sleep between experiments.
- On notification, immediately collect results, record them, and launch the next batch.
- If multiple experiments run in parallel, each notification triggers an incremental collect-and-plan pass.

See `references/claude-code-adapter.md` for the full background job pattern.

## Codex: External Keepalive (Cron / systemd)

Codex cannot self-wake. An external scheduler must send a follow-up prompt.

## Keepalive Prompt

If an external scheduler can send a message to the active conversation, use a short prompt like:

```text
$my-auto-experiment-tuning Continue the existing tuning session. Keep GPUs occupied within contention limits. Do not stop unless the explicit target is met, the user budget is exhausted, or continuation is blocked. If recent runs are stuck in a local optimum, broaden the search space and run an escape batch. Record results and update the benchmark ledger.
```

If the objective has a numeric target, include it:

```text
$my-auto-experiment-tuning Continue the existing tuning session. Target: PSNR > 25 on the benchmark metric. Keep launching batches until a clean run reaches the target or the user stops the job. If no active experiments are running, inspect the ledger and launch the next batch immediately.
```

## Watchdog Behavior

A good external watchdog should:
- run every 30-60 minutes for multi-day tuning
- check whether GPU jobs for the session are active
- if the session is idle and the target is unmet, send the keepalive prompt
- include the project root, session path, target metric, and current target threshold
- avoid starting duplicate sessions unless the previous one is unrecoverable

Do not rely on the watchdog to replace the skill's normal autonomy. The main agent should still keep launching batches during an active turn.
