# Tuning Plan

Canonical file: this template is rendered by `aet.py init` into `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/plan.md`. Keep updating that generated file in place.

## Objective

- Objective: {{ objective }}
- Metric:
- Direction: {{ goal }}
- Baseline:
- Current best:
- Explicit target threshold:
- Success criterion:
- Budget: open-ended until target/user stop, unless specified otherwise

## Constraints

- Compute budget:
- GPU parallelism: (authoritative policy is script-owned in `meta.json`; set with `aet.py set-policy`)
- GPU slots / total_capacity: read `aet.py gpu-slots` or `aet.py loop-state` (live)
- Ready-queue invariant: keep `Ready Queue` count at or above total_capacity whenever useful unexplored regions remain. Run the Strategist transaction (`aet.py strategist-begin` → tool_use → `strategist-return`) whenever count drops below total_capacity.
- Invalid or untrusted conditions:
- Forbidden parameter regions:

## Hypotheses

1.
2.
3.

## Coupled Parameters

| Group | Why Coupled | Broad Test | Local Refinement Trigger |
| ----- | ----------- | ---------- | ------------------------ |

## Execution Board

Keep this board current. Move rows between sections instead of leaving stale duplicate entries.

### Completed / Recorded

| Run ID | Hypothesis | Parameters | Status | Primary Metric | Trust | Key Finding | Follow-up |
| ------ | ---------- | ---------- | ------ | -------------- | ----- | ----------- | --------- |

### Running

| Run ID | Hypothesis | Parameters | GPU | Output Dir | Log Path | Started | Expected Signal |
| ------ | ---------- | ---------- | --- | ---------- | -------- | ------- | --------------- |

### Ready Queue

| Queue ID | Hypothesis | Parameters | Rationale | Priority | Expected Signal | Launch Template |
| -------- | ---------- | ---------- | --------- | -------- | --------------- | --------------- |

<!-- Rolling queue protocol:
1. Plan enough Ready Queue candidates that after free slots are filled, ready_count stays >= total_capacity (target ≈ current_free_slots + total_capacity; = 2× total_capacity at session start).
2. When slots are free, take as many highest-priority ready rows as current resource checks allow, assign run id/GPU/output dir/log path, register each with `aet.py create-run`, launch each command, then record each accepted process with `aet.py record --status running` and move them to Running.
3. When a run finishes, record terminal status with `aet.py record` (it adds the run to the pending set), move that row from Running to Completed / Recorded.
4. When ready_count < total_capacity, run the Strategist transaction (`aet.py strategist-begin` → subagent tool_use → `strategist-return`) and append the candidates it returns — 0, 1, or many, including a small grid/factorial group. Do not analyze results or design candidates inline when the Strategist is available.
5. If the Strategist's return invalidates a ready candidate before launch, remove or rewrite that Ready Queue row and note why in observations.md.

Keep the `### Ready Queue` heading name verbatim — the script counts the table rows beneath it for `ready_count`. Machine loop state (pending runs, Strategist agent id, open call, exhaustion handshake) is script-owned in `loop_state.json`; read it via `aet.py loop-state`.
-->

### Per-HP Rationale (for non-obvious value choices, cite prior run evidence)

<!-- Example:
- Q1: lr=1e-4 because Exp 3 showed 1e-3 caused val oscillation; weight_decay=1e-3 because Exp 5 showed overfitting
- Q2:
-->

## Stop/Continue Rule

- Stop if:
- Strategist may declare plateau only after (evidence requirements for Strategist to evaluate, not you):
  - minimum run count:
  - broad interaction group completed:
  - local refinement group completed:
  - escape group completed:
  - clean confirmation completed:
- Continue if:
  - explicit target is unmet and useful GPU slots are available
  - current best is only a local result without an escape group
  - current best sits on a scanned boundary
  - no user stop or budget exhaustion has occurred
