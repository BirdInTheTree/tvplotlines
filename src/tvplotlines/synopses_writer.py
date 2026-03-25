"""CLI utility for generating episode synopses from Wikipedia data.

Not part of the public library API — not exported from __init__.py.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import TypedDict


class RawEpisode(TypedDict):
    number: int       # 1, 2, 3...
    title: str        # "Pilot"
    description: str  # Raw Wikipedia description


try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

_USER_AGENT = "tvplotlines/0.1.0 (https://github.com/BirdInTheTree/tvplotlines)"
_MAX_RETRIES = 3
_MIN_DESCRIPTION_LENGTH = 50


def fetch_season_page(
    show: str,
    season: int,
    *,
    lang: str = "en",
    wiki_title: str | None = None,
) -> str:
    """Fetch season page HTML from Wikipedia API.

    Tries {Show}_(season_{N}), then {Show}_season_{N} if 404.
    Use wiki_title to override automatic title construction.

    Requires httpx (pip install tvplotlines[writer]).
    User-Agent: tvplotlines/0.1.0

    Args:
        show: Show name, e.g. "House" or "Breaking Bad".
        season: Season number.
        lang: Wikipedia language code.
        wiki_title: Explicit Wikipedia page title override.

    Returns:
        Raw HTML string from the Wikipedia parse API.
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for fetching Wikipedia pages. "
            "Install with: pip install tvplotlines[writer]"
        )

    if wiki_title:
        titles_to_try = [wiki_title]
    else:
        # Normalize show name: spaces → underscores
        slug = show.replace(" ", "_")
        titles_to_try = [
            f"{slug}_(season_{season})",
            f"{slug}_season_{season}",
        ]

    endpoint = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {"User-Agent": _USER_AGENT}
    last_error = None

    for title in titles_to_try:
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "redirects": "true",
        }
        html = _fetch_with_retry(endpoint, params, headers)
        if html is not None:
            return html
        last_error = title

    raise ValueError(
        f"Wikipedia page not found for '{show}' season {season}. "
        f"Tried: {', '.join(titles_to_try)}. "
        f"Use --wiki-title to specify the exact Wikipedia page title."
    )


def _fetch_with_retry(
    endpoint: str,
    params: dict,
    headers: dict,
) -> str | None:
    """Fetch a Wikipedia parse API response with exponential backoff.

    Returns HTML string on success, None if page not found.
    Raises on network errors after retries exhausted.
    """
    for attempt in range(_MAX_RETRIES):
        try:
            response = httpx.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                # Page not found — don't retry, try next title
                return None

            return data["parse"]["text"]["*"]

        except (httpx.HTTPError, KeyError) as exc:
            if attempt == _MAX_RETRIES - 1:
                raise ConnectionError(
                    f"Failed to fetch Wikipedia page after {_MAX_RETRIES} attempts: {exc}"
                ) from exc
            # Exponential backoff: 1s, 2s, 4s
            time.sleep(2 ** attempt)

    return None


