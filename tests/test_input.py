"""Tests for input.py — loading synopses from directories."""

from pathlib import Path

import pytest

from tvplotlines.input import load_synopses_dir


@pytest.fixture
def synopses_dir(tmp_path: Path) -> Path:
    """Create a temp directory with synopsis files."""
    show_dir = tmp_path / "breaking-bad"
    show_dir.mkdir()
    (show_dir / "S01E01.txt").write_text("Walt gets diagnosed.", encoding="utf-8")
    (show_dir / "S01E02.txt").write_text("Walt and Jesse cook.", encoding="utf-8")
    (show_dir / "S01E03.txt").write_text("Krazy-8 in the basement.", encoding="utf-8")
    return show_dir


class TestShowName:
    def test_kebab_case(self, synopses_dir: Path):
        show, _, _ = load_synopses_dir(synopses_dir)
        assert show == "Breaking Bad"

    def test_underscore(self, tmp_path: Path):
        d = tmp_path / "game_of_thrones"
        d.mkdir()
        (d / "S01E01.txt").write_text("Winter is coming.", encoding="utf-8")
        show, _, _ = load_synopses_dir(d)
        assert show == "Game Of Thrones"

    def test_override(self, synopses_dir: Path):
        show, _, _ = load_synopses_dir(synopses_dir, show="BB")
        assert show == "BB"


class TestSeason:
    def test_auto_from_files(self, synopses_dir: Path):
        _, season, _ = load_synopses_dir(synopses_dir)
        assert season == 1

    def test_season_2(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "S02E01.txt").write_text("Episode 1.", encoding="utf-8")
        _, season, _ = load_synopses_dir(d)
        assert season == 2

    def test_override(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "S05E01.txt").write_text("Episode 1.", encoding="utf-8")
        _, season, _ = load_synopses_dir(d, season=5)
        assert season == 5

    def test_filters_by_season(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "S01E01.txt").write_text("S01.", encoding="utf-8")
        (d / "S01E02.txt").write_text("S01.", encoding="utf-8")
        (d / "S02E01.txt").write_text("S02.", encoding="utf-8")
        _, _, episodes = load_synopses_dir(d)
        assert len(episodes) == 2
        assert "S01E01" in episodes
        assert "S02E01" not in episodes


class TestEpisodes:
    def test_correct_keys(self, synopses_dir: Path):
        _, _, episodes = load_synopses_dir(synopses_dir)
        assert sorted(episodes.keys()) == ["S01E01", "S01E02", "S01E03"]

    def test_content(self, synopses_dir: Path):
        _, _, episodes = load_synopses_dir(synopses_dir)
        assert episodes["S01E01"] == "Walt gets diagnosed."

    def test_prefix_ignored(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "BB_S01E01.txt").write_text("text", encoding="utf-8")
        _, _, episodes = load_synopses_dir(d)
        assert "S01E01" in episodes


class TestErrors:
    def test_not_a_directory(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("not a dir", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Not a directory"):
            load_synopses_dir(f)

    def test_empty_directory(self, tmp_path: Path):
        d = tmp_path / "empty"
        d.mkdir()
        with pytest.raises(FileNotFoundError, match="No .txt files"):
            load_synopses_dir(d)

    def test_no_episode_pattern(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "episode1.txt").write_text("no pattern", encoding="utf-8")
        with pytest.raises((ValueError, FileNotFoundError)):
            load_synopses_dir(d)

    def test_duplicate_episode(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "S01E01.txt").write_text("first", encoding="utf-8")
        (d / "BB_S01E01.txt").write_text("duplicate", encoding="utf-8")
        with pytest.raises(ValueError, match="Duplicate episode ID"):
            load_synopses_dir(d)

    def test_nonexistent_directory(self):
        with pytest.raises(FileNotFoundError, match="Not a directory"):
            load_synopses_dir("/nonexistent/path")

    def test_no_files_for_season(self, tmp_path: Path):
        d = tmp_path / "show"
        d.mkdir()
        (d / "S01E01.txt").write_text("text", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="No files matching season 2"):
            load_synopses_dir(d, season=2)
