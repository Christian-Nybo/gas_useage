"""Shared fixtures and stubs for the gas_useage test suite.

Provides a row factory (``make_gas_row``) and a multi-season DataFrame
fixture (``two_season_df``) shaped like the ``gas_reading_differences``
view returned by Supabase. Also defines a ``DataSource`` Protocol matching
:class:`gas_useage.db.Sbase.query` and a ``FakeDataSource`` in-memory stub
so seam tests can run without touching the supabase SDK or the network.
"""

# Core Package
from typing import Any, Protocol

# 3rd Party Packages
import pandas as pd
import pytest

# User Defined Packages


def make_gas_row(
    *,
    datetime: str = "2024-08-01T00:00:00",
    gas_reading: int = 1000,
    gas_usage: float = 10.0,
    days: str = "1 days 00:00:00",
    season_name: str = "2024/2025",
    running_sum: float = 10.0,
) -> dict[str, Any]:
    """Build a single row matching the ``gas_reading_differences`` view shape."""

    return {
        "datetime": datetime,
        "gas_reading": gas_reading,
        "gas_usage": gas_usage,
        "days": days,
        "season_name": season_name,
        "running_sum": running_sum,
    }


@pytest.fixture
def two_season_df() -> pd.DataFrame:
    """Two seasons of readings: 2023/2024 ending at 300.0, 2024/2025 starting fresh."""

    rows = [
        make_gas_row(
            datetime="2023-07-15", season_name="2023/2024", running_sum=5.0, gas_reading=900
        ),
        make_gas_row(
            datetime="2023-10-15", season_name="2023/2024", running_sum=50.0, gas_reading=950
        ),
        make_gas_row(
            datetime="2024-06-15", season_name="2023/2024", running_sum=300.0, gas_reading=1200
        ),
        make_gas_row(
            datetime="2024-08-01", season_name="2024/2025", running_sum=8.0, gas_reading=1208
        ),
        make_gas_row(
            datetime="2024-10-01", season_name="2024/2025", running_sum=40.0, gas_reading=1240
        ),
    ]
    return pd.DataFrame(rows)


# --- Protocol seam ---------------------------------------------------------
# ``Sbase.query`` already structurally conforms to ``DataSource``; using a
# Protocol here lets us swap in a fake without importing the supabase SDK.


class DataSource(Protocol):
    """Structural type matching :meth:`gas_useage.db.Sbase.query`."""

    def query(
        self, table_name: str, query: str, schema: str | None = None
    ) -> list[dict] | None: ...


class FakeDataSource:
    """In-memory stub returning canned table contents.

    Returns the rows for ``table_name`` if present, or ``None`` when the
    fake table is missing so callers can exercise both branches.
    """

    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self._tables = tables

    def query(
        self, table_name: str, query: str, schema: str | None = None
    ) -> list[dict] | None:
        return self._tables.get(table_name)