def parse_episode_table(html: str) -> list[RawEpisode]:
    """Extract episodes from Wikipedia HTML episode table.

    Parses wikiepisodetable: tr.vevent for metadata,
    tr.expand-child for plot descriptions.

    Args:
        html: Raw HTML from the Wikipedia parse API.

    Returns:
        List of RawEpisode dicts with number, title, description.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikiepisodetable")
    if not table:
        raise ValueError(
            "No episode table found in Wikipedia HTML. "
            "The page may not have a standard episode listing."
        )

    episode_rows = table.find_all("tr", class_="vevent")
    if not episode_rows:
        raise ValueError(
            "No episode rows found in the episode table. "
            "The page structure may differ from the expected format."
        )

    episodes: list[RawEpisode] = []
    has_any_description = False

    for idx, row in enumerate(episode_rows, start=1):
        title = _extract_title(row)
        description = _extract_description(row)

        if description:
            has_any_description = True
            if len(description) < _MIN_DESCRIPTION_LENGTH:
                print(
                    f"Warning: Episode {idx} '{title}' has a short description "
                    f"({len(description)} chars)",
                    file=sys.stderr,
                )

        episodes.append(RawEpisode(
            number=idx,
            title=title,
            description=description,
        ))

    if not has_any_description:
        raise ValueError(
            "No episode descriptions found in the table. "
            "The page may not include plot summaries. "
            "Consider using --from-files instead."
        )

    return episodes


def _extract_title(row) -> str:
    """Extract episode title from a vevent row.

    Looks for td.summary, then falls back to the first link text.
    Strips surrounding quotes.
    """
    summary_cell = row.find("td", class_="summary")
    if not summary_cell:
        return ""

    # Prefer link text (cleaner, no subtitle noise)
    link = summary_cell.find("a")
    if link:
        title = link.get_text(strip=True)
    else:
        title = summary_cell.get_text(strip=True)

    # Strip surrounding typographic or straight quotes
    title = re.sub(r'^[\u201c\u201d"\']+|[\u201c\u201d"\']+$', "", title)
    return title


def _extract_description(row) -> str:
    """Extract plot description from the expand-child row following a vevent row.

    The description is in the next sibling tr.expand-child, inside a td
    (usually with class 'description').
    """
    next_row = row.find_next_sibling("tr")
    if not next_row or "expand-child" not in next_row.get("class", []):
        return ""

    # Try td.description first, then any td with colspan
    desc_cell = next_row.find("td", class_="description")
    if not desc_cell:
        desc_cell = next_row.find("td")

    if not desc_cell:
        return ""

    # Remove hidden elements (e.g. shortSummaryText with display:none)
    for hidden in desc_cell.find_all(style=re.compile(r"display\s*:\s*none")):
        hidden.decompose()

    return desc_cell.get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------------
# LLM rewriting
# ---------------------------------------------------------------------------


def rewrite_synopses(
    episodes: list[RawEpisode],
    show: str,
    season: int,
    config: "LLMConfig",
    *,
    show_format: str | None = None,
) -> list[str]:
    """Rewrite raw episode descriptions into full synopses via LLM.

    Args:
        episodes: Raw episodes from Wikipedia or user files.
        show: Show title.
        season: Season number.
        config: LLM configuration.
        show_format: Optional format hint (procedural/serial/hybrid/limited).

    Returns:
        List of synopsis texts, one per episode, in order.
    """
    from tvplotlines.llm import call_llm_parallel
    from tvplotlines.prompts import load_prompt

    system_prompt = load_prompt("synopses_writer")
    format_hint = f"Format: {show_format}" if show_format else "Format: unknown (determine from context)"

    user_messages = []
    for ep in episodes:
        msg = (
            f"Show: {show}\n"
            f"Season: {season}, Episode: {ep['number']}\n"
            f"{format_hint}\n\n"
            f"Raw description:\n{ep['description']}"
        )
        user_messages.append(msg)

    results = call_llm_parallel(
        system_prompt, user_messages, config, cache_system=True
    )

    return [r["synopsis"] for r in results]


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


def _save_individual_files(
    synopses: list[str],
    episodes: list[RawEpisode],
    season: int,
    output_dir: Path,
) -> list[Path]:
    """Save each synopsis as S01E01.txt, S01E02.txt, etc."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ep, text in zip(episodes, synopses):
        filename = f"S{season:02d}E{ep['number']:02d}.txt"
        path = output_dir / filename
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def _save_combined_file(
    synopses: list[str],
    episodes: list[RawEpisode],
    show: str,
    season: int,
    output_path: Path,
) -> Path:
    """Save all synopses as one combined file compatible with input_parser."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parts = [f"{show}, Season {season}", ""]
    for ep, text in zip(episodes, synopses):
        title_part = f" \u2014 {ep['title']}" if ep["title"] else ""
        parts.append(f"Episode {ep['number']}{title_part}")
        parts.append(text)
        parts.append("")
    output_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def write_synopses(
    show: str,
    season: int,
    output: str,
    *,
    from_files: list[str] | None = None,
    lang: str = "en",
    wiki_title: str | None = None,
    show_format: str | None = None,
    dry_run: bool = False,
    provider: str = "anthropic",
    model: str | None = None,
    base_url: str | None = None,
) -> None:
    """Generate episode synopses and save to files.

    Args:
        show: Show title.
        season: Season number.
        output: Output path — directory for individual files, file for combined.
        from_files: Optional list of raw description file paths (skip Wikipedia).
        lang: Wikipedia language code.
        wiki_title: Explicit Wikipedia page title.
        show_format: Show format hint for LLM.
        dry_run: Fetch and parse only, don't call LLM.
        provider: LLM provider.
        model: LLM model name.
        base_url: Custom API endpoint.
    """
    # Determine episodes source
    if from_files:
        episodes = _load_from_files(from_files, season)
    else:
        html = fetch_season_page(show, season, lang=lang, wiki_title=wiki_title)
        episodes = parse_episode_table(html)

    if dry_run:
        print(f"Found {len(episodes)} episodes:")
        for ep in episodes:
            desc_len = len(ep["description"])
            print(f"  S{season:02d}E{ep['number']:02d} — {ep['title']} ({desc_len} chars)")
        return

    from tvplotlines.llm import LLMConfig

    config = LLMConfig(provider=provider, model=model, base_url=base_url)
    synopses = rewrite_synopses(
        episodes, show, season, config, show_format=show_format
    )

    # Save: directory → individual files, file → combined
    output_path = Path(output)
    is_dir = output.endswith("/") or output.endswith("\\") or output_path.is_dir()

    if is_dir:
        paths = _save_individual_files(synopses, episodes, season, output_path)
        print(f"Saved {len(paths)} synopsis files to {output_path}/")
    else:
        path = _save_combined_file(synopses, episodes, show, season, output_path)
        print(f"Saved combined synopsis to {path}")


def _load_from_files(file_paths: list[str], season: int) -> list[RawEpisode]:
    """Load raw descriptions from user-provided files.

    Files should contain one episode description each.
    Episode number is extracted from filename (S01E03 pattern) or sequential order.
    """
    episodes = []
    for idx, path_str in enumerate(sorted(file_paths), start=1):
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"Warning: empty file {path}, skipping", file=sys.stderr)
            continue

        # Try to extract episode number from filename
        match = re.search(r"S\d{2}E(\d{2})", path.stem, re.IGNORECASE)
        number = int(match.group(1)) if match else idx

        # Use filename stem as title fallback
        title = path.stem
        if match:
            # Remove the episode ID prefix to get a cleaner title
            title = re.sub(r"S\d{2}E\d{2}[_\-\s]*", "", title, flags=re.IGNORECASE).strip()

        episodes.append(RawEpisode(number=number, title=title, description=text))

    if not episodes:
        raise ValueError("No valid episode files found.")

    return episodes
