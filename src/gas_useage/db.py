# Core Package
import logging

# 3rd Party Packages
import streamlit as st
from supabase import Client, create_client

# User Defined Packages
from gas_useage.settings import SupabaseSettings

logger = logging.getLogger(__name__)


class Sbase:
    """A wrapper class for Supabase database operations in Streamlit applications."""

    def __init__(self, default_schema: str | None = None) -> None:
        self.default_schema = default_schema or SupabaseSettings().default_schema
        self.client: Client = self.create_client()

    def create_client(self) -> Client:
        """
        Create and authenticate a Supabase client instance.

        Reads Supabase URL/key and user credentials from ``st.secrets`` and
        signs in with email/password.

        Returns:
            supabase.Client: Authenticated Supabase client
        """

        # credentials to auth
        SUPABASE_URL: str = st.secrets["supabase"]["SUPABASE_URL"]
        SUPABASE_KEY: str = st.secrets["supabase"]["SUPABASE_KEY"]

        # Sign in user
        USER_EMAIL: str = st.secrets["supabase_auth"]["USER_EMAIL"]
        USER_PASSWORD: str = st.secrets["supabase_auth"]["USER_PASSWORD"]

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        client.auth.sign_in_with_password({"email": USER_EMAIL, "password": USER_PASSWORD})

        return client

    def query(self, table_name: str, query: str, schema: str | None = None) -> list[dict]:
        """
        Query the specified table with the given query.

        Args:
            table_name: The name of the table.
            query: The Supabase select expression (e.g. ``"*"``).
            schema: Database schema. Defaults to ``self.default_schema``.

        Returns:
            list[dict]: Query results, or an empty list when the table has no
            matching rows. Never returns ``None``.
        """

        schema = schema or self.default_schema
        response = self.client.schema(schema).table(table_name).select(query).execute()
        return response.data or []

    def add_record(
        self, table_name: str, data: dict, schema: str | None = None
    ) -> list[dict] | None:
        """
        Add a record to the specified table.

        Args:
            table_name: The name of the table.
            data: Data to insert.
            schema: Database schema. Defaults to ``self.default_schema``.

        Returns:
            list[dict] | None: Inserted rows, or ``None`` if validation failed
            or the insert raised an exception.
        """
        if not table_name or not data:
            st.error("Table name and data are required")
            return None

        schema = schema or self.default_schema

        try:
            response = self.client.schema(schema).table(table_name).insert(data).execute()
            return response.data or None
        except Exception as e:
            st.error(f"Failed to add record: {e!s}")
            return None
