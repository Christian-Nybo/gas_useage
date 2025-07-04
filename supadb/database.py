# Core Package

# 3th Party Packages
from supabase import create_client
import streamlit as st

# User Defined Packages


class Sbase:
    """A wrapper class for Supabase database operations in Streamlit applications."""

    def __init__(self, default_schema: str = "gas") -> None:
        self.default_schema = default_schema
        self.client = self.create_client()

    def create_client(self):
        """
        Create and authenticate a Supabase client instance.

        Returns:
            supabase.Client: Authenticated Supabase client
        """

        # credentials to auth
        SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]

        # Sign in user
        USER_EMAIL = st.secrets["supabase_auth"]["USER_EMAIL"]
        USER_PASSWORD = st.secrets["supabase_auth"]["USER_PASSWORD"]

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        client.auth.sign_in_with_password({
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })

        return client

    def query(self, table_name, query, schema="gas"):
        """
        Query the specified table with the given query.

        Args:
            table_name (str): The name of the table
            query (str): The query to execute
            schema (str, optional): Database schema. Defaults to "None"

        Returns:
            list or None: Query results or None if no data/error
        """

        response = self.client.schema(schema).table(table_name).select(query).execute()

        return response.data if response.data else None

    def add_record(self, table_name, data, schema=None):
        """
        Add a record to the specified table.

        Args:
            table_name (str): The name of the table
            data (dict): Data to insert
            schema (str, optional): Database schema. Defaults to "None"

        Returns:
            dict or None: Inserted data or None if operation failed
        """
        if not table_name or not data:
            st.error("Table name and data are required")
            return None

        schema = schema or self.default_schema

        try:
            response = self.client.schema(schema).table(table_name).insert(data).execute()
            return response.data if response.data else None
        except Exception as e:
            st.error(f"Failed to add record: {str(e)}")
            return None
