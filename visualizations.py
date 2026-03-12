"""Generate 6 visualizations from Plotter analysis results.

Usage:
    python visualizations.py [path_to_result.json]

Defaults to tests/fixtures/slovo_patsana_s01_result.json
Outputs PNGs to viz/
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns
import networkx as nx


# --- Config ---

FIXTURE = Path("tests/fixtures/slovo_patsana_s01_result.json")
OUT_DIR = Path("viz")

STORYLINE_COLORS = {
    "belonging": "#4C72B0",
    "brotherhood": "#C44E52",
    "leadership": "#55A868",
    "family_destruction": "#DD8452",
    "innocence": "#8172B3",
    "redemption": "#64B5CD",
    "investigation": "#8C8C8C",
}

FUNCTION_COLORS = {
    "setup": "#D4D4D4",
    "escalation": "#F0E442",
    "turning_point": "#56B4E9",
    "seed": "#009E73",
    "climax": "#D55E00",
    "resolution": "#CC79A7",
    "cliffhanger": "#E69F00",
}

FUNCTION_TENSION = {
    "setup": 1,
    "seed": 1,
    "escalation": 2,
    "turning_point": 3,
    "climax": 4,
    "cliffhanger": 4,
    "resolution": 0.5,
}

RANK_ORDER = {"A": 0, "B": 1, "C": 2, "runner": 3}

ALL_FUNCTIONS = ["setup", "seed", "escalation", "turning_point", "climax", "resolution", "cliffhanger"]


def load_data(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_color(storyline_id: str) -> str:
    """Get color for a storyline, falling back to a generated color."""
    if storyline_id in STORYLINE_COLORS:
        return STORYLINE_COLORS[storyline_id]
    # Generate deterministic color for unknown storylines
    palette = sns.color_palette("husl", 12)
    idx = hash(storyline_id) % len(palette)
    return matplotlib.colors.to_hex(palette[idx])


def sorted_plotlines(plotlines: list[dict]) -> list[dict]:
    """Sort plotlines: A first, then B, then C."""
    return sorted(plotlines, key=lambda p: RANK_ORDER.get(p["rank"], 99))


# --- Chart 1: Span Timeline (Gantt) ---

def chart_span_timeline(data: dict):
    plotlines = sorted_plotlines(data["plotlines"])
    episodes_list = [ep["episode"] for ep in data["episodes"]]
    ep_idx = {ep: i for i, ep in enumerate(episodes_list)}
    n_eps = len(episodes_list)

    # Count events per storyline per episode for weight
    event_counts = defaultdict(lambda: defaultdict(int))
    for ep in data["episodes"]:
        for ev in ep["events"]:
            if ev["storyline"]:
                event_counts[ev["storyline"]][ep["episode"]] += 1

    fig, ax = plt.subplots(figsize=(14, max(4, len(plotlines) * 0.8)))

    rank_alpha = {"A": 1.0, "B": 0.7, "C": 0.45, "runner": 0.3}

    for row, pl in enumerate(reversed(plotlines)):
        base_color = get_color(pl["id"])
        base_alpha = rank_alpha.get(pl["rank"], 0.5)

        for ep_name in pl.get("span", []):
            if ep_name not in ep_idx:
                continue
            x = ep_idx[ep_name]
            count = event_counts[pl["id"]][ep_name]
            # Weight: scale alpha by event count relative to max for this line
            max_count = max(event_counts[pl["id"]].values()) if event_counts[pl["id"]] else 1
            weight_factor = max(0.4, count / max_count) if max_count > 0 else 0.4
            alpha = base_alpha * weight_factor

            rect = mpatches.FancyBboxPatch(
                (x - 0.4, row - 0.3), 0.8, 0.6,
                boxstyle="round,pad=0.05",
                facecolor=base_color, alpha=alpha,
                edgecolor=base_color, linewidth=0.5,
            )
            ax.add_patch(rect)

            if count > 0:
                ax.text(x, row, str(count), ha="center", va="center",
                        fontsize=8, color="white" if alpha > 0.5 else "black", fontweight="bold")

    # Cast lookup for driver names
    cast_map = {c["id"]: c["name"] for c in data["cast"]}
    y_labels = [f"[{pl['rank']}] {pl['name']} ({cast_map.get(pl['driver'], pl['driver'])})"
                for pl in reversed(plotlines)]

    ax.set_yticks(range(len(plotlines)))
    ax.set_yticklabels(y_labels, fontsize=10)
    ax.set_xticks(range(n_eps))
    ax.set_xticklabels(episodes_list, fontsize=9, rotation=45, ha="right")
    ax.set_xlim(-0.6, n_eps - 0.4)
    ax.set_ylim(-0.5, len(plotlines) - 0.5)
    ax.set_title("Span Timeline — when each storyline is active", fontsize=14, fontweight="bold")
    ax.set_xlabel("Episodes")
    ax.grid(axis="x", alpha=0.2)

    # Add episode themes as secondary x-labels
    themes = [ep.get("theme", "") for ep in data["episodes"]]
    if any(themes):
        ax2 = ax.secondary_xaxis("top")
        ax2.set_xticks(range(n_eps))
        ax2.set_xticklabels([t[:30] for t in themes], fontsize=7, rotation=45, ha="left")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "01_span_timeline.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  01_span_timeline.png")


# --- Chart 2: Episode Balance (Stacked Bar) ---

def chart_episode_balance(data: dict):
    plotlines = sorted_plotlines(data["plotlines"])
    pl_ids = [p["id"] for p in plotlines]
    episodes_list = [ep["episode"] for ep in data["episodes"]]

    # Count events per storyline per episode
    counts = {pl_id: [] for pl_id in pl_ids}
    for ep in data["episodes"]:
        ep_counts = Counter(ev["storyline"] for ev in ep["events"] if ev["storyline"])
        for pl_id in pl_ids:
            counts[pl_id].append(ep_counts.get(pl_id, 0))

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(episodes_list))
    bottom = np.zeros(len(episodes_list))

    for pl_id in pl_ids:
        values = np.array(counts[pl_id])
        ax.bar(x, values, bottom=bottom, label=pl_id, color=get_color(pl_id), width=0.7)
        # Add count labels in segments > 1
        for i, v in enumerate(values):
            if v > 1:
                ax.text(i, bottom[i] + v / 2, str(v), ha="center", va="center",
                        fontsize=8, color="white", fontweight="bold")
        bottom += values

    # Themes as x-labels
    themes = [ep.get("theme", "") for ep in data["episodes"]]
    x_labels = [f"{ep}\n{themes[i][:25]}" if themes[i] else ep
                for i, ep in enumerate(episodes_list)]

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=8)
    ax.set_ylabel("Number of events")
    ax.set_title("Episode Balance — storyline weight per episode", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9, ncol=2)
    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "02_episode_balance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  02_episode_balance.png")


# --- Chart 3: Tension Curves ---

def chart_tension_curves(data: dict):
    plotlines = sorted_plotlines(data["plotlines"])
    episodes_list = [ep["episode"] for ep in data["episodes"]]
    ep_idx = {ep: i for i, ep in enumerate(episodes_list)}

    fig, ax = plt.subplots(figsize=(12, 6))

    for pl in plotlines:
        xs, ys = [], []
        for ep in data["episodes"]:
            # Get max tension for this storyline in this episode
            tensions = [
                FUNCTION_TENSION.get(ev["function"], 1)
                for ev in ep["events"]
                if ev["storyline"] == pl["id"]
            ]
            if tensions:
                xs.append(ep_idx[ep["episode"]])
                ys.append(max(tensions))

        if xs:
            ax.plot(xs, ys, marker="o", label=f"{pl['name']} [{pl['rank']}]",
                    color=get_color(pl["id"]), linewidth=2, markersize=6, alpha=0.85)

    ax.set_xticks(range(len(episodes_list)))
    ax.set_xticklabels(episodes_list, fontsize=9, rotation=45, ha="right")
    ax.set_yticks([0.5, 1, 2, 3, 4])
    ax.set_yticklabels(["resolution", "setup/seed", "escalation", "turning point", "climax/cliffhanger"],
                       fontsize=9)
    ax.set_ylim(0, 4.5)
    ax.set_title("Tension Curves — dramatic arc shape per storyline", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "03_tension_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  03_tension_curve.png")


# --- Chart 4: Convergence Map (Heatmap) ---

def chart_convergence_map(data: dict):
    plotlines = sorted_plotlines(data["plotlines"])
    pl_ids = [p["id"] for p in plotlines]
    pl_names = [p["name"] for p in plotlines]
    n = len(pl_ids)

    # Build interaction matrix
    matrix = np.zeros((n, n))
    id_to_idx = {pid: i for i, pid in enumerate(pl_ids)}

    # From interactions
    for ep in data["episodes"]:
        for inter in ep.get("interactions", []):
            lines = [l for l in inter.get("lines", []) if l in id_to_idx]
            for i, a in enumerate(lines):
                for b in lines[i + 1:]:
                    matrix[id_to_idx[a]][id_to_idx[b]] += 1
                    matrix[id_to_idx[b]][id_to_idx[a]] += 1

    # From also_affects
    for ep in data["episodes"]:
        for ev in ep["events"]:
            if ev["storyline"] and ev.get("also_affects"):
                src = ev["storyline"]
                if src not in id_to_idx:
                    continue
                for tgt in ev["also_affects"]:
                    if tgt in id_to_idx and tgt != src:
                        matrix[id_to_idx[src]][id_to_idx[tgt]] += 1
                        matrix[id_to_idx[tgt]][id_to_idx[src]] += 1

    fig, ax = plt.subplots(figsize=(8, 7))
    mask = np.eye(n, dtype=bool)
    sns.heatmap(matrix, mask=mask, annot=True, fmt=".0f", cmap="YlOrRd",
                xticklabels=pl_names, yticklabels=pl_names,
                square=True, linewidths=0.5, ax=ax, cbar_kws={"label": "Interactions"})
    ax.set_title("Storyline Convergence — how storylines interact", fontsize=14, fontweight="bold")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "04_convergence_map.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  04_convergence_map.png")


# --- Chart 5: Function Distribution (Small Multiples) ---

def chart_function_distribution(data: dict):
    episodes = data["episodes"]
    n_eps = len(episodes)
    cols = min(4, n_eps)
    rows = (n_eps + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows), sharey=True)
    if rows == 1:
        axes = [axes] if cols == 1 else list(axes)
    else:
        axes = [ax for row in axes for ax in row]

    for i, ep in enumerate(episodes):
        ax = axes[i]
        func_counts = Counter(ev["function"] for ev in ep["events"])
        funcs = ALL_FUNCTIONS
        values = [func_counts.get(f, 0) for f in funcs]
        colors = [FUNCTION_COLORS.get(f, "#999") for f in funcs]

        y_pos = np.arange(len(funcs))
        bars = ax.barh(y_pos, values, color=colors, edgecolor="#666", linewidth=0.5, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f.replace("_", " ") for f in funcs], fontsize=8)
        ax.set_title(f"{ep['episode']}", fontsize=10, fontweight="bold")
        ax.set_xlim(0, max(max(values) + 1, 5))

        for bar, v in zip(bars, values):
            if v > 0:
                ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                        str(v), va="center", fontsize=8)

    # Hide unused subplots
    for j in range(len(episodes), len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Function Distribution — dramatic beat types per episode",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "05_function_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  05_function_distribution.png")


# --- Chart 6: Character-Storyline Network ---

def chart_character_network(data: dict):
    cast_map = {c["id"]: c["name"] for c in data["cast"]}
    plotlines = sorted_plotlines(data["plotlines"])
    pl_map = {p["id"]: p for p in plotlines}

    # Count character appearances per storyline
    char_story_counts = defaultdict(lambda: defaultdict(int))
    char_total = defaultdict(int)

    for ep in data["episodes"]:
        for ev in ep["events"]:
            sl = ev["storyline"]
            if not sl:
                continue
            for ch in ev["characters"]:
                char_story_counts[ch][sl] += 1
                char_total[ch] += 1

    # Filter: only characters with >= 2 events
    active_chars = [ch for ch, total in char_total.items() if total >= 2]
    active_storylines = [p["id"] for p in plotlines]

    G = nx.Graph()

    # Add character nodes (left)
    for ch in active_chars:
        G.add_node(f"ch_{ch}", bipartite=0, label=cast_map.get(ch, ch), total=char_total[ch])

    # Add storyline nodes (right)
    for sl in active_storylines:
        G.add_node(f"sl_{sl}", bipartite=1, label=pl_map[sl]["name"], rank=pl_map[sl]["rank"])

    # Add edges
    for ch in active_chars:
        for sl in active_storylines:
            w = char_story_counts[ch][sl]
            if w > 0:
                G.add_edge(f"ch_{ch}", f"sl_{sl}", weight=w)

    # Layout: bipartite
    char_nodes = [n for n in G.nodes if n.startswith("ch_")]
    story_nodes = [n for n in G.nodes if n.startswith("sl_")]

    pos = {}
    for i, n in enumerate(char_nodes):
        pos[n] = (0, -i)
    for i, n in enumerate(story_nodes):
        pos[n] = (3, -i * (len(char_nodes) / max(len(story_nodes), 1)))

    fig, ax = plt.subplots(figsize=(14, max(8, len(char_nodes) * 0.7)))

    # Draw edges
    for u, v, d in G.edges(data=True):
        w = d["weight"]
        sl_id = v.replace("sl_", "") if v.startswith("sl_") else u.replace("sl_", "")
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=get_color(sl_id), alpha=min(0.8, 0.2 + w * 0.1),
                linewidth=max(0.5, w * 0.6))

    # Draw character nodes
    rank_colors = {"A": "#E74C3C", "B": "#F39C12", "C": "#95A5A6", "runner": "#BDC3C7"}
    for n in char_nodes:
        total = G.nodes[n]["total"]
        size = max(200, total * 40)
        ax.scatter(*pos[n], s=size, c="#3498DB", zorder=5, edgecolors="white", linewidth=1.5)
        ax.text(pos[n][0] - 0.15, pos[n][1], G.nodes[n]["label"],
                ha="right", va="center", fontsize=9, fontweight="bold")

    # Draw storyline nodes
    for n in story_nodes:
        rank = G.nodes[n]["rank"]
        color = rank_colors.get(rank, "#95A5A6")
        ax.scatter(*pos[n], s=600, c=color, zorder=5, marker="s", edgecolors="white", linewidth=1.5)
        sl_id = n.replace("sl_", "")
        ax.text(pos[n][0] + 0.15, pos[n][1],
                f"{G.nodes[n]['label']} [{rank}]",
                ha="left", va="center", fontsize=10, fontweight="bold")

    ax.set_xlim(-1.5, 4.5)
    ax.axis("off")
    ax.set_title("Character-Storyline Network — who drives what",
                 fontsize=14, fontweight="bold")

    # Legend
    for rank, color in rank_colors.items():
        if rank in {p["rank"] for p in plotlines}:
            ax.scatter([], [], s=100, c=color, marker="s", label=f"Rank {rank}")
    ax.legend(loc="lower right", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "06_character_network.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  06_character_network.png")


# --- Main ---

def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURE
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    data = load_data(path)

    show = data.get("context", {}).get("story_engine", "")
    print(f"Generating visualizations for: {show[:60]}...")
    print(f"  {len(data['plotlines'])} plotlines, {len(data['episodes'])} episodes")
    print()

    chart_span_timeline(data)
    chart_episode_balance(data)
    chart_tension_curves(data)
    chart_convergence_map(data)
    chart_function_distribution(data)
    chart_character_network(data)

    print(f"\nDone! All charts saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
