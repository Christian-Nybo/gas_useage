# Core Package

# 3th Party Packages
from supabase import create_client
import streamlit as st

# User Defined Packages


class Sbase:
    def __init__(self):
        self.client = self.create_client()

    def create_client(self):
        """
        pass
        """

        # credentials to auth
        SUBABASE_URL = st.secrets["supabase"]["SUBABASE_URL"]
        SUBABASE_KEY = st.secrets["supabase"]["SUBABASE_KEY"]

        # Sign in user
        USER_EMAIL = st.secrets["supabase_auth"]["USER_EMAIL"]
        USER_PASSWORD = st.secrets["supabase_auth"]["USER_PASSWORD"]

        client = create_client(SUBABASE_URL, SUBABASE_KEY)

        client.auth.sign_in_with_password({
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })

        return client

    def query(self, table_name, query, schema="gas"):
        """
        Query the specified table with the given query.
        """

        response = self.client.schema(schema).table(table_name).select(query).execute()

        return response.data if response.data else None

    def add_record(self, table_name, data, schema="gas"):
        """
        Add a record to the specified table.
        """

        response = self.client.schema(schema).table(table_name).insert(data).execute()

        return response.data if response.data else None
