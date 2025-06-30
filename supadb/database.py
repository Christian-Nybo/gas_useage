# Core Package

# 3th Party Packages
from supabase import create_client
import streamlit as st

# User Defined Packages


class Sbase:
    def __init__(self):
        self.url = st.secrets["supabase"]["url"]
        self.key = st.secrets["supabase"]["key"]

        self.client = create_client(self.url, self.key)

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

def class_test():
    """
    Test function to verify the connection to Supabase.
    """

    db = Sbase()
    response = db.query("gas_reading_differences", "*")

    print(response)  # Print the first record from the response

if __name__ == "__main__":
    class_test()