"""Tests for :mod:`gas_useage.seasons`.

Time-dependent helpers freeze ``gas_useage.seasons.datetime`` to a known
date so the assertions are deterministic. We subclass ``datetime`` rather
than mocking the whole module so that ``datetime.strptime`` continues to
work in the function under test.
"""

# Core Package
from datetime import datetime as _dt

# 3rd Party Packages
import pandas as pd
import pytest

# User Defined Packages
from gas_useage.seasons import (
    calculate_time_elapsed_in_season,
    calculate_time_left_in_season,
    get_seasons,
)


def _freeze_seasons_clock(monkeypatch: pytest.MonkeyPatch, year: int, month: int, day: int) -> None:
    """Freeze ``gas_useage.seasons.datetime.now`` to a fixed instant.

    Subclassing preserves ``strptime`` and other classmethods used by the
    functions under test.
    """

    frozen = _dt(year, month, day)

    class _Frozen(_dt):
        @classmethod
        def now(cls, tz: object = None) -> _dt:  # noqa: ANN001 - matches stdlib signature
            return frozen

    monkeypatch.setattr("gas_useage.seasons.datetime", _Frozen)


class TestCalculateTimeLeftInSeason:
    def test_season_in_progress_returns_positive_days(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN today is 2024-08-15 and the active season is 2024/2025
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask how many days remain
        days_left = calculate_time_left_in_season("2024/2025")
        # THEN it equals the day-delta from 2024-08-15 to 2025-06-30
        expected = (_dt(2025, 6, 30) - _dt(2024, 8, 15)).days
        assert days_left == expected

    def test_season_already_ended_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN today is well past the end of season 2024/2025
        _freeze_seasons_clock(monkeypatch, 2025, 7, 15)
        # WHEN we ask how many days remain
        # THEN the result is clamped to zero (not negative)
        assert calculate_time_left_in_season("2024/2025") == 0

    def test_season_not_yet_started_returns_more_than_a_year(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN today is before season 2025/2026 begins
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask how many days remain in a future season
        days_left = calculate_time_left_in_season("2025/2026")
        # THEN we get more than a year of days
        assert days_left > 365


class TestCalculateTimeElapsedInSeason:
    def test_mid_season_returns_positive_days(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN today is 2024-08-15 (45 days into the 2024/2025 season)
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask how many days have elapsed
        elapsed = calculate_time_elapsed_in_season("2024/2025")
        # THEN it equals the day-delta from 2024-07-01 to 2024-08-15
        expected = (_dt(2024, 8, 15) - _dt(2024, 7, 1)).days
        assert elapsed == expected

    def test_past_season_clamped_to_365(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN today is years after season 2020/2021
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask how much of an old season has elapsed
        # THEN the result is clamped to a single year of days
        assert calculate_time_elapsed_in_season("2020/2021") == 365

    def test_first_day_of_season_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN today is the first day of the 2024/2025 season
        _freeze_seasons_clock(monkeypatch, 2024, 7, 1)
        # WHEN we ask how many days have elapsed
        # THEN no days have elapsed yet
        assert calculate_time_elapsed_in_season("2024/2025") == 0


class TestGetSeasons:
    def test_returns_unique_seasons_descending(self) -> None:
        # GIVEN a DataFrame with several seasons in mixed order
        df = pd.DataFrame(
            {
                "season_name": [
                    "2022/2023",
                    "2024/2025",
                    "2022/2023",
                    "2023/2024",
                    None,
                ]
            }
        )
        # WHEN we extract the seasons
        # THEN duplicates and NaN are dropped, and the result is descending
        assert get_seasons(df) == ["2024/2025", "2023/2024", "2022/2023"]

    def test_accepts_a_list_of_dict_records(self) -> None:
        # GIVEN raw query rows passed in as a list (not yet a DataFrame)
        rows = [{"season_name": "2023/2024"}, {"season_name": "2024/2025"}]
        # WHEN we ask for the seasons
        # THEN the list path coerces to a DataFrame and returns descending names
        assert get_seasons(rows) == ["2024/2025", "2023/2024"]

    def test_empty_dataframe_returns_empty_list(self) -> None:
        # GIVEN a DataFrame with the right column but no rows
        df = pd.DataFrame({"season_name": pd.Series(dtype="object")})
        # WHEN we ask for the seasons
        # THEN we get an empty list, not an error
        assert get_seasons(df) == []
