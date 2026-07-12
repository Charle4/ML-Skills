# Subagent Delegation Guide

Use this file before spawning or resuming the registered Strategist subagent.

## Agent Roles

### Strategist (`experiment-strategist`)

Returns six sections: evidence-linked observations, reusable rules, Ready Queue candidates, stop/continue text, Queue Edits, and escape/confirmation need. Does not write session files; apply all returned outputs via `aet.py queue-add` / `queue-drop` and `session.md` edits.

## When to Delegate

| Trigger | Spawn | Required |
| ------- | ----- | -------- |
| `projected_ready_after_launch < total_capacity` under the stored GPU policy | Strategist | Yes |

`projected_ready_after_launch = planned_count - min(current_free_slots, planned_count)`. It is the planned queue that remains after the launch pairings printed for this cycle.

Agent-side suppression conditions: explicit user stop, explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable. Plateau and exhaustion are never self-evaluatable — Strategist must be the one to declare them. `loop-state` handles state-unchanged detection automatically (routes a wait when session state is identical to the last Strategist call); always run it and follow its `YOU`.

## The Strategist Transaction: begin → tool_use → return

Calling the Strategist is your own tool_use (Agent/SendMessage on Claude Code, spawn_agent/send_message/followup_task on Codex). It is bracketed by two `aet.py` bookkeeping calls that own the loop state machine. Run all three beats in order, every time:

**Beat 1 — `aet.py strategist-begin --session S`**
Bookkeeping only; it does not call the subagent. It snapshots the current pending runs, computes the route from `loop_state.json`, opens an `active_strategist_call`, and prints:
- `call_id`, `role` (`primary`|`confirmer`), `invocation` (`fresh`|`resume`), target agent id, blocking/background mode
- the exact spawn/resume tool call to make
- the payload (run list with status/metric)

If an `active_strategist_call` is already open, `strategist-begin` refuses. An open call means YOU still owe a close for it — it is not evidence the subagent is still running. If it returned, use `strategist-return` with its result. If a resume-route call fails on the actual resume tool, close with `strategist-return --resume-failed`. Reserve `strategist-abort` for an open fresh call whose spawn failed, whose spawned subagent is truly unreachable, or which was cancelled.

**Beat 2 — your subagent tool_use**, using Beat 1's branch and payload:
- Claude Code fresh: `Agent(subagent_type="experiment-strategist", prompt=<payload>, run_in_background=<mode>)`
- Claude Code resume: `SendMessage(to=<target_agent_id>, message=<payload>)` (always background)
- Codex fresh / confirmer: `spawn_agent(task_name="experiment_strategist", message=<payload>, fork_turns="all")`
- Codex resume: inspect the target with `list_agents`; use `send_message(target=<target_agent_id>, message=<payload>)` while it is running or `followup_task(target=<target_agent_id>, message=<payload>)` while it is idle, then `wait_agent`

