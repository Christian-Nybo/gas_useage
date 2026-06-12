"""Tests for Streamlit app-layer functions in :mod:`gas_useage.app`.

``app.py`` is excluded from coverage measurement (heavy Streamlit UI code),
but these tests still verify critical behavioral contracts.
``st.*`` calls are monkeypatched so no active Streamlit session is needed.
"""

# Core Package
from unittest.mock import MagicMock, patch

# 3rd Party Packages
import pandas as pd

# User Defined Packages
from gas_useage.settings import Tariffs


class TestRenderCostChartEmptyPricesGuard:
    def test_returns_early_without_calling_build_daily_cost_frame(self) -> None:
        # GIVEN load_prices() returns an empty DataFrame (DB failure)
        # WHEN render_cost_chart is called
        # THEN build_daily_cost_frame is never called — the guard fires first

        with (
            patch("gas_useage.app.load_prices", return_value=pd.DataFrame()),
            patch("gas_useage.app.build_daily_cost_frame") as mock_bdc,
            patch("streamlit.warning"),
        ):
            from gas_useage.app import render_cost_chart

            render_cost_chart(pd.DataFrame(), Tariffs())

        mock_bdc.assert_not_called()

    def test_calls_build_daily_cost_frame_when_prices_are_available(self) -> None:
        # GIVEN load_prices() returns non-empty price data
        prices = pd.DataFrame({"date": ["2024-07-15"], "unit_price": [4.2]})
        cost_result = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-08-01"]),
                "gas_cost": [10.0],
                "season_name": ["2024/2025"],
            }
        )

        with (
            patch("gas_useage.app.load_prices", return_value=prices),
            patch("gas_useage.app.build_daily_cost_frame", return_value=cost_result) as mock_bdc,
            patch("gas_useage.app.aggregate_cost", return_value=(cost_result, "date:T")),
            patch("gas_useage.app.build_cost_chart", return_value=MagicMock()),
            patch("streamlit.selectbox", return_value="Day"),
            patch("streamlit.altair_chart"),
        ):
            from gas_useage.app import render_cost_chart

            render_cost_chart(pd.DataFrame(), Tariffs())

        mock_bdc.assert_called_once()
