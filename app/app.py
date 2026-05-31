# Core Package
import sys
import os
from datetime import datetime

# 3rd Party Packages
import streamlit as st
import pandas as pd
import altair as alt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# User Defined Packages
from supadb.database import Sbase

db = Sbase()


def get_all_data(table_name: str) -> pd.DataFrame:
    """
    Fetch data from the gas_reading_differences table.
    This function retrieves all records and returns them as a DataFrame.
    """

    print(f"Fetching data from database: {table_name}")

    response = db.query(table_name, "*")

    df = pd.DataFrame(response)

    return df


def get_seasons(df: pd.DataFrame) -> list[str]:
    """
    Get unique seasons from the DataFrame.
    """

    # Ensure df is a DataFrame
    if isinstance(df, list):
        df = pd.DataFrame(df)
    return df['season_name'].unique().tolist()


def prep_dataframe(df_original: pd.DataFrame, columns_to_drop: list[str] = None) -> pd.DataFrame:
    """
    Manipulate the DataFrame to prepare it for display.
    """

    df = df_original.copy()

    # Convert 'datetime' column to date type
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime']).dt.date

    # Convert 'days' column to hours (string format: 5 days 02:45:00)
    if 'days' in df.columns:
        df['hours'] = pd.to_timedelta(df['days']).dt.total_seconds() / 3600

    # add a 'Gas_per_day' column
    if 'gas_usage' in df.columns and 'days' in df.columns:
        df['Gas_per_day'] = df['gas_usage'] / (df['hours'] / 24)

    # order the DataFrame by 'datetime' newest to oldest
    if 'datetime' in df.columns:
        df = df.sort_values(by='datetime', ascending=False)

    # Drop unnecessary columns
    if columns_to_drop is not None:
        df = df.drop(columns=columns_to_drop, errors='ignore')

    return df


def calculate_time_left_in_season(seasons: str) -> int:
    """
    Calculate the time left in the current season based on the current date.
    The seasons are expected to be in the format "YYYY/YYYY", e.g., "2023/2024".
    """

    seasons_end_date = f"{seasons.split('/')[1]}-06-30"

    days_left_in_season = (datetime.strptime(seasons_end_date, "%Y-%m-%d") - datetime.now()).days

    # Ensure days_left_in_season is not negative round up if decimal
    if days_left_in_season < 0:
        days_left_in_season = 0
    else:
        days_left_in_season = round(days_left_in_season)

    return days_left_in_season


def calculate_time_elapsed_in_season(seasons: str) -> int:
    """
    Calculate the time elapsed in the current season based on the current date.
    The seasons are expected to be in the format "YYYY/YYYY", e.g., "2023/2024".
    """

    seasons_start_date = f"{seasons.split('/')[0]}-07-01"

    days_elapsed_in_season = (datetime.now() - datetime.strptime(seasons_start_date, "%Y-%m-%d")).days

    # Ensure days_elapsed_in_season is not above 365
    if days_elapsed_in_season > 365:
        days_elapsed_in_season = 365
    else:
        days_elapsed_in_season = round(days_elapsed_in_season)

    return days_elapsed_in_season


def add_chart_data(df) -> None:
    """
    Visualize the DataFrame using Altair charts.
    This function creates a layered chart with a bar chart for 'Gas_per_day'
    :return: None
    """

    chart_data = df.copy()
    chart_data['datetime'] = pd.to_datetime(chart_data['datetime'])

    base = alt.Chart(chart_data).encode(
        x=alt.X('datetime:T', title='Date')
    )

    bar = base.mark_bar(color='#4C78A8').encode(
        y=alt.Y('Gas_per_day:Q', title='Gas per Day', axis=alt.Axis(title='Gas per Day'))
    )

    line = base.mark_line(color='#F58518', point=True).encode(
        y=alt.Y('running_sum:Q', title='Running Sum', axis=alt.Axis(title='Running Sum', orient='right'))
    )

    chart = alt.layer(bar, line).resolve_scale(
        y='independent'
    ).properties(
        width=700,
        height=400,
        title='Running Sum (Line, Right Axis) and Gas per Day (Bar, Left Axis)'
    )

    st.altair_chart(chart, use_container_width=True)


def get_season_filter(df: pd.DataFrame) -> str:
    """
    This function creates a sidebar filter to select a season.
    """

    st.sidebar.title("Seasons")

    seasons = get_seasons(df)

    # Get selected season
    current_season_filter = st.sidebar.selectbox(
        "Select a season",
        seasons,
        # Default to the latest season
        index= 0 #  len(seasons) - 1 if seasons else 0
    )

    last_year_season = st.sidebar.selectbox(
        "Select a season",
        seasons,
        # Default to the latest season
        index= 1 #  len(seasons) - 1 if seasons else 0
    )


    return current_season_filter, last_year_season


