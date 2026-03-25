"""Tests for Wikipedia parsing in write_synopses."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import pytest

from tvplotlines.write_synopses import (
    fetch_season_page,
    parse_episode_table,
    RawEpisode,
)

FIXTURES = Path(__file__).parent / "fixtures"


# --- parse_episode_table ---


class TestParseEpisodeTable:
    @pytest.fixture()
    def house_html(self) -> str:
        return (FIXTURES / "wikipedia_house_s01.html").read_text()

    def test_parse_episode_table_house_s01(self, house_html):
        episodes = parse_episode_table(house_html)

        assert len(episodes) == 22

        for ep in episodes:
            assert ep["title"], f"Episode {ep['number']} has empty title"
            assert ep["description"], f"Episode {ep['number']} has empty description"

        # Sequential numbering
        numbers = [ep["number"] for ep in episodes]
        assert numbers == list(range(1, 23))

        # Spot-check known titles
        assert episodes[0]["title"] == "Pilot"
        assert episodes[1]["title"] == "Paternity"

    def test_parse_episode_table_no_descriptions(self):
        """Table with episode rows but no expand-child description rows."""
        html = """
        <table class="wikitable wikiepisodetable">
        <tr><th>No.</th><th>Title</th></tr>
        <tr class="vevent module-episode-list-row">
            <th>1</th>
            <td class="summary">"Pilot"</td>
        </tr>
        <tr class="vevent module-episode-list-row">
            <th>2</th>
            <td class="summary">"Second"</td>
        </tr>
        </table>
        """
        with pytest.raises(ValueError, match="No episode descriptions found"):
            parse_episode_table(html)

    def test_parse_episode_table_no_table(self):
        """HTML without any episode table."""
        with pytest.raises(ValueError, match="No episode table found"):
            parse_episode_table("<div>No table here</div>")


# --- fetch_season_page ---


def _make_success_response(html: str = "<div>ok</div>") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"parse": {"text": {"*": html}}}
    resp.raise_for_status.return_value = None
    return resp


def _make_error_response() -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"error": {"code": "missingtitle", "info": "not found"}}
    resp.raise_for_status.return_value = None
    return resp


class TestFetchSeasonPage:
    @patch("tvplotlines.write_synopses.httpx.get")
    def test_title_construction(self, mock_get):
        """Verify URL params for standard show names."""
        mock_get.return_value = _make_success_response("<html>content</html>")

        result = fetch_season_page("House", 1)

        assert result == "<html>content</html>"
        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["page"] == "House_(season_1)"

    @patch("tvplotlines.write_synopses.httpx.get")
    def test_title_construction_multi_word(self, mock_get):
        """Spaces in show name become underscores."""
        mock_get.return_value = _make_success_response()

        fetch_season_page("Breaking Bad", 2)

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["page"] == "Breaking_Bad_(season_2)"

    @patch("tvplotlines.write_synopses.httpx.get")
    def test_wiki_title_override(self, mock_get):
        """Explicit wiki_title skips automatic construction."""
        mock_get.return_value = _make_success_response()

        fetch_season_page("House", 1, wiki_title="House_season_1")

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["page"] == "House_season_1"

    @patch("tvplotlines.write_synopses.httpx.get")
    @patch("tvplotlines.write_synopses.time.sleep")
    def test_fallback_on_missing_page(self, _mock_sleep, mock_get):
        """First title 404 → tries second naming convention."""
        mock_get.side_effect = [
            _make_error_response(),
            _make_success_response("<html>found</html>"),
        ]

        result = fetch_season_page("House", 1)

        assert result == "<html>found</html>"
        assert mock_get.call_count == 2
        # Second call uses underscore (no parens) convention
        second_call_params = mock_get.call_args_list[1].kwargs.get("params") or \
            mock_get.call_args_list[1][1].get("params")
        assert second_call_params["page"] == "House_season_1"

    @patch("tvplotlines.write_synopses.httpx.get")
    @patch("tvplotlines.write_synopses.time.sleep")
    def test_all_titles_missing_raises(self, _mock_sleep, mock_get):
        """Both naming conventions fail → raise with helpful message."""
        mock_get.return_value = _make_error_response()

        with pytest.raises(ValueError, match="--wiki-title"):
            fetch_season_page("House", 1)
