"""Synopses writer experiment: compare execution modes.

Runs all modes on one show, saves results, generates blind evaluation file.

Usage:
    # Smoke test (one episode)
    python scripts/synopses_experiment.py smoke path/to/synopses_dir/ --show "Mad Men" --season 1

    # Full run (all episodes)
    python scripts/synopses_experiment.py run path/to/synopses_dir/ --show "Mad Men" --season 1

    # Generate blind eval from saved results
    python scripts/synopses_experiment.py blind path/to/experiment_dir/ --episodes S01E01 S01E07 S01E13

    # Cost/speed summary
    python scripts/synopses_experiment.py summary path/to/experiment_dir/
"""

import argparse
import json
import random
import subprocess
import sys
import time
import uuid
from pathlib import Path


MODES = ["parallel", "batch", "sequential", "single"]
GLOSSARY_CONFIGS = [
    {"mode": "parallel", "glossary": False, "label": "parallel_no_glossary"},
    {"mode": "parallel", "glossary": True, "label": "parallel_glossary"},
    {"mode": "batch", "glossary": True, "label": "batch_glossary"},
    {"mode": "sequential", "glossary": True, "label": "sequential_glossary"},
    {"mode": "single", "glossary": True, "label": "single_glossary"},
]

COST_ABORT_THRESHOLD = 3.0  # abort if cumulative cost exceeds this


def _get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


def _parse_usage(usage_str: str) -> dict:
    """Parse usage string like '7 requests, 30,000 input + 10,000 output tokens, ~$0.200'"""
    info = {"raw": usage_str}
    try:
        if "$" in usage_str:
            cost_part = usage_str.split("$")[-1]
            info["cost"] = float(cost_part)
    except (ValueError, IndexError):
        pass
    return info


