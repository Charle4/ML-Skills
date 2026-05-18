# GPU Slot Policy

## Defaults

These apply whenever no override is in effect:

| Parameter | Default | Hard limit |
|---|---|---|
| Concurrent experiments per GPU | 1 | 3 per GPU |
| GPU utilization ceiling | 95% | — |
| Memory cap per GPU slot | none | — |
| GPU selection | all GPUs nvidia-smi reports | — |

The default of 1 per GPU is conservative and safe for most methods. Raise it only when evidence supports it (see "When to use multiple per GPU" below).

## Override Sources (checked in priority order)

1. **User instruction in the current session** — highest priority; honor immediately
2. **Project adapter** (`references/project-adapter-*.md`) — project-specific scheduling rules
3. **Project README or experiment notes** — documented conventions for the codebase
4. **Project memory** (`aet/knowledge.md` or the project's memory system) — rules recorded from prior sessions

When an override specifies which GPU indices to use, launch only on those GPUs. Do not use unlisted GPUs without asking.

## Configurable Parameters

Users and project adapters can provide any of the following:

| Parameter | Example | Effect |
|---|---|---|
| `gpu_ids` | `[0, 1, 3]` | Only use these GPU indices |
| `max_per_gpu` | `2` | Maximum concurrent experiments per GPU (hard cap: 3 unless user explicitly overrides) |
| `max_memory_used_mb` | `70000` | Skip a GPU whose used memory is already at or above this value |
| `min_free_memory_mb` | `20000` | Skip a GPU unless at least this much memory is free |
| `max_util` | `80%` | Do not launch onto a GPU whose utilization is at or above this threshold |

If the user says "use GPU 2 and 3, up to 2 jobs each", record that in the session `meta.json` and plan accordingly.

## Runtime Slot Check

Before each launch, check available slots:

```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader
python SKILL_DIR/scripts/aet.py gpu-slots
```

The raw `nvidia-smi` command is for readable context and keeps units. The helper command uses `nvidia-smi --format=csv,noheader,nounits` internally so it can parse memory and utilization reliably.

A GPU slot is **available** if all of the following hold:
- GPU utilization is below `max_util` (default 95%)
- Active experiments on that GPU are below `max_per_gpu` (default 1)
- If a memory limit is set: used memory is below `max_memory_used_mb` and/or remaining memory is at least `min_free_memory_mb`

If all configured GPUs are at capacity, wait for the next completion notification rather than forcing a launch.

Use `--kind default|light|heavy` for generic estimates. If a project adapter or user instruction gives a project-specific limit, pass it explicitly with `--capacity N`, `--gpu-ids`, `--saturated-util`, `--max-memory-used-mb`, or `--min-free-memory-mb` rather than adding project-specific method names to the helper script.

CLI mapping:

| Policy setting | `aet.py gpu-slots` flag |
|---|---|
| `gpu_ids: [0, 1, 3]` | `--gpu-ids 0,1,3` |
| `max_per_gpu: 2` | `--capacity 2` |
| `max_util: 80%` | `--saturated-util 80` |
| "util unlimited" / "util 无限制" | `--saturated-util 101` (> 100 disables the ceiling entirely) |
| `max_memory_used_mb: 70000` | `--max-memory-used-mb 70000` |
| `min_free_memory_mb: 20000` | `--min-free-memory-mb 20000` |

## When to Use Multiple Experiments per GPU

Raise `max_per_gpu` above 1 only when:
- The method is memory-light (short iterative optimization, small-batch inference, not full diffusion or large-model training)
- Prior runs in this session confirm GPU memory and utilization stay within limits under the extra load
- The user or project adapter explicitly permits concurrent runs on the same GPU

Never exceed 3 experiments per GPU without an explicit user instruction that names a higher number.
