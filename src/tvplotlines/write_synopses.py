"""CLI utility for generating episode synopses from Wikipedia data.

Not part of the public library API — not exported from __init__.py.
"""
from __future__ import annotations

import re
import sys
import time
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
