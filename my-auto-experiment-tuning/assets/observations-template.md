# Observations

Canonical file: this template is rendered by `aet.py init` into `PROJECT/aet/YYYY-MM-DD/HH-MM-SS/observations.md`. Keep updating that generated file in place; do not create separate observation files under `PROJECT/aet/` or `PROJECT/aet/YYYY-MM-DD/`.

- Created: `{{ created_at }}`
- Objective: {{ objective }}

## Run Notes

<!-- Append short notes after each completed, failed, or inconclusive run. Include the run id, metric, trust status, and one actionable takeaway. -->
<!-- `aet.py record --notes` appends here automatically. Prefer notes on terminal statuses; omit routine running notes unless an anomaly matters. -->

## Reusable Rules

<!-- Promote repeated findings here, such as forbidden parameter regions, contamination patterns, or consistently promising settings. -->

## Final Analysis

<!-- Fill this only when a valid stop condition is met. Include best configuration, per-HP influence summary, and future exploration directions. -->