def _run_one_config(
    config: dict,
    synopses_dir: Path,
    show: str,
    season: int,
    output_dir: Path,
    experiment_id: str,
    max_episodes: int | None = None,
) -> dict:
    """Run write-synopses with one configuration, return result metadata."""
    label = config["label"]
    mode = config["mode"]
    glossary = config["glossary"]

    out_dir = output_dir / label
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        sys.executable, "-m", "tvplotlines",
        "write-synopses", show,
        "--season", str(season),
        "--mode", mode,
        "-o", str(out_dir) + "/",
        "--provider", "anthropic",
    ]
    if not glossary:
        cmd.append("--no-glossary")

    # For smoke test: we still run full Wikipedia fetch but only use first episode
    # The write-synopses command processes all episodes — smoke test just checks output

    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"  Mode: {mode}, Glossary: {glossary}")
    print(f"{'='*60}")

    t0 = time.monotonic()
    timeout = 3600 if mode == "batch" else 600
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.monotonic() - t0
        print(f"  TIMEOUT after {elapsed:.0f}s")
        (out_dir / "stdout.txt").write_text(e.stdout or "", encoding="utf-8")
        (out_dir / "stderr.txt").write_text(e.stderr or "", encoding="utf-8")
        meta = {
            "label": label, "mode": mode, "glossary": glossary,
            "experiment_id": experiment_id, "git_commit": _get_git_commit(),
            "elapsed_seconds": round(elapsed, 1), "exit_code": -1,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": f"timeout after {timeout}s",
        }
        (out_dir / "meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8",
        )
        return meta
    elapsed = time.monotonic() - t0

    # Save stdout/stderr
    (out_dir / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (out_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    # Parse results
    meta = {
        "label": label,
        "mode": mode,
        "glossary": glossary,
        "experiment_id": experiment_id,
        "git_commit": _get_git_commit(),
        "elapsed_seconds": round(elapsed, 1),
        "exit_code": result.returncode,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Extract cost from stdout
    for line in result.stdout.splitlines():
        if "Usage:" in line:
            meta["usage"] = _parse_usage(line)
        if "Saved" in line and "synopsis" in line.lower():
            meta["saved"] = line.strip()

    # Save metadata
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Check for errors
    if result.returncode != 0:
        print(f"  ERROR (exit {result.returncode}):")
        print(f"  {result.stderr[:500]}")
    else:
        cost = meta.get("usage", {}).get("cost", "?")
        print(f"  Done in {elapsed:.0f}s, cost: ${cost}")

    return meta


def cmd_smoke(args):
    """Smoke test: run all configs, verify output."""
    experiment_id = str(uuid.uuid4())[:8]
    output_dir = Path(args.output_dir) / f"smoke_{experiment_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Smoke test — experiment_id: {experiment_id}")
    print(f"Git commit: {_get_git_commit()}")
    print(f"Output: {output_dir}")

    results = []
    for config in GLOSSARY_CONFIGS:
        meta = _run_one_config(
            config, Path(args.synopses_dir), args.show, args.season,
            output_dir, experiment_id,
        )
        results.append(meta)

        # Check cost abort
        total_cost = sum(
            r.get("usage", {}).get("cost", 0) for r in results
        )
        if total_cost > COST_ABORT_THRESHOLD:
            print(f"\n  ABORT: cumulative cost ${total_cost:.2f} exceeds ${COST_ABORT_THRESHOLD}")
            break

    # Smoke test validation
    print(f"\n{'='*60}")
    print("  Smoke test results")
    print(f"{'='*60}")
    for meta in results:
        label = meta["label"]
        status = "OK" if meta["exit_code"] == 0 else f"FAIL (exit {meta['exit_code']})"
        out_dir = output_dir / label
        synopsis_files = list(out_dir.glob("S*.txt"))
        print(f"  {label:30s} {status:10s} {len(synopsis_files)} files, {meta['elapsed_seconds']}s")

    # Save experiment summary
    (output_dir / "experiment.json").write_text(
        json.dumps({
            "experiment_id": experiment_id,
            "git_commit": _get_git_commit(),
            "type": "smoke",
            "show": args.show,
            "season": args.season,
            "results": results,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def cmd_run(args):
    """Full experiment run."""
    experiment_id = str(uuid.uuid4())[:8]
    output_dir = Path(args.output_dir) / f"run_{experiment_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Full run — experiment_id: {experiment_id}")
    print(f"Git commit: {_get_git_commit()}")
    print(f"Output: {output_dir}")

    results = []
    for config in GLOSSARY_CONFIGS:
        meta = _run_one_config(
            config, Path(args.synopses_dir), args.show, args.season,
            output_dir, experiment_id,
        )
        results.append(meta)

        total_cost = sum(
            r.get("usage", {}).get("cost", 0) for r in results
        )
        if total_cost > COST_ABORT_THRESHOLD:
            print(f"\n  ABORT: cumulative cost ${total_cost:.2f} exceeds ${COST_ABORT_THRESHOLD}")
            break

    _print_summary(results)

    (output_dir / "experiment.json").write_text(
        json.dumps({
            "experiment_id": experiment_id,
            "git_commit": _get_git_commit(),
            "type": "full",
            "show": args.show,
            "season": args.season,
            "results": results,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def cmd_blind(args):
    """Generate blind evaluation file from experiment results."""
    experiment_dir = Path(args.experiment_dir)
    episodes = args.episodes

    experiment = json.loads(
        (experiment_dir / "experiment.json").read_text(encoding="utf-8")
    )

    # Collect synopses per episode per mode (exclude batch — programmatic diff only)
    blind_labels = [c["label"] for c in GLOSSARY_CONFIGS if c["mode"] != "batch"]

    all_synopses = {}  # episode -> [(label, text)]
    for label in blind_labels:
        label_dir = experiment_dir / label
        for ep_id in episodes:
            ep_file = label_dir / f"{ep_id}.txt"
            if ep_file.exists():
                text = ep_file.read_text(encoding="utf-8").strip()
                all_synopses.setdefault(ep_id, []).append((label, text))

    # Shuffle and assign blind labels
    mapping = {}  # blind_label -> real_label
    blind_output = []

    for ep_id in episodes:
        entries = all_synopses.get(ep_id, [])
        random.shuffle(entries)

        blind_output.append(f"\n## {ep_id}\n")
        for i, (real_label, text) in enumerate(entries):
            blind_label = chr(65 + i)  # A, B, C, D
            mapping[f"{ep_id}_{blind_label}"] = real_label
            blind_output.append(f"### Synopsis {blind_label}\n")
            blind_output.append(text)
            blind_output.append("")

    # Save blind eval file
    blind_path = experiment_dir / "blind_eval.md"
    blind_path.write_text(
        "# Blind Evaluation\n\n"
        "Score each synopsis using the event checklist.\n"
        "Do NOT open _mapping.json until scoring is complete.\n\n"
        + "\n".join(blind_output),
        encoding="utf-8",
    )

    # Save mapping separately
    mapping_path = experiment_dir / "_mapping.json"
    mapping_path.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Blind eval: {blind_path}")
    print(f"Mapping (DO NOT OPEN YET): {mapping_path}")
    print(f"Episodes: {', '.join(episodes)}")
    print(f"Conditions: {len(blind_labels)} (batch excluded — verify programmatically)")


def cmd_summary(args):
    """Print cost/speed summary from experiment results."""
    experiment_dir = Path(args.experiment_dir)
    experiment = json.loads(
        (experiment_dir / "experiment.json").read_text(encoding="utf-8")
    )
    _print_summary(experiment["results"])


def _print_summary(results: list[dict]):
    """Print comparison table."""
    print(f"\n{'='*70}")
    print(f"  {'Label':30s} {'Time':>8s} {'Cost':>8s} {'Status':>8s}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8}")
    for r in results:
        cost = r.get("usage", {}).get("cost", 0)
        cost_str = f"${cost:.3f}" if cost else "?"
        elapsed = f"{r['elapsed_seconds']}s"
        status = "OK" if r["exit_code"] == 0 else "FAIL"
        print(f"  {r['label']:30s} {elapsed:>8s} {cost_str:>8s} {status:>8s}")
    total_cost = sum(r.get("usage", {}).get("cost", 0) for r in results)
    print(f"\n  Total cost: ${total_cost:.3f}")


def main():
    parser = argparse.ArgumentParser(
        description="Synopses writer experiment runner",
    )
    sub = parser.add_subparsers(dest="command")

    # smoke
    smoke = sub.add_parser("smoke", help="Smoke test — all modes, verify output")
    smoke.add_argument("synopses_dir", help="Directory with raw synopsis .txt files (or show name for Wikipedia)")
    smoke.add_argument("--show", required=True)
    smoke.add_argument("--season", type=int, required=True)
    smoke.add_argument("--output-dir", default="experiments/synopses", help="Output directory")

    # run
    run = sub.add_parser("run", help="Full experiment run")
    run.add_argument("synopses_dir", help="Directory or show name")
    run.add_argument("--show", required=True)
    run.add_argument("--season", type=int, required=True)
    run.add_argument("--output-dir", default="experiments/synopses", help="Output directory")

    # blind
    blind = sub.add_parser("blind", help="Generate blind evaluation file")
    blind.add_argument("experiment_dir", help="Path to experiment output directory")
    blind.add_argument("--episodes", nargs="+", required=True, help="Episode IDs for eval (e.g. S01E01 S01E07 S01E13)")

    # summary
    summary = sub.add_parser("summary", help="Print cost/speed summary")
    summary.add_argument("experiment_dir")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {"smoke": cmd_smoke, "run": cmd_run, "blind": cmd_blind, "summary": cmd_summary}
    commands[args.command](args)


if __name__ == "__main__":
    main()