def add_new_gas_reading(df: pd.DataFrame) -> None:
    """
    This function creates a sidebar form to input a new gas reading.
    """

    # Add a button to add a new record
    st.sidebar.subheader("New Gas Reading")

    min_gas_allowed = df['gas_reading'].max() + 1 if not df.empty else 0

    with st.sidebar.form(key='add_record_form'):
        gas_reading = st.number_input("Gas Reading", min_value=min_gas_allowed, step=1)
        submit_button = st.form_submit_button(label='Add gas reading')

        if submit_button:
            new_record = {
                "gas": gas_reading,
            }

            db.add_record("gas_reading", new_record)
            st.success("Gas Reading has been Saved!")


def price_chart_data(df) -> None:

    prices = pd.DataFrame(db.query("gas_prices", "*"))

    # Ensure datetime columns are proper Timestamps
    df['datetime'] = pd.to_datetime(df['datetime'], format='mixed')
    prices['date'] = pd.to_datetime(prices['date'], format='mixed')

    df = df.sort_values('datetime')
    prices = prices.sort_values('date')

    df['prev_datetime'] = df['datetime'].shift()
    prices['prev_date'] = prices['date'].shift()

    df['hours'] = pd.to_timedelta(df['days']).dt.total_seconds() / 3600
    df['gas_per_day'] = df['gas_usage'] / (df['hours'] / 24)

    date_range = pd.date_range(df['datetime'].min().date(), df['datetime'].max().date(), freq='D')
    result = pd.DataFrame({'date': date_range})

    for _, row in df.iterrows():
        if pd.isna(row['prev_datetime']):
            continue
        prev_date = row['prev_datetime'].date()
        curr_date = row['datetime'].date()
        mask = (result['date'].dt.date > prev_date) & (result['date'].dt.date <= curr_date)
        result.loc[mask, ['gas_per_day', 'season_name']] = row[['gas_per_day', 'season_name']].values

    for _, row in prices.iterrows():
        if pd.isna(row['prev_date']):
            continue
        prev_date = row['prev_date'].date()
        curr_date = row['date'].date()
        mask = (result['date'].dt.date > prev_date) & (result['date'].dt.date <= curr_date)
        result.loc[mask, 'unit_price'] = row['unit_price']

    avg_unit_price = result['unit_price'].mean()
    is_estimated = result['unit_price'].isna()
    result['estimated_price'] = is_estimated

    result['unit_price'] = result['unit_price'].fillna(avg_unit_price)

    result['unit_fee'] = 4.38
    result['subscription_fee1'] = 2051.44 / 365  # Evidas årlige systemtarif samt målerbetaling.
    result['subscription_fee2'] = 228.00 / 365  # Andel Energi - Abonnement pr. år

    result['total_unit_fee'] = result['unit_fee'] + result['subscription_fee1'] + result['subscription_fee2']

    result['total_unit_price'] = result['unit_price'] + result['total_unit_fee']

    result['gas_cost'] = result['total_unit_price'] * result['gas_per_day']

    print(result)


    # if gas_per_day is NaN, set it to 0
    result['gas_cost'] = result['gas_cost'].fillna(avg_unit_price)

    # use Altair to visualize the price data
    # Add a selectbox to choose aggregation level
    aggregation = st.selectbox("View by", ["Day", "Month", "Total"], index=0)

    # Aggregate data based on selection
    if aggregation == "Month":
        result['month'] = result['date'].dt.to_period('M').dt.to_timestamp()
        grouped = result.groupby(['month', 'season_name'], as_index=False).agg({'gas_cost': 'sum'})
        x_field = 'month:T'
    elif aggregation == "Total":
        grouped = result.groupby(['season_name'], as_index=False).agg({'gas_cost': 'sum'})
        x_field = 'season_name:N'
    else:
        grouped = result
        x_field = 'date:T'

    # Plot the chart as a bar chart
    price_chart = alt.Chart(grouped).mark_bar().encode(
        x=alt.X(x_field, title='Date'),
        y=alt.Y('gas_cost:Q', title='Gas Cost'),
        color=alt.Color('season_name:N', title='Season')
    ).properties(
        width=700,
        height=400,
        title=f'Gas Price per {"Month" if aggregation == "Month" else "Day"} by Season'
    )

    st.altair_chart(price_chart, use_container_width=True)

def get_last_season_usage(df: pd.DataFrame, last_season: str) -> float:
    """
    Get the last row of the DataFrame for the specified season.
    """

    last_season_df = df[df['season_name'] == last_season]

    if last_season_df.empty:
        return 0.0

    last_row = last_season_df.iloc[-1]

    return last_row['running_sum'] if 'running_sum' in last_row else 0.0


