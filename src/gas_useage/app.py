"""Streamlit entry point for the gas usage dashboard.

This module wires the pure helpers in :mod:`gas_useage.transforms`,
:mod:`gas_useage.seasons`, :mod:`gas_useage.charts` and the cached
data accessors in :mod:`gas_useage.data` into the Streamlit UI. It owns the
logging configuration (set up exactly once in :func:`main`).
"""

# Core Package
import logging

# 3rd Party Packages
import pandas as pd
import streamlit as st

# User Defined Packages
from gas_useage.charts import build_cost_chart, build_usage_chart
from gas_useage.data import add_gas_reading, get_all_data, load_prices
from gas_useage.seasons import (
    calculate_time_elapsed_in_season,
    calculate_time_left_in_season,
    get_seasons,
    parse_season,
)
from gas_useage.settings import Tariffs
from gas_useage.transforms import (
    aggregate_cost,
    build_daily_cost_frame,
    prep_dataframe,
    previous_season_total_usage,
)

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging once for the Streamlit process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )


def get_season_filter(df: pd.DataFrame) -> tuple[str, str]:
    """Render the season picker in the sidebar and return (current, previous)."""
    st.sidebar.title("Seasons")

    seasons = get_seasons(df)

    current_season_filter = st.sidebar.selectbox(
        "Select a season",
        seasons,
        # Latest season first because get_seasons sorts descending.
        index=0,
    )

    # Derive previous season from the selected one (e.g. "2025/2026" -> "2024/2025").
    try:
        start_s, end_s = parse_season(current_season_filter)
        last_year_season = f"{int(start_s) - 1}/{int(end_s) - 1}"
    except ValueError:
        logger.warning("Invalid season format: %r", current_season_filter)
        st.sidebar.warning("Season format is invalid — previous-season comparison unavailable.")
        last_year_season = ""

    return current_season_filter, last_year_season


def check_password() -> bool:
    """Return True if the user is authenticated via st.secrets[auth][password].

    Shows a login form for unauthenticated visitors and a Logout button for
    authenticated ones. Fails closed if the secret is missing so the form
    stays hidden and the public dashboard continues to work.
    """
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = 0

    if st.session_state["authenticated"]:
        if st.sidebar.button("Logout", key="logout_btn"):
            st.session_state["authenticated"] = False
            st.rerun()
        return True

    if st.session_state["login_attempts"] >= 3:
        st.sidebar.error("Too many failed attempts. Refresh the page to try again.")
        return False

    try:
        expected = st.secrets["auth"]["password"]
    except (KeyError, FileNotFoundError):
        logger.warning("st.secrets missing [auth].password — write form hidden.")
        return False

    st.sidebar.subheader("Owner Login")
    entered = st.sidebar.text_input("Password", type="password", key="password_input")
    if st.sidebar.button("Login", key="login_btn"):
        if entered.strip() == expected.strip():
            st.session_state["authenticated"] = True
            st.session_state["login_attempts"] = 0
            st.rerun()
        else:
            st.session_state["login_attempts"] += 1
            remaining = 3 - st.session_state["login_attempts"]
            if remaining > 0:
                st.sidebar.error(f"Incorrect password. {remaining} attempt(s) remaining.")
            else:
                st.sidebar.error("Too many failed attempts. Refresh the page to try again.")
    return False


def add_new_gas_reading(df: pd.DataFrame) -> None:
    """Render the sidebar form for submitting a new gas reading."""
    st.sidebar.subheader("New Gas Reading")

    min_gas_allowed = df["gas_reading"].max() + 1 if not df.empty else 0

    with st.sidebar.form(key="add_record_form"):
        gas_reading = st.number_input("Gas Reading", min_value=min_gas_allowed, step=1)
        submit_button = st.form_submit_button(label="Add gas reading")

        if submit_button:
            # ``add_gas_reading`` returns False on failure (and already shows an
            # st.error via the data layer); only celebrate + rerun on success.
            if add_gas_reading(int(gas_reading)):
                st.success("Gas Reading has been Saved!")

                # Trigger a rerun so the dashboard reflects the new reading immediately.
                if hasattr(st, "rerun"):
                    st.rerun()
                else:
                    st.experimental_rerun()


