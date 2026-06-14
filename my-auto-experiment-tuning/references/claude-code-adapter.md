Read this file only when you are Claude Code and have loaded the `my-auto-experiment-tuning` skill.

# Claude Code Adapter

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

When a `run_in_background=True` command finishes, Claude Code receives an automatic notification containing the return code and a summary. You do not need to poll. This applies equally to a background Strategist subagent — both a `SendMessage` (background) resume and an `Agent(..., run_in_background=True)` spawn notify you on completion, and that notification is your cue to run Beat 3 (`strategist-return`).

Never `sleep`, `tail`, or otherwise busy-wait on a background job's output file (an experiment log or a subagent task-output file) to wait for it to finish — the notification already does that, so polling only burns wall-clock inside your turn. When a background Strategist call is open and you have nothing else to do (all GPU slots full, no other completion to record), end the turn; the Strategist's completion notification will wake you to run Beat 3. The only reason to read a running job's log is a one-off progress check the user asked for, never a wait loop.

**On receiving a notification:**

1. Identify the run from your session map (run id ↔ output dir).
2. Verify output files exist: metrics JSON/CSV/NPZ, logs.
3. Parse primary metric in priority order: structured JSON/CSV/NPZ → TensorBoard event files → log regex via `aet.py parse-log` → manual extraction as last resort.
4. Determine terminal status: `finished`, `failed`, or `inconclusive`. Mark sandbox failures, dependency failures, code bugs, GPU contention, and partial crashes as `failed` or `inconclusive`.
5. Call `aet.py record --status <status> --run-id <id> [--primary-metric <value> --metric-name <name> --metrics '<json>'] [--notes '<notes>']` (omit metric flags if no valid metric).
6. If trust note is relevant: append to `runs/<id>/summary.md` (after record); move the row in `plan.md` from `Running` to `Completed / Recorded`. `aet.py record` already added the terminal run to the pending set in `loop_state.json`.
7. Check if a self-evaluatable stop condition is now met: explicit user stop, explicit numeric target cleanly met with evidence, explicit budget consumed, or required permission/resource unavailable. Do not evaluate plateau or exhaustion here. If you find yourself about to write that a parameter direction is "exhausted", "hit a ceiling", or "at a local optimum" — that is not a self-evaluatable stop condition. It is the signal to run the Strategist transaction at step 9.
8. If not, run `aet.py loop-state` (it counts the Ready Queue from `plan.md`) and follow its `YOU` block — this is the control-flow router; run it right after `record`, before selecting or launching anything. Step 6's bookkeeping is order-independent with it (loop-state reads `results.csv` and the Ready Queue count, which the `Completed / Recorded` move does not affect), so you may run loop-state first and finish the plan.md/summary.md bookkeeping after. It names the only free GPU ids to launch onto, and when ready_count < total_capacity it routes you into the Strategist transaction.
9. Execute what loop-state routed. Launch each candidate it cleared onto a GPU id it named: `aet.py create-run` → launch with `run_in_background=True` → `aet.py record --status running` → move the row to Running. When it routed a Strategist call, run the three-beat transaction (begin → tool_use → return) described in `references/subagents.md`:
   - **Beat 1** `aet.py strategist-begin` snapshots pending, computes the branch (fresh / resume / fresh confirmer), opens the call, and prints the exact tool call + payload. If a call is already open it refuses.
   - **Beat 2** make the printed tool_use. For a resume, that is the literal `SendMessage` tool (invoked by name, background) targeting the existing agent id — NOT `Agent`. Spawning `Agent(subagent_type="experiment-strategist")` on a resume route cold-starts a new strategist and throws away the context that makes resume worthwhile; do not substitute it. Call `SendMessage` directly: it is a real, always-available tool — its absence from `ToolSearch` or your visible toolset does NOT mean it is unavailable; if its schema is not loaded, load it, then call it. The ONLY signal that resume failed is the call itself returning `success:false`; knowing the agent died with a prior conversation is not that signal — make the call and let it fail. Only on `success:false` fall back to a fresh `Agent` spawn and pass `--resume-failed` to Beat 3. Use `Agent(subagent_type="experiment-strategist", run_in_background=...)` directly only for a genuine fresh spawn / confirmer. Between this beat and Beat 3, keep processing other completion notifications; each `record` adds to pending without disturbing the open call.
   - **Beat 3** `aet.py strategist-return --call-id C --candidates-count K [--agent-id A] [--observations-present] [--queue-edits-present] [--stop-update-present]` clears the snapshot, records the agent id, derives exhaustion from `K == 0`, and applies the handshake. Follow its `YOU` block.

   The script owns fresh-vs-resume-vs-confirmer, the exhaustion handshake (`pending_exhaustion_confirmation`, promotion of a confirmer to Primary), and quiescence (computed by the script from the live experiment state and the Ready Queue count). Do not hand-evaluate any of it. On a `CONFIRMED_EXHAUSTION` result the handshake is complete and the next steps run in the same turn — nothing is running to notify you later. The only valid reasons to not begin a call are the self-evaluatable stop conditions and an already-open call (begin refuses); "recently called", "pending is empty", and "no new completions" are not suppression conditions (see anti-patterns #8 and #9 in SKILL.md).

Do not batch notifications — process each one as soon as it arrives, even if another experiment is still running. Incremental recording prevents data loss if the session is interrupted.

## Periodic Keepalive (CronCreate)

`CronCreate` schedules a recurring prompt that fires while the REPL is idle. Use it as your native keepalive so the tuning loop restarts automatically even if the session sits idle between background notifications.

**When to set up**: immediately after the AET session is created (`aet.py init`), before launching the first runs.

**Call the `CronCreate` tool directly** (it is a tool, not a shell command, and not the `/loop` slash command — `/loop`'s human-friendly interval parsing buys you nothing here and writes a worse `0 * * * *` cron). Construct the call yourself:

```python
CronCreate(
    cron="7 * * * *",
    prompt="/my-auto-experiment-tuning Continue fine-tuning. Target: PSNR > XX (substitute actual target, or omit if none). Keep GPUs occupied. At the start of each invocation: (1) run `aet.py status` — if results.csv finished count exceeds plan.md Completed entries, reconcile plan.md from results.csv first; (2) run `aet.py loop-state` (it counts the Ready Queue from plan.md itself) and follow its YOU block — it routes any launches and the Strategist transaction (begin -> subagent tool_use -> return) for you; the script owns the Strategist routing and exhaustion handshake. Skip this prompt only if you are currently mid-execution of these steps in this exact conversation turn.",
    recurring=True,
    durable=False,
)
```

`CronCreate` returns a job id; cancel with it later, or recover it via `CronList`.

**After scheduling, run the first cycle now** — do not wait for the first cron fire. Each tick re-enqueues the prompt; the leading `/my-auto-experiment-tuning` re-triggers the skill after a context compaction drops the loaded instructions.

Customize the call:
- Replace `PSNR > XX` with the actual metric target, or omit the target clause entirely if none was given.
- Pick the `cron` by cadence (1 h fits long sessions):

  | Cadence | `cron` | Notes |
  |---|---|---|
  | hourly (default) | `7 * * * *` | off-:00 to avoid the top-of-hour scheduler herd |
  | every 2 h | `13 */2 * * *` | for runs ≥ 2 h |
  | every 30 min | `*/30 * * * *` | short runs (< 20 min) |

  Do not go below ~20 min — shorter intervals create noise. The escape clause in the prompt prevents re-entry only when you are already mid-execution in the same turn — it does NOT apply just because experiments are running or no new completions occurred.

**`durable=False` (set above) keeps the job session-only — leave it that way.** Do not set it `true`: a durable job outlives this session and can interfere with other sessions running on the same project.

**7-day bound**: a recurring job auto-expires after 7 days (one final fire, then deleted). For a tuning session expected to run longer, issue another `CronCreate` when it nears expiry.

**When to cancel**: `CronDelete(id)` — pass the id `CronCreate` returned, or run `CronList` to find it — only when the user ends the session or a valid stop condition has been recorded and the session is being closed. Do not cancel merely because one run hit a local or provisional target.

## Subagent Differences vs Codex

Claude Code uses the `Agent` tool (not Codex's `multi_tool_use.parallel` pattern):

- The Strategist is an independent process with its own tool access.
- Pass the session path, ledger summary, and bounded write scope explicitly in the agent prompt, because the subagent starts without the parent's context.
- `aet.py strategist-begin` prints the blocking/background mode (and the resume vs fresh `Agent`/`SendMessage` call) — use what it prints. A resume runs background; a fresh spawn is blocking when the queue is empty and background when non-empty.

## Workflow Differences Summary

| Step | Codex | Claude Code |
|---|---|---|
| Launch one experiment | Foreground, one session | `run_in_background=True`, one Bash call |
| Launch candidate group (parallel) | One foreground session per run, serialized | Multiple `run_in_background=True` in same turn |
| Monitor progress | Poll with `write_stdin` or wait | Receive completion notification automatically |
| Keepalive between turns | External cron/systemd required | `CronCreate` recurring job (native) |
| Strategist subagent | `spawn_agent(message="...", fork_context=true)` with the registered custom agent selected as `experiment-strategist` when context inheritance is needed; `send_input(target=strategist_agent_id, ...)` for continuation | `Agent(subagent_type="experiment-strategist")` or `SendMessage` continuation |

## Safe Bash Patterns (Claude Code)

Claude Code runs a hook system that intercepts "complex shell structures" and escalates them for manual approval, breaking the autonomous tuning loop. The following patterns reliably trigger interception:

### Forbidden — always cause hook interception

```bash
# ✗ cd + redirection (any combination)
cd /path && python exp.py > log.txt

# ✗ for loop (any variant) — even simple ones are intercepted
for rid in 0 1 2 3 4 5 6; do python aet.py record --run-id $rid --status running; done

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

# ✓ batch identical bookkeeping commands with && — safe when there are no shell variables,
#   no redirections, and no command substitution in the chained commands:
python aet.py record --run-id 0 --status running && \
python aet.py record --run-id 1 --status running && \
python aet.py record --run-id 2 --status running

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
