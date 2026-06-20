# Tuning Session

- Objective: {{ objective }}
- Metric direction: {{ goal }}
- Created: {{ created_at }}

## Target & Constraints

- Metric:
- Baseline:
- Current best:
- Explicit target threshold:
- Success criterion:
- Budget: open-ended until target/user stop, unless specified otherwise
- Compute budget:
- GPU parallelism: (authoritative policy is script-owned in `meta.json`; set with `aet.py set-policy`)
- GPU slots / total_capacity: read `aet.py gpu-slots` or `aet.py loop-state` (live)
- Queue invariant: keep `planned` count at or above total_capacity whenever useful unexplored regions remain. Run the Strategist transaction whenever count drops below total_capacity.
- Invalid or untrusted conditions:
- Forbidden parameter regions:

## Hypotheses & Coupled Parameters

<!-- List numbered hypotheses, then the coupled-parameter table. -->

1.
2.
3.

| Group | Why Coupled | Broad Test | Local Refinement Trigger |
| ----- | ----------- | ---------- | ------------------------ |

## Reusable Rules

<!-- Promote repeated findings here: forbidden parameter regions, contamination patterns, consistently promising settings. Append only — this section accumulates across Strategist calls. -->

## Current Analysis

<!-- Overwritten each Strategist call with observations_to_append. Only the latest analysis lives here. -->

## Stop/Continue Rule

<!-- Overwritten each Strategist call. -->

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

## Final Analysis

<!-- Fill only when a valid stop condition is met. Include best configuration, per-HP influence summary, and future exploration directions. -->
