# Run Summary

Canonical file: this template is rendered by `aet.py create-run` into `SESSION/runs/<id>/summary.md`. Keep updating that generated file in place; do not create separate run-summary files under `PROJECT/aet/` or `PROJECT/aet/YYYY-MM-DD/`.

`aet.py record` rewrites this file when status or metrics change. Fill trust-check, metric-source, and takeaway fields after the terminal record, or reapply them if another record call is needed later.

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

## Metric Source

- Primary metric source file:
- Extraction method: <!-- structured JSON/CSV/NPZ, event file, log regex, or manual -->
- Metric definition/comparability notes:

## Trust Check

- Output files:
- Log matches command:
- GPU contention:
- Comparable metric:

## Takeaway
