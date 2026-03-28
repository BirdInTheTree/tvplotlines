"""Arc function experiment: test assignment order and scale.

Usage:
    # Stage 1: test assignment order (4 variants × 3 repeats)
    python scripts/arc_fn_experiment.py order examples/results/bb_s01.json --plotline empire

    # Stage 2: test scales (4 scales × 3 repeats, using best order from stage 1)
    python scripts/arc_fn_experiment.py scale examples/results/bb_s01.json --plotline empire --order A

    # Show results
    python scripts/arc_fn_experiment.py results experiments/arc_functions/
"""

import argparse
import json
import sys
import time
import uuid
from collections import Counter
from pathlib import Path


FUNCTIONS_7 = ["setup", "inciting_incident", "escalation", "turning_point", "crisis", "climax", "resolution"]
HARMON_8 = ["you", "need", "go", "search", "find", "take", "return", "change"]
MCKEE_5 = ["inciting_incident", "progressive_complications", "crisis", "climax", "resolution"]
FREYTAG_5 = ["exposition", "rising_action", "climax", "falling_action", "denouement"]

SCALE_DESCRIPTIONS = {
    "our7": {
        "setup": "Introduces the plotline. Status quo.",
        "inciting_incident": "The event that starts the plotline. One per plotline, does not repeat.",
        "escalation": "Raises the stakes. Can repeat.",
        "turning_point": "Changes direction. False peak or false collapse.",
        "crisis": "Lowest point. Hero faces what they feared most. True dilemma.",
        "climax": "Peak of the conflict. Outcome is irreversible.",
        "resolution": "Conflict resolved. Aftermath.",
    },
    "harmon": {
        "you": "The hero is in their comfort zone, ordinary world.",
        "need": "The hero is discontent or wants something.",
        "go": "An event propels the hero into action — crossing the threshold.",
        "search": "The hero pursues the goal and faces obstacles.",
        "find": "The hero finds or achieves what they wanted.",
        "take": "Getting what they wanted comes at a great cost.",
        "return": "The hero uses what they learned to deal with the consequences.",
        "change": "The hero is transformed — for better or worse.",
    },
    "mckee": {
        "inciting_incident": "The event that throws life out of balance.",
        "progressive_complications": "Obstacles escalate, forcing harder choices.",
        "crisis": "The ultimate dilemma — the hardest choice.",
        "climax": "The decisive action that resolves the crisis.",
        "resolution": "The aftermath — new equilibrium.",
    },
    "freytag": {
        "exposition": "Introduction of characters, setting, situation.",
        "rising_action": "Complications and conflicts build tension.",
        "climax": "The turning point — highest tension.",
        "falling_action": "Consequences of the climax unfold.",
        "denouement": "Final resolution, new normal.",
    },
}

SCALES = {
    "our7": FUNCTIONS_7,
    "harmon": HARMON_8,
    "mckee": MCKEE_5,
    "freytag": FREYTAG_5,
}

REPEATS = 3


def _extract_plotline_events(result: dict, plotline_id: str) -> list[dict]:
    """Extract events belonging to a plotline (primary or also_affects)."""
    events = []
    plotline_name = None
    plotline_dna = None
    for p in result.get("plotlines", []):
        if p["id"] == plotline_id:
            plotline_name = p["name"]
            plotline_dna = f"hero={p['hero']}, goal={p['goal']}, obstacle={p.get('obstacle','?')}, stakes={p.get('stakes','?')}"
            break

    for ep in result.get("episodes", []):
        for ev in ep.get("events", []):
            is_primary = ev.get("plotline_id") == plotline_id
            is_secondary = plotline_id in (ev.get("also_affects") or [])
            if is_primary or is_secondary:
                events.append({
                    "episode": ep["episode"],
                    "event": ev["event"],
                    "episode_fn": ev.get("function"),
                    "primary": is_primary,
                })
    return events, plotline_name, plotline_dna


def _format_scale(scale: list[str]) -> str:
    """Format scale with definitions for the prompt."""
    scale_name = None
    for name, vals in SCALES.items():
        if vals == scale:
            scale_name = name
            break
    if scale_name and scale_name in SCALE_DESCRIPTIONS:
        descs = SCALE_DESCRIPTIONS[scale_name]
        lines = [f"- **{v}**: {descs[v]}" for v in scale]
        return "\n".join(lines)
    return "Valid values: " + ", ".join(scale)


