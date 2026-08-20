# Skill Benchmark: mpaper-bib-tidy

**Model**: Sonnet
**Date**: 2026-07-29T11:26:28Z
**Evals**: 1, 2, 3, 4 (1 run per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100% ± 0% | 69% ± 14% | +0.31 |
| Time | 0.0s ± 0.0s | 0.0s ± 0.0s | +0.0s |
| Tokens | 0 ± 0 | 0 ± 0 | +0 |

## Limitations

- Each configuration ran once with Sonnet. The reported variation is across four distinct evals, not repeated stochastic trials.
- The Agent runtime prohibited subagents from writing `summary.md`. Their returned Tier 1/2/3 reports were persisted by the coordinator; formal grades still cover only deterministic `result.bib` transformations.
- Timing and token counts were not persisted by the Agent runtime, so the zero values are unavailable measurements rather than performance claims.
- The real-entry fixture contains eight entries copied from `CLIP-Deblur/Paper/ECCV_2026/paper/main.bib` and only deliberate formatting defects. The source and its archival copy were hash-verified unchanged.
- Iteration 1 is not comparable because it rewarded unverified Tier 2 venue and entry-type rewrites that the current skill prohibits.
