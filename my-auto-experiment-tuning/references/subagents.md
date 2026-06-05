# Subagent Delegation Guide

Use this file before spawning the registered Strategist subagent.

## Agent Roles

### Strategist (`experiment-strategist`)

Returns: `observations_to_append` (per-HP influence notes for `runs_since_last_strategist`) and Ready Queue candidates plus stop/continue text. Does not write `plan.md` or `observations.md`; apply all returned outputs.

## When to Delegate

| Trigger | Spawn | Required |
| ------- | ----- | -------- |
| Ready Queue count < total_capacity (capacity_per_gpu × gpu_count, constant) | Strategist — blocking if queue empty; background if queue non-empty where the runtime supports it. **Claude Code**: prefer `SendMessage` resume if `strategist_agent_id` is set, except a fresh confirmer spawn when `pending_exhaustion_confirmation` is true. **Codex**: prefer `send_input(target=strategist_agent_id, ...)` if `strategist_agent_id` is set, except a fresh confirmer spawn when `pending_exhaustion_confirmation` is true (see continuation protocols below) | Yes |

Self-evaluatable conditions that may suppress a Strategist call: explicit user stop, explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable. Plateau and exhaustion are never self-evaluatable — Strategist must be the one to declare them; they cannot gate this call. **Recency of the last Strategist call and empty `runs_since_last_strategist` are not suppression conditions.**

## Strategist Continuation Protocol (Claude Code only)

After the first successful Strategist spawn, prefer resuming it via `SendMessage` over spawning fresh:

1. Check `pending_exhaustion_confirmation` first, then `strategist_agent_id`, in plan.md Loop State before every Strategist call.
2. **`pending_exhaustion_confirmation` is true** (the continuous-context Primary already declared exhaustion while quiescent): spawn a **fresh confirmer** — `Agent(subagent_type="experiment-strategist", run_in_background=False, ...)` with the full standard neutral prompt. Do NOT `SendMessage` the Primary: confirming an exhaustion verdict by re-messaging the context that produced it gives no independence. On return: if the confirmer also returns 0 candidates + exhaustion → confirmed, stop per SKILL.md Default Stopping Rules; if it returns candidates → overturn the Primary, append candidates, **promote** (set `strategist_agent_id` ← confirmer `agentId`, set `pending_exhaustion_confirmation: false`), and continue. This gate overrides the `strategist_agent_id` cases below.
3. **`strategist_agent_id` not null** (and not pending confirmation): call `SendMessage(to: strategist_agent_id, summary="New runs for Strategist", message="runs_since_last_strategist: [...], current_free_slots: N, current_best: RUN_ID/METRIC")`. The Strategist retains full session context; do not re-send the full prompt.
4. **`strategist_agent_id` null** (first call or previous ID no longer valid): use `Agent(subagent_type="experiment-strategist", ...)` with the full standard prompt template. On return, write the `agentId` from the spawn result to `strategist_agent_id` in plan.md Loop State.
5. If `SendMessage` returns an error (agent unreachable): fall back to fresh `Agent` spawn and update `strategist_agent_id`.
6. `SendMessage` is always background: always set `background_strategist_in_flight: true` before sending, regardless of queue state. Queue empty: do not launch new experiments while waiting for the return notification. Queue non-empty: continue processing other notifications while Strategist works.

**Setting the handshake**: after any Primary return (SendMessage resume, or a fresh non-confirmer spawn), if it returned **0 candidates + an explicit exhaustion declaration** AND no experiments are running AND Ready Queue is empty, set `pending_exhaustion_confirmation: true` so the next spawn is the fresh confirmer above. A verdict only counts when fully quiescent — if runs are still in flight or candidates were returned, leave it false.

## Strategist Continuation Protocol (Codex only)

After the first successful Strategist spawn, prefer resuming it via `send_input` over spawning fresh:

