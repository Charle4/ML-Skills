Read this file only when running under an approval-gated sandbox (not full auto/bypass) or when a command is blocked and you need a narrowly scoped escalation.

# Permissions

## What the Skill Can and Cannot Grant

A skill cannot grant filesystem, network, GPU, or shell permissions by itself. It only tells you how to work. Actual permission decisions still come from the active sandbox, the approval policy, and the user's approved command-prefix rules (Codex sandbox/approval policy, or Claude Code allow/deny rules in settings.json).

If a command is blocked, the agent must request escalation once with a narrowly scoped prefix rule. After the user approves that prefix, later matching commands can run without repeated interruption.

## Command Shape and Prefix Hygiene

Approval matching is sensitive to command shape. Prefer stable, simple prefixes:
- Pick one interpreter style for the project, such as the venv Python path or `python` inside an activated environment, then keep it consistent across runs.
- Use absolute script paths when requesting reusable experiment launch approvals.
- Use the standard experiment launch shape `python -u <script.py> <script args including unique output_dir> > <output_dir>/train.log 2>&1` so stdout and stderr are preserved under the unique output directory.
- Avoid wrapping experiment launches in `bash -lc`, environment-variable prefixes, command substitution, loops, pipes, or multi-command strings unless there is a specific reason. These make approval matching harder and can hide the actual experiment command.
- If CUDA, filesystem, dependency, or network access fails in a way that looks sandbox-related, rerun the same command with escalation and a narrow prefix rule instead of inventing a workaround.
- Do not ask for broad prefixes like `["python"]` or `["bash", "-lc"]` for routine tuning; they are too permissive for a long autonomous loop.

## Recommended Pre-Approval Pattern

Useful approvals are narrow command prefixes, not broad shells. Project-specific adapters may list exact prefixes for known experiment suites.

Recommended:
- `["nvidia-smi"]`
- the skill helper script, such as `["python", "~/.codex/skills/my-auto-experiment-tuning/scripts/aet.py"]` for Codex or the equivalent runtime install path
- process checks scoped to experiment scripts, such as `["pgrep", "-af", "experiments/exp_"]`
- one prefix per experiment script that may be tuned, such as `["python", "-u", "/path/to/project/experiments/exp_method.py"]`
- if the project venv interpreter is used directly, mirror the same narrow shape with that interpreter path

Avoid broad approvals such as `["python"]`, `["bash"]`, or `["bash", "-lc"]`; those are too permissive and can hide unsafe commands inside a generic shell.

## Working Inside the Sandbox

Most tuning should not need elevated filesystem permission when the project root is writable. If GPU execution, CUDA access, or a long experiment launch is blocked by sandbox policy, rerun the same command with escalation and a prefix rule for that exact experiment script.
