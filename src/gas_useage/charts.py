"""Altair chart builders.

All builders return ``alt.Chart`` (or a layered chart) instances. None of them
call ``st.altair_chart``; rendering is the caller's responsibility.
"""

# Core Package
import logging

# 3rd Party Packages
import altair as alt
import pandas as pd

# User Defined Packages
from gas_useage.transforms import build_last_season_overlay

logger = logging.getLogger(__name__)


def build_usage_chart(
    df: pd.DataFrame,
    full_df: pd.DataFrame | None = None,
    current_season: str | None = None,
    last_season: str | None = None,
) -> alt.LayerChart:
    """Build the layered gas usage chart.

    The chart shows a bar for ``gas_per_day`` and a line for ``running_sum`` of
    the selected season. When ``full_df``, ``current_season`` and ``last_season``
    are all provided (and differ) a dashed overlay line is added showing last
    season's ``running_sum`` aligned by day-of-season.
    """

    chart_data = df.copy()
    chart_data["datetime"] = pd.to_datetime(chart_data["datetime"])

    base = alt.Chart(chart_data).encode(x=alt.X("datetime:T", title="Date"))

    bar = base.mark_bar(color="#4C78A8").encode(
        y=alt.Y("gas_per_day:Q", title="Gas per Day", axis=alt.Axis(title="Gas per Day"))
    )

    line = base.mark_line(color="#F58518", point=True).encode(
        y=alt.Y(
            "running_sum:Q",
            title="Running Sum",
            axis=alt.Axis(title="Running Sum", orient="right"),
        )
    )

    layers: list[alt.Chart] = [bar, line]
    if full_df is not None and current_season and last_season and last_season != current_season:
        overlay = build_last_season_overlay(full_df, last_season, current_season)
        if not overlay.empty:
            line_last = (
                alt.Chart(overlay)
                .mark_line(color="#F58518", strokeDash=[4, 4], opacity=0.5)
                .encode(
                    x=alt.X("datetime:T"),
                    y=alt.Y("running_sum:Q", axis=alt.Axis(title="Running Sum", orient="right")),
                )
            )
            layers.append(line_last)

    return (
        alt.layer(*layers)
        .resolve_scale(y="independent")
        .properties(
            width=700,
            height=400,
            title="Running Sum (Solid: Current, Dashed: Last Season) and Gas per Day",
        )
    )


def build_cost_chart(grouped: pd.DataFrame, x_field: str, aggregation: str) -> alt.Chart:
    """Build the gas cost bar chart for the given aggregation level."""

    return (
        alt.Chart(grouped)
        .mark_bar()
        .encode(
            x=alt.X(x_field, title="Date"),
            y=alt.Y("gas_cost:Q", title="Gas Cost"),
            color=alt.Color("season_name:N", title="Season"),
        )
        .properties(
            width=700,
            height=400,
            title=f"Gas Price per {'Month' if aggregation == 'Month' else 'Day'} by Season",
        )
    )
