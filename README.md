# Skills for research workflows

<!-- TOC -->

- [Skills for research workflows](#skills-for-research-workflows)
  - [Skills](#skills)
    - [`my-auto-experiment-tuning`](#my-auto-experiment-tuning)
      - [Install](#install)
      - [Example invocation](#example-invocation)
      - [What to tell the agent](#what-to-tell-the-agent)
    - [`my-zh-academic-polish`](#my-zh-academic-polish)
      - [Install](#install-1)
      - [Example invocation](#example-invocation-1)
      - [What to tell the agent](#what-to-tell-the-agent-1)
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

### `my-zh-academic-polish`

Chinese academic writing assistant for journal-style rewriting, conservative polishing, AI-like wording reduction, translationese cleanup, and formal paragraph drafting. Best suited for computer science papers, Chinese core journal style, dissertation prose, and Word-friendly pure-text output.

**Core features:**

- 重构写作: turn rough notes, oral descriptions, fragmented ideas, or bullet lists into coherent Chinese academic paragraphs
- 克制润色: polish already formed Chinese academic prose while preserving authorial intent, terminology, citations, formulas, and section structure
- 去 AI 味: remove empty rhetoric, mechanical connectors, translationese, inflated claims, and unnatural model-generated phrasing
- 撰写辅助: draft formal Chinese academic prose from clear technical points, constraints, and intended claims

#### Install

Claude Code:

```bash
ln -s $(pwd)/my-zh-academic-polish ~/.claude/skills/my-zh-academic-polish
```

Codex:

```bash
ln -s $(pwd)/my-zh-academic-polish ~/.codex/skills/my-zh-academic-polish
```

#### Example invocation

Claude Code:

```
/my-zh-academic-polish 帮我把下面这段中文论文草稿重构成自然、严谨的计算机学术论文表达，保留 Transformer、PSNR 和公式符号。

草稿：
我们的方法主要是想解决退化未知的时候恢复不稳定的问题。先用一个网络估计退化，再用扩散模型做先验约束，最后在几个数据集上效果更好。
```

Codex:

```
$my-zh-academic-polish 帮我给下面段落降 AI 味，去掉翻译腔和空泛表达，输出 Word 友好的纯文本。

原文：
该方法展现了令人惊叹的能力，并且在多种复杂场景下体现出强大的泛化潜力，为相关领域带来了颠覆性影响。
```

#### What to tell the agent

The skill works best when you name the writing mode and provide the text scope clearly.

_Common task modes:_

| Mode     | Use when                                                       | Example request                            |
| -------- | -------------------------------------------------------------- | ------------------------------------------ |
| 重构写作 | Input is rough notes, lists, oral wording, or fragmented ideas | `"把这些要点改成一段论文正文"`             |
| 克制润色 | Input is already a formed academic paragraph                   | `"只做必要润色，保留原意和术语"`           |
| 去 AI 味 | Text sounds model-generated, inflated, or translation-like     | `"降 AI 味，去掉空泛套话和机械连接"`       |
| 撰写辅助 | You have technical points and need a formal paragraph          | `"根据这些技术点写一段方法介绍"`           |
| 文件编辑 | A file contains the passage to polish                          | `"润色 section 2.1，保留引用、公式和表格"` |

_Recommended context:_

| Information                    | Example                                       |
| ------------------------------ | --------------------------------------------- |
| Target style or venue          | `"按《计算机学报》中文论文风格"`              |
| Editing strength               | `"克制润色"` / `"大幅重构"` / `"只改病句"`    |
| Text boundaries                | `"只处理摘要第二段"` / `"只改引言最后三段"`   |
| Terms that must be preserved   | `"保留 LLM、diffusion model、Few-shot、PSNR"` |
| Formatting constraints         | `"输出纯文本，方便粘贴到 Word"`               |
| Claims that cannot be invented | `"不要增加实验结论、引用或未给出的消融分析"`  |

_Default output behavior:_

- Chat-only polishing returns `[正文]` plus a short `[修改说明]`, `[逻辑说明]`, or `[修改日志]` depending on the task.
- File edits keep the target document clean: no review labels, modification logs, or skill metadata are inserted into the file unless explicitly requested.
- If the original text is already clear and publishable, the skill may preserve it and explain that no substantive edit is needed.

### Coming Soon

---

## See Also

- [Using DeepSeek with Claude Code](https://api-docs.deepseek.com/zh-cn/guides/agent_integrations/claude_code)
- [Using GLM with Claude Code](https://docs.bigmodel.cn/cn/guide/develop/claude)
