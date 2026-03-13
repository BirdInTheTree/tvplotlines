"""CLI for plotter: extract storylines from TV series synopses.

Usage:
    plotter run synopses/SP_S01E*.txt --show "Слово пацана" --season 1
    plotter run episodes/ --show "House" --season 1 --lang en --output house_s01.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _run(args: argparse.Namespace) -> None:
    """Run the full pipeline on synopsis files."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from plotter import get_plotlines

    # Read synopsis files in sorted order
    paths = sorted(args.files, key=lambda p: p.name)
    if not paths:
        print("No synopsis files found.", file=sys.stderr)
        sys.exit(1)

    episodes = []
    for p in paths:
        episodes.append(p.read_text(encoding="utf-8"))

    print(f"Running pipeline: {args.show} S{args.season:02d}")
    print(f"Episodes: {len(episodes)} synopses from {paths[0].name} to {paths[-1].name}")

    result = get_plotlines(
        show=args.show,
        season=args.season,
        episodes=episodes,
        lang=args.lang,
        llm_provider=args.provider,
        model=args.model,
        skip_review=args.skip_review,
        pass2_mode=args.pass2_mode,
    )

    # Save result
    output = args.output or Path(f"{args.show.lower().replace(' ', '_')}_s{args.season:02d}_result.json")
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved to {output}")

    # Print summary
    print(f"Context: {result.context.franchise_type} | {result.context.story_engine}")
    print(f"Cast: {len(result.cast)} characters")
    print(f"Storylines: {len(result.plotlines)}")
    for s in result.plotlines:
        print(f"  [{s.rank}] {s.name} (driver={s.driver})")
    print(f"Episodes: {len(result.episodes)}")
    for ep in result.episodes:
        print(f"  {ep.episode}: {len(ep.events)} events")
    if hasattr(result, "usage"):
        print(f"\nUsage: {result.usage}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="plotter",
        description="Extract storylines from TV series synopses using LLM.",
    )
    sub = parser.add_subparsers(dest="command")

    # plotter run
    run_parser = sub.add_parser("run", help="Run pipeline on synopsis files")
    run_parser.add_argument(
        "files", nargs="+", type=Path,
        help="Synopsis text files (one per episode)",
    )
    run_parser.add_argument("--show", required=True, help="Series title")
    run_parser.add_argument("--season", type=int, default=1, help="Season number (default: 1)")
    run_parser.add_argument("--lang", default="en", help="Language: en or ru (default: en)")
    run_parser.add_argument("--output", "-o", type=Path, help="Output JSON path")
    run_parser.add_argument("--provider", default="anthropic", help="LLM provider (default: anthropic)")
    run_parser.add_argument("--model", default=None, help="Specific model name")
    run_parser.add_argument("--skip-review", action="store_true", help="Skip Pass 3 narratologist review")
    run_parser.add_argument("--pass2-mode", default="parallel", choices=["parallel", "batch", "sequential"])

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        _run(args)


if __name__ == "__main__":
    main()
