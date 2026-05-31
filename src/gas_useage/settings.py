"""Configuration models backed by pydantic-settings.

Centralises tariff constants and Supabase configuration so they can be
overridden via environment variables or a ``.env`` file without code changes.
"""

# Core Package

# 3rd Party Packages
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# User Defined Packages


class Tariffs(BaseSettings):
    """Distribution and subscription tariffs used to compute gas cost.

    Defaults reproduce the values previously hard-coded in ``app.py``:
    Evidas' yearly system tariff + meter fee and the Andel Energi yearly
    subscription, both billed daily, plus the per-cubic-metre distribution
    unit fee.
    """

    model_config = SettingsConfigDict(env_prefix="TARIFF_", env_file=".env", extra="ignore")

    unit_fee: float = Field(4.38, description="DKK/m3 distribution unit fee")
    evidas_yearly: float = Field(
        2051.44, description="Evidas yearly system tariff plus meter fee in DKK"
    )
    andel_yearly: float = Field(228.00, description="Andel Energi yearly subscription in DKK")

    @property
    def total_daily_fee(self) -> float:
        """Return the sum of the unit fee and the daily share of yearly fees."""
        return self.unit_fee + self.evidas_yearly / 365 + self.andel_yearly / 365


class SupabaseSettings(BaseSettings):
    """Supabase connection settings.

    Currently only the default schema is configurable. Credentials still come
    from ``st.secrets`` because they are managed by Streamlit's secrets store.
    """

    model_config = SettingsConfigDict(env_prefix="SUPABASE_", env_file=".env", extra="ignore")

    default_schema: str = Field("gas", description="Default Supabase schema used by Sbase")
