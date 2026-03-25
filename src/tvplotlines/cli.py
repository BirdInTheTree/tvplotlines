"""CLI for tvplotlines: extract plotlines from TV series synopses.

Usage:
    tvplotlines run synopses/SP_S01E*.txt --show "Слово пацана" --season 1
    tvplotlines run episodes/ --show "House" --season 1 --lang en --output house_s01.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_EPISODE_ID_RE = re.compile(r"S\d{2}E\d{2}")


def _run(args: argparse.Namespace) -> None:
    """Run the full pipeline on synopsis files."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from tvplotlines import get_plotlines

    # Read synopsis files and extract episode IDs from filenames
    paths = sorted(args.files, key=lambda p: p.name)
    if not paths:
        print("No synopsis files found.", file=sys.stderr)
        sys.exit(1)

    episodes: dict[str, str] = {}
    for p in paths:
        match = _EPISODE_ID_RE.search(p.stem)
        if not match:
            print(
                f"Cannot extract episode ID (SddEdd) from filename: {p.name}",
                file=sys.stderr,
            )
            sys.exit(1)
        episode_id = match.group()
        if episode_id in episodes:
            print(f"Duplicate episode ID {episode_id} from {p.name}", file=sys.stderr)
            sys.exit(1)
        episodes[episode_id] = p.read_text(encoding="utf-8")

    print(f"Running pipeline: {args.show} S{args.season:02d}")
    print(f"Episodes: {len(episodes)} synopses from {paths[0].name} to {paths[-1].name}")

    result = get_plotlines(
        show=args.show,
        season=args.season,
        episodes=episodes,
        lang=args.lang,
        llm_provider=args.provider,
        model=args.model,
        base_url=args.base_url,
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
    print(f"Context: {result.context.format} | {result.context.story_engine}")
    if result.context.is_ensemble:
        print("  (ensemble)")
    if result.context.is_anthology:
        print("  (anthology)")
    print(f"Cast: {len(result.cast)} characters")
    print(f"Plotlines: {len(result.plotlines)}")
    for s in result.plotlines:
        print(f"  [{s.rank or 'runner'}] {s.name} (hero={s.hero})")
    print(f"Episodes: {len(result.episodes)}")
    for ep in result.episodes:
        print(f"  {ep.episode}: {len(ep.events)} events")
    if hasattr(result, "usage"):
        print(f"\nUsage: {result.usage}")


def _write_synopses(args: argparse.Namespace) -> None:
    """Generate episode synopses from Wikipedia or raw files."""
    try:
        from tvplotlines.synopses_writer import write_synopses
    except ImportError:
        print(
            "write-synopses requires additional dependencies.\n"
            "Install with: pip install tvplotlines[writer]",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    write_synopses(
        show=args.show,
        season=args.season,
        output=args.output,
        from_files=args.from_files,
        lang=args.lang,
        wiki_title=args.wiki_title,
        show_format=args.show_format,
        dry_run=args.dry_run,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tvplotlines",
        description="Extract plotlines from TV series synopses using LLM.",
    )
    sub = parser.add_subparsers(dest="command")

    # tvplotlines run
    run_parser = sub.add_parser("run", help="Run pipeline on synopsis files")
    run_parser.add_argument(
        "files", nargs="+", type=Path,
        help="Synopsis text files (one per episode)",
    )
    run_parser.add_argument("--show", required=True, help="Series title")
    run_parser.add_argument("--season", type=int, default=1, help="Season number (default: 1)")
    run_parser.add_argument("--lang", default="en", help="Language: en or ru (default: en)")
    run_parser.add_argument("--output", "-o", type=Path, help="Output JSON path")
    run_parser.add_argument("--provider", default="anthropic",
                            help="LLM provider: anthropic, openai, ollama, deepseek, groq, or any OpenAI-compatible")
    run_parser.add_argument("--model", default=None, help="Specific model name")
    run_parser.add_argument("--base-url", default=None, help="Custom API endpoint (for OpenAI-compatible providers)")
    run_parser.add_argument("--skip-review", action="store_true", help="Skip Pass 3 structural review")
    run_parser.add_argument("--pass2-mode", default="parallel", choices=["parallel", "batch", "sequential"])

    # tvplotlines write-synopses
    ws_parser = sub.add_parser(
        "write-synopses",
        help="Generate episode synopses from Wikipedia",
    )
    ws_parser.add_argument("show", help="Show title (e.g. 'House', 'Breaking Bad')")
    ws_parser.add_argument("--season", type=int, default=1, help="Season number (default: 1)")
    ws_parser.add_argument("-o", "--output", default="synopses/",
                           help="Output path: directory for individual files, file for combined (default: synopses/)")
    ws_parser.add_argument("--from-files", nargs="+",
                           help="Raw description files to rewrite (skip Wikipedia fetch)")
    ws_parser.add_argument("--wiki-title",
                           help="Exact Wikipedia page title (override auto-detection)")
    ws_parser.add_argument("--format", dest="show_format",
                           choices=["procedural", "serial", "hybrid", "limited"],
                           help="Show format hint for beat counts (auto-detected if omitted)")
    ws_parser.add_argument("--lang", default="en", help="Wikipedia language (default: en)")
    ws_parser.add_argument("--dry-run", action="store_true",
                           help="Fetch and parse only, show episodes without calling LLM")
    ws_parser.add_argument("--provider", default="anthropic",
                           help="LLM provider (default: anthropic)")
    ws_parser.add_argument("--model", default=None, help="Specific model name")
    ws_parser.add_argument("--base-url", default=None, help="Custom API endpoint")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        _run(args)
    elif args.command == "write-synopses":
        _write_synopses(args)


if __name__ == "__main__":
    main()
