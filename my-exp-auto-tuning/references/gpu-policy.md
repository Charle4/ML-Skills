# GPU Slot Policy

Read this file at session start after [workflow.md](workflow.md). Persist the selected GPU policy and apply the multi-run conditions below.

## Configurable Parameters

Users and project adapters can provide any of the following overrides:

| Parameter | Example | Effect |
|---|---|---|
| `gpu_ids` | `[0, 1, 3]` | Only use these GPU indices |
| `max_per_gpu` | `2` | Maximum concurrent experiments per GPU (hard cap: 3 unless user explicitly overrides) |
| `max_memory_used_mb` | `70000` | Skip a GPU whose used memory is already at or above this value |
| `min_free_memory_mb` | `20000` | Per-job GPU memory requirement — free memory divides into slots (see below) |
| `max_util` | `80%` | Do not launch onto a GPU whose utilization is at or above this threshold |

If the user says "use GPU 2 and 3, up to 2 jobs each", persist it once with `aet.py set-policy --gpu-ids 2,3 --max-per-gpu 2` (or pass the same flags to `aet.py init`). It is stored in `meta.json` `gpu_policy`, and `gpu-slots` / `loop-state` / `strategist-begin` all read that one stored policy, so capacity is computed consistently across commands.

Treat the GPU-id list printed by `loop-state` as slot occurrences. When `max_per_gpu > 1`, the same GPU id may appear more than once; assign one routed run to each occurrence.

### How memory limits become slots

`min_free_memory_mb` states what **one** job needs, so a GPU's slot count is `min(max_per_gpu - running, free_memory // min_free_memory_mb)`. With `--max-per-gpu 2 --min-free-memory-mb 5000`, a card holding 6 GB free offers one slot, not two; once that job has taken its memory the next `loop-state` re-measures and opens a second slot only if at least 5 GB is still free. Memory requirements are usually stated conservatively, so this staged filling is the expected steady state, not an anomaly. `gpu-slots` prints the `memory_slots` term alongside `capacity` so the binding constraint is visible.

`max_memory_used_mb` is a whole-card gate: at or above it the GPU offers no slots regardless of how much memory remains. `total_capacity` is the nominal `max_per_gpu × gpu_count` — it is the Ready Queue refill target, so it stays fixed under the stored policy rather than tracking live memory, which would make the queue target drift with other users' load.

## CLI Mapping

Persist limits once via `aet.py set-policy` (or `init`); the flags below are also accepted as one-off overrides on `aet.py gpu-slots`. Do not add project-specific method names to the helper script. Use `--kind default|light|heavy` only for generic estimates when no policy is stored.

| Policy setting | `aet.py gpu-slots` flag |
|---|---|
| `gpu_ids: [0, 1, 3]` | `--gpu-ids 0,1,3` |
| `max_per_gpu: 2` | `--max-per-gpu 2` |
| `max_util: 80%` | `--max-util 80` |
| "util unlimited" / "util 无限制" | `--max-util 101` (> 100 disables the ceiling entirely) |
| `max_memory_used_mb: 70000` | `--max-memory-used-mb 70000` |
| `min_free_memory_mb: 20000` | `--min-free-memory-mb 20000` (per-job requirement) |

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

Set `min_free_memory_mb` in the same `set-policy` call that raises `max_per_gpu`. It is what keeps the extra slots from being handed out on a card that cannot hold them: without it the slot count is the process count alone, so a card with 2 GB free still offers a second slot.

Never exceed 3 experiments per GPU without an explicit user instruction that names a higher number.
