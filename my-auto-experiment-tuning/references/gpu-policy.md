# GPU Slot Policy

Slot defaults, the override-priority chain, the runtime slot check, and the `total_capacity` definition are in `references/workflow.md` section 6. This file holds the override configuration tables and the conditions for running more than one experiment per GPU.

## Configurable Parameters

Users and project adapters can provide any of the following overrides:

| Parameter | Example | Effect |
|---|---|---|
| `gpu_ids` | `[0, 1, 3]` | Only use these GPU indices |
| `max_per_gpu` | `2` | Maximum concurrent experiments per GPU (hard cap: 3 unless user explicitly overrides) |
| `max_memory_used_mb` | `70000` | Skip a GPU whose used memory is already at or above this value |
| `min_free_memory_mb` | `20000` | Skip a GPU unless at least this much memory is free |
| `max_util` | `80%` | Do not launch onto a GPU whose utilization is at or above this threshold |

If the user says "use GPU 2 and 3, up to 2 jobs each", persist it once with `aet.py set-policy --gpu-ids 2,3 --max-per-gpu 2` (or pass the same flags to `aet.py init`). It is stored in `meta.json` `gpu_policy`, and `gpu-slots` / `loop-state` / `strategist-begin` all read that one stored policy, so capacity is computed consistently across commands.

## CLI Mapping

Persist limits once via `aet.py set-policy` (or `init`); the flags below are also accepted as one-off overrides on `aet.py gpu-slots`. Do not add project-specific method names to the helper script. Use `--kind default|light|heavy` only for generic estimates when no policy is stored.

| Policy setting | `aet.py gpu-slots` flag |
|---|---|
| `gpu_ids: [0, 1, 3]` | `--gpu-ids 0,1,3` |
| `max_per_gpu: 2` | `--capacity 2` |
| `max_util: 80%` | `--max-util 80` |
| "util unlimited" / "util 无限制" | `--max-util 101` (> 100 disables the ceiling entirely) |
| `max_memory_used_mb: 70000` | `--max-memory-used-mb 70000` |
| `min_free_memory_mb: 20000` | `--min-free-memory-mb 20000` |

## Process Pattern (required at init)

`--process-pattern` is required when creating a session (`aet.py init`). It is a regex matched against `ps ax` output to identify this session's experiment processes. `loop-state` uses it to detect experiments that finished but were never recorded with a terminal `aet.py record` — without it, those ghost "running" entries cause `loop-state` to report stale free slots and route launches onto GPUs that should first have their results collected.

### Good patterns

| Pattern | Why it works |
|---|---|
| `exp_dip_deblur\.py` | Matches the exact script filename |
| `experiments/exp_clip_deblur` | Matches a path fragment unique to this project's experiment script |
| `run_diffusion_sampling\.py` | Matches a distinctive script name |

### Bad patterns (rejected by `init`)

| Pattern | Problem |
|---|---|
| `python` | Matches every Python process on the system |
| `python3` | Same — too broad |
| `train` | Matches unrelated training scripts from other projects |
| `exp` | Matches `export`, `expect`, other projects' `exp_*` scripts |

### Edge cases

- If a project uses multiple experiment scripts (e.g. `exp_train.py` and `exp_eval.py`), use a shared path prefix: `'experiments/exp_'`. Ensure this prefix does not match scripts from other active AET sessions on the same machine.
- If only one script is used, prefer the full filename with escaped dot: `'exp_dip_deblur\\.py'`.
- The pattern is stored in `meta.json` `gpu_policy.process_pattern`. Update it mid-session with `aet.py set-policy --process-pattern '...'` if the experiment script changes.

## When to Use Multiple Experiments per GPU

Raise `max_per_gpu` above 1 only when:
- The method is memory-light (short iterative optimization, small-batch inference, not full diffusion or large-model training)
- Prior runs in this session confirm GPU memory and utilization stay within limits under the extra load
- The user or project adapter explicitly permits concurrent runs on the same GPU

Never exceed 3 experiments per GPU without an explicit user instruction that names a higher number.
