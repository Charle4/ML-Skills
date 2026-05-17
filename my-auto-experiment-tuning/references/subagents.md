# Subagent Delegation Guide

Use this file before spawning the registered Strategist or Runner subagents.

## Agent Roles

### Strategist (`experiment-strategist`)

Returns: `observations_to_append` (per-HP influence notes for `runs_since_last_strategist`) and Ready Queue candidates plus stop/continue text. Does not write `plan.md` or `observations.md`; apply all returned outputs.

### Runner (`experiment-runner`)

Runner is optional. Use it only when launch execution needs context isolation or parallel delegation. Normally register, launch, and record `running` directly.

## When to Delegate

| Trigger | Spawn | Required |
| ------- | ----- | -------- |
| Ready Queue count <= current free slots, or Queue is empty | Strategist | Yes |
| Launching many independent runs and context isolation is useful | Runner | Optional |

Self-evaluatable conditions that may suppress a Strategist spawn: explicit user stop, explicit numeric target cleanly met with evidence, explicit run/wall-clock budget consumed, required permission/resource unavailable. Plateau and exhaustion are never self-evaluatable — Strategist must be the one to declare them; they cannot gate this spawn.

Prompt neutrality: always use the standard prompt template when calling Strategist. Never add context about previous Strategist verdicts, never ask "is the search exhausted?", never prime the Strategist's conclusion in any direction — including during double-verification.

Record each completed run inline immediately (verify files → parse metrics → determine status → call `aet.py record` → append trust details → move row → add to `runs_since_last_strategist`). Do not wait for a whole batch to finish before recording.

## Shared Prompt Inputs

Pass paths and stable context, not a parent-agent interpretation of results:
- `session_path`
- `project_root`
- relevant experiment scripts and CLI notes
- `algorithm_context`: metric meaning, target, benchmark constraints, known data/implementation risks, and important parameter couplings
- runtime notes: Codex vs Claude Code launch behavior, GPU policy, and current free slots when relevant

Pass only session-specific context in the prompt; each subagent's role instructions are already loaded via its registered system prompt (`experiment-strategist`, `experiment-runner`).

## Call Prompt Template: Strategist

**Claude Code:** `Agent(subagent_type="experiment-strategist", description="Plan next queue candidates", prompt="""...""")`

**Codex:** `spawn_agent(agent_type="experiment-strategist", message="""...""")`.

```text
You are not alone in the codebase; other agents may be working. Do not revert unrelated changes.

session_path: SESSION_PATH
project_root: PROJECT_ROOT
experiment_scripts: SCRIPT_PATHS
cli_notes: CLI_NOTES
algorithm_context: METRIC/TARGET/RISKS/COUPLINGS
current_free_slots: N
current_best: RUN_ID/METRIC as a locator only
runs_since_last_strategist: [run_id list with recorded status, primary_metric, metric_name from results.csv]

Read SESSION_PATH/meta.json, results.csv, observations.md, plan.md, and important runs/<id>/ artifacts directly.

Tasks:
0. Generate observations: for runs in runs_since_last_strategist, read their artifacts directly (runs/<id>/metrics.json, params.json, summary.md, train.log) and synthesize per-HP influence notes (patterns, boundary hits, forbidden regions, settings that help only under specific companion knobs). Return as observations_to_append. Omit if nothing new.
1. Determine whether the next candidates should broaden, refine, confirm, expand a boundary, or run an escape group.
2. Return enough Ready Queue candidates so ready_count will be greater than current_free_slots while useful search remains.
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

## Call Prompt Template: Runner

**Claude Code:** `Agent(subagent_type="experiment-runner", description="Launch assigned runs", prompt="""...""")`

**Codex:** `spawn_agent(agent_type="experiment-runner", message="""...""")`.

```text
You are not alone in the codebase; other agents may be working. Do not revert unrelated changes.

session_path: SESSION_PATH
assigned_runs:
- run_id: RUN_ID
  gpu_id: GPU_ID
  output_dir: OUTPUT_DIR
  log_path: OUTPUT_DIR/train.log
  command: FULL_COMMAND
experiment_script: SCRIPT_PATH

Tasks:
1. Verify script and output directory exist.
2. Register the run with SKILL_DIR/scripts/aet.py create-run if not already registered.
3. Launch exactly the assigned command.
4. Record running with SKILL_DIR/scripts/aet.py record --status running after the process starts.

Return run_id, command, gpu_id, output_dir, log_path, process/session status, and create-run/record status.
```

## Interpreting Returns

### After Strategist Returns

0. If `observations_to_append` provided: append to `SESSION/observations.md`; clear the `runs_since_last_strategist` tracking list.
1. Apply or lightly edit returned rows, then append them to `plan.md` `Ready Queue`.
2. Update the `Stop/Continue Rule` section.
3. Remove or rewrite invalidated ready rows if the strategist identified any.
4. Re-check GPU slots and launch the highest-priority ready rows until usable slots are filled.
   - Codex: run the standard command with `exec_command`, one foreground tool session per experiment; if it yields a `session_id`, record `session_id -> run_id/output_dir/log_path` and poll with `write_stdin`.
   - Claude Code: use one `Bash(run_in_background=True)` call per experiment.

### After Runner Returns

1. Confirm `create-run` and `record --status running` completed.
2. Record run id, output directory, log path, GPU, and process/session status in `plan.md` `Running`.
3. Wait for normal completion handling; record each terminal run inline.
