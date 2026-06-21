# Subagent Delegation Guide

Use this file before spawning or resuming the registered Strategist subagent.

## Agent Roles

### Strategist (`experiment-strategist`)

Returns: `observations_to_append` (per-HP influence notes for the runs handed to it) and Ready Queue candidates plus stop/continue text. Does not write session files; apply all returned outputs via `aet.py queue-add` / `queue-drop` and `session.md` edits.

## When to Delegate

| Trigger | Spawn | Required |
| ------- | ----- | -------- |
| Ready queue count < total_capacity (capacity_per_gpu × gpu_count, constant) | Strategist | Yes |

Queue count is the number of planned rows in `results.csv` (rows not yet launched).

Self-evaluatable conditions that may suppress a Strategist call: explicit user stop, explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable. Plateau and exhaustion are never self-evaluatable — Strategist must be the one to declare them; they cannot gate this call. **Recency of the last Strategist call and an empty pending set are not suppression conditions.**

## The Strategist Transaction: begin → tool_use → return

Calling the Strategist is your own tool_use (Agent/SendMessage on Claude Code, spawn_agent/send_input on Codex). It is bracketed by two `aet.py` bookkeeping calls that own the loop state machine. Run all three beats in order, every time:

**Beat 1 — `aet.py strategist-begin --session S`**
Bookkeeping only; it does not call the subagent. It snapshots the current pending runs, computes the route from `loop_state.json`, opens an `active_strategist_call`, and prints:
- `call_id`, `role` (`primary`|`confirmer`), `invocation` (`fresh`|`resume`), target agent id, blocking/background mode
- the exact spawn/resume tool call to make
- the payload (run list with status/metric pulled from `results.csv`) to pass to the subagent

If an `active_strategist_call` is already open, `strategist-begin` refuses. An open call means YOU still owe a `strategist-return` for it — it is not evidence the subagent is still running (the script cannot see the subagent). Resolve it against the subagent's real state: if it returned, `strategist-return` with its result; if its output is lost from your context, resume the same agent to re-request it; use `strategist-abort` only if that resume confirms the subagent is dead.

**Beat 2 — your subagent tool_use**, using Beat 1's branch and payload:
- Claude Code fresh: `Agent(subagent_type="experiment-strategist", prompt=<payload>, run_in_background=<mode>)`
- Claude Code resume: `SendMessage(to=<target_agent_id>, message=<payload>)` (always background)
- Codex fresh / confirmer: `spawn_agent(message=<payload>, fork_context=true)` with the registered custom agent `experiment-strategist`
- Codex resume: `send_input(target=<target_agent_id>, message=<payload>)`, then `wait_agent` when the result is needed

On a resume route, `SendMessage` is the literal tool named `SendMessage` — invoke it by name. A resume is not an `Agent` spawn: calling `Agent(subagent_type="experiment-strategist")` here cold-starts a new strategist and discards the accumulated context that is the entire reason to resume. Call `SendMessage` directly — it is a real, always-available tool, not something to pre-clear: its absence from `ToolSearch` or from your visible toolset does NOT mean it is unavailable; if its schema is not loaded, load it, then call it. The ONLY signal that resume failed is the call itself returning `success:false` (e.g. the transcript was cleaned up); knowing the agent is from a dead prior conversation is NOT that signal — make the call and let it fail. Only on `success:false` fall back to a fresh `Agent` spawn and pass `--resume-failed` to `strategist-return`. A resume that succeeds resumes the same agent id, so pass that same id (or omit `--agent-id`); a new id on a resume route without `--resume-failed` is recorded as a silent substitution and warned.

On a resume the Strategist keeps its prior session context, so the payload's new-run list plus current free slots and current best is enough — the full prompt template is only needed for a fresh spawn (or confirmer).

The subagent returns its five sections plus a short "Main Agent: Next Steps" block pointing back here.

**Beat 3 — `aet.py strategist-return --session S --call-id C --candidates-count K [--agent-id A] [--observations-present] [--queue-edits-present] [--stop-update-present]`** (`K` = how many Ready Queue candidates the Strategist returned; the script derives exhaustion from `K == 0`)
Validates the `call_id`, clears exactly the snapshot it opened (version-guarded, so runs that completed during analysis stay pending), records the agent id, applies the exhaustion handshake deterministically, and prints the `YOU` doc-update obligations. Follow its `YOU` block — `queue-add` the candidates, write observations/Stop-Continue into `session.md`, then `aet.py loop-state` to route the next action.

Between Beat 1 and Beat 3 (background Strategist on Claude Code), keep processing completion notifications; each `aet.py record` adds the new run to pending without disturbing the open call. Do not `sleep` or poll the Strategist's output file to wait for it — a background Strategist notifies you on completion. With nothing else to do, end the turn; that notification will wake you for Beat 3.

### Routing and the exhaustion handshake (owned by aet.py)

You do not hand-derive fresh-vs-resume-vs-confirmer, set flags, or evaluate plateau/exhaustion. `strategist-begin` computes the branch from `loop_state.json`; `strategist-return` applies the state transition:
- Primary returns candidates → continue.
- Returning zero candidates IS the exhaustion signal.
- Primary returns 0 candidates while quiescent (no `planned`/`created`/`running` runs, computed by the script) → the next `strategist-begin` is forced to a **fresh confirmer** (independent context).
- Confirmer returns 0 candidates while quiescent → `CONFIRMED_EXHAUSTION`; **you** own the final stop decision.
- Confirmer returns candidates → the Primary's exhaustion signal is overturned; the confirmer is promoted to Primary and the loop continues.
- A foreign-runtime or dead agent id makes the `SendMessage`/`send_input` resume return `success:false`; only then fall back to a fresh spawn. Pass `--resume-failed` to `strategist-return` either with the replacement's `--agent-id` (records it) or, if you have not spawned a replacement yet, alone (it clears the dead id so the next `strategist-begin` fresh-spawns instead of routing resume to the corpse again). A `--resume-failed` close with no `--agent-id` is pure dead-id cleanup — its placeholder candidate count does not feed the exhaustion handshake. Do not skip the resume tool_use and spawn fresh preemptively — a new agent id on a resume route without `--resume-failed` is flagged as a substitution (a fresh strategist was spawned instead of resuming, losing context).

