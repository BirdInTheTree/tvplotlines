"""CLI for tvplotlines: extract plotlines from TV series synopses.

Usage:
    tvplotlines run breaking-bad/
    tvplotlines run breaking-bad/ --show "Breaking Bad"
    tvplotlines run S01E01.txt S01E02.txt --show "House" --season 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_EPISODE_ID_RE = re.compile(r"S\d{2}E\d{2}")


from tvplotlines.callbacks import PipelineCallback


class _CLICallback(PipelineCallback):
    """Print one line per pipeline stage."""

    def on_pass0_complete(self, context):
        print(f"  Pass 0 done: {context.format} | {context.story_engine}")

    def on_pass1_complete(self, cast, plotlines):
        print(f"  Pass 1 done: {len(plotlines)} plotlines, {len(cast)} cast")

    def on_batch_submitted(self, batch_id):
        print(f"  Pass 2 batch submitted: {batch_id}")

    def on_pass2_complete(self, breakdowns):
        print(f"  Pass 2 done: {len(breakdowns)} episodes")

    def on_pass3_complete(self, verdicts):
        print(f"  Pass 3 done: {len(verdicts)} verdicts applied")


def _run(args: argparse.Namespace) -> None:
    """Run the full pipeline on synopsis files."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from tvplotlines import get_plotlines
    from tvplotlines.input import load_synopses_dir

    # Directory mode: single arg that is a directory
    if len(args.files) == 1 and args.files[0].is_dir():
        try:
            show, season, episodes = load_synopses_dir(
                args.files[0],
                show=args.show,
                season=args.season,
            )
        except (FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    else:
        # File mode: explicit files, --show required
        if not args.show:
            print("--show is required when passing individual files.", file=sys.stderr)
            sys.exit(1)
        show = args.show
        season = args.season or 1
        paths = sorted(args.files, key=lambda p: p.name)
        if not paths:
            print("No synopsis files found.", file=sys.stderr)
            sys.exit(1)
        episodes = {}
        for p in paths:
            match = _EPISODE_ID_RE.search(p.stem)
            if not match:
                print(
                    f"Cannot extract episode ID (S01E01) from filename: {p.name}",
                    file=sys.stderr,
                )
                sys.exit(1)
            episode_id = match.group()
            if episode_id in episodes:
                print(f"Duplicate episode ID {episode_id} from {p.name}", file=sys.stderr)
                sys.exit(1)
            episodes[episode_id] = p.read_text(encoding="utf-8")

    # Validate mutually exclusive flags
    if args.stop_after and args.resume_from:
        print("--stop-after and --resume-from are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    import time
    print(f"Running pipeline: {show} S{season:02d}")
    print(f"Episodes: {len(episodes)} synopses")

    # --stop-after pass1: run Pass 0 + Pass 1 only, save intermediate JSON
    if args.stop_after == "pass1":
        from dataclasses import asdict

        from tvplotlines.llm import LLMConfig
        from tvplotlines.pass0 import detect_context
        from tvplotlines.pass1 import extract_plotlines

        config = LLMConfig(
            provider=args.provider, model=args.model,
            base_url=args.base_url, lang=args.lang,
        )
        episode_pairs = [(eid, episodes[eid]) for eid in sorted(episodes)]

        t0 = time.monotonic()
        context = detect_context(show, season, episode_pairs[:3], config=config)
        print(f"  Pass 0 done: {context.format} | {context.story_engine}")

        cast, plotlines = extract_plotlines(
            show, season, context, episode_pairs, config=config,
        )
        print(f"  Pass 1 done: {len(plotlines)} plotlines, {len(cast)} cast")

        intermediate = {
            "show": show,
            "season": season,
            "context": asdict(context),
            "cast": [asdict(c) for c in cast],
            "plotlines": [asdict(p) for p in plotlines],
        }
        out = args.output or Path(f"{show.lower().replace(' ', '-')}_s{season:02d}_pass1.json")
        out.write_text(
            json.dumps(intermediate, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        elapsed = time.monotonic() - t0
        minutes, seconds = divmod(int(elapsed), 60)
        time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
        print(f"\nIntermediate result saved to {out} ({time_str})")
        return

    # --resume-from: load intermediate JSON, skip Pass 0 + Pass 1
    resume_kwargs = {}
    if args.resume_from:
        from tvplotlines.models import CastMember, Plotline, SeriesContext

        if not args.resume_from.exists():
            print(f"File not found: {args.resume_from}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(args.resume_from.read_text(encoding="utf-8"))
        resume_kwargs["context"] = SeriesContext(**data["context"])
        resume_kwargs["cast"] = [CastMember(**c) for c in data["cast"]]
        # Strip 'rank' key if present — rank is now a property, not a field.
        # Old intermediate JSONs may contain it; new ones use computed_rank/reviewed_rank.
        resume_kwargs["plotlines"] = [
            Plotline(**{k: v for k, v in p.items() if k != "rank"})
            for p in data["plotlines"]
        ]
        print(f"  Resumed from {args.resume_from}: "
              f"{len(resume_kwargs['plotlines'])} plotlines, "
              f"{len(resume_kwargs['cast'])} cast")

    t0 = time.monotonic()
    result = get_plotlines(
        show=show,
        season=season,
        episodes=episodes,
        lang=args.lang,
        llm_provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        skip_review=args.skip_review,
        pass2_mode=args.pass2_mode,
        callback=_CLICallback(),
        **resume_kwargs,
    )

    # Save result
    from datetime import datetime
    result_json = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    output = args.output or Path(f"{show.lower().replace(' ', '-')}_s{season:02d}.json")
    output.write_text(result_json, encoding="utf-8")
    print(f"\nSaved to {output}")

    # Save timestamped copy if --output-dir
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = show.lower().replace(" ", "-")
        ts_path = args.output_dir / f"{slug}_s{season:02d}_{ts}.json"
        ts_path.write_text(result_json, encoding="utf-8")
        print(f"Copy saved to {ts_path}")

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
    elapsed = time.monotonic() - t0
    minutes, seconds = divmod(int(elapsed), 60)
    time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
    print(f"\nModel: {args.provider}:{args.model or 'default'}, time: {time_str}")
    if hasattr(result, "usage"):
        print(f"Usage: {result.usage}")


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

    output = args.output or args.show.lower().replace(" ", "-") + "/"

    write_synopses(
        show=args.show,
        season=args.season,
        output=output,
        from_files=args.from_files,
        lang=args.lang,
        wiki_title=args.wiki_title,
        show_format=args.show_format,
        dry_run=args.dry_run,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        mode=args.mode,
        use_glossary=not args.no_glossary,
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
        help="Synopsis directory or individual text files",
    )
    run_parser.add_argument("--show", default=None, help="Series title (auto-detected from directory name)")
    run_parser.add_argument("--season", type=int, default=None, help="Season number (auto-detected from filenames)")
    run_parser.add_argument("--lang", default="en", help="Language: en or ru (default: en)")
    run_parser.add_argument("--output", "-o", type=Path, help="Output JSON path")
    run_parser.add_argument("--provider", default="anthropic",
                            help="LLM provider: anthropic, openai, ollama, deepseek, groq, or any OpenAI-compatible")
    run_parser.add_argument("--model", default=None, help="Specific model name")
    run_parser.add_argument("--base-url", default=None, help="Custom API endpoint (for OpenAI-compatible providers)")
    run_parser.add_argument("--skip-review", action="store_true", help="Skip Pass 3 structural review")
    run_parser.add_argument("--pass2-mode", default="batch", choices=["parallel", "batch", "sequential"])
    run_parser.add_argument(
        "--stop-after", choices=["pass1"],
        help="Stop after the given pass and save intermediate result to JSON",
    )
    run_parser.add_argument(
        "--resume-from", type=Path, metavar="JSON",
        help="Resume from intermediate JSON (skip Pass 0 and Pass 1)",
    )
    run_parser.add_argument(
        "--output-dir", type=Path, metavar="DIR",
        help="Save timestamped result to this directory (e.g. runs/)",
    )

    # tvplotlines write-synopses
    ws_parser = sub.add_parser(
        "write-synopses",
        help="Generate episode synopses from Wikipedia",
    )
    ws_parser.add_argument("show", help="Show title (e.g. 'House', 'Breaking Bad')")
    ws_parser.add_argument("--season", type=int, default=1, help="Season number (default: 1)")
    ws_parser.add_argument("-o", "--output", default=None,
                           help="Output directory (default: show name as folder, e.g. 'mad-men/')")
    ws_parser.add_argument("--from-files", nargs="+",
                           help="Raw description files to rewrite (skip Wikipedia fetch)")
    ws_parser.add_argument("--wiki-title",
                           help="Exact Wikipedia page title (override auto-detection)")
    ws_parser.add_argument("--format", dest="show_format",
                           choices=["procedural", "serial", "hybrid", "ensemble"],
                           help="Show format hint for beat counts (auto-detected if omitted)")
    ws_parser.add_argument("--lang", default="en", help="Wikipedia language (default: en)")
    ws_parser.add_argument("--dry-run", action="store_true",
                           help="Fetch and parse only, show episodes without calling LLM")
    ws_parser.add_argument("--provider", default="anthropic",
                           help="LLM provider (default: anthropic)")
    ws_parser.add_argument("--model", default=None, help="Specific model name")
    ws_parser.add_argument("--base-url", default=None, help="Custom API endpoint")
    ws_parser.add_argument("--mode", default="parallel",
                           choices=["parallel", "batch", "sequential", "single"],
                           help="Execution mode (default: parallel)")
    ws_parser.add_argument("--no-glossary", action="store_true",
                           help="Skip glossary injection into system prompt")

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
