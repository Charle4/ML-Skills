#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json_arg(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def command_init(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).expanduser().resolve()
    timestamp = datetime.now().astimezone()
    created_at = timestamp.isoformat(timespec="seconds")
    session = project_root / "aet" / timestamp.strftime("%Y-%m-%d") / timestamp.strftime("%H-%M-%S")
    session.mkdir(parents=True, exist_ok=False)
    (session / "runs").mkdir()
    meta = {
        "project_root": str(project_root),
        "session_dir": str(session),
        "name": args.name,
        "objective": args.objective,
        "goal": args.goal,
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
    print(session)


def next_run_id(session: Path) -> int:
    existing = []
    for path in (session / "runs").iterdir():
        if path.is_dir() and path.name.isdigit():
            existing.append(int(path.name))
    return 0 if not existing else max(existing) + 1


def command_create_run(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = json.loads((session / "meta.json").read_text(encoding="utf-8"))
    run_id = args.run_id if args.run_id is not None else next_run_id(session)
    run_name = args.name or f"run-{run_id:04d}"
    run_dir = session / "runs" / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=False)

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

    rows = read_rows(session / "results.csv")
    row = {
        "run_id": str(run_id),
        "run_name": run_name,
        "status": "created",
        "goal": meta.get("goal", ""),
        "primary_metric": "",
        "metric_name": "",
        "gpu_id": args.gpu_id or "",
        "output_dir": args.output_dir or "",
        "log_path": args.log_path or "",
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
    print(run_dir)


def command_record(args: argparse.Namespace) -> None:
    session = require_session(args)
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
            "end_time": now_iso() if args.status in {"finished", "failed", "inconclusive", "superseded"} else row.get("end_time", ""),
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
    print(session / "results.csv")


def parse_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


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


def process_gpu_counts(pattern: str) -> dict[str, int]:
    try:
        out = subprocess.check_output(["ps", "ax", "-o", "args="], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return {}
    counts: dict[str, int] = {}
    matcher = re.compile(pattern)
    for line in out.splitlines():
        if not matcher.search(line):
            continue
        match = re.search(r"--gpu(?:_id)?(?:=|\s+)(\d+)", line)
        if match:
            gpu = match.group(1)
            counts[gpu] = counts.get(gpu, 0) + 1
    return counts


def command_gpu_slots(args: argparse.Namespace) -> None:
    capacity = args.capacity if args.capacity is not None else CAPACITY_BY_KIND.get(args.kind, 2)
    if capacity > HARD_CAP_PER_GPU and not args.allow_over_cap:
        capacity = HARD_CAP_PER_GPU
    gpu_info = nvidia_rows()
    if args.gpu_ids:
        allowed = {gpu.strip() for gpu in args.gpu_ids.split(",") if gpu.strip()}
        gpu_info = [row for row in gpu_info if row["index"] in allowed]
    counts = process_gpu_counts(args.process_pattern)
    result = []
    for row in gpu_info:
        gpu = row["index"]
        running = counts.get(gpu, 0)
        util = int(float(row["utilization"]))
        memory_used = int(float(row["memory_used"]))
        memory_total = int(float(row["memory_total"]))
        memory_free = max(0, memory_total - memory_used)
        free_slots = max(0, capacity - running)
        if util >= args.saturated_util:
            free_slots = 0
        if args.max_memory_used_mb is not None and memory_used >= args.max_memory_used_mb:
            free_slots = 0
        if args.min_free_memory_mb is not None and memory_free < args.min_free_memory_mb:
            free_slots = 0
        item = {
            "gpu": int(gpu),
            "utilization": util,
            "memory_used_mb": memory_used,
            "memory_total_mb": memory_total,
            "memory_free_mb": memory_free,
            "running_count": running,
            "capacity": capacity,
            "free_slots": free_slots,
        }
        result.append(item)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in result:
            print(
                f"gpu {item['gpu']}: util={item['utilization']}%, "
                f"mem={item['memory_used_mb']}/{item['memory_total_mb']} MiB "
                f"(free={item['memory_free_mb']} MiB), running={item['running_count']}, "
                f"capacity={item['capacity']}, free={item['free_slots']}"
            )


def safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def command_summarize(args: argparse.Namespace) -> None:
    session = require_session(args)
    meta = json.loads((session / "meta.json").read_text(encoding="utf-8"))
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto Experiment Tuning helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--project-root", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--goal", choices=["max", "min"], default="max")
    p.set_defaults(func=command_init)

    p = sub.add_parser("create-run")
    p.add_argument("--session")
    p.add_argument("--project-root", default=".")
    p.add_argument("--run-id", type=int)
    p.add_argument("--name")
    p.add_argument("--params")
    p.add_argument("--command")
    p.add_argument("--gpu-id")
    p.add_argument("--output-dir")
    p.add_argument("--log-path")
    p.add_argument("--notes")
    p.set_defaults(func=command_create_run)

    p = sub.add_parser("record")
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
    p.add_argument("--notes")
    p.set_defaults(func=command_record)

    p = sub.add_parser("parse-log")
    p.add_argument("log")
    p.add_argument("--pattern", action="append", help="Regex with named groups name and value, or one numeric group")
    p.set_defaults(func=command_parse_log)

    p = sub.add_parser("unique-dir")
    p.add_argument("path")
    p.add_argument("--mkdir", action="store_true")
    p.set_defaults(func=command_unique_dir)

    p = sub.add_parser("gpu-slots")
    p.add_argument("--kind", default="default", choices=sorted(CAPACITY_BY_KIND))
    p.add_argument("--capacity", type=int)
    p.add_argument("--saturated-util", type=int, default=95)
    p.add_argument("--process-pattern", default=r"python")
    p.add_argument("--gpu-ids", help="Comma-separated GPU indices to consider, e.g. 0,1,3")
    p.add_argument("--max-memory-used-mb", type=int, help="Set free_slots=0 when used memory is at or above this value")
    p.add_argument("--min-free-memory-mb", type=int, help="Set free_slots=0 unless at least this much memory is free")
    p.add_argument("--allow-over-cap", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_gpu_slots)

    p = sub.add_parser("status")
    p.add_argument("--project-root", default=".")
    p.add_argument("--session")
    p.add_argument("--goal", choices=["max", "min"])
    p.set_defaults(func=command_summarize)

    p = sub.add_parser("summarize")
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
