"""Protocol seam tests for the data-access boundary.

These tests verify the ``DataSource`` Protocol used to abstract the
database layer. We deliberately do NOT import :class:`gas_useage.db.Sbase`
because constructing it would call ``st.secrets`` and authenticate against
Supabase. Instead we exercise the Protocol via :class:`FakeDataSource`,
documenting the contract callers can rely on.
"""

# Core Package

# 3rd Party Packages

# User Defined Packages
from conftest import DataSource, FakeDataSource


class TestFakeDataSourceProtocol:
    def test_fake_satisfies_datasource_protocol_structurally(self) -> None:
        # GIVEN a FakeDataSource instance
        fake = FakeDataSource({"gas_reading": []})
        # WHEN we bind it to the ``DataSource`` Protocol type
        ds: DataSource = fake
        # THEN it is callable as expected (the type check passes at runtime)
        assert callable(ds.query)

    def test_returns_canned_rows_for_known_table(self) -> None:
        # GIVEN a fake stocked with one table's rows
        rows = [{"datetime": "2024-08-01", "gas_reading": 1000}]
        fake = FakeDataSource({"gas_reading_differences": rows})
        # WHEN we query the known table
        result = fake.query("gas_reading_differences", "*")
        # THEN we get the canned rows back unchanged
        assert result == rows

    def test_returns_none_for_unknown_table(self) -> None:
        # GIVEN a fake with no tables stocked
        fake = FakeDataSource({})
        # WHEN we query an unknown table
        result = fake.query("does_not_exist", "*")
        # THEN we get None back (matches the ``list[dict] | None`` contract)
        assert result is None

    def test_accepts_schema_keyword(self) -> None:
        # GIVEN a fake stocked with a single table
        rows = [{"unit_price": 4.0}]
        fake = FakeDataSource({"gas_prices": rows})
        # WHEN we query with a non-default schema
        result = fake.query("gas_prices", "*", schema="public")
        # THEN the schema keyword is accepted and rows still come back
        assert result == rows
