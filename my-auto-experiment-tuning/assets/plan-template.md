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
- GPU parallelism:
- Current free GPU slots:
- total_capacity: (capacity_per_gpu × gpu_count, from `aet.py gpu-slots`)
- Ready-queue invariant: keep `Ready Queue` count at or above total_capacity whenever useful unexplored regions remain. Strategist is spawned whenever count drops below total_capacity.
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
1. Plan enough Ready Queue candidates so ready_count >= total_capacity (capacity_per_gpu × gpu_count).
2. When slots are free, take as many highest-priority ready rows as current resource checks allow, assign run id/GPU/output dir/log path, register each with `aet.py create-run`, launch each command, then record each accepted process with `aet.py record --status running` and move them to Running.
3. When a run finishes, collect metrics, record terminal status with `aet.py record`, move that row from Running to Completed / Recorded, then update observations.
4. Analyze current results and append informative candidates to Ready Queue when useful. This can be 0, 1, or many candidates, including a small grid/factorial group; do not force a one-finished-run to one-new-run cadence.
5. If new evidence invalidates a ready candidate before launch, remove or rewrite that Ready Queue row and note why in observations.md.
-->

### Loop State (Claude Code — update after each completion/Strategist event)

- `runs_since_last_strategist`: []  <!-- append run_id each time a run reaches terminal status -->
- `background_strategist_in_flight`: false  <!-- set true when background Agent spawn issued; set false when it returns; skip re-spawn while true -->

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
