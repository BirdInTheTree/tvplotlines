"""Load synopses from a directory.

Convention:
    breaking-bad/
        S01E01.txt
        S01E02.txt
        ...

Show name is derived from the directory name (kebab-case or underscores → title case).
Season number is extracted from the filenames (S01 → 1).
"""

from __future__ import annotations

import re
from pathlib import Path

_EPISODE_ID_RE = re.compile(r"S\d{2}E\d{2}")
_SEASON_RE = re.compile(r"S(\d{2})")


def _show_name_from_dir(path: Path) -> str:
    """breaking-bad → Breaking Bad, game_of_thrones → Game Of Thrones."""
    return path.name.replace("-", " ").replace("_", " ").title()


def _season_from_files(paths: list[Path]) -> int:
    """Extract season number from first file. All files must be same season."""
    match = _SEASON_RE.search(paths[0].stem)
    if not match:
        raise ValueError(
            f"Cannot extract season number from filename: {paths[0].name}. "
            f"Expected S01E01 pattern."
        )
    return int(match.group(1))


def load_synopses_dir(
    path: Path | str,
    *,
    show: str | None = None,
    season: int | None = None,
) -> tuple[str, int, dict[str, str]]:
    """Load synopses from a directory.

    Args:
        path: Directory containing .txt synopsis files.
        show: Show name override. If None, derived from directory name.
        season: Season override. If None, derived from filenames.

    Returns:
        (show_name, season_number, episodes_dict) ready for get_plotlines().

    Raises:
        FileNotFoundError: If directory doesn't exist or has no .txt files.
        ValueError: If filenames don't contain S01E01 pattern.
    """
    path = Path(path)
    if not path.is_dir():
        raise FileNotFoundError(f"Not a directory: {path}")

    all_txt = sorted(path.glob("*.txt"), key=lambda p: p.name)
    if not all_txt:
        raise FileNotFoundError(f"No .txt files found in {path}")

    show_name = show or _show_name_from_dir(path)
    season_num = season or _season_from_files(all_txt)

    # Filter files by season
    season_prefix = f"S{season_num:02d}"
    txt_files = [p for p in all_txt if season_prefix in p.stem]
    if not txt_files:
        raise FileNotFoundError(
            f"No files matching season {season_num} (S{season_num:02d}) in {path}"
        )

    episodes: dict[str, str] = {}
    for p in txt_files:
        match = _EPISODE_ID_RE.search(p.stem)
        if not match:
            raise ValueError(
                f"Cannot extract episode ID (S01E01) from filename: {p.name}"
            )
        episode_id = match.group()
        if episode_id in episodes:
            raise ValueError(f"Duplicate episode ID {episode_id} from {p.name}")
        episodes[episode_id] = p.read_text(encoding="utf-8")

    return show_name, season_num, episodes
