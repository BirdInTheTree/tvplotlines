"""Tests for prior season data injection in Pass 1."""

import json
import logging

from tvplotlines.models import CastMember, Plotline, SeriesContext
from tvplotlines.pass1 import _build_user_message, _check_prior_overlap


def _make_context():
    return SeriesContext(
        format="serial",
        story_engine="A teacher builds a drug empire",
        genre="drama",
    )


def _make_prior_cast():
    return [
        CastMember(id="walt", name="Walter White", aliases=["Walt"]),
        CastMember(id="jesse", name="Jesse Pinkman", aliases=["Jesse"]),
    ]


def _make_prior_plotlines():
    return [
        Plotline(
            id="empire", name="Walt: Empire", hero="walt",
            goal="build a drug business", obstacle="morality", stakes="death",
            type="serialized", nature="plot-led", confidence="solid",
            computed_rank="A",
            span=["S01E01", "S01E07"],  # should be excluded from prior
        ),
    ]


class TestBuildUserMessage:
    def test_without_prior(self):
        msg = _build_user_message("Breaking Bad", 2, _make_context(), [("S02E01", "ep1"), ("S02E02", "ep2")])
        data = json.loads(msg)
        assert "prior_season" not in data

    def test_with_prior(self):
        msg = _build_user_message(
            "Breaking Bad", 2, _make_context(), [("S02E01", "ep1"), ("S02E02", "ep2")],
            prior_cast=_make_prior_cast(),
            prior_plotlines=_make_prior_plotlines(),
        )
        data = json.loads(msg)
        assert "prior_season" in data
        prior = data["prior_season"]
        # Cast present with correct fields
        assert len(prior["cast"]) == 2
        assert prior["cast"][0]["id"] == "walt"
        # Plotlines present with Story DNA, without span
        assert len(prior["plotlines"]) == 1
        assert prior["plotlines"][0]["id"] == "empire"
        assert "span" not in prior["plotlines"][0]
        assert "confidence" not in prior["plotlines"][0]
        assert "nature" not in prior["plotlines"][0]
        assert "devices" not in prior["plotlines"][0]

    def test_empty_prior_lists_no_injection(self):
        """Empty prior cast/plotlines should not inject prior_season block."""
        msg = _build_user_message(
            "Breaking Bad", 2, _make_context(), [("S02E01", "ep1")],
            prior_cast=[], prior_plotlines=[],
        )
        data = json.loads(msg)
        assert "prior_season" not in data


class TestPriorOverlapWarning:
    def test_warns_on_same_hero_not_continued(self, caplog):
        prior_plotlines = _make_prior_plotlines()  # empire, hero=walt
        new_plotlines = [
            Plotline(
                id="drug_business", name="Walt: Drug Business", hero="walt",
                goal="expand meth operation", obstacle="rivals", stakes="death",
                type="serialized", nature="plot-led", confidence="solid",
                computed_rank="A",
            ),
        ]
        with caplog.at_level(logging.WARNING):
            _check_prior_overlap(new_plotlines, prior_plotlines)
        assert "empire" in caplog.text
        assert "drug_business" in caplog.text

    def test_no_warning_when_id_reused(self, caplog):
        prior_plotlines = _make_prior_plotlines()  # empire, hero=walt
        new_plotlines = [
            Plotline(
                id="empire", name="Walt: Empire", hero="walt",
                goal="expand empire", obstacle="DEA", stakes="prison",
                type="serialized", nature="plot-led", confidence="solid",
                computed_rank="A",
            ),
        ]
        with caplog.at_level(logging.WARNING):
            _check_prior_overlap(new_plotlines, prior_plotlines)
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_records == []