def _build_prompt_A(events: list[dict], plotline_name: str, plotline_dna: str, scale: list[str]) -> tuple[str, str]:
    """Run A: Pass 3 assigns arc function, no episode functions visible."""
    scale_desc = _format_scale(scale)
    event_list = "\n".join(
        f"  [{e['episode']}] {e['event']}"
        for e in events
    )
    system = (
        f"You are a story editor looking at all events of one plotline across the entire season.\n"
        f"Assign an arc function to each event — its role in the season-long arc of this plotline.\n\n"
        f"Functions:\n{scale_desc}\n\n"
        f"Return JSON: {{\"arc_functions\": [\"function1\", \"function2\", ...]}}\n"
        f"One value per event, in the same order as the input."
    )
    user = (
        f"Plotline: {plotline_name}\n"
        f"Story DNA: {plotline_dna}\n"
        f"Events in episode order:\n{event_list}"
    )
    return system, user


def _build_prompt_B(events: list[dict], plotline_name: str, plotline_dna: str, scale: list[str]) -> tuple[str, str]:
    """Run B: Pass 3 assigns arc function, sees episode functions."""
    scale_desc = _format_scale(scale)
    event_list = "\n".join(
        f"  [{e['episode']}] ({e['episode_fn']}) {e['event']}"
        for e in events
    )
    system = (
        f"You are a story editor looking at all events of one plotline across the entire season.\n"
        f"Each event already has an episode-level function in parentheses — its role within that episode.\n"
        f"Assign an arc function to each event — its role in the season-long arc. This may differ from the episode function.\n\n"
        f"Functions:\n{scale_desc}\n\n"
        f"Return JSON: {{\"arc_functions\": [\"function1\", \"function2\", ...]}}\n"
        f"One value per event, in the same order as the input."
    )
    user = (
        f"Plotline: {plotline_name}\n"
        f"Story DNA: {plotline_dna}\n"
        f"Events in episode order (episode function in parentheses):\n{event_list}"
    )
    return system, user


def _build_prompt_C_pass2(event: dict, plotline_name: str, plotline_dna: str, scale: list[str]) -> tuple[str, str]:
    """Run C step 1: Pass 2 assigns preliminary arc function (one episode)."""
    scale_str = ", ".join(scale)
    system = (
        f"You are a story editor looking at one event from a plotline.\n"
        f"Guess its arc function — its likely role in the season-long arc.\n"
        f"You only see this episode, so your guess may be wrong.\n"
        f"Valid values: {scale_str}.\n"
        f"Return JSON: {{\"arc_fn\": \"value\"}}"
    )
    user = (
        f"Plotline: {plotline_name}\n"
        f"Story DNA: {plotline_dna}\n"
        f"Episode: {event['episode']}\n"
        f"Event: {event['event']}"
    )
    return system, user


def _build_prompt_C_pass3(events: list[dict], preliminary: list[str], plotline_name: str, plotline_dna: str, scale: list[str]) -> tuple[str, str]:
    """Run C step 2: Pass 3 corrects preliminary arc functions."""
    scale_str = ", ".join(scale)
    event_list = "\n".join(
        f"  [{e['episode']}] (preliminary: {p}) {e['event']}"
        for e, p in zip(events, preliminary)
    )
    system = (
        f"You are a story editor reviewing all events of one plotline across the season.\n"
        f"Each event has a preliminary arc function (may be wrong — assigned from single-episode context).\n"
        f"Correct the arc functions using full season context.\n"
        f"Valid values: {scale_str}.\n"
        f"inciting_incident occurs once per plotline across the season.\n"
        f"Return JSON: {{\"arc_functions\": [\"function1\", \"function2\", ...]}}\n"
        f"One value per event, in the same order."
    )
    user = (
        f"Plotline: {plotline_name}\n"
        f"Story DNA: {plotline_dna}\n"
        f"Events with preliminary arc functions:\n{event_list}"
    )
    return system, user


def _build_prompt_D(event: dict, plotline_name: str, plotline_dna: str, scale: list[str]) -> tuple[str, str]:
    """Run D: Pass 2 assigns both episode function and arc function."""
    scale_str = ", ".join(scale)
    system = (
        f"You are a story editor looking at one event from a plotline.\n"
        f"Assign two functions:\n"
        f"1. episode_fn — its role within this episode\n"
        f"2. arc_fn — its likely role in the season-long arc (you only see this episode)\n"
        f"Valid values for both: {scale_str}.\n"
        f"Return JSON: {{\"episode_fn\": \"value\", \"arc_fn\": \"value\"}}"
    )
    user = (
        f"Plotline: {plotline_name}\n"
        f"Story DNA: {plotline_dna}\n"
        f"Episode: {event['episode']}\n"
        f"Event: {event['event']}"
    )
    return system, user


