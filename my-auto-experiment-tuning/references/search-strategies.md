# Search Strategies

Use this file when deciding what to run next.

## General Principles

- Start from a known-good baseline before changing many knobs.
- Change one conceptual factor per planning group unless testing an interaction.
- Always ask which knobs interact mechanistically before interpreting a one-dimensional sweep.
- Do not conclude "parameter X is bad" unless the relevant companion knobs have been held in valid regimes or explicitly varied.
- Spend early budget on broad coverage of plausible interaction groups; spend late budget on local refinement and confirmation.
- Search log-scale for learning rates, regularization weights, noise levels, and guidance scales.
- Search linearly for switch iterations, iteration counts, crop IDs, and discrete time indices.
- Treat a collapse as information, not noise, if repeated under clean conditions.
- Treat a surprising high result as provisional until confirmed under clean conditions.
- For open-ended tuning, assume the search should continue across many planning groups. A good result should trigger refinement, boundary expansion, seed checks, or alternative-regime tests rather than an immediate final answer.

## Baseline Fidelity Checks

When a standard baseline is far below literature or project expectations:
- Pause pure hyperparameter sweeps and audit implementation fidelity first.
- Check objective terms, regularizers, loss schedules, seeds, color spaces, preprocessing, postprocessing, evaluation crops, and metric definitions.
- Compare project notes and prior assistant analyses against source code, papers, logs, and controlled ablations; treat notes as hypotheses until verified.
- If missing CLI knobs require script edits, keep defaults backward compatible and record exactly which code change made new results comparable or non-comparable.

## Interaction and Sensitivity

- Treat hyperparameter tuning as response-surface exploration, not independent one-dimensional optimization.
- Identify coupled groups before launching narrow scans. Examples: learning rate with regularizer weight; noise schedule with guidance strength; loss switch with iteration budget; kernel regularization with kernel size; seed with zero-shot neural optimization.
- Use small factorial or fractional-factorial candidate groups to expose interactions when the space is not yet understood.
- If two one-dimensional scans disagree, assume a hidden interaction until ruled out.
- If a local optimum is found by coordinate descent, run at least one broader escape group around alternative regimes before declaring the space exhausted.
- Promote random seed and initialization to first-class knobs for zero-shot, DIP, and self-supervised neural optimization baselines.
- Test coupled parameter groups when mechanisms interact, for example regularizer weight with loss switch, seed, channel mode, and iteration budget.
- Do not declare a parameter globally good or bad from a single-factor scan if another active knob changes the mechanism.
- For sentinel values that disable schedules, verify the sentinel still disables the schedule for the current iteration count. Prefer an explicit disable flag or a value greater than `iters`.
- For constrained variables such as Softmax-normalized kernels, reason about the regularizer under the constraint before interpreting it. An L2 penalty on a simplex can encourage uniformity rather than sparsity.
- Mark runs from groups that used a later-discovered data conversion or metric bug as `inconclusive`, then rerun only the informative candidates cleanly.

## Strategy Selection

Few knobs, cheap runs:
- Use structured grid or paired comparisons.
- Run full-length if runtime is small.

Many knobs, expensive runs:
- Use coarse exploration first.
- First test a sparse interaction design over the most plausible coupled groups.
- Fix obviously important knobs only after their main interactions are understood.
- Use coordinate descent around the current best only as a refinement phase, not as the entire search.
- If the user expects hundreds of experiments, cycle phases: broad interaction design → local refinement → clean confirmation → escape group → next interaction family. Do not spend the whole session in one local basin.

Non-smooth or discrete landscapes:
- Do not assume neighboring values behave similarly.
- Confirm isolated peaks with independent reruns.
- Avoid overfitting a smooth curve to jagged data.

Resource-sensitive runs:
- Include a "clean confirmation" phase with lower parallelism.
- Mark overloaded runs as inconclusive if project history shows contention changes metrics.

## Rolling Queue Design

A good planning group has:
- 3-12 independent configurations, depending on runtime, configured capacity, and method risk
- a single written hypothesis
- at least one baseline or known-good anchor if contamination is possible
- output names that encode the varied knobs

For open-ended/high-resource tuning:
- Maintain a `Ready Queue`, not just a same-size batch. Ready candidates must be strictly greater than current free GPU slots whenever useful unexplored regions remain.
- If free slots = N, plan at least N+1 ready candidates. If free slots = 0, keep at least one ready candidate unless a valid stop condition is documented.
- Keep the ready queue compact enough to stay relevant: usually no more than about 2x configured total capacity unless runs are very short or the method tolerates a larger backlog.
- Fill GPU slots from `Ready Queue` immediately as they open; do not wait for the rest of the planning group to finish.
- After analyzing a completed run, append 0, 1, or several candidates depending on what the result teaches. Do not force one-new-run per finished run.
- Prefer many medium-cost screening runs plus periodic clean confirmations over a few very long local runs, unless the metric is only meaningful at full length.
- Record every run even when it is a failure; failed regions are what justify continued expansion rather than repeated local probing.

Poor queue patterns:
- random values without a hypothesis
- repeating a known-bad region
- scanning too narrowly before checking wider scale
- optimizing one parameter at a time for many rounds without interaction checks
- declaring a local peak final before testing an alternative regime
- launching more parallel jobs than the method can tolerate
- combining multiple unrelated changes so the result cannot be attributed
- keeping `Ready Queue` empty or equal to free slots while useful search remains
- waiting for all currently running experiments to finish before collecting one finished run or filling currently free slots from `Ready Queue`

## Boundary Expansion

If the best value is at the edge of a tested range:
- expand one step beyond the edge
- keep one anchor at the previous best
- stop expanding after the metric clearly degrades or violates a constraint

## Confirmation Runs

Confirm when:
- the new best is much better than prior results
- the new best occurred during different GPU load
- the landscape is known to have isolated peaks
- benchmark claims or paper figures depend on the result

Do not over-confirm:
- repeated bad configurations
- methods already shown to be dominated
- dense neighbors around a known isolated failure band

## Stopping Rules

Stop when one of these is true:
- the user objective is met with clean evidence
- the remaining plausible improvement is too small to affect the decision and this is supported by the minimum plateau evidence below
- the parameter space is exhausted by project-specific constraints
- the run budget or wall-clock budget is consumed
- additional experiments require code changes outside the requested scope

Minimum plateau evidence for open-ended tuning:
- at least 30 finished or inconclusive runs for the target method, unless runs are extremely expensive or the user set a smaller budget
- at least one broad interaction group after implementation fidelity is trusted
- at least one local refinement group around the current best
- at least one escape group testing a different regime after the current best
- at least one clean confirmation of the current best if it will update a benchmark or paper-facing table
- no untested boundary where the current best sits at the edge of a scanned range

If these conditions are not met and the explicit target is not met, continue tuning.

Report the stopping reason explicitly.
