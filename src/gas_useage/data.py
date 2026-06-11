"""Cached Supabase access for the dashboard.

``get_db`` returns a shared :class:`Sbase` client (cached via
``st.cache_resource``) so the client and its auth session are created exactly
once per Streamlit session. Query helpers are cached with ``st.cache_data``
and invalidated by :func:`add_gas_reading` after each successful write.
"""

# Core Package
import logging

# 3rd Party Packages
import pandas as pd
import streamlit as st

# User Defined Packages
from gas_useage.db import Sbase

logger = logging.getLogger(__name__)


@st.cache_resource
def get_db() -> Sbase:
    """Return the process-wide :class:`Sbase` client (cached)."""
    logger.info("Creating Supabase client")
    return Sbase()


@st.cache_data(ttl=300)
def get_all_data(table_name: str) -> pd.DataFrame:
    """Fetch all rows from ``table_name`` as a ``DataFrame`` (cached 5 min)."""
    logger.debug("Fetching data from database: %s", table_name)
    try:
        return pd.DataFrame(get_db().query(table_name, "*"))
    except Exception:
        logger.exception("Failed to fetch data from %s", table_name)
        st.error("Failed to fetch data from the database. Please try again later.")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_prices() -> pd.DataFrame:
    """Load the gas price history as a ``DataFrame`` (cached 1 hour)."""
    return pd.DataFrame(get_db().query("gas_prices", "*"))


def add_gas_reading(reading: int) -> bool:
    """Insert a new gas reading and invalidate cached query results on success.

    Returns ``True`` if the insert succeeded, ``False`` otherwise. The cache
    is only cleared on success so a failed write does not evict known-good
    cached data.
    """
    success = get_db().add_record("gas_reading", {"gas": reading})
    if success:
        st.cache_data.clear()
    return success
