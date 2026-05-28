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
    - [`my-en-academic-writing`](#my-en-academic-writing)
      - [Install](#install-2)
      - [Example invocation](#example-invocation-2)
      - [What to tell the agent](#what-to-tell-the-agent-2)
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
mkdir -p ~/.claude/skills ~/.claude/agents
ln -s $(pwd)/my-auto-experiment-tuning ~/.claude/skills/my-auto-experiment-tuning
ln -s $(pwd)/my-auto-experiment-tuning/agents/experiment-runner.md ~/.claude/agents/experiment-runner.md
ln -s $(pwd)/my-auto-experiment-tuning/agents/experiment-strategist.md ~/.claude/agents/experiment-strategist.md

# Set environment variables
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

Codex:

```bash
mkdir -p ~/.codex/skills ~/.codex/agents
ln -s $(pwd)/my-auto-experiment-tuning ~/.codex/skills/my-auto-experiment-tuning
ln -s $(pwd)/my-auto-experiment-tuning/codex-agents/experiment-runner.toml ~/.codex/agents/experiment-runner.toml
ln -s $(pwd)/my-auto-experiment-tuning/codex-agents/experiment-strategist.toml ~/.codex/agents/experiment-strategist.toml
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
| `"use subagents"`    | Activates Strategist / Runner parallel roles                                                    |
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

### `my-en-academic-writing`

English academic writing assistant for LaTeX polishing, Chinese-to-English translation, AI-like wording reduction, section drafting, related-work synthesis, grammar checking, and focused proofreading.

**Core features:**

- Polish / rewrite: conservative cleanup or deep publication-level rewriting of English LaTeX
- De-AI rewrite: remove formulaic, inflated, model-generated phrasing while preserving technical content
- Chinese-to-English translation: translate Chinese drafts into rigorous English academic LaTeX, with Chinese back-translation for checking
- Section drafting: draft a complete section from an outline or notes without adding unsupported claims
- Related-work synthesis: summarize and position literature thematically with factual limitations
- Grammar check / focused proofreading: surface-level correction for near-submission text
- External review pass: when Codex or Gemini MCP tools are configured, the agent dispatches an independent cold-context review and synthesizes the feedback before finalizing output

#### Install

Claude Code:

```bash
ln -s $(pwd)/my-en-academic-writing ~/.claude/skills/my-en-academic-writing
```

Codex:

```bash
ln -s $(pwd)/my-en-academic-writing ~/.codex/skills/my-en-academic-writing
```

#### Example invocation

Polish an English LaTeX passage:

```
/my-en-academic-writing Deep polish the following paragraph for ICLR submission. Preserve all LaTeX commands.

Despite the success of diffusion-based methods in image restoration, existing approaches typically require
the degradation type to be known \textit{a priori}, which significantly limits their practical applicability.
To address this limitation, we propose \texttt{BlindDiff}, a blind image restoration framework that jointly
estimates the degradation kernel and performs restoration under a unified diffusion prior.
```

Chinese-to-English translation:

```
/my-en-academic-writing 把下面这段话翻译成 NeurIPS 风格的英文学术 LaTeX，保留公式符号，输出 Part 1 [LaTeX] 和 Part 2 [Translation]。

尽管基于扩散模型的方法在图像复原中取得了显著进展，现有方法通常要求退化类型已知，
这严重限制了其在真实场景中的适用性。
```

De-AI rewrite:

```
/my-en-academic-writing De-AI this paragraph. Remove mechanical connectors and inflated claims. Keep all \cite{} and \eqref{} unchanged.

In the realm of image restoration, our method leverages cutting-edge diffusion priors to foster robust
and versatile recovery, paving the way for unprecedented performance across diverse degradation scenarios.
```

#### What to tell the agent

The skill selects the editing mode from your request automatically. Naming the mode explicitly ("deep polish", "de-AI", "translate", "grammar check") gives the most precise result.

_Task modes:_

| Mode                   | Use when                                             | Example request                                                      |
| ---------------------- | ---------------------------------------------------- | -------------------------------------------------------------------- |
| Conservative polish    | Text is nearly ready; minimize changes               | `"只做必要修改，保留句式结构"` / `"light touch, preserve structure"` |
| Deep polish / rewrite  | Substantial improvement needed for publication       | `"deep polish for NeurIPS"` / `"rewrite for top-conference quality"` |
| De-AI rewrite          | Text sounds model-generated, inflated, or mechanical | `"de-AI this paragraph"` / `"remove AI-like phrasing"`               |
| Chinese-to-English     | Input is Chinese; need English academic LaTeX        | `"翻译成英文学术 LaTeX"` / `"translate and polish"`                  |
| Section drafting       | You have an outline or notes                         | `"draft the Related Work section from this outline"`                 |
| Related-work synthesis | You have a reference list to synthesize              | `"write a related work paragraph grouping these by method family"`   |
| Grammar check          | Identify errors without rewriting                    | `"grammar check only, list issues in a table"`                       |
| Focused proofreading   | Near-submission, want surface fixes only             | `"proofread without restructuring"`                                  |
| Venue adaptation       | Tune style to a specific target                      | `"adapt for applied mathematics journal"`                            |

_Recommended context:_

| Information                 | Example                                                        |
| --------------------------- | -------------------------------------------------------------- |
| Target venue or style       | `"NeurIPS"` / `"IEEE Transactions"` / `"CCF A"`                |
| Editing strength            | `"minimal"` / `"deep rewrite"` / `"only fix grammar"`          |
| Text scope                  | `"only Section 3.2"` / `"just the abstract"`                   |
| Terms to preserve           | `"keep LLM, diffusion model, PSNR, and all \cite{} unchanged"` |
| Output format               | `"只输出英文"` / `"no modification log"`                       |
| Claims that cannot be added | `"do not add new experimental results or citations"`           |

_Default output (chat mode):_

- English LaTeX polishing returns `Part 1 [LaTeX]` + `Part 2 [Translation]` + `Part 3 [Modification Log]`.
- Chinese-to-English translation returns `Part 1 [LaTeX]` + `Part 2 [Translation]`.
- Grammar check returns a Markdown table of issues and suggested corrections.
- Say `只输出英文` / `manuscript only` / `no explanation` to suppress the translation and log.
- File edits keep the manuscript clean: no modification logs or skill metadata are inserted into the file.

---

## See Also

- [Using DeepSeek with Claude Code](https://api-docs.deepseek.com/zh-cn/guides/agent_integrations/claude_code)
- [Using GLM with Claude Code](https://docs.bigmodel.cn/cn/guide/develop/claude)
- [Using MiMo with Claude Code](https://platform.xiaomimimo.com/docs/zh-CN/integration/claudecode)