def render_cost_chart(prepared_df: pd.DataFrame, tariffs: Tariffs) -> None:
    """Render the gas cost chart for the prepared per-season dataframe."""
    prices = load_prices()
    if prices.empty:
        st.warning("Gas price data is unavailable. Cost chart cannot be displayed.")
        return
    result = build_daily_cost_frame(prepared_df, prices, tariffs)

    aggregation = st.selectbox("View by", ["Day", "Month", "Total"], index=0)
    grouped, x_field = aggregate_cost(result, aggregation)

    st.altair_chart(build_cost_chart(grouped, x_field, aggregation), use_container_width=True)


def main() -> None:
    """Main function to run the Streamlit app."""
    _configure_logging()

    tariffs = Tariffs()

    st.title("Gas Reading Dashboard")

    df = get_all_data("gas_reading_differences")

    if df.empty:
        st.error("Failed to fetch data from the database. Please check your connection and query.")
        return

    # Sidebar
    seasons_filter, last_seasons_filter = get_season_filter(df)
    if check_password():
        add_new_gas_reading(df)

    # Filter the DataFrame based on the selected season and prep once.
    filtered_df = df[df["season_name"] == seasons_filter]
    prepared_df = prep_dataframe(filtered_df)

    days_left_in_season = calculate_time_left_in_season(seasons_filter)
    days_elapsed_in_season = calculate_time_elapsed_in_season(seasons_filter)

    last_year_total_gas = previous_season_total_usage(df, last_seasons_filter)
    avg_usage_last_year = last_year_total_gas / 365

    estimated_usage_to_date = int(avg_usage_last_year * days_elapsed_in_season)

    # First row: 1 metric
    col1 = st.columns(1)
    with col1[0]:
        st.metric(
            label="Data for Season:",
            value=seasons_filter,
            help="Season are define as the period from July 1st to June 30th of the next year.",
        )

    # Second row: 3 metrics
    col2 = st.columns(3)
    with col2[0]:
        st.metric(
            label="Gas Reading",
            value=f"{filtered_df['gas_reading'].max():,}"
            if not filtered_df.empty and "gas_reading" in filtered_df.columns
            else "0",
            help="The latest gas reading for the selected season.",
        )

    with col2[1]:
        st.metric(
            label="Gas Usage in Season",
            value=f"{filtered_df['running_sum'].max():,}"
            if not filtered_df.empty and "running_sum" in filtered_df.columns
            else "0",
            delta=f"{estimated_usage_to_date}",
            help="The difference between the latest and the first gas reading in the season.",
        )
    with col2[2]:
        st.metric(
            label="Days left in season",
            value=days_left_in_season,
            help="The number of days left in the current season.",
        )

    # Third row: 1 metric
    col3 = st.columns(1)
    with col3[0]:
        avg_gas = (
            filtered_df["running_sum"].max() / days_elapsed_in_season
            if not filtered_df.empty
            and "running_sum" in filtered_df.columns
            and days_elapsed_in_season > 0
            else 0
        )

        st.metric(
            label="Average Gas Usage per Day",
            value=round(avg_gas, 2),
            help="The average gas usage per day in the current season.",
        )

    # Usage chart
    st.altair_chart(
        build_usage_chart(
            prepared_df,
            full_df=df,
            current_season=seasons_filter,
            last_season=last_seasons_filter,
        ),
        use_container_width=True,
    )

    # Cost chart
    render_cost_chart(prepared_df, tariffs)

    # Display filtered data
    st.subheader("Raw Data")
    st.dataframe(
        prepared_df.drop(columns=["season_name", "running_sum", "hours"], errors="ignore"),
    )


if __name__ == "__main__":
    main()
