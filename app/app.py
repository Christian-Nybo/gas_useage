# Core Package
import sys
import os
from datetime import datetime, timedelta

# 3th Party Packages
import streamlit as st
import pandas as pd
import altair as alt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# User Defined Packages
from supadb.database import Sbase

db = Sbase()

def get_data():
    """
    Fetch data from the gas_reading_differences table.
    """

    print("Fetching data from database...")

    response = db.query("gas_reading_differences", "*")

    df = pd.DataFrame(response)

    return df # Return the data as a DataFrame

def add_record_to_db(table_name, data):
    """
    Add a new record to the gas_reading_differences table.
    """

    response = db.add_record(table_name, data)

    if response:
        print("Record added successfully.")
    else:
        print("Failed to add record.")

def get_seasons(df):
    # Ensure df is a DataFrame
    if isinstance(df, list):
        df = pd.DataFrame(df)
    return df['season_name'].unique().tolist()

def prep_dataframe(df, columns_to_drop=None):

    # Convert 'datetime' column to date type
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime']).dt.date

    # Convert 'days' column to hours
    # days are in string format: 5 days 02:45:00
    if 'days' in df.columns:
        df['hours'] = pd.to_timedelta(df['days']).dt.total_seconds() / 3600

    # add a 'Gas_per_day' column - Dividing Gas_usage by days
    if 'gas_usage' in df.columns and 'days' in df.columns:
        df['Gas_per_day'] = df['gas_usage'] / (df['hours'] / 24)

    # order the DataFrame by 'datetime' newest to oldest
    if 'datetime' in df.columns:
        df = df.sort_values(by='datetime', ascending=False)

    # Drop unnecessary columns
    if columns_to_drop is not None:
        df = df.drop(columns=columns_to_drop, errors='ignore')

    return df

def calculate_time_left_in_season(seasons):
    """
    Calculate the time left in the current season based on the current date.
    """

    seasons_end_date = f"{seasons.split('/')[1]}-06-30"

    days_left_in_season = (datetime.strptime(seasons_end_date, "%Y-%m-%d") - datetime.now()).days

    # Ensure days_left_in_season is not negative round up if decimal
    if days_left_in_season < 0:
        days_left_in_season = 0
    else:
        days_left_in_season = round(days_left_in_season)

    return days_left_in_season

def calculate_time_elapsed_in_season(seasons):

    seasons_start_date = f"{seasons.split('/')[0]}-07-01"

    days_elapsed_in_season = (datetime.now() - datetime.strptime(seasons_start_date, "%Y-%m-%d")).days

    # Ensure days_elapsed_in_season is not above 365
    if days_elapsed_in_season > 365:
        days_elapsed_in_season = 365
    else:
        days_elapsed_in_season = round(days_elapsed_in_season)

    return days_elapsed_in_season

def add_chart_data(df):
    if 'datetime' in df.columns:
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

def main():
    """
    Main function to run the Streamlit app.
    """

    st.title("Gas Reading Dashboard")

    df = get_data()  # Fetch data from the database

    if df is None:
        st.error("Failed to fetch data from the database. Please check your connection and query.")
        return

    seasons = get_seasons(df)

    st.sidebar.title("Seasons")

    # Get selected season
    seasons_filter = st.sidebar.selectbox(
        "Select a season",
        seasons,
        # Default to the latest season
        index= len(seasons) - 1 if seasons else 0
    )

    # Filter the DataFrame based on the selected season
    filtered_df = df[df['season_name'] == seasons_filter]

    # Calculate days left and elapsed in the season
    days_left_in_season = calculate_time_left_in_season(seasons_filter)
    days_elapsed_in_season = calculate_time_elapsed_in_season(seasons_filter)

    col1 = st.columns(1)
    with col1[0]:
        st.metric(
            label="Data for Season:",
            value=seasons_filter)

    # Second row: 3 metrics
    col2 = st.columns(3)
    with col2[0]:
        st.metric(label="Latest Gas Reading",
                  value=f"{filtered_df['gas_reading'].max():,}" if 'running_sum' in df.columns else "0"
                  )

    with col2[1]:
        st.metric(label="Gas Usage in Season",
                  value=f"{filtered_df['running_sum'].max():,}" if 'running_sum' in df.columns else "0"
                  )
    with col2[2]:
        st.metric(label="Days left in season",
                  value=days_left_in_season
                  )

    # Third row: 1 metric
    col3 = st.columns(1)
    with col3[0]:
        st.metric(
            label="Average Gas Usage per Day",
            value=filtered_df[
                      'running_sum'].max() / days_elapsed_in_season if 'running_sum' in filtered_df.columns and days_elapsed_in_season > 0 else 0
        )

    # Add a graph to visualize the data
    add_chart_data(
        prep_dataframe(filtered_df)
    )

    # Display filtered data
    st.subheader("Raw Data")
    st.dataframe(
        prep_dataframe(filtered_df, columns_to_drop=['season_name', 'running_sum', 'hours']),
    )

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

            print(new_record)

            add_record_to_db("gas_reading", new_record)
            st.success("Gas Reading has been Saved!")

if __name__ == "__main__":
    main()