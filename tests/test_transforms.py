"""Tests for :mod:`gas_useage.transforms`.

Covers ``prep_dataframe``, ``add_derived_columns``, ``build_daily_cost_frame``,
``aggregate_cost`` and ``build_last_season_overlay``. These are all pure
pandas helpers — no Streamlit, no Supabase.
"""

# Core Package

# 3rd Party Packages
import pandas as pd
import pytest
from conftest import make_gas_row

# User Defined Packages
from gas_useage.settings import Tariffs
from gas_useage.transforms import (
    add_derived_columns,
    aggregate_cost,
    build_daily_cost_frame,
    build_last_season_overlay,
    prep_dataframe,
)


class TestPrepDataframe:
    def test_converts_datetime_and_sorts_newest_first(self) -> None:
        # GIVEN a frame with two readings in chronological order
        df = pd.DataFrame(
            [
                make_gas_row(datetime="2024-07-01T00:00:00", gas_reading=100, running_sum=1.0),
                make_gas_row(datetime="2024-08-01T00:00:00", gas_reading=110, running_sum=11.0),
            ]
        )
        # WHEN we prep the frame
        out = prep_dataframe(df)
        # THEN datetime is a date and rows are sorted newest first
        assert out.iloc[0]["gas_reading"] == 110
        assert str(out.iloc[0]["datetime"]) == "2024-08-01"
        assert {"hours", "gas_per_day"}.issubset(out.columns)

    def test_drops_requested_columns(self) -> None:
        # GIVEN a frame with columns we don't want to display
        df = pd.DataFrame([make_gas_row()])
        # WHEN we prep and ask to drop ``season_name``
        out = prep_dataframe(df, columns_to_drop=["season_name"])
        # THEN that column is gone
        assert "season_name" not in out.columns

    def test_drops_columns_ignores_missing_names(self) -> None:
        # GIVEN a frame and a drop list referencing a column that does not exist
        df = pd.DataFrame([make_gas_row()])
        # WHEN we prep with a non-existent column in the drop list
        out = prep_dataframe(df, columns_to_drop=["does_not_exist"])
        # THEN nothing raises and the frame is returned untouched (shape-wise)
        assert len(out) == 1

    def test_handles_frame_without_datetime(self) -> None:
        # GIVEN a partial frame missing the datetime column
        df = pd.DataFrame({"gas_usage": [1.0, 2.0], "days": ["1 days", "2 days"]})
        # WHEN we prep it
        out = prep_dataframe(df)
        # THEN no datetime branch fires and derived cols are still added
        assert "hours" in out.columns
        assert "gas_per_day" in out.columns

    def test_handles_frame_without_days(self) -> None:
        # GIVEN a frame missing ``days``
        df = pd.DataFrame({"datetime": ["2024-08-01"], "gas_usage": [5.0]})
        # WHEN we prep it
        out = prep_dataframe(df)
        # THEN ``hours``/``gas_per_day`` are not derived because their source is absent
        assert "hours" not in out.columns
        assert "gas_per_day" not in out.columns

    def test_does_not_mutate_input(self) -> None:
        # GIVEN a frame the caller still holds
        df = pd.DataFrame([make_gas_row()])
        original_columns = list(df.columns)
        # WHEN we prep it
        _ = prep_dataframe(df, columns_to_drop=["season_name"])
        # THEN the input is unchanged
        assert list(df.columns) == original_columns


class TestAddDerivedColumns:
    def test_adds_hours_and_gas_per_day_when_inputs_present(self) -> None:
        # GIVEN a frame with both ``days`` and ``gas_usage``
        df = pd.DataFrame({"days": ["1 days 00:00:00"], "gas_usage": [12.0]})
        # WHEN we add derived columns
        out = add_derived_columns(df)
        # THEN ``hours`` is 24 and ``gas_per_day`` equals the original usage
        assert out["hours"].iloc[0] == pytest.approx(24.0)
        assert out["gas_per_day"].iloc[0] == pytest.approx(12.0)

    def test_skips_gas_per_day_when_gas_usage_absent(self) -> None:
        # GIVEN a frame with ``days`` but no ``gas_usage``
        df = pd.DataFrame({"days": ["1 days 00:00:00"]})
        # WHEN we add derived columns
        out = add_derived_columns(df)
        # THEN ``hours`` is derived but ``gas_per_day`` is not
        assert "hours" in out.columns
        assert "gas_per_day" not in out.columns