1. Check `pending_exhaustion_confirmation` first, then `strategist_agent_id`, in plan.md Loop State before every Strategist call.
2. **`pending_exhaustion_confirmation` is true**: spawn a **fresh confirmer** with the full standard neutral prompt. Do NOT `send_input` the Primary: confirming an exhaustion verdict by re-messaging the context that produced it gives no independence. On return: if the confirmer also returns 0 candidates + exhaustion → confirmed, stop per SKILL.md Default Stopping Rules; if it returns candidates → overturn the Primary, append candidates, **promote** (set `strategist_agent_id` ← confirmer agent id, set `pending_exhaustion_confirmation: false`), and continue.
3. **`strategist_agent_id` not null** (and not pending confirmation): call `send_input(target=strategist_agent_id, message="runs_since_last_strategist: [...], current_free_slots: N, current_best: RUN_ID/METRIC")`, then `wait_agent` when the Strategist result is needed. The Strategist retains full session context; do not re-send the full prompt.
4. **`strategist_agent_id` null** (first call or previous ID no longer valid): use `spawn_agent(message=STANDARD_PROMPT, fork_context=true)` with the registered custom agent selected as `experiment-strategist` when the Strategist needs current main-thread context beyond durable files and prompt fields. Omit `fork_context` when the prompt plus durable files are sufficient. On return, write the spawned agent id to `strategist_agent_id` in plan.md Loop State.
5. If the target agent is still running, `send_input` queues by default. Use `interrupt=true` only when abandoning the current Strategist task is intentional; otherwise wait for the queued result.
6. If the agent was closed, use `resume_agent(id=strategist_agent_id)` before `send_input` when continuity is still useful. If resume/send fails because the agent is unreachable, fall back to a fresh `spawn_agent` and update `strategist_agent_id`.

**Setting the handshake**: after any Primary return (`send_input` resume, or a fresh non-confirmer spawn), if it returned **0 candidates + an explicit exhaustion declaration** AND no experiments are running AND Ready Queue is empty, set `pending_exhaustion_confirmation: true` so the next call is the fresh confirmer above. A verdict only counts when fully quiescent — if runs are still in flight or candidates were returned, leave it false.

Prompt neutrality: always use the standard prompt template when calling Strategist. Never add context about previous Strategist verdicts, never ask "is the search exhausted?", never prime the Strategist's conclusion in any direction — including during double-verification. Do not echo plateau, ceiling, or exhaustion language from `observations.md` or `plan.md` into the prompt (e.g., "all parameters are at local optima", "text images have hit a ceiling").

Record each completed run inline immediately (verify files → parse metrics → determine status → call `aet.py record` → append trust details → move row → add to `runs_since_last_strategist`). Do not wait for a whole batch to finish before recording.

## Shared Call Inputs

Pass paths and stable context, not a parent-agent interpretation of results:
- `session_path`
- `project_root`
- relevant experiment scripts and CLI notes
- `algorithm_context`: metric meaning, target, benchmark constraints, known data/implementation risks, and important parameter couplings
- runtime notes: Codex vs Claude Code launch behavior, GPU policy, and current free slots when relevant

Pass only session-specific context in the prompt; the Strategist's role instructions are already loaded via its registered system prompt (`experiment-strategist`).

## Strategist Call Template

**Claude Code:** `Agent(subagent_type="experiment-strategist", description="Plan next queue candidates", prompt="""...""")`

**Codex first call / fresh confirmer:** `spawn_agent(message="""...""", fork_context=true)` with the registered custom agent selected as `experiment-strategist`; omit `fork_context` when current main-thread context is not needed.

**Codex continuation:** `send_input(target=strategist_agent_id, message="""...""")`, then `wait_agent` when the result is needed.

