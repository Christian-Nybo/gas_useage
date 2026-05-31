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

    def test_independent_of_row_order(self) -> None:
        # GIVEN season rows in a non-chronological / shuffled order
        # (Supabase does not guarantee row order, so ``.iloc[-1]`` would be unsafe.)
        df = pd.DataFrame(
            {
                "datetime": [
                    "2024-06-15",  # chronologically last but placed first
                    "2023-07-15",
                    "2024-03-01",
                    "2023-10-15",
                ],
                "season_name": ["2023/2024"] * 4,
                "running_sum": [300.0, 5.0, 180.0, 50.0],
            }
        )
        # WHEN we ask for the previous-season total
        # THEN we still get the maximum running_sum regardless of physical order
        assert previous_season_total_usage(df, "2023/2024") == 300.0


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

    def test_returns_zero_when_filter_empties_frame(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN last season only has rows EARLIER in the season than today's
        # day-of-season offset, so the ``days_into_season >= today`` filter
        # drops every row.
        df = pd.DataFrame(
            {
                # 2023-08-15 is ~45 days into the 2023/2024 season.
                "datetime": ["2023-08-15T00:00:00"],
                "season_name": ["2023/2024"],
                "running_sum": [20.0],
            }
        )
        # Today is well past day 45 of the 2024/2025 season -> filter empties.
        _freeze_seasons_clock(monkeypatch, 2025, 4, 1)

        # Spy on ``DataFrame.sort_values`` to assert the empty-frame guard
        # short-circuits BEFORE the sort. Without the guard, ``pd.Series.max``
        # on the emptied frame silently returns NaN (no warning), and the
        # downstream ``time_elapsed > 0`` check also evaluates to False on
        # NaN -- so pre-fix and post-fix both yield 0.0 for the caller.
        # Asserting that ``sort_values`` is never reached is the discriminating
        # signal: with the guard it is not called; without the guard it is.
        original_sort_values = pd.DataFrame.sort_values
        sort_calls: list[None] = []

        def spy_sort_values(self: pd.DataFrame, *args: object, **kwargs: object) -> pd.DataFrame:
            sort_calls.append(None)
            return original_sort_values(self, *args, **kwargs)

        monkeypatch.setattr(pd.DataFrame, "sort_values", spy_sort_values)

        # WHEN we ask for the avg
        avg = previous_season_avg_usage_to_date(df, "2023/2024", "2024/2025")
        # THEN we get 0.0 AND the empty-frame guard fired before the sort step
        # (i.e. no NaN-yielding ``.max()`` was reached).
        assert avg == 0.0
        assert sort_calls == [], (
            "Expected the empty-frame guard to short-circuit before "
            "sort_values; instead the function continued past the filter."
        )

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