class TestBuildLastSeasonOverlay:
    def test_remaps_last_season_dates_onto_current_season(self) -> None:
        # GIVEN a frame holding rows from a previous season
        df = pd.DataFrame(
            [
                make_gas_row(datetime="2023-07-15", season_name="2023/2024", running_sum=5.0),
                make_gas_row(datetime="2023-10-15", season_name="2023/2024", running_sum=50.0),
            ]
        )
        # WHEN we build the overlay onto the current season
        out = build_last_season_overlay(df, "2023/2024", "2024/2025")
        # THEN the years are shifted forward by one but the day-of-season is preserved
        assert out.iloc[0]["datetime"] == pd.Timestamp("2024-07-15")
        assert out.iloc[1]["datetime"] == pd.Timestamp("2024-10-15")
        assert list(out.columns) == ["datetime", "running_sum"]

    def test_returns_empty_when_last_season_absent(self) -> None:
        # GIVEN a frame with no rows for the requested last season
        df = pd.DataFrame([make_gas_row(season_name="2024/2025")])
        # WHEN we build the overlay
        out = build_last_season_overlay(df, "2022/2023", "2024/2025")
        # THEN we get back an empty frame, not an error
        assert out.empty

    def test_strips_tz_when_datetime_is_tz_aware(self) -> None:
        # GIVEN a tz-aware ``datetime`` column for last season
        df = pd.DataFrame(
            {
                "datetime": pd.to_datetime(
                    ["2023-07-15T00:00:00", "2023-10-15T00:00:00"], utc=True
                ),
                "season_name": ["2023/2024", "2023/2024"],
                "running_sum": [5.0, 50.0],
            }
        )
        # WHEN we build the overlay (which strips tz internally)
        out = build_last_season_overlay(df, "2023/2024", "2024/2025")
        # THEN the resulting timestamps are tz-naive
        assert out["datetime"].dt.tz is None


class TestBuildDailyCostFrame:
    def test_produces_one_row_per_day_with_expected_columns(self) -> None:
        # GIVEN two readings five days apart and a single unit-price entry
        df = pd.DataFrame(
            [
                make_gas_row(
                    datetime="2024-08-01T00:00:00",
                    gas_usage=0.0,
                    days="0 days 00:00:00",
                    running_sum=0.0,
                ),
                make_gas_row(
                    datetime="2024-08-06T00:00:00",
                    gas_usage=10.0,
                    days="5 days 00:00:00",
                    running_sum=10.0,
                ),
            ]
        )
        prices = pd.DataFrame({"date": ["2024-07-15", "2024-08-10"], "unit_price": [2.0, 3.0]})
        tariffs = Tariffs()
        # WHEN we build the daily cost frame
        out = build_daily_cost_frame(df, prices, tariffs)
        # THEN it spans the reading range and carries the expected columns
        assert len(out) == 6  # 2024-08-01 through 2024-08-06 inclusive
        for col in [
            "date",
            "gas_per_day",
            "season_name",
            "unit_price",
            "estimated_price",
            "total_unit_fee",
            "total_unit_price",
            "gas_cost",
        ]:
            assert col in out.columns


class TestAggregateCost:
    def _result_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-08-01", "2024-08-15", "2024-09-01", "2024-09-15"]),
                "season_name": ["2024/2025"] * 4,
                "gas_cost": [1.0, 2.0, 3.0, 4.0],
            }
        )

    def test_day_aggregation_returns_frame_untouched(self) -> None:
        # GIVEN a per-day cost frame
        df = self._result_frame()
        # WHEN we aggregate by day
        grouped, x_field = aggregate_cost(df, "Day")
        # THEN the frame is returned as-is with the date x-encoding
        assert x_field == "date:T"
        assert len(grouped) == 4

    def test_month_aggregation_sums_per_month(self) -> None:
        # GIVEN a per-day cost frame spanning two months
        df = self._result_frame()
        # WHEN we aggregate by month
        grouped, x_field = aggregate_cost(df, "Month")
        # THEN we get two rows with summed costs and the month x-encoding
        assert x_field == "month:T"
        assert len(grouped) == 2
        assert grouped["gas_cost"].sum() == pytest.approx(10.0)

    def test_total_aggregation_collapses_to_one_row_per_season(self) -> None:
        # GIVEN a per-day cost frame in a single season
        df = self._result_frame()
        # WHEN we aggregate to a total
        grouped, x_field = aggregate_cost(df, "Total")
        # THEN we get one row per season with the season x-encoding
        assert x_field == "season_name:N"
        assert len(grouped) == 1
        assert grouped["gas_cost"].iloc[0] == pytest.approx(10.0)