Claude Code resume only: output the `SendMessage` tool call directly — it always works. Do NOT skip it because the schema appears missing or "not loaded"; that is not a real error (anti-pattern #12). A successful resume keeps the same agent id, so pass that id or omit `--agent-id`. If `SendMessage` returns `success:false`, close the open resume transaction with pure `--resume-failed` cleanup; the next `strategist-begin` fresh-spawns.

Codex resume only: inspect the target with `list_agents`, then use `send_message` while running or `followup_task` while idle. If the actual resume call fails, close the open resume transaction with pure `--resume-failed` cleanup; the next `strategist-begin` fresh-spawns.

On a resume the Strategist keeps its prior session context, so the payload's new-run list plus current free slots and current best is enough — the full prompt template is only needed for a fresh spawn (or confirmer).

The subagent returns its six sections plus a short "Main Agent: Next Steps" block pointing back here.

**Beat 2.5 — read the Strategist's output (mandatory)**
When the Strategist returns (completion notification for background, or inline for blocking), read its full response: Ready Queue Candidates JSON, observations, reusable rules, stop/continue update, queue edits, and escape/confirmation need. Count the actual candidates. This is the `K` you pass to Beat 3. Closing with `--candidates-count 0` without reading the output is data falsification (anti-pattern #11) — it poisons the exhaustion handshake with a fabricated signal.

**Beat 3 — `aet.py strategist-return --session S --call-id C --candidates-count K [--agent-id A] [--observations-present] [--reusable-rules-present] [--queue-edits-present] [--stop-update-present]`** (`K` = how many Ready Queue candidates the Strategist **actually returned**; the script derives exhaustion from `K == 0`)
Validates the call, confirmer identity, and evidence versions before clearing state. Pure `--resume-failed` cleanup consumes no pending runs.
Every fresh invocation requires `--agent-id`; `K` must be non-negative.

Between Beat 1 and Beat 3 (background Strategist on Claude Code), keep processing completion notifications; each `aet.py record` adds the new run to pending without disturbing the open call. Do not `sleep` or poll the Strategist's output file to wait for it — a background Strategist notifies you on completion. With nothing else to do, end the turn; that notification will wake you for Beat 3.

### Routing and the exhaustion handshake (owned by aet.py)

You do not hand-derive fresh-vs-resume-vs-confirmer, set flags, or evaluate plateau/exhaustion. `strategist-begin` computes the branch from `loop_state.json`; `strategist-return` applies the state transition:
- Primary returns candidates → continue.
- Returning zero candidates IS the exhaustion signal.
- Primary returns 0 candidates while quiescent (no `planned`/`created`/`running` runs, computed by the script) → the next `strategist-begin` is forced to a **fresh confirmer** (independent context).
- Confirmer return requires its fresh agent id. The script refuses a missing id or an id equal to the Primary id.
- A distinct confirmer returns 0 candidates while quiescent → `CONFIRMED_EXHAUSTION`; apply every returned session update before the final stop steps printed by the script.
- Confirmer returns candidates → the Primary's exhaustion signal is overturned; the confirmer is promoted to Primary and the loop continues.
- A foreign-runtime or dead agent id makes the runtime resume call fail. Only after that actual failure, close with `strategist-return --resume-failed --candidates-count 0`, without agent id or presence flags. This pure cleanup consumes no pending evidence and makes the next `strategist-begin` fresh-spawn.

Prompt neutrality: always use the standard prompt template below. Never add context about previous Strategist conclusions, never ask "is the search exhausted?", never prime the conclusion in any direction — including during confirmation. Do not echo plateau, ceiling, or exhaustion language from `session.md` into the prompt.

Record each completed run inline immediately (verify files → parse metrics → determine status → call `aet.py record`). `record` adds terminal runs to the pending set for you. Do not wait for a whole batch to finish before recording.

## Shared Call Inputs

Pass paths and stable context, not a parent-agent interpretation of results:
- `session_path`
- `project_root`
- relevant experiment scripts and CLI notes
- `algorithm_context`: metric meaning, target, evaluation constraints, known data/implementation risks, and important parameter couplings
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
total_capacity: M  # capacity_per_gpu × gpu_count under the current stored policy. Refill target: after the parent fills current_free_slots, queue count must stay >= total_capacity, so target queue count ≈ current_free_slots + total_capacity (= 2× total_capacity at session start when the queue is empty and all slots are free).
current_best: RUN_ID/METRIC as a locator only
runs_since_last_strategist: [run_id list with recorded status, primary_metric, metric_name from results.csv — copy the line printed by strategist-begin]
# Values above are raw fields from results.csv — not interpreted conclusions about trends or plateau.

Read SESSION_PATH/meta.json (objective, metric direction, project root), results.csv (all run data including planned rows = current queue), session.md (Evaluation Contract, hypotheses, reusable rules, current analysis, stop rule), and important runs/<id>/{params.json,metrics.json} artifacts directly.

Tasks:
0. Generate evidence-linked observations: for runs in runs_since_last_strategist, read their artifacts directly (runs/<id>/metrics.json, params.json, output/train.log, and best model/program/config artifacts when available). Compare the primary metric with secondary, per-case/seed/slice or worst-case, failure, and stability metrics; synthesize per-HP influence notes without treating an aggregate gain as robustness. Return as observations_to_append. Omit if nothing new. **If runs_since_last_strategist is empty (session start / first call), skip observations entirely and proceed directly to task 1 — plan initial candidates from meta.json's objective and session.md's hypotheses and coupled parameters.**
1. Determine whether the next candidates should broaden, refine, confirm, expand a boundary, or run an escape group.
2. Count existing planned rows, then return enough Ready Queue candidates that after the parent fills the current free slots, queue count stays at or above total_capacity. Target the resulting queue count at current_free_slots + total_capacity (= 2× total_capacity at session start, since the queue is empty and all slots are free); subtract existing planned rows when deciding how many new candidates to return.
3. Include per-HP rationale for non-obvious values, cited from run evidence.
4. If evaluator fidelity, metric headroom, failure handling, or aggregate-vs-slice robustness is unresolved, prioritize diagnostic probe/baseline/held-out/confirmation candidates and state the decision evidence required before exploitation.
5. Return stop/continue rule updates and any existing queued runs the parent should rewrite or remove (reference them by run_id from results.csv).

Do not write any session file.
Return:
0. Evidence-Linked Observations as observations_to_append (per-HP influence notes; omit if nothing new).
1. reusable_rules_to_append (cross-target parameter patterns only; per-target stop conclusions go in observations or Stop/Continue Rule, not here; `none` when empty).
2. Ready Queue Candidates as a JSON array; each element:
   {"queue_id": "Q42", "hypothesis": "...", "params": {...}, "priority": 1, "expected_signal": "...", "rationale": "..."}
3. Stop/Continue Rule Update.
4. Queue Edits (run_ids to rewrite/remove).
5. Escape/Confirmation Need.
```

## Interpreting Returns

Run `aet.py strategist-return` (Beat 3) and follow its `YOU` block. The script version-clears only represented snapshot entries, records the agent id, and applies the handshake:
- run `aet.py queue-add --candidates '<JSON>'`, passing the Strategist's Ready Queue Candidates JSON array verbatim; this writes the new planned rows into `results.csv`
- run `aet.py queue-drop` for each run_id in Queue Edits to remove invalidated planned rows
- write `observations_to_append` into Current Analysis, append `reusable_rules_to_append` to Reusable Rules, and overwrite Stop/Continue Rule when those sections are present
- then `aet.py loop-state` and launch the highest-priority planned rows into any free slots with `aet.py create-run --run-id <id> --gpu-id <gpu>` (the run-id points to a planned row from `queue-add`), one experiment at a time (Claude Code: one `Bash(run_in_background=True)` per experiment; Codex: one `exec_command` foreground session per experiment, recording any `session_id -> run_id/output_dir/log_path`).

On `CONFIRMED_EXHAUSTION`, the script hands you the stop: verify the target/budget is genuinely unmet, write `## Final Analysis` into `session.md`, run `aet.py summarize`, then stop the keepalive. You may still continue if you judge it premature; the next `strategist-begin` forms a fresh handshake.
