#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


RESULT_COLUMNS = [
    "run_id",
    "run_name",
    "status",
    "goal",
    "primary_metric",
    "metric_name",
    "gpu_id",
    "output_dir",
    "log_path",
    "params_json",
    "command",
    "metrics_json",
    "start_time",
    "end_time",
    "notes",
]


CAPACITY_BY_KIND = {
    "default": 1,
    "light": 3,
    "heavy": 2,
}

HARD_CAP_PER_GPU = 3

TERMINAL_STATUSES = {"finished", "failed", "inconclusive", "superseded"}

# Conservative per-dimension defaults (workflow.md section 6). Used when a session
# has no stored gpu_policy and no explicit flag is passed.
DEFAULT_POLICY = {
    "gpu_ids": None,
    "max_per_gpu": 1,
    "max_util": 95,
    "max_memory_used_mb": None,
    "min_free_memory_mb": None,
    "process_pattern": "python",
}

LOOP_STATE_VERSION = 1


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def minutes_since(iso: str | None) -> int:
    if not iso:
        return 0
    try:
        then = datetime.fromisoformat(iso)
    except ValueError:
        return 0
    delta = datetime.now().astimezone() - then
    return max(0, int(delta.total_seconds() // 60))


# ---------------------------------------------------------------------------
# Three-zone output: OK (what was durably written) / STATE (pre-computed facts
# the next decision needs) / YOU (doc-update obligations + next action, only
# what is actually due now). Every command speaks to the calling agent, not a
# human reader.
# ---------------------------------------------------------------------------
def emit(ok: list[str] | None = None, state: list[str] | None = None, you: list[str] | None = None) -> None:
    def block(label: str, lines: list[str] | None) -> None:
        if not lines:
            return
        for i, line in enumerate(lines):
            print((f"{label:<6}" if i == 0 else " " * 6) + line)

    block("OK", ok)
    block("STATE", state)
    block("YOU", you)


def load_json_arg(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    path = Path(value)
    try:
        exists = path.exists()
    except OSError:
        exists = False
    if exists:
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def read_asset(name: str) -> str:
    path = skill_dir() / "assets" / name
    if not path.exists():
        raise SystemExit(f"Missing skill asset: {path}")
    return path.read_text(encoding="utf-8")


def render_plan_template(objective: str, goal: str) -> str:
    return (
        read_asset("plan-template.md")
        .replace("{{ objective }}", objective)
        .replace("{{ goal }}", goal)
    )


def render_observations_template(created_at: str, objective: str) -> str:
    return (
        read_asset("observations-template.md")
        .replace("{{ created_at }}", created_at)
        .replace("{{ objective }}", objective)
    )


def render_run_summary_template(command: str, params: dict[str, Any], metrics: dict[str, Any] | None = None) -> str:
    return (
        read_asset("run-summary-template.md")
        .replace("{{ command }}", command)
        .replace("{{ params_json }}", json.dumps(params, ensure_ascii=False, indent=2, sort_keys=True))
        .replace("{{ metrics_json }}", json.dumps(metrics or {}, ensure_ascii=False, indent=2, sort_keys=True))
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in RESULT_COLUMNS})


def append_run_observation(path: Path, run_id: str, status: str, notes: str) -> None:
    entry = f"\n## Run {run_id} - {status}\n\n{notes}\n\n"
    if not path.exists():
        path.write_text("# Observations\n\n## Run Notes\n" + entry, encoding="utf-8")
        return

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    run_notes_index = next((i for i, line in enumerate(lines) if line.strip() == "## Run Notes"), None)
    if run_notes_index is None:
        path.write_text(text.rstrip() + "\n\n## Run Notes\n" + entry, encoding="utf-8")
        return

    insert_at = len(lines)
    for i in range(run_notes_index + 1, len(lines)):
        if lines[i].startswith("## "):
            insert_at = i
            break
    lines[insert_at:insert_at] = [entry]
    path.write_text("".join(lines), encoding="utf-8")


def latest_session(project_root: Path) -> Path | None:
    root = project_root / "aet"
    if not root.exists():
        return None
    candidates = [p for p in root.glob("*/*") if p.is_dir() and (p / "meta.json").exists()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def require_session(args: argparse.Namespace) -> Path:
    if getattr(args, "session", None):
        session = Path(args.session).expanduser().resolve()
    else:
        root = Path(args.project_root).expanduser().resolve()
        session = latest_session(root)
        if session is None:
            raise SystemExit(f"No session found under {root / 'aet'}")
    if not (session / "meta.json").exists():
        raise SystemExit(f"Not an AET session: {session}")
    return session


def load_meta(session: Path) -> dict[str, Any]:
    return json.loads((session / "meta.json").read_text(encoding="utf-8"))


def save_meta(session: Path, meta: dict[str, Any]) -> None:
    atomic_write_json(session / "meta.json", meta)


def resolve_runtime(args: argparse.Namespace, meta: dict[str, Any]) -> str:
    return getattr(args, "runtime", None) or meta.get("runtime") or "claude"


# ---------------------------------------------------------------------------
# loop_state.json: script-owned Strategist state machine (pending run set,
# agent id, open call, exhaustion-confirmation handshake).
# ---------------------------------------------------------------------------
def default_loop_state() -> dict[str, Any]:
    return {
        "schema_version": LOOP_STATE_VERSION,
        "strategist_agent_id": None,
        "pending_exhaustion_confirmation": False,
        "pending_runs": {},
        "active_strategist_call": None,
        "strategist_call_count": 0,
        "last_strategist_at": None,
        "agent_history": [],
    }


def terminal_version(status: str, primary_metric: str, notes: str) -> str:
    raw = f"{status}|{primary_metric}|{notes}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def load_loop_state(session: Path) -> dict[str, Any]:
    path = session / "loop_state.json"
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        for key, value in default_loop_state().items():
            state.setdefault(key, value)
        return state
    # Conservative rebuild after loss: every terminal run becomes pending. This
    # may re-trigger one redundant observation pass but never drops evidence.
    state = default_loop_state()
    for row in read_rows(session / "results.csv"):
        if row.get("status") in TERMINAL_STATUSES:
            rid = row.get("run_id", "")
            state["pending_runs"][rid] = {
                "version": terminal_version(row.get("status", ""), row.get("primary_metric", ""), row.get("notes", "")),
                "added_at": now_iso(),
            }
    return state


def save_loop_state(session: Path, state: dict[str, Any]) -> None:
    atomic_write_json(session / "loop_state.json", state)


def history_append(state: dict[str, Any], agent_id: str, reason: str) -> None:
    state["agent_history"].append({"id": agent_id, "set_at": now_iso(), "reason": reason})


def maybe_update_primary_id(state: dict[str, Any], agent_id: str | None, reason: str) -> None:
    if agent_id and state.get("strategist_agent_id") != agent_id:
        state["strategist_agent_id"] = agent_id
        history_append(state, agent_id, reason)


def pending_run_ids(state: dict[str, Any]) -> list[str]:
    return sorted(state["pending_runs"].keys(), key=lambda x: int(x) if x.isdigit() else x)


def count_ready_rows(session: Path) -> int | None:
    """Count data rows under the '### Ready Queue' table in plan.md. None if plan.md is unreadable or the section is missing."""
    try:
        lines = (session / "plan.md").read_text().splitlines()
    except Exception:
        return None
    start = None
    for i, line in enumerate(lines):
        ls = line.strip().lower()
        if ls.startswith("#") and "ready queue" in ls:  # tolerate heading-level edits
            start = i + 1
            break
    if start is None:
        return None
    count = 0
    seen_sep = False
    for line in lines[start:]:
        s = line.strip()
        if s.startswith("#") or s.startswith("<!--"):
            break
        if not s.startswith("|"):
            continue
        body = s.strip("|").replace("|", "").strip()
        if body and set(body) <= set("-: "):
            seen_sep = True
            continue
        if not seen_sep:
            continue  # header row, before the separator
        count += 1
    return count


def resolve_ready_count(args: argparse.Namespace, session: Path) -> tuple[int, str | None]:
    """The script owns the Ready Queue count by reading plan.md; --ready-count is only an optional override/fallback.
    Returns (count, note) where note flags a stale supplied value or an unreadable plan."""
    computed = count_ready_rows(session)
    supplied = getattr(args, "ready_count", None)
    if computed is None:
        if supplied is None:
            return 0, "WARNING: could not read plan.md '### Ready Queue'; assuming ready=0. Restore the plan template or pass --ready-count."
        return supplied, None
    if supplied is not None and supplied != computed:
        return computed, f"NOTE: counted {computed} Ready Queue row(s) in plan.md; the --ready-count {supplied} you passed was stale and is ignored."
    return computed, None


def best_finished(session: Path, goal: str) -> tuple[str, str, float] | None:
    scored = []
    for row in read_rows(session / "results.csv"):
        if row.get("status") != "finished":
            continue
        value = safe_float(row.get("primary_metric", ""))
        if value is not None:
            scored.append((row, value))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[1], reverse=(goal != "min"))
    best, value = scored[0]
    return best.get("run_id", ""), best.get("metric_name", ""), value


def is_new_best(session: Path, run_id: str, status: str, goal: str) -> bool:
    if status != "finished":
        return False
    best = best_finished(session, goal)
    return best is not None and best[0] == run_id


def specific_process_pattern(session: Path) -> str | None:
    """The stored process_pattern if it specifically identifies THIS session's experiments; None for the
    generic 'python' default, which is too broad to judge real liveness from."""
    pattern = (load_meta(session).get("gpu_policy") or {}).get("process_pattern")
    if not pattern or pattern == "python":
        return None
    return pattern


def is_quiescent(session: Path, ready_count: int) -> bool:
    if ready_count != 0:
        return False
    rows = read_rows(session / "results.csv")
    if any(row.get("status") == "created" for row in rows):
        return False
    pattern = specific_process_pattern(session)
    if pattern:
        # A specific process_pattern lets us judge "running" from real processes, immune to
        # ledger 'running' rows whose experiments already finished but were never recorded terminal.
        return count_live_processes(pattern) == 0
    # No specific pattern (or the generic "python" default): fall back to the ledger 'running' status.
    return not any(row.get("status") == "running" for row in rows)


# ---------------------------------------------------------------------------
# GPU policy + slot computation. gpu-slots/loop-state/strategist-begin all read
# the same stored meta.gpu_policy so capacity is computed under one policy.
# ---------------------------------------------------------------------------
def parse_gpu_ids(value: Any) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [int(v) for v in value]
    return [int(v.strip()) for v in str(value).split(",") if v.strip()]


def policy_from_flags(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if getattr(args, "gpu_ids", None) is not None:
        out["gpu_ids"] = parse_gpu_ids(args.gpu_ids)
    if getattr(args, "max_per_gpu", None) is not None:
        out["max_per_gpu"] = args.max_per_gpu
    if getattr(args, "capacity", None) is not None:
        out["max_per_gpu"] = args.capacity
    if getattr(args, "max_util", None) is not None:
        out["max_util"] = args.max_util
    if getattr(args, "max_memory_used_mb", None) is not None:
        out["max_memory_used_mb"] = args.max_memory_used_mb
    if getattr(args, "min_free_memory_mb", None) is not None:
        out["min_free_memory_mb"] = args.min_free_memory_mb
    if getattr(args, "process_pattern", None) is not None:
        out["process_pattern"] = args.process_pattern
    return out


def resolve_policy(args: argparse.Namespace, session: Path | None) -> dict[str, Any]:
    policy = dict(DEFAULT_POLICY)
    if session is not None:
        stored = load_meta(session).get("gpu_policy") or {}
        policy.update({k: v for k, v in stored.items() if v is not None or k == "gpu_ids"})
    if getattr(args, "kind", None):
        policy["max_per_gpu"] = CAPACITY_BY_KIND.get(args.kind, policy["max_per_gpu"])
    policy.update(policy_from_flags(args))
    policy["gpu_ids"] = parse_gpu_ids(policy.get("gpu_ids"))
    return policy


def query_slots(policy: dict[str, Any], allow_over_cap: bool = False) -> list[dict[str, Any]]:
    capacity = policy.get("max_per_gpu") or 1
    if capacity > HARD_CAP_PER_GPU and not allow_over_cap:
        capacity = HARD_CAP_PER_GPU
    gpu_info = nvidia_rows()
    if policy.get("gpu_ids"):
        allowed = {str(g) for g in policy["gpu_ids"]}
        gpu_info = [row for row in gpu_info if row["index"] in allowed]
    counts = process_gpu_counts(policy.get("process_pattern") or "python")
    max_util_threshold = policy.get("max_util", 95)
    max_memory_used_mb = policy.get("max_memory_used_mb")
    min_free_memory_mb = policy.get("min_free_memory_mb")
    result = []
    for row in gpu_info:
        gpu = row["index"]
        running = counts.get(gpu, 0)
        util = int(float(row["utilization"]))
        memory_used = int(float(row["memory_used"]))
        memory_total = int(float(row["memory_total"]))
        memory_free = max(0, memory_total - memory_used)
        free_slots = max(0, capacity - running)
        if util >= max_util_threshold:
            free_slots = 0
        if max_memory_used_mb is not None and memory_used >= max_memory_used_mb:
            free_slots = 0
        if min_free_memory_mb is not None and memory_free < min_free_memory_mb:
            free_slots = 0
        result.append(
            {
                "gpu": int(gpu),
                "utilization": util,
                "memory_used_mb": memory_used,
                "memory_total_mb": memory_total,
                "memory_free_mb": memory_free,
                "running_count": running,
                "capacity": capacity,
                "free_slots": free_slots,
            }
        )
    return result


def slots_summary(slots: list[dict[str, Any]]) -> tuple[int, int]:
    free = sum(item["free_slots"] for item in slots)
    total = sum(item["capacity"] for item in slots)
    return free, total


# ---------------------------------------------------------------------------
# Strategist routing. The branch is fully determined by the stored flags; the
# script renders it (including the runtime-specific verb), it does not decide
# whether to stop or what candidates to plan.
# ---------------------------------------------------------------------------
def compute_route(state: dict[str, Any], runtime: str, ready_count: int) -> dict[str, Any]:
    if state.get("pending_exhaustion_confirmation"):
        role, invocation, target = "confirmer", "fresh", None
    elif state.get("strategist_agent_id"):
        role, invocation, target = "primary", "resume", state["strategist_agent_id"]
    else:
        role, invocation, target = "primary", "fresh", None
    verb = "SendMessage" if runtime == "claude" else "send_input"
    if runtime == "claude":
        mode = "background" if invocation == "resume" else ("blocking" if ready_count == 0 else "background")
    else:
        mode = "blocking"
    return {"role": role, "invocation": invocation, "target_agent_id": target, "verb": verb, "mode": mode}


def verb_instruction(runtime: str, route: dict[str, Any]) -> str:
    invocation = route["invocation"]
    target = route["target_agent_id"]
    mode = route["mode"]
    if runtime == "codex":
        if invocation == "resume":
            return f"Call `send_input(target={target}, message=<payload>)`, then `wait_agent`."
        return "Call `spawn_agent(message=<payload>, fork_context=true)` with the custom agent `experiment-strategist`."
    if invocation == "resume":
        return (
            f"Call the tool literally named `SendMessage` (NOT the `Agent` tool) — "
            f"`SendMessage(to={target}, message=<payload>)` [background]. This resumes the SAME strategist "
            f"with its accumulated context. `Agent`-spawning a strategist here is the WRONG action: it cold-starts "
            f"a new one and discards that context. Call `SendMessage` directly — it is a real, always-available tool, "
            f"not something to pre-clear: its absence from `ToolSearch` or from your visible toolset does NOT mean it "
            f"is unavailable; if its schema is not loaded, load it, then call it. The ONLY signal that resume failed "
            f"is the call itself returning `success:false` (e.g. 'no transcript to resume'). Knowing the agent is from "
            f"a dead prior conversation is NOT that signal — make the call and let it fail. Only on `success:false` "
            f"fall back to `Agent(subagent_type=\"experiment-strategist\", prompt=<payload>, run_in_background=True)` "
            f"and pass `--resume-failed` to strategist-return (which clears the dead id even with no replacement id)."
        )
    bg = "run_in_background=True" if mode == "background" else "run_in_background=False"
    return f'Call `Agent(subagent_type="experiment-strategist", prompt=<payload>, {bg})`.'


def build_payload(session: Path, snapshot: dict[str, str]) -> list[str]:
    rows = {row["run_id"]: row for row in read_rows(session / "results.csv")}
    items = []
    for rid in sorted(snapshot, key=lambda x: int(x) if x.isdigit() else x):
        row = rows.get(rid, {})
        items.append(f"{rid}:{row.get('status', '?')}/{row.get('metric_name', '')}={row.get('primary_metric', '')}")
    if items:
        runs_str = ", ".join(items)
    else:
        runs_str = "(empty — session start / first call; Strategist skips observations and plans from plan.md)"
    return [
        f"runs_since_last_strategist: [{runs_str}]",
        "plus session_path, project_root, experiment scripts, algorithm_context, current_free_slots, total_capacity,",
        "current_best — fill from the standard template in references/subagents.md (do not summarize results).",
    ]


def render_branch(runtime: str, route: dict[str, Any]) -> str:
    if route["role"] == "confirmer":
        return f"fresh CONFIRMER spawn (independent context; ignore strategist_agent_id; do NOT prime it with the prior exhaustion conclusion), {route['mode']}"
    if route["invocation"] == "resume":
        return f"resume Primary {route['target_agent_id']} via the `{route['verb']}` tool — resume, not a fresh spawn ({route['mode']})"
    return f"fresh spawn ({route['mode']})"


def compute_next(state: dict[str, Any], runtime: str, ready: int, free_slots: int, total_capacity: int, free_gpu_ids: list[str] | None = None) -> list[str]:
    active = state.get("active_strategist_call")
    if active:
        age = minutes_since(active.get("started_at"))
        if active.get("invocation") == "resume":
            target = f"this call's subagent {state.get('strategist_agent_id')}"
        else:
            target = "the subagent you spawned for this call (use the agent id from your spawn result, not any stored id)"
        return [
            f"Strategist call {active['call_id']} is OPEN ({active['role']}/{active['invocation']}, age {age}m). This means YOU still owe an `aet.py strategist-return` for it — it does NOT mean the subagent is still running. This script cannot see the subagent; only you can. Do NOT open another call.",
            f"Determine the subagent's real state yourself (its completion notification / the agent panel / its task-output file). If it already returned, close the call now: `aet.py strategist-return --call-id {active['call_id']} --candidates-count K [--agent-id A]`.",
            f"If you cannot find its output, re-request it by resuming {target} (Claude Code: the `SendMessage` tool; Codex: `send_input`). Do NOT abort just because a result is momentarily lost from your context.",
            f"Use `aet.py strategist-abort --call-id {active['call_id']} --reason unreachable` ONLY if that resume itself returns `success:false` (the subagent is truly gone). Abort discards this call AND clears the agent id, losing the resume chain and the strategist's already-produced work.",
            "Meanwhile keep recording completions; `aet.py record` auto-adds them to pending.",
        ]
    actions: list[str] = []
    launch_n = min(free_slots, ready)
    projected_ready = ready - launch_n
    if launch_n > 0:
        targets = (free_gpu_ids or [])[:launch_n]
        actions.append(
            f"LAUNCH {launch_n} top Ready-Queue row(s) onto GPU id(s) {targets} — one job per id, these are the only free GPUs, use no other. "
            f"Per row: `aet.py create-run --gpu-id <id>` -> launch -> `aet.py record --status running` -> move to Running."
        )
    if projected_ready < total_capacity:
        route = compute_route(state, runtime, projected_ready)
        actions.append(
            f"run `aet.py strategist-begin`  ->  {render_branch(runtime, route)}"
        )
    if not actions:
        actions.append("All slots full and Ready Queue >= total_capacity. Wait for the next completion; nothing to launch or plan now.")
    return actions


def next_run_id(session: Path) -> int:
    existing = []
    for path in (session / "runs").iterdir():
        if path.is_dir() and path.name.isdigit():
            existing.append(int(path.name))
    for row in read_rows(session / "results.csv"):
        try:
            existing.append(int(row["run_id"]))
        except (KeyError, ValueError):
            pass
    return 0 if not existing else max(existing) + 1


def safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def command_init(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).expanduser().resolve()
    timestamp = datetime.now().astimezone()
    created_at = timestamp.isoformat(timespec="seconds")
    session = project_root / "aet" / timestamp.strftime("%Y-%m-%d") / timestamp.strftime("%H-%M-%S")
    session.mkdir(parents=True, exist_ok=False)
    (session / "runs").mkdir()

    gpu_policy = dict(DEFAULT_POLICY)
    gpu_policy.update(policy_from_flags(args))
    gpu_policy["gpu_ids"] = parse_gpu_ids(gpu_policy.get("gpu_ids"))

    meta = {
        "project_root": str(project_root),
        "session_dir": str(session),
        "name": args.name,
        "objective": args.objective,
        "goal": args.goal,
        "runtime": args.runtime,
        "gpu_policy": gpu_policy,
        "created_at": created_at,
        "status": "running",
    }
    dump_json(session / "meta.json", meta)
    write_rows(session / "results.csv", [])
    (session / "queue.jsonl").write_text("", encoding="utf-8")
    (session / "observations.md").write_text(
        render_observations_template(created_at, args.objective),
        encoding="utf-8",
    )
    (session / "plan.md").write_text(render_plan_template(args.objective, args.goal), encoding="utf-8")
    save_loop_state(session, default_loop_state())

    policy_set = bool(policy_from_flags(args))
    you = []
    if args.runtime == "claude":
        you.append("1) start `/loop` now (before the first launch); see `references/claude-code-adapter.md`.")
    if not policy_set:
        you.append(("2)" if you else "1)") + " set GPU policy: run `aet.py set-policy --gpu-ids ... --max-per-gpu ...` (else conservative 1/gpu default).")
    you.append(f"{len(you) + 1}) fill `plan.md`: metric, baseline, target, constraints, hypotheses, coupled params.")
    you.append(f"{len(you) + 1}) Ready Queue < total_capacity -> run `aet.py strategist-begin` (do NOT hand-design the initial candidate set).")
    emit(
        ok=[f"session: {session}", "files: meta.json plan.md observations.md results.csv queue.jsonl loop_state.json runs/"],
        state=[f"objective: {args.objective} ({args.goal})  runtime: {args.runtime}  gpu_policy: {'set' if policy_set else 'default (1/gpu)'}"],
        you=you,
    )


def command_set_policy(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    policy = dict(DEFAULT_POLICY)
    policy.update(meta.get("gpu_policy") or {})
    policy.update(policy_from_flags(args))
    policy["gpu_ids"] = parse_gpu_ids(policy.get("gpu_ids"))
    meta["gpu_policy"] = policy
    save_meta(session, meta)
    emit(
        ok=[f"gpu_policy updated: {json.dumps(policy, ensure_ascii=False, sort_keys=True)}"],
        you=["`aet.py gpu-slots` / `loop-state` / `strategist-begin` now compute capacity from this policy. No `plan.md` edit needed."],
    )


def command_create_run(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    run_id = next_run_id(session)
    run_name = args.name or f"run-{run_id:04d}"
    run_dir = session / "runs" / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "output").mkdir()

    params = load_json_arg(args.params)
    metrics: dict[str, Any] = {}
    dump_json(run_dir / "params.json", params)
    dump_json(run_dir / "metrics.json", metrics)
    (run_dir / "summary.md").write_text(
        render_run_summary_template(args.command or "", params, metrics),
        encoding="utf-8",
    )
    if args.command:
        (run_dir / "command.sh").write_text(args.command + "\n", encoding="utf-8")

    output_dir = args.output_dir or str(run_dir / "output")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    log_path = args.log_path or str(Path(output_dir) / "train.log")
    rows = read_rows(session / "results.csv")
    row = {
        "run_id": str(run_id),
        "run_name": run_name,
        "status": "created",
        "goal": meta.get("goal", ""),
        "primary_metric": "",
        "metric_name": "",
        "gpu_id": args.gpu_id or "",
        "output_dir": output_dir,
        "log_path": log_path,
        "params_json": json.dumps(params, ensure_ascii=False, sort_keys=True),
        "command": args.command or "",
        "metrics_json": "{}",
        "start_time": "",
        "end_time": "",
        "notes": args.notes or "",
    }
    rows = [r for r in rows if r.get("run_id") != str(run_id)]
    rows.append(row)
    write_rows(session / "results.csv", rows)
    with (session / "queue.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    emit(
        ok=[
            f"run {run_id} registered",
            f"run_dir: {run_dir}",
            f"run_id: {run_id}",
            f"output_dir: {output_dir}   (created)",
            f"log: {log_path}",
        ],
        state=[f"status=created  gpu={args.gpu_id or '(unset)'}"],
        you=[
            f"1) launch: `python -u SCRIPT --gpu_id {args.gpu_id or 'G'} --output_dir {output_dir} > {log_path} 2>&1`",
            f"2) after it starts: run `aet.py record --run-id {run_id} --status running`",
            "3) move this row Ready Queue -> Running in `plan.md`",
        ],
    )


def command_record(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    run_id = str(args.run_id)
    rows = read_rows(session / "results.csv")
    matches = [row for row in rows if row.get("run_id") == run_id]
    if matches:
        row = matches[0]
    else:
        row = {key: "" for key in RESULT_COLUMNS}
        row["run_id"] = run_id
        row["run_name"] = args.name or f"run-{int(args.run_id):04d}"
        rows.append(row)

    metrics = load_json_arg(args.metrics)
    if args.primary_metric is not None and args.metric_name:
        metrics[args.metric_name] = args.primary_metric

    row.update(
        {
            "status": args.status,
            "primary_metric": "" if args.primary_metric is None else str(args.primary_metric),
            "metric_name": args.metric_name or row.get("metric_name", ""),
            "gpu_id": args.gpu_id or row.get("gpu_id", ""),
            "output_dir": args.output_dir or row.get("output_dir", ""),
            "log_path": args.log_path or row.get("log_path", ""),
            "metrics_json": json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            "start_time": now_iso() if args.status == "running" and not row.get("start_time") else row.get("start_time", ""),
            "end_time": now_iso() if args.status in TERMINAL_STATUSES else row.get("end_time", ""),
            "notes": args.notes or row.get("notes", ""),
        }
    )
    run_dir = session / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    dump_json(run_dir / "metrics.json", metrics)
    summary = render_run_summary_template(row.get("command", ""), load_json_arg(row.get("params_json")), metrics)
    summary += f"\n## Status\n\n{row['status']}\n\n## Notes\n\n{row['notes']}\n"
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")
    write_rows(session / "results.csv", rows)
    if args.notes:
        append_run_observation(session / "observations.md", run_id, args.status, args.notes)

    if args.status == "running":
        emit(
            ok=[f"run {run_id} -> running   start_time recorded"],
            you=[
                "1) ensure this run's `plan.md` Running row (gpu / output / log / expected signal) is current",
                "2) once you have executed everything the last `aet.py loop-state` routed (free slots filled, any Strategist call handled), this cycle is complete: wait for the next completion, then `aet.py loop-state` again. Otherwise finish the remaining routed launches first.",
            ],
        )
        return

    if args.status not in TERMINAL_STATUSES:
        emit(ok=[f"run {run_id} -> {args.status}   results.csv updated"])
        return

    # Terminal: update pending set (version-guarded) and detect a new best.
    state = load_loop_state(session)
    version = terminal_version(row["status"], row["primary_metric"], row["notes"])
    existing = state["pending_runs"].get(run_id)
    if existing is None or existing.get("version") != version:
        state["pending_runs"][run_id] = {"version": version, "added_at": now_iso()}
        save_loop_state(session, state)
    new_best = is_new_best(session, run_id, args.status, meta.get("goal", "max"))

    metric_str = ""
    if row["primary_metric"]:
        metric_str = f"   {row.get('metric_name', 'metric')}={row['primary_metric']}"
    state_lines = [f"pending_run_ids={pending_run_ids(state)}"]
    best = best_finished(session, meta.get("goal", "max"))
    if best:
        tag = "  (NEW BEST)" if new_best else ""
        state_lines.append(f"best: run {best[0]} {best[1]}={best[2]}{tag}")
    you = [
        "1) NEXT COMMAND (required): run `aet.py loop-state` — it returns what to launch/plan next and is the loop's control-flow router. Run it before any `aet.py create-run`, launch, status recap, or candidate planning.",
        f"2) bookkeeping: move run {run_id} row Running -> Completed/Recorded in `plan.md`",
        f"3) trust caveat? append it to `runs/{run_id}/summary.md` (after this record)",
    ]
    if new_best:
        you.append(f"{len(you) + 1}) NEW BEST: if the project tracks a benchmark/current-best table, update it.")
    active = state.get("active_strategist_call")
    if active:
        you.insert(
            0,
            f"OPEN DEBT: Strategist call {active['call_id']} is still open (age {minutes_since(active.get('started_at'))}m) — "
            f"you owe `aet.py strategist-return --call-id {active['call_id']} --candidates-count K` once that subagent "
            f"returns (resume it via the `SendMessage` tool / Codex `send_input` if you lost its output). Do NOT open another call.",
        )
    emit(
        ok=[f"run {run_id} -> {args.status}{metric_str}", "results.csv + runs/<id>/summary.md updated; pending += this run"],
        state=state_lines,
        you=you,
    )


def command_parse_log(args: argparse.Namespace) -> None:
    path = Path(args.log).expanduser().resolve()
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = args.pattern or []
    if not patterns:
        patterns = [
            r"(?P<name>PSNR|psnr|best PSNR|Best PSNR)[^0-9+-]*(?P<value>[+-]?\d+(?:\.\d+)?)",
            r"(?P<name>SSIM|ssim|best SSIM|Best SSIM)[^0-9+-]*(?P<value>[+-]?\d+(?:\.\d+)?)",
        ]
    found: dict[str, float] = {}
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if "name" in match.groupdict() and "value" in match.groupdict():
                name = match.group("name").strip().replace(" ", "_")
                value = parse_float(match.group("value"))
            else:
                name = f"metric_{len(found) + 1}"
                value = parse_float(match.group(match.lastindex or 1))
            if value is not None:
                found[name] = value
    print(json.dumps(found, ensure_ascii=False, indent=2, sort_keys=True))


def command_unique_dir(args: argparse.Namespace) -> None:
    base = Path(args.path).expanduser()
    candidate = base
    index = 1
    while candidate.exists():
        candidate = Path(f"{base}_{index:02d}")
        index += 1
    if args.mkdir:
        candidate.mkdir(parents=True, exist_ok=False)
    print(candidate.resolve())


def nvidia_rows() -> list[dict[str, str]]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            rows.append(
                {
                    "index": parts[0],
                    "utilization": parts[1],
                    "memory_used": parts[2],
                    "memory_total": parts[3],
                }
            )
    return rows


_SHELL_BASENAMES = {"bash", "sh", "dash", "zsh", "ksh", "fish"}


def is_wrapper_line(line: str) -> bool:
    """A background launch runs the real command as `<shell> -c '<command>'`; that wrapper line
    carries the same pattern and --gpu flag as its interpreter child, so a naive scan counts one
    launched job twice. Identify the wrapper (a shell invoked with -c) so callers count the
    interpreter child only."""
    tokens = line.split()
    if not tokens:
        return False
    if os.path.basename(tokens[0]) not in _SHELL_BASENAMES:
        return False
    return "-c" in tokens[1:]


def matching_proc_lines(pattern: str) -> list[str]:
    """Live process command lines matching pattern, with shell `-c` wrappers removed so each
    launched job appears once."""
    try:
        out = subprocess.check_output(["ps", "ax", "-o", "args="], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    matcher = re.compile(pattern)
    return [line for line in out.splitlines() if matcher.search(line) and not is_wrapper_line(line)]


def process_gpu_counts(pattern: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in matching_proc_lines(pattern):
        match = re.search(r"--gpu(?:_id)?(?:=|\s+)(\d+)", line)
        if match:
            gpu = match.group(1)
            counts[gpu] = counts.get(gpu, 0) + 1
    return counts


def count_live_processes(pattern: str) -> int:
    """Real liveness: count processes whose command line matches pattern, independent of the ledger."""
    return len(matching_proc_lines(pattern))


def reconcile_hint(session: Path) -> str | None:
    """When the ledger holds more 'running' rows than there are live experiment processes, some runs
    finished without a terminal record. Return an actionable reminder (or None). Needs a specific process_pattern."""
    pattern = specific_process_pattern(session)
    if not pattern:
        return None
    ledger_running = sum(1 for r in read_rows(session / "results.csv") if r.get("status") == "running")
    if not ledger_running:
        return None
    live = count_live_processes(pattern)
    if ledger_running <= live:
        return None
    return (
        f"RECONCILE: ledger shows {ledger_running} 'running' but only {live} matching process(es) are alive — "
        f"{ledger_running - live} run(s) finished without a terminal record. Record each (`aet.py record --run-id <id> "
        f"--status finished|failed|inconclusive` after parsing its metrics) and move it from Running to Completed in `plan.md`."
    )


def stale_created_hint(session: Path) -> str | None:
    """Runs stuck in 'created' (registered but never launched) block quiescence and the exhaustion
    handshake. Return an actionable hint listing the run ids, or None."""
    created_ids = [row.get("run_id", "") for row in read_rows(session / "results.csv") if row.get("status") == "created"]
    if not created_ids:
        return None
    ids_str = ", ".join(created_ids)
    return (
        f"STALE CREATED: run(s) {ids_str} have status='created' (registered via `create-run` but never launched), "
        f"blocking quiescence. For each: determine whether it should still be launched "
        f"(`aet.py record --run-id <id> --status running` after launch) or was abandoned "
        f"(`aet.py record --run-id <id> --status superseded --notes 'never launched'`)."
    )


def quiescence_blockers(session: Path, ready_count: int) -> list[str]:
    """Mirrors is_quiescent checks; returns one actionable message per failing condition.
    Used by strategist-return to explain why the exhaustion handshake could not proceed."""
    blockers = []
    if ready_count > 0:
        blockers.append(
            f"READY QUEUE: {ready_count} row(s) remain — launch or remove them."
        )
    rows = read_rows(session / "results.csv")
    created_ids = [r.get("run_id", "") for r in rows if r.get("status") == "created"]
    if created_ids:
        blockers.append(
            f"STALE CREATED: run(s) {', '.join(created_ids)} have status='created' (registered but never launched). "
            f"For each: launch and `aet.py record --status running`, or "
            f"`aet.py record --run-id <id> --status superseded --notes 'never launched'`."
        )
    pattern = specific_process_pattern(session)
    if pattern:
        live = count_live_processes(pattern)
        if live > 0:
            blockers.append(
                f"ACTIVE: {live} experiment process(es) matching '{pattern}' still running. "
                f"Wait for completion, then record terminal status."
            )
        ledger_running = sum(1 for r in rows if r.get("status") == "running")
        if ledger_running > live:
            stale = ledger_running - live
            blockers.append(
                f"RECONCILE: ledger shows {ledger_running} 'running' but only {live} live process(es) — "
                f"{stale} run(s) finished without terminal record. Record each with "
                f"`aet.py record --run-id <id> --status finished|failed|inconclusive`."
            )
    else:
        running_ids = [r.get("run_id", "") for r in rows if r.get("status") == "running"]
        if running_ids:
            blockers.append(
                f"RUNNING: run(s) {', '.join(running_ids)} in 'running' status (no specific process_pattern). "
                f"Verify if still active; if finished, record terminal status."
            )
    return blockers


def command_gpu_slots(args: argparse.Namespace) -> None:
    session = None
    if getattr(args, "session", None) or getattr(args, "project_root", None):
        try:
            session = require_session(args)
        except SystemExit:
            session = None
    policy = resolve_policy(args, session)
    # A stored session policy is the user's recorded authorization, so honor it
    # above the hard cap; cap only the standalone/transient path unless --allow-over-cap.
    slots = query_slots(policy, allow_over_cap=args.allow_over_cap or session is not None)
    free, total = slots_summary(slots)
    if args.json:
        print(json.dumps(slots, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for item in slots:
        print(
            f"gpu {item['gpu']}: util={item['utilization']}%, "
            f"mem={item['memory_used_mb']}/{item['memory_total_mb']} MiB "
            f"(free={item['memory_free_mb']} MiB), running={item['running_count']}, "
            f"capacity={item['capacity']}, free={item['free_slots']}"
        )
    print(f"TOTAL  free_slots={free}  total_capacity={total}")


def command_loop_state(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    runtime = resolve_runtime(args, meta)
    state = load_loop_state(session)
    goal = meta.get("goal", "max")
    policy = resolve_policy(args, session)
    slots = query_slots(policy, allow_over_cap=True)
    free_slots, total_capacity = slots_summary(slots)
    free_gpu_ids = [str(s["gpu"]) for s in slots for _ in range(s["free_slots"])]
    ready, ready_note = resolve_ready_count(args, session)

    best = best_finished(session, goal)
    best_str = f"run {best[0]} {best[1]}={best[2]}" if best else "(none)"
    active = state.get("active_strategist_call")
    active_str = f"{active['call_id']} ({active['role']}/{active['invocation']}, age {minutes_since(active.get('started_at'))}m)" if active else "none"
    gap = total_capacity - ready
    state_lines = [
        f"objective: {meta.get('objective', '')}   best: {best_str}",
        f"free_slots={free_slots}  total_capacity={total_capacity}  ready={ready}  gap={gap if gap > 0 else 0}",
        f"pending_run_ids={pending_run_ids(state)}",
        f"strategist_agent_id={state.get('strategist_agent_id')}  active_call={active_str}  pending_exhaustion={state.get('pending_exhaustion_confirmation')}",
    ]
    ok_lines = [f"session: {session}  runtime: {runtime}"]
    if ready_note:
        ok_lines.append(ready_note)
    if getattr(args, "gpu_ids", None) is not None or getattr(args, "max_per_gpu", None) is not None:
        ok_lines.append(
            "POLICY: you passed transient GPU flags to loop-state; strategist-begin and gpu-slots read the stored "
            "policy in meta.json, not these flags, so they may compute a different total_capacity. Run `aet.py "
            "set-policy` once with these flags to make every command agree."
        )
    hint = reconcile_hint(session)
    created_hint_msg = stale_created_hint(session)
    if hint or created_hint_msg:
        you = []
        if hint:
            you.append(hint)
        if created_hint_msg:
            you.append(created_hint_msg)
        you.append("Then re-run `aet.py loop-state` for the routed next action — the counts above are stale until you reconcile.")
    else:
        you = compute_next(state, runtime, ready, free_slots, total_capacity, free_gpu_ids)
    emit(ok=ok_lines, state=state_lines, you=you)


def command_strategist_begin(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    runtime = resolve_runtime(args, meta)
    state = load_loop_state(session)

    active = state.get("active_strategist_call")
    if active:
        emit(
            ok=[f"REFUSED: Strategist call {active['call_id']} already open ({active['role']}/{active['invocation']})."],
            you=[
                f"You still owe an `aet.py strategist-return` for it — an open call is NOT evidence the subagent is still running. Check its real state; if it already returned: `aet.py strategist-return --call-id {active['call_id']} ...`",
                f"if its output is merely lost, resume that subagent to re-request it; use `aet.py strategist-abort --call-id {active['call_id']} --reason unreachable` ONLY if that resume returns `success:false`.",
                "Do NOT open a second call.",
            ],
        )
        raise SystemExit(1)

    ready, ready_note = resolve_ready_count(args, session)
    policy = resolve_policy(args, session)
    slots = query_slots(policy, allow_over_cap=True)
    free_slots, total_capacity = slots_summary(slots)
    route = compute_route(state, runtime, ready)

    state["strategist_call_count"] = state.get("strategist_call_count", 0) + 1
    call_id = f"strat-{state['strategist_call_count']:04d}"
    snapshot = {rid: meta_v["version"] for rid, meta_v in state["pending_runs"].items()}
    state["active_strategist_call"] = {
        "call_id": call_id,
        "role": route["role"],
        "invocation": route["invocation"],
        "target_agent_id": route["target_agent_id"],
        "snapshot": snapshot,
        "started_at": now_iso(),
        "ready_count_at_call": ready,
        "free_slots_at_call": free_slots,
    }
    state["last_strategist_at"] = now_iso()
    save_loop_state(session, state)

    you = [f"[{runtime}] {render_branch(runtime, route)}", verb_instruction(runtime, route), "payload:"]
    you += ["  " + line for line in build_payload(session, snapshot)]
    you.append(
        f"on return: run `aet.py strategist-return --call-id {call_id} --candidates-count K "
        "[--agent-id A] [--observations-present] [--queue-edits-present] [--stop-update-present]`"
    )
    you.append(f"do NOT open another call while {call_id} is active.")
    ok_lines = [f"call opened: {call_id}  role={route['role']}  invocation={route['invocation']}  snapshot={pending_run_ids(state) or '[]'}"]
    if ready_note:
        ok_lines.append(ready_note)
    emit(
        ok=ok_lines,
        state=[f"target_agent={route['target_agent_id'] or '(none)'}  mode={route['mode']}  free_slots={free_slots}  total_capacity={total_capacity}"],
        you=you,
    )


def command_strategist_return(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    state = load_loop_state(session)
    active = state.get("active_strategist_call")
    if not active or active["call_id"] != args.call_id:
        emit(
            ok=[f"REFUSED: no active call matching {args.call_id}. Current active: {active['call_id'] if active else '(none)'}."],
            you=["Pass the call-id printed by `aet.py strategist-begin`. Inspect with `aet.py loop-state`."],
        )
        raise SystemExit(1)

    role = active["role"]
    invocation = active["invocation"]
    prior_agent_id = state.get("strategist_agent_id")
    snapshot = active.get("snapshot", {})
    cleared = []
    for rid, version in snapshot.items():
        current = state["pending_runs"].get(rid)
        if current and current.get("version") == version:
            del state["pending_runs"][rid]
            cleared.append(rid)
    state["active_strategist_call"] = None

    candidates = args.candidates_count
    # Zero candidates returned is the exhaustion signal; the two-context handshake
    # (a fresh confirmer) catches a transient false zero.
    exhaustion = candidates == 0
    ready, ready_note = resolve_ready_count(args, session)
    quiescent = is_quiescent(session, ready)
    flag = None
    substituted = False

    if role == "confirmer":
        if candidates > 0:
            maybe_update_primary_id(state, args.agent_id, "promoted_confirmer")
            state["pending_exhaustion_confirmation"] = False
            flag = "CONFIRMER_OVERTURNED"
        elif candidates == 0 and exhaustion and quiescent:
            state["pending_exhaustion_confirmation"] = False
            flag = "CONFIRMED_EXHAUSTION"
        else:
            state["pending_exhaustion_confirmation"] = False
            flag = "CONFIRMATION_NOT_QUIESCENT"
    else:
        # Pure cleanup: a resume failed and no replacement was spawned. The candidate count is a
        # placeholder, not a strategist result, so it must not feed the exhaustion handshake.
        pure_resume_cleanup = args.resume_failed and not args.agent_id
        if args.resume_failed:
            # The resume tool returned success:false — the prior agent is genuinely gone.
            # Forget it whether or not a replacement was spawned: with --agent-id (a fresh
            # strategist already spawned) record it; without it, clear the id so the next
            # strategist-begin routes a fresh spawn instead of re-resuming the same corpse.
            if args.agent_id:
                maybe_update_primary_id(state, args.agent_id, "resume_failed")
            elif prior_agent_id is not None:
                state["strategist_agent_id"] = None
                history_append(state, "(cleared)", "resume_failed")
        elif args.agent_id:
            if invocation == "fresh":
                reason = "first_spawn"
            else:
                # Resume route but a new agent id came back with no asserted failure: the parent
                # Agent-spawned a fresh strategist instead of resuming via SendMessage, losing context.
                reason = "fresh_substituted"
                substituted = args.agent_id != prior_agent_id
            maybe_update_primary_id(state, args.agent_id, reason)
        if pure_resume_cleanup:
            pass
        elif candidates > 0:
            state["pending_exhaustion_confirmation"] = False
        elif candidates == 0 and exhaustion and quiescent:
            state["pending_exhaustion_confirmation"] = True
            flag = "PRIMARY_EXHAUSTION_PENDING"
        elif candidates == 0 and exhaustion and not quiescent:
            state["pending_exhaustion_confirmation"] = False
            flag = "EXHAUSTION_NOT_QUIESCENT"
        else:
            state["pending_exhaustion_confirmation"] = False
    save_loop_state(session, state)

    ok = [f"call {args.call_id} closed  cleared={cleared or '[]'}  pending now={pending_run_ids(state)}"]
    if ready_note:
        ok.append(ready_note)
    if args.agent_id:
        ok.append(f"strategist_agent_id={state.get('strategist_agent_id')} ({role})")
    elif args.resume_failed and role != "confirmer" and state.get("strategist_agent_id") is None:
        ok.append("strategist_agent_id cleared (resume_failed, no replacement); the next `aet.py strategist-begin` will fresh-spawn")
    if substituted:
        ok.append(
            "WARNING: a resume route returned a NEW agent id without `--resume-failed`. The existing strategist was "
            "NOT resumed via the resume tool (`SendMessage` on Claude Code / `send_input` on Codex); a fresh one was "
            "spawned instead, so its accumulated context is lost. If the resume genuinely failed (the resume tool "
            "returned `success:false`), re-run with `--resume-failed`. Otherwise next cycle resume with the resume "
            "tool, not a fresh spawn."
        )
    state_lines = [f"candidates={candidates}  quiescent={quiescent}  pending_exhaustion={state.get('pending_exhaustion_confirmation')}"]

    if flag == "CONFIRMED_EXHAUSTION":
        state_lines.append("CONFIRMED_EXHAUSTION (two independent quiescent 0-candidate signals agree)")
        you = [
            "Exhaustion confirmed by independent contexts. YOU own the final stop:",
            "verify target/budget genuinely unmet -> write `## Final Analysis` to `observations.md` -> run `aet.py summarize` -> `/loop` stop (Claude Code) or end supervision (Codex).",
            "If you judge it premature you may continue; the next `aet.py strategist-begin` forms a fresh handshake.",
        ]
        emit(ok=ok, state=state_lines, you=you)
        return

    you = []
    step = 1
    if candidates > 0:
        you.append(f"{step}) append {candidates} candidate(s) -> `plan.md` Ready Queue")
        step += 1
    if args.stop_update_present or args.observations_present:
        you.append(f"{step}) (if there are updates) update `plan.md`, `observations.md`, or other relevant documents accordingly.")
        step += 1
    if args.queue_edits_present:
        you.append(f"{step}) apply Queue Edits (rewrite/remove invalidated Ready Queue rows)")
        step += 1
    if flag == "CONFIRMER_OVERTURNED":
        state_lines.append("confirmer returned candidates, overturning the exhaustion signal; promoted to Primary")
    elif flag == "PRIMARY_EXHAUSTION_PENDING":
        state_lines.append("Primary returned 0 candidates while quiescent; next strategist-begin = fresh confirmer")
    elif flag in ("EXHAUSTION_NOT_QUIESCENT", "CONFIRMATION_NOT_QUIESCENT"):
        who = "Primary" if flag == "EXHAUSTION_NOT_QUIESCENT" else "confirmer"
        blockers = quiescence_blockers(session, ready)
        if blockers:
            state_lines.append(f"{who} returned 0 candidates but quiescence blocked; resolve before exhaustion handshake can proceed:")
            for b in blockers:
                you.append(f"{step}) {b}")
                step += 1
        else:
            state_lines.append(f"{who} returned 0 candidates but not quiescent; exhaustion handshake deferred")
    you.append(f"{step}) then: run `aet.py loop-state` to route the next launch/Strategist action")
    emit(ok=ok, state=state_lines, you=you)


def command_strategist_abort(args: argparse.Namespace) -> None:
    session = require_session(args)
    state = load_loop_state(session)
    active = state.get("active_strategist_call")
    if not active or active["call_id"] != args.call_id:
        # No matching open call. Still honor a pure agent-id reset: on a new-conversation
        # recovery, loop_state.json may hold a strategist_agent_id whose subagent died with the
        # prior conversation while no call is open. `--reason unreachable` clears it so the next
        # strategist-begin fresh-spawns instead of routing resume to a corpse.
        if args.reason == "unreachable" and state.get("strategist_agent_id"):
            prior = state["strategist_agent_id"]
            state["strategist_agent_id"] = None
            history_append(state, "(cleared)", "abort_unreachable_reset")
            save_loop_state(session, state)
            emit(
                ok=[f"no open call; cleared stale strategist_agent_id={prior} (unreachable reset)"],
                you=["the next `aet.py strategist-begin` will fresh-spawn."],
            )
            return
        emit(
            ok=[f"REFUSED: no active call matching {args.call_id}. Current active: {active['call_id'] if active else '(none)'}."],
            you=["Inspect with `aet.py loop-state`."],
        )
        raise SystemExit(1)
    state["active_strategist_call"] = None
    cleared_id = False
    if args.reason in {"unreachable", "spawn_failed"} and state.get("strategist_agent_id"):
        state["strategist_agent_id"] = None
        cleared_id = True
    save_loop_state(session, state)
    ok = [f"call {args.call_id} aborted ({args.reason}); pending preserved: {pending_run_ids(state)}"]
    if cleared_id:
        ok.append("strategist_agent_id cleared; the next `aet.py strategist-begin` will fresh-spawn")
    emit(
        ok=ok,
        you=["pending runs were kept. Re-open with `aet.py strategist-begin` when ready."],
    )


def command_summarize(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = load_meta(session)
    rows = read_rows(session / "results.csv")
    goal = args.goal or meta.get("goal", "max")
    scored = [(row, safe_float(row.get("primary_metric", ""))) for row in rows]
    scored = [(row, score) for row, score in scored if score is not None and row.get("status") == "finished"]
    reverse = goal != "min"
    scored.sort(key=lambda pair: pair[1], reverse=reverse)
    print(f"session: {session}")
    print(f"objective: {meta.get('objective', '')}")
    print(f"runs: {len(rows)}")
    if scored:
        best, score = scored[0]
        print(f"best: run {best.get('run_id')} {best.get('run_name')} {best.get('metric_name')}={score}")
        print(f"params: {best.get('params_json', '')}")
        print(f"notes: {best.get('notes', '')}")
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.get("status", "")] = status_counts.get(row.get("status", ""), 0) + 1
    print("statuses: " + json.dumps(status_counts, ensure_ascii=False, sort_keys=True))
    hint = reconcile_hint(session)
    if hint:
        print(hint)


def add_policy_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gpu-ids", help="Comma-separated GPU indices to use, e.g. 0,1,3")
    parser.add_argument("--max-per-gpu", type=int, help="Concurrent experiments per GPU (hard cap 3)")
    parser.add_argument("--max-util", type=int, help="Skip a GPU at or above this utilization %% (default 95)")
    parser.add_argument("--max-memory-used-mb", type=int, help="Skip a GPU whose used memory is at or above this")
    parser.add_argument("--min-free-memory-mb", type=int, help="Skip a GPU unless at least this much memory is free")
    parser.add_argument("--process-pattern", help="Regex identifying experiment processes (default python)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto Experiment Tuning helper. Durable state + GPU slots + Strategist state machine for the autonomous tuning loop. Every command prints OK/STATE/YOU; follow the YOU block."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create one session per tuning objective; then start /loop, set-policy, fill plan.md.")
    p.add_argument("--project-root", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--goal", choices=["max", "min"], default="max")
    p.add_argument("--runtime", choices=["claude", "codex"], default="claude", help="Stored as the session default for verb rendering")
    add_policy_flags(p)
    p.set_defaults(func=command_init)

    p = sub.add_parser("set-policy", help="Set/change GPU policy mid-session; stored in meta.json and read by gpu-slots/loop-state/strategist-begin.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    add_policy_flags(p)
    p.set_defaults(func=command_set_policy)

    p = sub.add_parser("create-run", help="Register a run before launch; prints output_dir (already created). Then launch, record running, move to Running.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--name")
    p.add_argument("--params")
    p.add_argument("--command")
    p.add_argument("--gpu-id")
    p.add_argument("--output-dir")
    p.add_argument("--log-path")
    p.add_argument("--notes")
    p.set_defaults(func=command_create_run)

    p = sub.add_parser("record", help="Record a status/metric change. running after launch; finished/failed/inconclusive on completion. Terminal records add to pending + flag NEW BEST.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--name")
    p.add_argument("--status", choices=["created", "running", "finished", "failed", "inconclusive", "superseded"], required=True)
    p.add_argument("--primary-metric", type=float)
    p.add_argument("--metric-name")
    p.add_argument("--metrics")
    p.add_argument("--gpu-id")
    p.add_argument("--output-dir")
    p.add_argument("--log-path")
    p.add_argument("--notes", help="Appends to observations.md; use for terminal trust/failure notes, omit for routine running updates")
    p.set_defaults(func=command_record)

    p = sub.add_parser("parse-log", help="Last-resort metric extraction from a log when structured metrics are unavailable; inspect output before recording.")
    p.add_argument("log")
    p.add_argument("--pattern", action="append", help="Regex with named groups name and value, or one numeric group")
    p.set_defaults(func=command_parse_log)

    p = sub.add_parser("unique-dir", help="Pick a non-existing path. Use only for output dirs OUTSIDE the session; for session runs use create-run.")
    p.add_argument("path")
    p.add_argument("--mkdir", action="store_true")
    p.set_defaults(func=command_unique_dir)

    p = sub.add_parser("gpu-slots", help="Live GPU slot check under the stored (or flag-overridden) policy. Prints per-GPU lines + TOTAL free_slots/total_capacity.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--kind", choices=sorted(CAPACITY_BY_KIND), help="Generic capacity preset when no policy is stored")
    p.add_argument("--capacity", type=int, help="Override max_per_gpu for this call")
    add_policy_flags(p)
    p.add_argument("--allow-over-cap", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_gpu_slots)

    p = sub.add_parser("loop-state", help="Decision panel: free slots, capacity, pending, Strategist state, and the routed NEXT action. Call each cycle / each /loop tick. The script counts the Ready Queue from plan.md itself.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--ready-count", type=int, help="Optional override; normally omit. The script counts the '### Ready Queue' rows in plan.md itself.")
    p.add_argument("--runtime", choices=["claude", "codex"], help="Optional override; defaults to the runtime stored in meta.json at init. Normally omit it.")
    add_policy_flags(p)
    p.set_defaults(func=command_loop_state)

    p = sub.add_parser("strategist-begin", help="Open a Strategist transaction: snapshots pending, computes the route, prints the payload + the exact spawn/resume tool call. Then YOU do the subagent tool_use; close with strategist-return.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--ready-count", type=int, help="Optional override; normally omit. The script counts the '### Ready Queue' rows in plan.md itself.")
    p.add_argument("--runtime", choices=["claude", "codex"], help="Optional override; defaults to the runtime stored in meta.json at init. Normally omit it.")
    add_policy_flags(p)
    p.set_defaults(func=command_strategist_begin)

    p = sub.add_parser("strategist-return", help="Close the transaction after the subagent returns: clears the snapshot, records agent id, applies the exhaustion handshake. Presence flags gate the YOU doc reminders.")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--call-id", required=True)
    p.add_argument("--ready-count", type=int, help="Optional override; normally omit. The script counts plan.md '### Ready Queue' rows itself (before you append the returned candidates) to compute quiescence.")
    p.add_argument("--candidates-count", type=int, required=True, help="Number of Ready Queue candidates the Strategist returned; exhaustion is derived from 0")
    p.add_argument("--agent-id", help="Subagent id from the spawn result; on fresh spawn or fallback this updates strategist_agent_id. On a successful resume pass the same id (or omit) — a NEW id on a resume route triggers the substitution warning")
    p.add_argument("--resume-failed", action="store_true", help="Set ONLY when a resume route's SendMessage/send_input actually returned failure (e.g. no transcript to resume). Forgets the dead agent: with --agent-id it records the replacement you spawned; without --agent-id it clears strategist_agent_id so the next strategist-begin fresh-spawns. Suppresses the substitution warning")
    p.add_argument("--observations-present", action="store_true", help="Strategist returned observations_to_append")
    p.add_argument("--queue-edits-present", action="store_true", help="Strategist returned Queue Edits")
    p.add_argument("--stop-update-present", action="store_true", help="Strategist returned a Stop/Continue Rule update")
    p.set_defaults(func=command_strategist_return)

    p = sub.add_parser("strategist-abort", help="Last resort when the subagent is truly gone (spawn failed / resume returned success:false / cancelled). An open call is not proof the subagent died — return it if it finished, or resume to re-request first. Clears the active call (and the agent id) but KEEPS pending runs. With no open call, `--reason unreachable` still clears a stale strategist_agent_id (new-conversation recovery reset).")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--call-id", required=True)
    p.add_argument("--reason", choices=["spawn_failed", "unreachable", "cancelled"], required=True)
    p.set_defaults(func=command_strategist_abort)

    p = sub.add_parser("status", help="Print session path, objective, run/status counts, and current best finished result.")
    p.add_argument("--project-root", default=".")
    p.add_argument("--session")
    p.add_argument("--goal", choices=["max", "min"])
    p.set_defaults(func=command_summarize)

    p = sub.add_parser("summarize", help="Same as status; run alongside the Session Final Analysis at stop time.")
    p.add_argument("--project-root", default=".")
    p.add_argument("--session")
    p.add_argument("--goal", choices=["max", "min"])
    p.set_defaults(func=command_summarize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
