# Claude Code Adapter

Read this file immediately when you are Claude Code and have loaded the `my-auto-experiment-tuning` skill. It supplements the main skill with capabilities Codex does not have.

## SKILL_DIR

For Claude Code, the skill is installed at:

```
~/.claude/skills/my-auto-experiment-tuning
```

Substitute this path whenever the main skill uses the placeholder `SKILL_DIR`.

## run_in_background: Non-Blocking Experiment Launches

The Bash tool accepts `run_in_background=True`. Use it for every long-running experiment instead of shell `&` or `nohup`.

```python
# In your tool call:
Bash(
    command="python -u SCRIPT --gpu_id N --output_dir RUNDIR > RUNDIR/train.log 2>&1",
    run_in_background=True,
    description="Run experiment run_03 on GPU 2"
)
```

Rules:
- One `run_in_background=True` call per experiment, not per batch. Each call tracks independently.
- Create the unique run directory before launch so the shell can open `RUNDIR/train.log`.
- Capture stdout and stderr to a log file inside the run directory with `> RUNDIR/train.log 2>&1` so you can parse it later.
- Register the run with `aet.py create-run` before launch so `queue.jsonl` has a recovery snapshot, and write the live mapping (run id → output dir → background job description) in `plan.md` before returning, because you will not see the command again until the notification arrives.
- Do not add `&` or `nohup` to the shell command itself — `run_in_background=True` handles daemonization correctly.

### Launching Multiple Experiments in Parallel

You can fire several background jobs in the same turn (one per GPU slot):

```python
# In the same response, multiple independent Bash calls with run_in_background=True:
Bash(command="python -u SCRIPT --gpu_id 0 --output_dir run_04 ... > run_04/train.log 2>&1", run_in_background=True)
Bash(command="python -u SCRIPT --gpu_id 1 --output_dir run_05 ... > run_05/train.log 2>&1", run_in_background=True)
Bash(command="python -u SCRIPT --gpu_id 2 --output_dir run_06 ... > run_06/train.log 2>&1", run_in_background=True)
```

Each will notify independently when it finishes. Process each notification as it arrives.

## Background Completion Notifications

When a `run_in_background=True` command finishes, Claude Code receives an automatic notification containing the return code and a summary. You do not need to poll.

**On receiving a notification:**

1. Identify the run from your session map (run id ↔ output dir).
2. Verify output files exist: metrics JSON/CSV/NPZ, logs.
3. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort.
4. Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, GPU contention, and partial crashes as `failed` or `inconclusive`.
5. Call `aet.py record --status <status> --run-id <id> [--primary-metric <value> --metric-name <name> --metrics '<json>'] [--notes '<notes>']` (omit metric flags if no valid metric).
6. If trust note is relevant: append to `runs/<id>/summary.md` (after record); move the row in `plan.md` from `Running` to `Completed / Recorded`; add run_id to `runs_since_last_strategist`.
7. Check if a self-evaluatable stop condition is now met: explicit user stop, explicit numeric target cleanly met with evidence, explicit budget consumed, or required permission/resource unavailable. Do not evaluate plateau or exhaustion here. If you find yourself about to write that a parameter direction is "exhausted", "hit a ceiling", or "at a local optimum" — that is not a self-evaluatable stop condition. It is the signal that Strategist must be spawned at step 9.
8. If not, re-check current GPU slots, select as many ready candidates as resources allow, register each with `aet.py create-run`, launch each with `run_in_background=True`, then record each with `aet.py record --status running`.
9. If Ready Queue count < total_capacity (capacity_per_gpu × gpu_count, constant):
   - If `background_strategist_in_flight` is true in `plan.md` Loop State: **skip spawning**; run_id is already in `runs_since_last_strategist` and will be included when the in-flight Strategist returns.
   - Queue **empty** (and not in-flight): `Agent(subagent_type="experiment-strategist", run_in_background=False, ...)`; wait before launching.
   - Queue **non-empty** (and not in-flight): `Agent(subagent_type="experiment-strategist", run_in_background=True, ...)`; set `background_strategist_in_flight: true` in `plan.md`; continue processing other notifications while Strategist works. Record the run_ids passed at spawn time.
   On Strategist return (either path): append `observations_to_append` to `observations.md`; append candidates to `plan.md` Ready Queue; clear only the `runs_since_last_strategist` entries that were passed at spawn time; set `background_strategist_in_flight: false`.

Do not batch notifications — process each one as soon as it arrives, even if another experiment is still running. Incremental recording prevents data loss if the session is interrupted.

## /loop: Periodic Keepalive

Claude Code's `/loop` command sends a recurring prompt at a fixed interval inside the current session. Use it as a native keepalive so the tuning loop restarts automatically even if the session sits idle between background notifications.

**When to set up**: immediately after the AET session is created (`aet.py init`), before launching the first runs.

**Invoke `/loop` as a slash command in the conversation** (not in a shell). Pass the interval and the skill invocation prompt:

```
/loop 1h /my-auto-experiment-tuning Continue fine-tuning. Target: PSNR > XX (substitute actual target). Keep GPUs occupied. At the start of each invocation: (1) run `aet.py status` — if results.csv finished count exceeds plan.md Completed entries, rebuild plan.md from results.csv before anything else; (2) if Ready Queue count < total_capacity, spawn Strategist (blocking if queue empty, background if non-empty); pass recent run IDs from results.csv as runs_since_last_strategist. If actively working on steps 1–2 already, skip this prompt.
```

