Read this file only when re-attaching a runtime to an existing on-disk AET session — a `CronCreate` keepalive tick, a post-compaction continuation, or a user request to continue a prior loop. Not on a fresh start (that path is `aet.py init` per SKILL.md Quick Start).

# Recovery

The AET session on disk (`aet/YYYY-MM-DD/HH-MM-SS/`) outlives any single runtime context. Recovery means re-attaching a runtime to that on-disk session; never `aet.py init` during recovery — that starts a new session and fragments the ledger. There are two kinds, differing in what already carries over into the runtime.

## Same conversation, context compacted

The conversation thread is unchanged, so the keepalive (the `CronCreate` job / external cron) is still running — do not create a second one — and the session path is carried in the conversation summary. Compaction may have dropped the skill's detailed instructions from context; re-read SKILL.md and the core references if they are gone. Then:
1. `aet.py status --session SESSION` — if the results.csv terminal count exceeds the plan.md Completed entries, reconcile plan.md from results.csv first.
2. Re-read `meta.json`, `plan.md`, `results.csv`, and `observations.md` if they left context.
3. Run `aet.py loop-state` to recover the Strategist state machine (pending set, agent id, any open call, exhaustion handshake) and the routed next action. If `loop_state.json` was lost it rebuilds pending conservatively from terminal runs. An open `active_strategist_call` means you still owe a `strategist-return`, not that the subagent is running — its YOU block routes you to check the subagent, `strategist-return` if it finished, resume it if its output is lost, and `strategist-abort` only if it is truly dead.
4. Check active processes and GPU slots; reconcile any finished-but-unrecorded runs with `aet.py record`.
5. Resume from the routed action / next untested hypothesis.

## New conversation or process

Nothing carries over: no skill loaded, no docs in context, no keepalive running. Run the full startup bootstrap exactly as a fresh start — read SKILL.md and the core references, detect runtime, and re-establish the keepalive (Claude Code `CronCreate`; Codex external cron, see `watchdog.md`) — with one difference: do not `init`. Identify which on-disk session to resume from the user's explicit intent; only then locate it with `aet.py status --project-root PROJECT`. An idle on-disk session is not by itself authorization to resume it — do not scan `aet/` and adopt the latest session on your own. Once the session is identified, follow the "Same conversation" steps 1–5 above.

In both kinds, if the recovered session has no active processes and the target is unmet, do not summarize and stop. Treat the idle state as a failure to continue: read the last observations, refill `Ready Queue` to at least total_capacity, and relaunch.
