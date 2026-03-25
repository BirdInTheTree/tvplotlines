"""Tests for synopses_writer: Wikipedia parsing, LLM rewriting, save logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import pytest

from tvplotlines.synopses_writer import (
    fetch_season_page,
    parse_episode_table,
    rewrite_synopses,
    write_synopses,
    RawEpisode,
    _save_individual_files,
    _save_combined_file,
    _load_from_files,
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
    @patch("tvplotlines.synopses_writer.httpx.get")
    def test_title_construction(self, mock_get):
        """Verify URL params for standard show names."""
        mock_get.return_value = _make_success_response("<html>content</html>")

        result = fetch_season_page("House", 1)

        assert result == "<html>content</html>"
        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["page"] == "House_(season_1)"

    @patch("tvplotlines.synopses_writer.httpx.get")
    def test_title_construction_multi_word(self, mock_get):
        """Spaces in show name become underscores."""
        mock_get.return_value = _make_success_response()

        fetch_season_page("Breaking Bad", 2)

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["page"] == "Breaking_Bad_(season_2)"

    @patch("tvplotlines.synopses_writer.httpx.get")
    def test_wiki_title_override(self, mock_get):
        """Explicit wiki_title skips automatic construction."""
        mock_get.return_value = _make_success_response()

        fetch_season_page("House", 1, wiki_title="House_season_1")

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["page"] == "House_season_1"

    @patch("tvplotlines.synopses_writer.httpx.get")
    @patch("tvplotlines.synopses_writer.time.sleep")
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

    @patch("tvplotlines.synopses_writer.httpx.get")
    @patch("tvplotlines.synopses_writer.time.sleep")
    def test_all_titles_missing_raises(self, _mock_sleep, mock_get):
        """Both naming conventions fail → raise with helpful message."""
        mock_get.return_value = _make_error_response()

        with pytest.raises(ValueError, match="--wiki-title"):
            fetch_season_page("House", 1)


# --- rewrite_synopses ---


_SAMPLE_EPISODES = [
    RawEpisode(number=1, title="Pilot", description="A teacher collapses."),
    RawEpisode(number=2, title="Paternity", description="A teen has seizures."),
]


class TestRewriteSynopses:
    @patch("tvplotlines.llm.call_llm_parallel")
    @patch("tvplotlines.prompts.load_prompt", return_value="system prompt")
    def test_rewrite_returns_synopsis_texts(self, _mock_prompt, mock_parallel):
        """Returns list of synopsis strings from LLM JSON responses."""
        mock_parallel.return_value = [
            {"synopsis": "Full synopsis for episode 1..."},
            {"synopsis": "Full synopsis for episode 2..."},
        ]

        from tvplotlines.llm import LLMConfig
        config = LLMConfig()

        result = rewrite_synopses(_SAMPLE_EPISODES, "House", 1, config)

        assert len(result) == 2
        assert result[0] == "Full synopsis for episode 1..."
        assert result[1] == "Full synopsis for episode 2..."

    @patch("tvplotlines.llm.call_llm_parallel")
    @patch("tvplotlines.prompts.load_prompt", return_value="system prompt")
    def test_rewrite_user_messages_contain_episode_info(self, _mock_prompt, mock_parallel):
        """User messages include show, season, episode number, description."""
        mock_parallel.return_value = [{"synopsis": "x"}, {"synopsis": "y"}]

        from tvplotlines.llm import LLMConfig
        config = LLMConfig()

        rewrite_synopses(_SAMPLE_EPISODES, "House", 1, config, show_format="procedural")

        user_messages = mock_parallel.call_args[0][1]
        assert "House" in user_messages[0]
        assert "Episode: 1" in user_messages[0]
        assert "A teacher collapses." in user_messages[0]
        assert "procedural" in user_messages[0]

    @patch("tvplotlines.llm.call_llm_parallel")
    @patch("tvplotlines.prompts.load_prompt", return_value="system prompt")
    def test_rewrite_caches_system_prompt(self, _mock_prompt, mock_parallel):
        """System prompt is cached for efficiency."""
        mock_parallel.return_value = [{"synopsis": "x"}]

        from tvplotlines.llm import LLMConfig
        result = rewrite_synopses(
            [_SAMPLE_EPISODES[0]], "House", 1, LLMConfig()
        )

        assert mock_parallel.call_args.kwargs.get("cache_system") is True


# --- save helpers ---


class TestSaveFiles:
    def test_save_individual_files(self, tmp_path):
        synopses = ["Synopsis one.", "Synopsis two."]
        episodes = _SAMPLE_EPISODES

        paths = _save_individual_files(synopses, episodes, 1, tmp_path)

        assert len(paths) == 2
        assert paths[0].name == "S01E01.txt"
        assert paths[1].name == "S01E02.txt"
        assert paths[0].read_text() == "Synopsis one."
        assert paths[1].read_text() == "Synopsis two."

    def test_save_combined_file(self, tmp_path):
        synopses = ["Synopsis one.", "Synopsis two."]
        episodes = _SAMPLE_EPISODES
        out = tmp_path / "house_s01.txt"

        _save_combined_file(synopses, episodes, "House", 1, out)

        content = out.read_text()
        assert content.startswith("House, Season 1\n")
        assert "Episode 1 \u2014 Pilot" in content
        assert "Synopsis one." in content
        assert "Episode 2 \u2014 Paternity" in content
        assert "Synopsis two." in content

    def test_save_combined_compatible_with_episode_delimiter(self, tmp_path):
        """Combined file uses 'Episode N' format parseable by input_parser."""
        synopses = ["Text."]
        episodes = [RawEpisode(number=3, title="", description="raw")]
        out = tmp_path / "test.txt"

        _save_combined_file(synopses, episodes, "Show", 2, out)

        content = out.read_text()
        # No title → no dash
        assert "Episode 3\n" in content
        assert "Show, Season 2\n" in content


# --- _load_from_files ---


class TestLoadFromFiles:
    def test_load_extracts_episode_number_from_filename(self, tmp_path):
        f1 = tmp_path / "S01E03_some_title.txt"
        f1.write_text("Description three.")
        f2 = tmp_path / "S01E01_pilot.txt"
        f2.write_text("Description one.")

        episodes = _load_from_files([str(f1), str(f2)], season=1)

        assert len(episodes) == 2
        # Sorted by path, so S01E01 comes first
        assert episodes[0]["number"] == 1
        assert episodes[1]["number"] == 3

    def test_load_sequential_numbering_without_pattern(self, tmp_path):
        f1 = tmp_path / "pilot.txt"
        f1.write_text("First ep.")
        f2 = tmp_path / "second.txt"
        f2.write_text("Second ep.")

        episodes = _load_from_files([str(f1), str(f2)], season=1)

        assert episodes[0]["number"] == 1
        assert episodes[1]["number"] == 2

    def test_load_skips_empty_files(self, tmp_path):
        f1 = tmp_path / "ep1.txt"
        f1.write_text("Content.")
        f2 = tmp_path / "ep2.txt"
        f2.write_text("")

        episodes = _load_from_files([str(f1), str(f2)], season=1)
        assert len(episodes) == 1

    def test_load_no_valid_files_raises(self, tmp_path):
        f1 = tmp_path / "empty.txt"
        f1.write_text("")

        with pytest.raises(ValueError, match="No valid episode files"):
            _load_from_files([str(f1)], season=1)

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _load_from_files([str(tmp_path / "nonexistent.txt")], season=1)
