"""Example: run plotter pipeline on synopsis files and save result.

Equivalent CLI command:
    plotter run synopses/SP_S01E*.txt --show "Слово пацана" --season 1 --lang ru -o result.json
"""

import json
from pathlib import Path

from plotter import get_plotlines

SYNOPSES_DIR = Path("synopses")


def run(show: str, prefix: str, num_episodes: int, lang: str = "en") -> None:
    episodes = []
    for i in range(1, num_episodes + 1):
        path = SYNOPSES_DIR / f"{prefix}_S01E{i:02d}.txt"
        episodes.append(path.read_text(encoding="utf-8"))

    result = get_plotlines(show=show, season=1, episodes=episodes, lang=lang)

    output = Path(f"{prefix.lower()}_s01_result.json")
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"{show}: {len(result.plotlines)} storylines, {len(result.cast)} cast → {output}")
    for s in result.plotlines:
        print(f"  [{s.rank}] {s.name} (driver={s.driver})")


if __name__ == "__main__":
    run("Слово пацана", "SP", 8, lang="ru")