Template to customize:
- Replace `PSNR > XX` with the actual metric target, or omit the target clause entirely if none was given.
- Use `30m` instead of `1h` if individual runs are short (< 20 min) and you want tighter loop cadence.
- Minimum recommended interval: `20m`. Shorter intervals create noise.

**Effect**: every hour (or whatever interval), the skill is re-invoked with the keepalive prompt. The tail "if actively working, ignore this prompt" prevents duplicate launches when experiments are already running.

**When to stop the loop**: `/loop stop` only when the user ends the session or a valid stop condition has been recorded and the session is being closed. Do not stop the loop merely because one run hit a local or provisional target.

## Subagent Differences vs Codex

Claude Code uses the `Agent` tool (not Codex's `multi_tool_use.parallel` pattern):

- Launch Strategist and Runner as parallel `Agent` tool calls in a single message when both are needed.
- Each agent is an independent process with its own tool access.
- Pass the session path, ledger summary, and bounded write scope explicitly in the agent prompt, because subagents start without the parent's context.
- Background jobs launched by a Runner subagent do NOT notify the parent directly — the Runner must collect results before returning, or the parent must re-check the output directories after the Runner finishes.
- Use `run_in_background=True` in Runner subagents for their individual experiment launches; the Runner stays alive until its assigned runs finish, then reports back.
- When Ready Queue is non-empty but below total_capacity, spawn Strategist with `run_in_background=True` so experiments continue uninterrupted. When queue is empty, spawn blocking (omit `run_in_background` or set to False).

## Workflow Differences Summary

| Step | Codex | Claude Code |
|---|---|---|
| Launch one experiment | Foreground, one session | `run_in_background=True`, one Bash call |
| Launch candidate group (parallel) | One foreground session per run, serialized | Multiple `run_in_background=True` in same turn |
| Monitor progress | Poll with `write_stdin` or wait | Receive completion notification automatically |
| Keepalive between turns | External cron/systemd required | `/loop 1h` native |
| Subagents | Codex `exec_command` delegation | `Agent` tool, parallel calls |

## Safe Bash Patterns (Claude Code)

Claude Code runs a hook system that intercepts "complex shell structures" and escalates them for manual approval, breaking the autonomous tuning loop. The following patterns reliably trigger interception:

### Forbidden — always cause hook interception

```bash
# ✗ cd + redirection (any combination)
cd /path && python exp.py > log.txt

# ✗ for loop with variable assignment, command substitution, or conditional
for d in a b c; do f="${d}/log.txt"; r=$(grep ... "$f"); [ -n "$r" ] && echo ...; done

# ✗ multi-command sequence with redirections or separators
cmd1; echo "---"; cmd2 2>/dev/null | head -20

# ✗ python -c "..." with a newline followed by a # comment inside the quoted string
python -c "
import json
# this comment triggers the hook
print('hello')
"

# ✗ writing a shell script to a file and executing it as a multi-run launcher
bash /tmp/launch_batch.sh

# ✗ unique-dir for session-internal output + manual --run-id (causes ID collisions when plan.md is stale)
OUTPUT=$(aet.py unique-dir .../runs/run-0098 --mkdir) && aet.py create-run --run-id 98 ...
```

### Safe replacements

```bash
# ✓ absolute path, no cd
python -u /abs/path/exp.py --args > /abs/path/log.txt 2>&1

# ✓ rg or grep -r instead of a for loop over files
rg "PSNR" /abs/path/results/ 2>/dev/null | head -40
grep -r "pattern" /abs/path/results/ 2>/dev/null | head -40

# ✓ pass multiple files directly to grep — no loop
grep "pattern" /path/a/log.txt /path/b/log.txt /path/c/log.txt 2>/dev/null

# ✓ python -c without # comments inside the quoted argument
python -c "
import json
print('hello')
"

# ✓ session-internal run output: two-step Bash calls (no shell extraction)
#
#   Step 1: Bash("aet.py create-run ...")
#           → tool output contains three labeled lines; read output_dir: value directly
#               run_dir: /path/to/session/runs/42
#               run_id: 42
#               output_dir: /path/to/session/runs/42/output   ← already created
#
#   Step 2: Bash("python -u SCRIPT --output_dir OUTPUT_DIR > OUTPUT_DIR/train.log 2>&1",
#                run_in_background=True)
#           → substitute the literal path read from Step 1 output; no shell variable needed
```

### Multi-run launches: parallel tool calls, not loops

To launch multiple experiments at once, fire independent `Bash(run_in_background=True)` calls in the same response turn — never a shell `for` loop:

```python
# Correct: three separate Bash calls in one response
Bash(command="python -u SCRIPT --gpu_id 0 --output_dir run_A > run_A/train.log 2>&1", run_in_background=True)
Bash(command="python -u SCRIPT --gpu_id 1 --output_dir run_B > run_B/train.log 2>&1", run_in_background=True)
Bash(command="python -u SCRIPT --gpu_id 2 --output_dir run_C > run_C/train.log 2>&1", run_in_background=True)
```

### Reading result files: tools, not loops

Use the `Read` tool for known paths. Use `rg` or `grep -r` to scan multiple result directories at once. Never write a shell `for` loop to iterate over log files — it will be intercepted.
