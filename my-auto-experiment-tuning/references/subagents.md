# Subagent Roles

Use these prompts when the user requested autonomous tuning with subagent support and the environment permits delegation. If not, perform the role locally.

The main agent remains responsible for the loop. Subagents provide bounded sidecar work; they do not wait for human approval between normal tuning iterations.

## Strategist

Task:
Read the session ledger, project benchmark docs, and current observations. Propose the next queue of candidate experiments (plan more candidates than available GPU slots so there is always a ready candidate when a slot opens).

Output:
- current best and trust status
- active hypothesis and which interaction is being tested or intentionally deferred
- likely parameter couplings and whether this is broad exploration or local refinement
- exact parameter configurations to add to the queue
- per-HP rationale for non-obvious value choices, cited from prior run results (e.g., "lr=1e-4 because Exp 3 showed 1e-3 caused oscillation")
- launch commands or command template
- expected interpretation for possible outcomes
- stop/continue rule; note untested boundaries and unexhausted families

Rules:
- Avoid repeating known-bad regions.
- Avoid pure one-knob local search unless a broad interaction pass already supports it.
- Include clean confirmation when needed.
- Plan enough candidates to keep slots filled without over-committing; do not propose more than 2× the available GPU slots at once unless the method tolerates high parallelism.
- Do not write files unless assigned ownership of `plan.md` or a specific run list.

## Runner

Task:
Launch assigned experiments only. Each runner owns a disjoint set of run ids/output directories.

Output:
- command for each run
- run id/name
- GPU id
- output directory and log path
- process/session status

Rules:
- Do not modify code unless explicitly assigned.
- Do not overwrite directories.
- Create a unique output directory before launch and put the log inside it, normally `<output_dir>/train.log`.
- Launch with `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1`; use plain `python` unless the active environment is wrong.
- Do not use shell `&`, `nohup`, `screen`, or `tmux`.
- Assume other agents may be working in the codebase; do not revert their changes.

## Analyzer

Task:
Analyze finished runs, update the ledger, extract optimization trajectories, diagnose convergence, and accumulate per-HP influence notes.

Output (returned to parent agent — keep concise):
- primary metric and source file path
- status: finished, failed, or inconclusive
- one-line convergence diagnosis (healthy / overfitting / underfitting / divergence / oscillation / n/a)
- comparison to prior best
- short failure/success rule if reusable
- README/benchmark update needed or already done

Written to `observations.md` (not returned in full to parent):
- optimization trajectory: primary metric at 4–6 key checkpoints across the run
- per-HP influence notes accumulated across the session (e.g., "lr=1e-4 consistently outperforms 1e-3 in final metric")

Rules:
- Verify files exist before recording metrics.
- Prefer structured result files over regex.
- Mark contaminated runs as inconclusive.
- Keep the parent-facing return brief; write trajectory details and per-HP influence notes to `observations.md`.
- Keep observations concise and actionable.
