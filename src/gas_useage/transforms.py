"""Pure pandas transforms used by the dashboard.

No Streamlit, no Supabase. Functions return new ``DataFrame`` instances so the
caller can rely on the input being untouched and Streamlit caching can hand the
same frame to multiple callers safely.
"""

# Core Package
import logging

# 3rd Party Packages
import pandas as pd

# User Defined Packages
from gas_useage.seasons import calculate_time_elapsed_in_season
from gas_useage.settings import Tariffs

logger = logging.getLogger(__name__)


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``hours`` and ``gas_per_day`` columns derived from ``days``/``gas_usage``.

    Returns a copy. Columns are added only when the source columns are present
    so the helper is safe to call on partially populated frames.
    """

    out = df.copy()

    if "days" in out.columns:
        out["hours"] = pd.to_timedelta(out["days"]).dt.total_seconds() / 3600

    if {"gas_usage", "hours"}.issubset(out.columns):
        out["gas_per_day"] = out["gas_usage"] / (out["hours"] / 24)

    return out


def prep_dataframe(
    df_original: pd.DataFrame, columns_to_drop: list[str] | None = None
) -> pd.DataFrame:
    """Return a display-ready copy of ``df_original``.

    Converts ``datetime`` to a date, derives ``hours``/``gas_per_day`` via
    :func:`add_derived_columns`, sorts newest first, and optionally drops the
    requested columns.
    """

    df = df_original.copy()

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"]).dt.date

    df = add_derived_columns(df)

    if "datetime" in df.columns:
        df = df.sort_values(by="datetime", ascending=False)

    if columns_to_drop is not None:
        df = df.drop(columns=columns_to_drop, errors="ignore")

    return df


def build_daily_cost_frame(
    df: pd.DataFrame, prices: pd.DataFrame, tariffs: Tariffs
) -> pd.DataFrame:
    """Build a per-day cost frame from gas readings and price history.

    The returned frame has one row per day in the reading range with columns
    ``date``, ``gas_per_day``, ``season_name``, ``unit_price``,
    ``estimated_price``, ``total_unit_fee``, ``total_unit_price`` and
    ``gas_cost``.
    """

    df = df.copy()
    prices = prices.copy()

    df["datetime"] = pd.to_datetime(df["datetime"], format="mixed")
    prices["date"] = pd.to_datetime(prices["date"], format="mixed")

    df = df.sort_values("datetime")
    prices = prices.sort_values("date")

    df["prev_datetime"] = df["datetime"].shift()
    prices["prev_date"] = prices["date"].shift()

    df["hours"] = pd.to_timedelta(df["days"]).dt.total_seconds() / 3600
    df["gas_per_day"] = df["gas_usage"] / (df["hours"] / 24)

    date_range = pd.date_range(df["datetime"].min().date(), df["datetime"].max().date(), freq="D")
    result = pd.DataFrame({"date": date_range})

    for _, row in df.iterrows():
        if pd.isna(row["prev_datetime"]):
            continue
        prev_date = row["prev_datetime"].date()
        curr_date = row["datetime"].date()
        mask = (result["date"].dt.date > prev_date) & (result["date"].dt.date <= curr_date)
        result.loc[mask, ["gas_per_day", "season_name"]] = row[
            ["gas_per_day", "season_name"]
        ].values

    for _, row in prices.iterrows():
        if pd.isna(row["prev_date"]):
            continue
        prev_date = row["prev_date"].date()
        curr_date = row["date"].date()
        mask = (result["date"].dt.date > prev_date) & (result["date"].dt.date <= curr_date)
        result.loc[mask, "unit_price"] = row["unit_price"]

    avg_unit_price = result["unit_price"].mean()
    result["estimated_price"] = result["unit_price"].isna()
    result["unit_price"] = result["unit_price"].fillna(avg_unit_price)

    result["total_unit_fee"] = tariffs.total_daily_fee
    result["total_unit_price"] = result["unit_price"] + result["total_unit_fee"]
    result["gas_cost"] = result["total_unit_price"] * result["gas_per_day"]

    logger.debug("Daily cost frame: %s", result)

    # Backfill NaN costs with the average unit price (preserves prior behaviour).
    result["gas_cost"] = result["gas_cost"].fillna(avg_unit_price)

    return result


def aggregate_cost(result: pd.DataFrame, aggregation: str) -> tuple[pd.DataFrame, str]:
    """Aggregate the per-day cost frame by ``"Day"``, ``"Month"`` or ``"Total"``.

    Returns the aggregated frame and the Altair x-encoding string to plot it
    against.
    """

    if aggregation == "Month":
        result = result.copy()
        result["month"] = result["date"].dt.to_period("M").dt.to_timestamp()
        grouped = result.groupby(["month", "season_name"], as_index=False).agg({"gas_cost": "sum"})
        return grouped, "month:T"

    if aggregation == "Total":
        grouped = result.groupby(["season_name"], as_index=False).agg({"gas_cost": "sum"})
        return grouped, "season_name:N"

    return result, "date:T"


def build_last_season_overlay(
    full_df: pd.DataFrame, last_season: str, current_season: str
) -> pd.DataFrame:
    """Slice last season from ``full_df`` and remap dates onto the current season.

    Returns a frame with only ``datetime`` and ``running_sum`` columns, sorted
    by ``datetime``.
    """

    last_df = full_df[full_df["season_name"] == last_season].copy()
    if last_df.empty:
        return last_df

    last_df["datetime"] = pd.to_datetime(last_df["datetime"])
    if last_df["datetime"].dt.tz is not None:
        last_df["datetime"] = last_df["datetime"].dt.tz_localize(None)

    last_start = pd.to_datetime(f"{last_season.split('/')[0]}-07-01")
    current_start = pd.to_datetime(f"{current_season.split('/')[0]}-07-01")
    last_df["days_into_season"] = (last_df["datetime"] - last_start).dt.days
    last_df["datetime"] = current_start + pd.to_timedelta(last_df["days_into_season"], unit="D")

    return last_df[["datetime", "running_sum"]].sort_values("datetime")


def previous_season_total_usage(df: pd.DataFrame, last_season_name: str) -> float:
    """Return the final ``running_sum`` for ``last_season_name`` (or ``0.0``).

    Uses ``.max()`` because ``running_sum`` is monotonic within a season and is
    therefore independent of Supabase row order (which is not guaranteed).
    """

    last_season_df = df[df["season_name"] == last_season_name]

    if last_season_df.empty or "running_sum" not in last_season_df.columns:
        return 0.0

    return float(last_season_df["running_sum"].max())


def previous_season_avg_usage_to_date(
    df: pd.DataFrame, last_season_name: str, current_season_name: str
) -> float:
    """Estimate the daily average usage remaining for the rest of the season.

    Uses last season's usage curve at the same point in the season as today and
    extrapolates over the remaining days. Returns ``0.0`` if last season has no
    data past the current day-of-season offset.
    """

    last_df = df[df["season_name"] == last_season_name].copy()
    if last_df.empty:
        return 0.0

    last_df["datetime"] = pd.to_datetime(last_df["datetime"])
    if last_df["datetime"].dt.tz is not None:
        last_df["datetime"] = last_df["datetime"].dt.tz_localize(None)

    last_df["days_into_season"] = (
        last_df["datetime"] - pd.to_datetime(f"{last_season_name.split('/')[0]}-07-01")
    ).dt.days

    days_into_current_season = calculate_time_elapsed_in_season(current_season_name)
    last_df = last_df[last_df["days_into_season"] >= days_into_current_season]
    if last_df.empty:
        return 0.0
    last_df = last_df.sort_values(by="days_into_season", ascending=False).tail(1)

    gas_usage = last_df["running_sum"].max()
    time_elapsed = 365 - last_df["days_into_season"].max()

    avg_gas_usage_per_day = gas_usage / time_elapsed if time_elapsed > 0 else 0

    logger.debug("Previous season avg lookup row: %s", last_df)

    return float(avg_gas_usage_per_day)
