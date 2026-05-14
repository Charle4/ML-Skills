# Subagent Delegation Guide

Use this file before spawning the registered Analyzer, Strategist, or Runner subagents.

The main agent is the orchestrator. It manages the AET session lifecycle, writes `plan.md`, checks GPU slots, starts the next launchable work, and decides when to stop. Subagents provide bounded analysis, strategy, or launch execution without owning the full loop.

## Agent Roles
### Analyzer (`result-analyzer`)

Analyzer handles per-run result parsing, trust judgment, and per-HP pattern accumulation. It returns structured data (status, metrics, trust notes, per-HP observations) for the main agent to record and write. Analyzer does not call `aet.py record` or write any files directly. Spawn it for each completed run or small group of completed runs.

### Strategist (`experiment-strategist`)

Strategist reads the full durable ledger and proposes the next `Ready Queue` candidates plus stop/continue text. It does not write `plan.md`; the main agent applies or edits its returned rows.

### Runner (`experiment-runner`)

Runner is optional. Use it only when launch execution needs context isolation or parallel delegation. The main agent normally registers, launches, and records `running` itself.

## When to Delegate

| Trigger | Spawn | Required |
| ------- | ----- | -------- |
| A run reaches terminal state or a background completion notification arrives | Analyzer | Yes |
| Ready Queue count <= current free slots, or Queue is empty, and no stop condition is met | Strategist | Yes |
| Launching many independent runs and context isolation is useful | Runner | Optional |

Do not wait for a whole conceptual batch to finish. Analyze each completed run promptly, then refill slots from `Ready Queue` or request Strategist output if the queue is low.

## Shared Prompt Inputs

Pass paths and stable context, not a parent-agent interpretation of results:
- `session_path`
- `project_root`
- relevant experiment scripts and CLI notes
- `algorithm_context`: metric meaning, target, benchmark constraints, known data/implementation risks, and important parameter couplings
- runtime notes: Codex vs Claude Code launch behavior, GPU policy, and current free slots when relevant

Pass only session-specific context in the prompt; each subagent's role instructions are already loaded via its registered system prompt (`result-analyzer`, `experiment-strategist`, `experiment-runner`).

## Call Prompt Template: Analyzer

**Claude Code:** `Agent(subagent_type="result-analyzer", description="Analyze run(s) RUN_IDS", prompt="""...""")`

**Codex:** `spawn_agent(agent_type="result-analyzer", message="""...""")`.

```text
You are not alone in the codebase; other agents may be working. Do not revert unrelated changes.

session_path: SESSION_PATH
run_ids: RUN_IDS
project_root: PROJECT_ROOT
experiment_scripts: SCRIPT_PATHS
algorithm_context: METRIC/TARGET/RISKS/COUPLINGS

Read SESSION_PATH/meta.json, results.csv, observations.md, plan.md, and SESSION_PATH/runs/<id>/ artifacts directly. Do not rely on this prompt as a result summary.

Tasks:
1. Verify artifacts for each assigned run.
2. Parse metrics by structured files first, then event files if applicable, then explicit log parsing fallback.
3. Decide finished/failed/inconclusive; determine trust note and per-HP observations. Do NOT call aet.py record or write any files — return all data to the main agent.
4. Accumulate 1-3 lines of per-HP influence notes (patterns across runs, boundary hits, forbidden regions).

Do not edit plan.md or any other file.
Return structured data per run:
run_id, status, primary_metric, metric_name, metrics_json, metric_source,
trust_note, record_notes, observations_to_append, summary_trust_details,
benchmark_update_needed: yes/no
```

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

Read SESSION_PATH/meta.json, results.csv, observations.md, plan.md, and important runs/<id>/ artifacts directly.

Tasks:
1. Determine whether the next candidates should broaden, refine, confirm, expand a boundary, or run an escape group.
2. Return enough Ready Queue candidates so ready_count will be greater than current_free_slots while useful search remains.
3. Include per-HP rationale for non-obvious values, cited from run evidence.
4. Return stop/continue rule updates and any existing Ready Queue rows the parent should rewrite or remove.

Do not write plan.md or observations.md.
Return:
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

### After Analyzer Returns

1. Call `aet.py record --status <status> --run-id <id> [--notes '<record_notes>']` — add `--primary-metric <value> --metric-name <name> --metrics '<metrics_json>'` only if Analyzer returned a valid metric
2. If `summary_trust_details` provided: append it to `SESSION/runs/<run_id>/summary.md` (after record, since record rewrites that file)
3. If `observations_to_append` provided: append it to `SESSION/observations.md`
4. If `benchmark_update_needed: yes`: update the project benchmark table or README
5. Move the corresponding row in `plan.md` from `Running` to `Completed / Recorded`.
6. Re-check GPU slots.
7. If `Ready Queue` count <= free slots and no stop condition is met, spawn Strategist.
8. Launch from `Ready Queue` into available slots.

### After Strategist Returns

1. Apply or lightly edit returned rows, then append them to `plan.md` `Ready Queue`.
2. Update the `Stop/Continue Rule` section.
3. Remove or rewrite invalidated ready rows if the strategist identified any.
4. Re-check GPU slots and launch the highest-priority ready rows until usable slots are filled.
   - Codex: run the standard command with `exec_command`, one foreground tool session per experiment; if it yields a `session_id`, record `session_id -> run_id/output_dir/log_path` and poll with `write_stdin`.
   - Claude Code: use one `Bash(run_in_background=True)` call per experiment.

### After Runner Returns

1. Confirm `create-run` and `record --status running` completed.
2. Record run id, output directory, log path, GPU, and process/session status in `plan.md` `Running`.
3. Wait for normal completion handling; every terminal run still goes through Analyzer.
