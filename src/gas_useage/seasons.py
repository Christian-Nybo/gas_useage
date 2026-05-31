"""Helpers for working with gas reading seasons.

A season runs from July 1st of year Y to June 30th of year Y+1 and is
identified by the string ``"Y/Y+1"`` (e.g. ``"2024/2025"``).
"""

# Core Package
import logging
from datetime import datetime

# 3rd Party Packages
import pandas as pd

# User Defined Packages

logger = logging.getLogger(__name__)


def get_seasons(df: pd.DataFrame) -> list[str]:
    """Return the unique season names in ``df`` sorted descending.

    Sorting descending guarantees that index ``0`` of the returned list is the
    most recent season, which the sidebar selectbox uses as its default value.
    """

    if isinstance(df, list):
        df = pd.DataFrame(df)

    return sorted(df["season_name"].dropna().unique().tolist(), reverse=True)


def calculate_time_left_in_season(season: str) -> int:
    """Return the number of whole days remaining in ``season``.

    ``season`` must be formatted as ``"YYYY/YYYY"`` (e.g. ``"2023/2024"``).
    The value is clamped to ``0`` for seasons that have already ended.
    """

    seasons_end_date = f"{season.split('/')[1]}-06-30"

    days_left_in_season = (datetime.strptime(seasons_end_date, "%Y-%m-%d") - datetime.now()).days

    if days_left_in_season < 0:
        return 0
    return round(days_left_in_season)


def calculate_time_elapsed_in_season(season: str) -> int:
    """Return the number of whole days elapsed since ``season`` began.

    ``season`` must be formatted as ``"YYYY/YYYY"`` (e.g. ``"2023/2024"``).
    The value is clamped to ``365`` for seasons that have already ended.
    """

    seasons_start_date = f"{season.split('/')[0]}-07-01"

    days_elapsed_in_season = (
        datetime.now() - datetime.strptime(seasons_start_date, "%Y-%m-%d")
    ).days

    if days_elapsed_in_season > 365:
        return 365
    return round(days_elapsed_in_season)