def _call_llm(system: str, user: str) -> dict:
    """Call LLM and return parsed JSON."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from tvplotlines.llm import LLMConfig, call_llm
    config = LLMConfig(provider="anthropic")
    return call_llm(system, user, config)


def _run_variant_A(events, name, dna, scale, repeats=REPEATS):
    """Run A: Pass 3 assigns, no episode functions."""
    results = []
    for _ in range(repeats):
        system, user = _build_prompt_A(events, name, dna, scale)
        r = _call_llm(system, user)
        fns = r.get("arc_functions", [])
        if len(fns) != len(events):
            print(f"  WARNING: got {len(fns)} functions for {len(events)} events")
            fns = (fns + ["?"] * len(events))[:len(events)]
        results.append(fns)
    return results


def _run_variant_B(events, name, dna, scale, repeats=REPEATS):
    """Run B: Pass 3 assigns, sees episode functions."""
    results = []
    for _ in range(repeats):
        system, user = _build_prompt_B(events, name, dna, scale)
        r = _call_llm(system, user)
        fns = r.get("arc_functions", [])
        if len(fns) != len(events):
            print(f"  WARNING: got {len(fns)} functions for {len(events)} events")
            fns = (fns + ["?"] * len(events))[:len(events)]
        results.append(fns)
    return results


def _run_variant_C(events, name, dna, scale, repeats=REPEATS):
    """Run C: Pass 2 preliminary → Pass 3 corrects."""
    results = []
    for _ in range(repeats):
        # Step 1: preliminary (one call per event — expensive but matches design)
        preliminary = []
        for ev in events:
            system, user = _build_prompt_C_pass2(ev, name, dna, scale)
            r = _call_llm(system, user)
            preliminary.append(r.get("arc_fn", "?"))
        # Step 2: correction
        system, user = _build_prompt_C_pass3(events, preliminary, name, dna, scale)
        r = _call_llm(system, user)
        fns = r.get("arc_functions", [])
        if len(fns) != len(events):
            fns = (fns + ["?"] * len(events))[:len(events)]
        results.append(fns)
    return results


def _run_variant_D(events, name, dna, scale, repeats=REPEATS):
    """Run D: Pass 2 assigns both (one call per event)."""
    results = []
    for _ in range(repeats):
        fns = []
        for ev in events:
            system, user = _build_prompt_D(ev, name, dna, scale)
            r = _call_llm(system, user)
            fns.append(r.get("arc_fn", "?"))
        results.append(fns)
    return results


def _compute_agreement(results: list[list[str]], events: list[dict]) -> dict:
    """Compute agreement metrics from repeated runs."""
    n = len(events)
    full_agree = 0
    partial_agree = 0
    disagree = 0

    per_event = []
    for i in range(n):
        vals = [r[i] for r in results]
        counts = Counter(vals)
        most_common_count = counts.most_common(1)[0][1]

        if most_common_count == len(results):
            full_agree += 1
            status = "agree"
        elif most_common_count >= 2:
            partial_agree += 1
            status = "partial"
        else:
            disagree += 1
            status = "disagree"

        per_event.append({
            "episode": events[i]["episode"],
            "event": events[i]["event"][:60],
            "values": vals,
            "consensus": counts.most_common(1)[0][0],
            "status": status,
        })

    distribution = Counter()
    for r in results:
        for fn in r:
            distribution[fn] += 1

    return {
        "total": n,
        "full_agree": full_agree,
        "partial_agree": partial_agree,
        "disagree": disagree,
        "agreement_rate": full_agree / n if n else 0,
        "distribution": dict(distribution.most_common()),
        "per_event": per_event,
    }


def cmd_order(args):
    """Stage 1: test assignment order."""
    result = json.loads(Path(args.result_file).read_text(encoding="utf-8"))
    events, name, dna = _extract_plotline_events(result, args.plotline)
    scale = SCALES["our7"]

    print(f"Plotline: {name} ({len(events)} events)")
    print(f"Scale: our7")
    print(f"Repeats: {REPEATS}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = {"A": _run_variant_A, "B": _run_variant_B, "C": _run_variant_C, "D": _run_variant_D}

    all_results = {}
    for variant_name, fn in variants.items():
        print(f"\n--- Variant {variant_name} ---")
        t0 = time.monotonic()
        results = fn(events, name, dna, scale)
        elapsed = time.monotonic() - t0
        agreement = _compute_agreement(results, events)
        agreement["time"] = round(elapsed, 1)
        all_results[variant_name] = agreement
        print(f"  Agreement: {agreement['full_agree']}/{agreement['total']} ({agreement['agreement_rate']:.0%})")
        print(f"  Partial: {agreement['partial_agree']}, Disagree: {agreement['disagree']}")
        print(f"  Distribution: {agreement['distribution']}")
        print(f"  Time: {elapsed:.1f}s")

    # Save
    out_file = output_dir / "stage1_order.json"
    out_file.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved to {out_file}")

    # Summary
    print(f"\n{'='*50}")
    print(f"  {'Variant':<10} {'Agree':>8} {'Partial':>8} {'Disagree':>8} {'Rate':>8} {'Time':>8}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for v in ["A", "B", "C", "D"]:
        a = all_results[v]
        print(f"  {v:<10} {a['full_agree']:>8} {a['partial_agree']:>8} {a['disagree']:>8} {a['agreement_rate']:>7.0%} {a['time']:>7.1f}s")


def cmd_scale(args):
    """Stage 2: test scales with fixed order."""
    result = json.loads(Path(args.result_file).read_text(encoding="utf-8"))
    events, name, dna = _extract_plotline_events(result, args.plotline)

    variant_fns = {"A": _run_variant_A, "B": _run_variant_B, "C": _run_variant_C, "D": _run_variant_D}
    run_fn = variant_fns[args.order]

    print(f"Plotline: {name} ({len(events)} events)")
    print(f"Order: {args.order}")
    print(f"Repeats: {REPEATS}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for scale_name, scale in SCALES.items():
        print(f"\n--- Scale: {scale_name} ({len(scale)} values) ---")
        t0 = time.monotonic()
        results = run_fn(events, name, dna, scale)
        elapsed = time.monotonic() - t0
        agreement = _compute_agreement(results, events)
        agreement["time"] = round(elapsed, 1)
        all_results[scale_name] = agreement
        print(f"  Agreement: {agreement['full_agree']}/{agreement['total']} ({agreement['agreement_rate']:.0%})")
        print(f"  Distribution: {agreement['distribution']}")
        print(f"  Time: {elapsed:.1f}s")

    out_file = output_dir / f"stage2_scale_{args.order}.json"
    out_file.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved to {out_file}")

    print(f"\n{'='*50}")
    print(f"  {'Scale':<10} {'Agree':>8} {'Rate':>8} {'Time':>8}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
    for s in SCALES:
        a = all_results[s]
        print(f"  {s:<10} {a['full_agree']:>8} {a['agreement_rate']:>7.0%} {a['time']:>7.1f}s")


def cmd_results(args):
    """Show saved results."""
    d = Path(args.results_dir)
    for f in sorted(d.glob("*.json")):
        print(f"\n=== {f.name} ===")
        data = json.loads(f.read_text(encoding="utf-8"))
        for key, val in data.items():
            if isinstance(val, dict) and "agreement_rate" in val:
                print(f"  {key}: {val['full_agree']}/{val['total']} ({val['agreement_rate']:.0%}), time={val.get('time','?')}s")


def main():
    parser = argparse.ArgumentParser(description="Arc function experiment")
    sub = parser.add_subparsers(dest="command")

    order = sub.add_parser("order", help="Stage 1: test assignment order")
    order.add_argument("result_file", help="Pipeline result JSON")
    order.add_argument("--plotline", required=True, help="Plotline ID")
    order.add_argument("--output-dir", default="experiments/arc_functions", help="Output directory")

    scale = sub.add_parser("scale", help="Stage 2: test scales")
    scale.add_argument("result_file", help="Pipeline result JSON")
    scale.add_argument("--plotline", required=True, help="Plotline ID")
    scale.add_argument("--order", required=True, choices=["A", "B", "C", "D"], help="Best order from stage 1")
    scale.add_argument("--output-dir", default="experiments/arc_functions", help="Output directory")

    results = sub.add_parser("results", help="Show results")
    results.add_argument("results_dir", help="Results directory")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"order": cmd_order, "scale": cmd_scale, "results": cmd_results}[args.command](args)


if __name__ == "__main__":
    main()
