# Tuning Plan

## Objective

- Metric:
- Direction:
- Baseline:
- Current best:
- Explicit target threshold:
- Success criterion:
- Budget: open-ended until target/user stop, unless specified otherwise

## Constraints

- Compute budget:
- GPU parallelism:
- Invalid or untrusted conditions:
- Forbidden parameter regions:

## Hypotheses

1.
2.
3.

## Coupled Parameters

| Group | Why Coupled | Broad Test | Local Refinement Trigger |
| --- | --- | --- | --- |

## Next Batch

| Run | Hypothesis | Parameters | GPU | Output Dir | Expected Signal |
| --- | --- | --- | --- | --- | --- |

<!-- Rolling queue: plan more candidates than available GPU slots. Launch a new experiment from the queue as soon as a slot opens — no need to wait for all running experiments to finish before refilling. When the queue runs low, plan the next set of candidates. -->

### Per-HP Rationale (for non-obvious value choices, cite prior run evidence)

<!-- Example:
- Run A: lr=1e-4 — Exp 3 showed 1e-3 caused val oscillation; weight_decay=1e-3 — first time testing this level of regularization given observed overfitting in Exp 5
- Run B: ...
-->

## Stop/Continue Rule

- Stop if:
- Plateau can be claimed only after:
  - minimum run count:
  - broad interaction batch completed:
  - local refinement batch completed:
  - escape batch completed:
  - clean confirmation completed:
- Continue if:
  - explicit target is unmet and useful GPU slots are available
  - current best is only a local result without an escape batch
  - current best sits on a scanned boundary
  - no user stop or budget exhaustion has occurred
