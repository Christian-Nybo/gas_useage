"""Tests for previous-season usage helpers in :mod:`gas_useage.transforms`.

Note: ``get_last_season_usage`` referenced by the original issue spec does
not exist after the refactor merged in sub-issue #5. Its behaviour (the
final running_sum for a season) is what ``previous_season_total_usage``
already returns, so it is intentionally omitted here.
"""

# Core Package
from datetime import datetime as _dt

# 3rd Party Packages
import pandas as pd
import pytest

# User Defined Packages
from gas_useage.transforms import (
    previous_season_avg_usage_to_date,
    previous_season_total_usage,
)


def _freeze_seasons_clock(monkeypatch: pytest.MonkeyPatch, year: int, month: int, day: int) -> None:
    """Freeze ``gas_useage.seasons.datetime.now`` used by ``calculate_time_elapsed_in_season``."""

    frozen = _dt(year, month, day)

    class _Frozen(_dt):
        @classmethod
        def now(cls, tz: object = None) -> _dt:  # noqa: ANN001 - matches stdlib signature
            return frozen

    monkeypatch.setattr("gas_useage.seasons.datetime", _Frozen)


class TestPreviousSeasonTotalUsage:
    def test_returns_final_running_sum_for_requested_season(
        self, two_season_df: pd.DataFrame
    ) -> None:
        # GIVEN a frame with season 2023/2024 ending at running_sum=300.0
        # WHEN we ask for the previous-season total
        # THEN we get the LAST row's running_sum.
        # NOTE: encodes the post-#3 contract (``.iloc[-1]`` not ``.iloc[1]``).
        assert previous_season_total_usage(two_season_df, "2023/2024") == 300.0

    def test_returns_zero_for_missing_season(self, two_season_df: pd.DataFrame) -> None:
        # GIVEN a frame with no rows for the requested season
        # WHEN we ask for the previous-season total
        # THEN we get 0.0 (sentinel, not an error)
        assert previous_season_total_usage(two_season_df, "1999/2000") == 0.0

    def test_returns_zero_when_running_sum_column_absent(self) -> None:
        # GIVEN a frame for the right season but lacking the running_sum column
        df = pd.DataFrame({"season_name": ["2023/2024"]})
        # WHEN we ask for the total
        # THEN we get 0.0
        assert previous_season_total_usage(df, "2023/2024") == 0.0

    def test_returns_value_for_single_row_season(self) -> None:
        # GIVEN a one-row season
        df = pd.DataFrame({"season_name": ["2023/2024"], "running_sum": [42.5]})
        # WHEN we ask for the total
        # THEN we get that row's running_sum
        assert previous_season_total_usage(df, "2023/2024") == 42.5


class TestPreviousSeasonAvgUsageToDate:
    def test_typical_mid_season_returns_positive_average(
        self, monkeypatch: pytest.MonkeyPatch, two_season_df: pd.DataFrame
    ) -> None:
        # GIVEN today is 2024-08-15 (45-ish days into the 2024/2025 season)
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask for last season's avg usage past the current day-of-season
        avg = previous_season_avg_usage_to_date(two_season_df, "2023/2024", "2024/2025")
        # THEN it is positive: there is post-2024-08-15-equivalent data in 2023/2024
        assert avg > 0

    def test_returns_zero_when_last_season_empty(
        self, monkeypatch: pytest.MonkeyPatch, two_season_df: pd.DataFrame
    ) -> None:
        # GIVEN today is mid-season
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask for a season that does not exist in the data
        avg = previous_season_avg_usage_to_date(two_season_df, "1999/2000", "2024/2025")
        # THEN we get 0.0
        assert avg == 0.0

    def test_returns_zero_when_time_elapsed_guard_trips(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN last season's only post-cutoff row is exactly at day 365
        # AND today is at the same day-of-season
        df = pd.DataFrame(
            {
                "datetime": ["2024-06-30T00:00:00"],
                "season_name": ["2023/2024"],
                "running_sum": [300.0],
            }
        )
        _freeze_seasons_clock(monkeypatch, 2025, 6, 30)
        # WHEN we ask for the avg
        avg = previous_season_avg_usage_to_date(df, "2023/2024", "2024/2025")
        # THEN the div-by-zero guard returns 0.0 (365 - 365 = 0)
        assert avg == 0.0

    def test_handles_tz_aware_datetime(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN a tz-aware ``datetime`` column for last season
        df = pd.DataFrame(
            {
                "datetime": pd.to_datetime(
                    ["2023-10-15T00:00:00", "2024-06-15T00:00:00"], utc=True
                ),
                "season_name": ["2023/2024", "2023/2024"],
                "running_sum": [50.0, 300.0],
            }
        )
        _freeze_seasons_clock(monkeypatch, 2024, 8, 15)
        # WHEN we ask for the avg (the function strips tz internally)
        avg = previous_season_avg_usage_to_date(df, "2023/2024", "2024/2025")
        # THEN it produces a positive average without raising
        assert avg > 0
