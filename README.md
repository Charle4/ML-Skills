# Skills for ML research workflows

<!-- TOC -->

- [Skills for ML research workflows](#skills-for-ml-research-workflows)
  - [Skills](#skills)
    - [`my-auto-experiment-tuning`](#my-auto-experiment-tuning)
    - [Coming Soon](#coming-soon)
  - [See Also](#see-also)

<!-- /TOC -->

---

## Skills

### `my-auto-experiment-tuning`

Hypothesis-driven hyperparameter tuning loop for ML experiments. Works with both Claude Code and Codex.

**Core features:**

- Durable session state in `aet/` inside the project — survives context compaction
- `aet.py` CLI for session init, GPU slot inspection, run recording, and summaries
- Project-specific adapters via `references/project-adapter-*.md`

#### Install

Claude Code:

```bash
ln -s $(pwd)/my-auto-experiment-tuning ~/.claude/skills/my-auto-experiment-tuning
```

Codex:

```bash
ln -s $(pwd)/my-auto-experiment-tuning ~/.codex/skills/my-auto-experiment-tuning
```

#### Example invocation

Claude Code:

```
/my-auto-experiment-tuning Tune train.py (NAFNet deblurring). Maximize PSNR on test set.
Target: PSNR > 30 dB (hard stop). Use GPU 0 and 1 only, max 16 GB VRAM per slot, util ≤ 80%.
Key hyperparams: lr [1e-5, 5e-3] log scale, batch_size {4, 8, 16}, num_blocks {8, 16, 32}.
Current best is PSNR 28.7 with lr=1e-3, batch=8, num_blocks=16. lr > 1e-2 is unstable.
Launch: python train.py --lr LR --batch_size BS --num_blocks NB --gpu_id GPU --output_dir DIR
```

Codex:

```
$my-auto-experiment-tuning Tune train.py (NAFNet deblurring). Maximize PSNR on test set.
Target: PSNR > 30 dB (hard stop). Use GPU 0 and 1 only, max 16 GB VRAM per slot, util ≤ 80%.
Key hyperparams: lr [1e-5, 5e-3] log scale, batch_size {4, 8, 16}, num_blocks {8, 16, 32}.
Current best is PSNR 28.7 with lr=1e-3, batch=8, num_blocks=16. lr > 1e-2 is unstable.
Launch: python train.py --lr LR --batch_size BS --num_blocks NB --gpu_id GPU --output_dir DIR
```

#### What to tell the agent

The skill runs autonomously once started. The more context you give upfront, the better the initial plan.

_Required — the agent will ask if missing:_

| Information                                   | Example                                            |
| --------------------------------------------- | -------------------------------------------------- |
| Optimization objective and metric direction   | `"maximize PSNR"` / `"minimize val loss"`          |
| Which script(s) to run and how to launch them | `"run <script>.py with --gpu_id and --output_dir"` |

_Recommended — significantly improves the first plan:_

| Information                                 | Example                                                    |
| ------------------------------------------- | ---------------------------------------------------------- |
| Hyperparameter names and search ranges      | `"lr in [1e-5, 1e-2] log scale"`                           |
| Known baseline / current best               | `"current best PSNR is 33.4 on <test_img_file.png>"`       |
| Numeric target threshold                    | `"stop when PSNR > 25"` — treated as a hard stop condition |
| Known-bad regions or forbidden combinations | `"lr=0.1 is unstable"`                                     |

_Optional — all have defaults, override when needed:_

| Information                        | Default                              | Example override                                                  |
| ---------------------------------- | ------------------------------------ | ----------------------------------------------------------------- |
| Which GPUs to use                  | all available                        | `"use GPU 0 and 2 only"`                                          |
| Max concurrent experiments per GPU | 1 (hard cap: 3)                      | `"up to 2 jobs per GPU"`                                          |
| GPU memory cap per slot            | none                                 | `"leave 6 GB headroom per GPU"`                                   |
| GPU utilization ceiling            | 95%                                  | `"don't exceed 80% util"`                                         |
| Run budget                         | open-ended                           | `"stop after 30 runs"` or `"run for 2 hours"`                     |
| Search style                       | broad interaction first, then refine | `"skip broad exploration, start local refinement around lr=1e-4"` |

_Mode flags — say these phrases to change behavior:_

| Phrase               | Effect                                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| `"use subagents"`    | Activates Strategist / Runner / Analyzer parallel roles                                         |
| `"set up keepalive"` | Agent configures `/loop` for periodic wakeup during long multi-hour sessions (Claude Code only) |
| `"stop"` / `"pause"` | Agent records state and stops; session is resumable later                                       |

_Advanced — for power users:_

- Drop a `references/project-adapter-<name>.md` in the skill directory to encode project-specific launch conventions, GPU rules, benchmark format, and forbidden regions once — the agent picks it up automatically on any future session in that project.
- The agent writes all session state to `aet/` inside your project root. After a context reset or crash, just re-invoke the skill — it will resume from the last recorded state.

### Coming Soon

---

## See Also

- [Using DeepSeek with Claude Code](https://api-docs.deepseek.com/zh-cn/guides/agent_integrations/claude_code)
- [Using GLM with Claude Code](https://docs.bigmodel.cn/cn/guide/develop/claude)