Prompt neutrality: always use the standard prompt template below. Never add context about previous Strategist conclusions, never ask "is the search exhausted?", never prime the conclusion in any direction — including during confirmation. Do not echo plateau, ceiling, or exhaustion language from `session.md` into the prompt.

Record each completed run inline immediately (verify files → parse metrics → determine status → call `aet.py record`). `record` adds terminal runs to the pending set for you. Do not wait for a whole batch to finish before recording.

## Shared Call Inputs

Pass paths and stable context, not a parent-agent interpretation of results:
- `session_path`
- `project_root`
- relevant experiment scripts and CLI notes
- `algorithm_context`: metric meaning, target, benchmark constraints, known data/implementation risks, and important parameter couplings
- runtime notes: Codex vs Claude Code launch behavior, GPU policy, and current free slots when relevant

Pass only session-specific context in the prompt; the Strategist's role instructions are already loaded via its registered system prompt (`experiment-strategist`). `strategist-begin` prints the run list for `runs_since_last_strategist`; fill the rest of the template from session files.

## Strategist Call Template

```text
You are not alone in the codebase; other agents may be working. Do not revert unrelated changes.

session_path: SESSION_PATH
project_root: PROJECT_ROOT
experiment_scripts: SCRIPT_PATHS
cli_notes: CLI_NOTES
algorithm_context: METRIC/TARGET/RISKS/COUPLINGS
current_free_slots: N
total_capacity: M  # capacity_per_gpu × gpu_count (constant). Refill target: after the parent fills current_free_slots, queue count must stay >= total_capacity, so target queue count ≈ current_free_slots + total_capacity (= 2× total_capacity at session start when the queue is empty and all slots are free).
current_best: RUN_ID/METRIC as a locator only
runs_since_last_strategist: [run_id list with recorded status, primary_metric, metric_name from results.csv — copy the line printed by strategist-begin]
# Values above are raw fields from results.csv — not interpreted conclusions about trends or plateau.

Read SESSION_PATH/meta.json (objective, metric direction, project root), results.csv (all run data including planned rows = current queue), session.md (hypotheses, reusable rules, current analysis, stop rule), and important runs/<id>/{params.json,metrics.json} artifacts directly.

Tasks:
0. Generate observations: for runs in runs_since_last_strategist, read their artifacts directly (runs/<id>/metrics.json, params.json, output/train.log) and synthesize per-HP influence notes (patterns, boundary hits, forbidden regions, settings that help only under specific companion knobs). Return as observations_to_append. Omit if nothing new. **If runs_since_last_strategist is empty (session start / first call), skip observations entirely and proceed directly to task 1 — plan initial candidates from meta.json's objective and session.md's hypotheses and coupled parameters.**
1. Determine whether the next candidates should broaden, refine, confirm, expand a boundary, or run an escape group.
2. Return enough Ready Queue candidates that after the parent fills the current free slots, queue count stays at or above total_capacity — target queue count ≈ current_free_slots + total_capacity (= 2× total_capacity at session start, since the queue is empty and all slots are free). Returning only total_capacity lets the first launch wave drain the queue and forces a redundant blocking re-call against the same result state.
3. Include per-HP rationale for non-obvious values, cited from run evidence.
4. Return stop/continue rule updates and any existing queued runs the parent should rewrite or remove (reference them by run_id from results.csv).

Do not write any session file.
Return:
0. observations_to_append (per-HP influence notes; omit if nothing new).
1. Ready Queue Candidates as a JSON array; each element:
   {"queue_id": "Q42", "hypothesis": "...", "params": {...}, "priority": 1, "expected_signal": "..."}
2. Stop/Continue Rule Update.
3. Queue Edits (run_ids to rewrite/remove).
4. Escape/Confirmation Need.
```

## Interpreting Returns

Run `aet.py strategist-return` (Beat 3) and follow its `YOU` block. The script clears the snapshot, records the agent id, and applies the handshake; its `YOU` output lists exactly what to update — gated by the `--observations-present` / `--queue-edits-present` / `--stop-update-present` flags you pass and by the returned candidate count:
- run `aet.py queue-add --candidates '<JSON>'`, passing the Strategist's Ready Queue Candidates JSON array verbatim; this writes the new planned rows into `results.csv`
- run `aet.py queue-drop` for each run_id in Queue Edits to remove invalidated planned rows
- write `observations_to_append` into `session.md`'s Current Analysis section (overwrite it) and update the Stop/Continue Rule section
- then `aet.py loop-state` and launch the highest-priority planned rows into any free slots with `aet.py create-run --run-id <id> --gpu-id <gpu>` (the run-id points to a planned row from `queue-add`), one experiment at a time (Claude Code: one `Bash(run_in_background=True)` per experiment; Codex: one `exec_command` foreground session per experiment, recording any `session_id -> run_id/output_dir/log_path`).

On `CONFIRMED_EXHAUSTION`, the script hands you the stop: verify the target/budget is genuinely unmet, write `## Final Analysis` into `session.md`, run `aet.py summarize`, then stop the keepalive. You may still continue if you judge it premature; the next `strategist-begin` forms a fresh handshake.