def previous_season_avg_usage_to_date(df, last_seasons_name, seasons_name) -> float:

    # Extract last season data
    last_df = df[df['season_name'] == last_seasons_name].copy()

    if last_df.empty:
        return 0.0

    # convert 'datetime' to datetime
    last_df['datetime'] = pd.to_datetime(last_df['datetime'])

    # Remove timezone info if exists
    if last_df['datetime'].dt.tz is not None:
        last_df['datetime'] = last_df['datetime'].dt.tz_localize(None)

    # Add column to last_season_df showing the days into the season
    last_df['days_into_season'] = (
        last_df['datetime'] - pd.to_datetime(f"{last_seasons_name.split('/')[0]}-07-01")
    ).dt.days

    # How many days into the current season
    days_into_current_season = calculate_time_elapsed_in_season(seasons_name)

    # Filter last_season_df to get the first row where days_into_season is greater than or equal to days_into_current_season
    last_df = last_df[last_df['days_into_season'] >= days_into_current_season]

    # Get the last row of the filtered last_season_df
    last_df = last_df.sort_values(by='days_into_season', ascending=False).tail(1)

    gas_usage = last_df['running_sum'].max()
    time_elapsed = (365 - last_df['days_into_season'].max())

    avg_gas_usage_per_day = gas_usage / time_elapsed if time_elapsed > 0 else 0

    print(last_df)

    return float(avg_gas_usage_per_day)

def previous_season_total_usage(df, last_seasons_name) -> float:

    # Extract last season data
    last_season_df = df[df['season_name'] == last_seasons_name]

    if last_season_df.empty or 'running_sum' not in last_season_df.columns:
        return 0.0

    # Get the last row of the filtered last_season_df
    last_row = last_season_df.iloc[-1]

    return float(last_row['running_sum'])

def main():
    """
    Main function to run the Streamlit app.
    """

    st.title("Gas Reading Dashboard")

    df = get_all_data("gas_reading_differences")  # Fetch data from the database

    if df is None or df.empty:
        st.error("Failed to fetch data from the database. Please check your connection and query.")
        return

    # Sidebar Stuff
    seasons_filter, last_seasons_filter = get_season_filter(df)  # 1st item in the sidebar
    add_new_gas_reading(df)  # 2nd item in the sidebar

    # Filter the DataFrame based on the selected season
    filtered_df = df[df['season_name'] == seasons_filter]

    # Calculate days left and elapsed in the season
    days_left_in_season = calculate_time_left_in_season(seasons_filter)
    days_elapsed_in_season = calculate_time_elapsed_in_season(seasons_filter)

    last_year_total_gas = previous_season_total_usage(df, last_seasons_filter)
    avg_usage_last_year = last_year_total_gas / 365

    # Estimate average usage to date based on last year's data
    estimated_usage_to_date = int(avg_usage_last_year * days_elapsed_in_season)

    # First row: 1 metric
    col1 = st.columns(1)
    with col1[0]:
        st.metric(
            label="Data for Season:",
            value=seasons_filter,
            help="Season are define as the period from July 1st to June 30th of the next year."
        )

    # Second row: 3 metrics
    col2 = st.columns(3)
    with col2[0]:
        st.metric(
            label="Gas Reading",
            value=f"{filtered_df['gas_reading'].max():,}" if 'gas_reading' in filtered_df.columns and not filtered_df.empty else "0",
            help="The latest gas reading for the selected season."
        )

    with col2[1]:
        st.metric(
            label="Gas Usage in Season",
            value=f"{filtered_df['running_sum'].max():,}" if 'running_sum' in df.columns else "0",
            delta=f"{estimated_usage_to_date}",
            help="The difference between the latest and the first gas reading in the season."
        )
    with col2[2]:
        st.metric(
            label="Days left in season",
            value=days_left_in_season,
            help="The number of days left in the current season."
        )

    # Third row: 1 metric
    col3 = st.columns(1)
    with col3[0]:

        avg_gas = (
            filtered_df['running_sum'].max() / days_elapsed_in_season
            if 'running_sum' in filtered_df.columns and days_elapsed_in_season > 0
            else 0
        )

        st.metric(
            label="Average Gas Usage per Day",
            value=round(avg_gas, 2),
            help="The average gas usage per day in the current season."
        )

    # Add a graph to visualize the data
    add_chart_data(
        prep_dataframe(filtered_df)
    )

    # Add price chart
    price_chart_data(
        prep_dataframe(filtered_df)
    )

    # Display filtered data
    st.subheader("Raw Data")
    st.dataframe(
        prep_dataframe(filtered_df, columns_to_drop=['season_name', 'running_sum', 'hours']),
    )


if __name__ == "__main__":
    main()