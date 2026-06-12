"""Tests for :mod:`gas_useage.data` exception-handling paths.

We test the underlying functions via ``__wrapped__`` to bypass
``@st.cache_data`` entirely, keeping the tests fast and deterministic.
``get_db`` is monkeypatched so no Supabase credentials are needed.
"""

# Core Package
from unittest.mock import MagicMock

# 3rd Party Packages
import pandas as pd
import pytest

# User Defined Packages
import gas_useage.data as data_module
from gas_useage.data import get_all_data, load_prices


class TestGetAllDataExceptionPath:
    def test_returns_empty_dataframe_when_query_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the DB client raises on query
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("connection refused")
        monkeypatch.setattr(data_module, "get_db", lambda: mock_db)

        # WHEN we call the underlying function directly (bypassing cache)
        result = get_all_data.__wrapped__("gas_reading_differences")

        # THEN an empty DataFrame is returned, not a raised exception
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_dataframe_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN the DB returns one row
        mock_db = MagicMock()
        mock_db.query.return_value = [{"gas_reading": 1000, "season_name": "2024/2025"}]
        monkeypatch.setattr(data_module, "get_db", lambda: mock_db)

        # WHEN we call the underlying function
        result = get_all_data.__wrapped__("gas_reading_differences")

        # THEN we get a populated DataFrame
        assert not result.empty
        assert "gas_reading" in result.columns


class TestLoadPricesExceptionPath:
    def test_returns_empty_dataframe_when_query_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the DB client raises on query
        mock_db = MagicMock()
        mock_db.query.side_effect = ConnectionError("service unavailable")
        monkeypatch.setattr(data_module, "get_db", lambda: mock_db)

        # WHEN we call the underlying function directly (bypassing cache)
        result = load_prices.__wrapped__()

        # THEN an empty DataFrame is returned, not a raised exception
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_dataframe_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GIVEN the DB returns price rows
        mock_db = MagicMock()
        mock_db.query.return_value = [{"date": "2024-07-15", "unit_price": 4.2}]
        monkeypatch.setattr(data_module, "get_db", lambda: mock_db)

        # WHEN we call the underlying function
        result = load_prices.__wrapped__()

        # THEN we get a populated DataFrame
        assert not result.empty
        assert "unit_price" in result.columns