```text
You are not alone in the codebase; other agents may be working. Do not revert unrelated changes.

session_path: SESSION_PATH
project_root: PROJECT_ROOT
experiment_scripts: SCRIPT_PATHS
cli_notes: CLI_NOTES
algorithm_context: METRIC/TARGET/RISKS/COUPLINGS
current_free_slots: N
total_capacity: M  # capacity_per_gpu × gpu_count (constant). Refill target: after the parent fills current_free_slots, ready_count must stay >= total_capacity, so target ready_count ≈ current_free_slots + total_capacity (= 2× total_capacity at session start when the queue is empty and all slots are free).
current_best: RUN_ID/METRIC as a locator only
runs_since_last_strategist: [run_id list with recorded status, primary_metric, metric_name from results.csv]
# Values above are raw fields from results.csv — not interpreted conclusions about trends or plateau.

Read SESSION_PATH/meta.json, results.csv, observations.md, plan.md, and important runs/<id>/ artifacts directly.

Tasks:
0. Generate observations: for runs in runs_since_last_strategist, read their artifacts directly (runs/<id>/metrics.json, params.json, summary.md, train.log) and synthesize per-HP influence notes (patterns, boundary hits, forbidden regions, settings that help only under specific companion knobs). Return as observations_to_append. Omit if nothing new. **If runs_since_last_strategist is empty (session start / first call), skip observations entirely and proceed directly to task 1 — plan initial candidates from plan.md's objective, hypotheses, and coupled parameters.**
1. Determine whether the next candidates should broaden, refine, confirm, expand a boundary, or run an escape group.
2. Return enough Ready Queue candidates that after the parent fills the current free slots, ready_count stays at or above total_capacity — target ready_count ≈ current_free_slots + total_capacity (= 2× total_capacity at session start, since the queue is empty and all slots are free). Returning only total_capacity lets the first launch wave drain the queue and forces a redundant blocking re-call against the same result state.
3. Include per-HP rationale for non-obvious values, cited from run evidence.
4. Return stop/continue rule updates and any existing Ready Queue rows the parent should rewrite or remove.

Do not write plan.md or observations.md.
Return:
0. observations_to_append (per-HP influence notes for runs_since_last_strategist; omit if nothing new).
1. Ready Queue Candidates as rows compatible with plan.md.
2. Stop/Continue Rule Update.
3. Queue Edits.
4. Escape/Confirmation Need.
```

## Interpreting Returns

### After Strategist Returns

0. If `observations_to_append` provided: append to `SESSION/observations.md`; clear only the `runs_since_last_strategist` entries that were passed at call time (runs completed during background analysis accumulate for the next call).
1. Apply or lightly edit returned rows, then append them to `plan.md` `Ready Queue`.
2. Update the `Stop/Continue Rule` section.
3. Remove or rewrite invalidated ready rows if the strategist identified any.
4. **Claude Code only**: set `background_strategist_in_flight: false`. If this was a fresh `Agent` spawn (not a `SendMessage` resume), also write the returned `agentId` to `strategist_agent_id` in plan.md Loop State.
4b. **Claude Code only — exhaustion handshake** (see Continuation Protocol above and `references/claude-code-adapter.md` step 9):
   - If this return was a **fresh confirmer** (`pending_exhaustion_confirmation` was true): 0 candidates + exhaustion → confirmed, stop per Default Stopping Rules; candidates → promote (set `strategist_agent_id` ← confirmer `agentId`, clear `pending_exhaustion_confirmation`) and continue.
   - Otherwise (Primary return): if it returned 0 candidates + exhaustion while fully quiescent (no runs in flight, Ready Queue empty), set `pending_exhaustion_confirmation: true` and spawn the confirmer immediately in the same turn (nothing is running to notify you later); otherwise leave it false.
4c. **Codex only — continuation and exhaustion handshake**:
   - If this was a fresh `spawn_agent` call (not a `send_input` resume), write the returned agent id to `strategist_agent_id` in plan.md Loop State.
   - If this return was a **fresh confirmer** (`pending_exhaustion_confirmation` was true): 0 candidates + exhaustion → confirmed, stop per Default Stopping Rules; candidates → promote (set `strategist_agent_id` ← confirmer agent id, clear `pending_exhaustion_confirmation`) and continue.
   - Otherwise (Primary return): if it returned 0 candidates + exhaustion while fully quiescent (no runs in flight, Ready Queue empty), set `pending_exhaustion_confirmation: true` and call the fresh confirmer next; otherwise leave it false.
5. Re-check GPU slots and launch the highest-priority ready rows until usable slots are filled.
   - Codex: run the standard command with `exec_command`, one foreground tool session per experiment; if it yields a `session_id`, record `session_id -> run_id/output_dir/log_path` and poll with `write_stdin`.
   - Claude Code: use one `Bash(run_in_background=True)` call per experiment.
