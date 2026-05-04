# Run Summary

Canonical file: this template is rendered by `aet.py create-run` into `SESSION/runs/<id>/summary.md`. Keep updating that generated file in place; do not create separate run-summary files under `PROJECT/aet/` or `PROJECT/aet/YYYY-MM-DD/`.

`aet.py record` rewrites this file when status or metrics change. Fill detailed trajectory, trust-check, and takeaway fields after the terminal record, or reapply them if another record call is needed later.

## Command

```bash
{{ command }}
```

## Parameters

```json
{{ params_json }}
```

## Metrics

```json
{{ metrics_json }}
```

## Optimization Trajectory (optional — fill if intermediate metrics are logged)

<!-- Key checkpoints only, ~4-6 points across the run. Adapt label to method (epoch/iter/step). -->

| checkpoint | primary metric | loss (if logged) |
| ---------- | -------------- | ---------------- |
|            |                |                  |

Convergence diagnosis: <!-- healthy / overfitting / underfitting / divergence / oscillation / n/a -->

## Trust Check

- Output files:
- Log matches command:
- GPU contention:
- Comparable metric:

## Takeaway
