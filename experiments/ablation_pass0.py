"""Ablation study: is Pass 0 (separate context detection) worth the extra LLM call?

Compares two conditions:
  A (baseline): Pass 0 → Pass 1 → Pass 2 → Pass 3
  B (merged):   Pass 1-merged → Pass 2 → Pass 3

Metrics: coverage, ARI (consistency), total tokens, wall-clock seconds.

Usage:
    python -m experiments.ablation_pass0 [--runs N] [--show CODE]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Load .env and add tvplotlines src to path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

import dotenv
dotenv.load_dotenv(_project_root / ".env")

from tvplotlines.llm import LLMConfig, UsageStats, usage
from tvplotlines.metrics import compute_consistency_ari, compute_coverage
from tvplotlines.models import TVPlotlinesResult
from tvplotlines.pass1_merged import extract_storylines_merged
from tvplotlines.pipeline import get_plotlines

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SYNOPSES_DIR = Path(__file__).resolve().parent.parent.parent / "plotter-app" / "data" / "synopses"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

SHOWS = {
    "BB":    {"name": "Breaking Bad",     "season": 1, "episodes": 7},
    "GOT":   {"name": "Game of Thrones",  "season": 1, "episodes": 10},
    "HOUSE": {"name": "House",            "season": 1, "episodes": 22},
}


@dataclass
class RunResult:
    show: str
    condition: str
    run: int
    coverage: float
    tokens_in: int
    tokens_out: int
    seconds: float
    franchise_type: str
    storyline_count: int
    result: TVPlotlinesResult


def load_synopses(code: str, info: dict) -> list[str]:
    """Load episode synopses from text files."""
    episodes = []
    for i in range(1, info["episodes"] + 1):
        path = SYNOPSES_DIR / f"{code}_S{info['season']:02d}E{i:02d}.txt"
        episodes.append(path.read_text(encoding="utf-8"))
    return episodes


def run_baseline(show: str, season: int, episodes: list[str], config: LLMConfig) -> RunResult:
    """Condition A: standard pipeline (Pass 0 → Pass 1 → Pass 2 → Pass 3)."""
    usage.__init__()
    t0 = time.monotonic()

    result = get_plotlines(show, season, episodes, lang=config.lang)

    elapsed = time.monotonic() - t0
    cov = compute_coverage(result.episodes)

    return RunResult(
        show=show,
        condition="baseline",
        run=0,
        coverage=cov,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        seconds=elapsed,
        franchise_type=result.context.franchise_type,
        storyline_count=len(result.plotlines),
        result=result,
    )


def run_merged(show: str, season: int, episodes: list[str], config: LLMConfig) -> RunResult:
    """Condition B: merged (Pass 1-merged → Pass 2 → Pass 3)."""
    usage.__init__()
    t0 = time.monotonic()

    # Pass 1-merged: context + cast + storylines in one call
    context, cast, storylines = extract_storylines_merged(
        show, season, episodes, config=config,
    )

    # Pass 2 + Pass 3 via standard pipeline (skip Pass 0 and Pass 1)
    result = get_plotlines(
        show, season, episodes,
        context=context,
        cast=cast,
        plotlines=storylines,
        lang=config.lang,
    )

    elapsed = time.monotonic() - t0
    cov = compute_coverage(result.episodes)

    return RunResult(
        show=show,
        condition="merged",
        run=0,
        coverage=cov,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        seconds=elapsed,
        franchise_type=result.context.franchise_type,
        storyline_count=len(result.plotlines),
        result=result,
    )


def main():
    parser = argparse.ArgumentParser(description="Ablation study: Pass 0 necessity")
    parser.add_argument("--runs", type=int, default=3, help="Runs per condition (default: 3)")
    parser.add_argument("--show", type=str, default=None, help="Run single show (BB, GOT, HOUSE)")
    parser.add_argument("--lang", type=str, default="en", help="Prompt language (default: en)")
    args = parser.parse_args()

    config = LLMConfig(lang=args.lang)

    shows = {args.show: SHOWS[args.show]} if args.show else SHOWS
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / "ablation_pass0.csv"

    all_results: list[RunResult] = []

    for code, info in shows.items():
        logger.info("=== %s (%s) ===", info["name"], code)
        episodes = load_synopses(code, info)

        for condition_fn, condition_name in [
            (run_baseline, "baseline"),
            (run_merged, "merged"),
        ]:
            for run_idx in range(args.runs):
                logger.info("  %s run %d/%d", condition_name, run_idx + 1, args.runs)
                result = condition_fn(info["name"], info["season"], episodes, config)
                result.run = run_idx + 1
                result.show = code
                all_results.append(result)

                logger.info(
                    "    coverage=%.3f tokens=%d+%d time=%.0fs type=%s storylines=%d",
                    result.coverage, result.tokens_in, result.tokens_out,
                    result.seconds, result.franchise_type, result.storyline_count,
                )

    # Write CSV
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "show", "condition", "run", "coverage",
            "tokens_in", "tokens_out", "seconds",
            "franchise_type", "storyline_count",
        ])
        for r in all_results:
            writer.writerow([
                r.show, r.condition, r.run, f"{r.coverage:.4f}",
                r.tokens_in, r.tokens_out, f"{r.seconds:.1f}",
                r.franchise_type, r.storyline_count,
            ])

    logger.info("Results written to %s", csv_path)

    # Compute ARI per show per condition
    logger.info("\n=== ARI (consistency across runs) ===")
    for code in shows:
        for condition in ["baseline", "merged"]:
            condition_results = [
                r for r in all_results
                if r.show == code and r.condition == condition
            ]
            if len(condition_results) < 2:
                continue

            # Collect cast ids from first run
            cast_ids = [c.id for c in condition_results[0].result.cast]
            runs_episodes = [r.result.episodes for r in condition_results]
            ari = compute_consistency_ari(runs_episodes, cast_ids)

            logger.info("  %s %s: ARI=%.3f", code, condition, ari)

    # Summary table
    logger.info("\n=== Summary ===")
    for code in shows:
        for condition in ["baseline", "merged"]:
            crs = [r for r in all_results if r.show == code and r.condition == condition]
            if not crs:
                continue
            avg_cov = sum(r.coverage for r in crs) / len(crs)
            avg_tok = sum(r.tokens_in + r.tokens_out for r in crs) / len(crs)
            avg_sec = sum(r.seconds for r in crs) / len(crs)
            logger.info(
                "  %s %s: coverage=%.3f tokens=%.0f time=%.0fs",
                code, condition, avg_cov, avg_tok, avg_sec,
            )


if __name__ == "__main__":
    main()
