"""Tests for :func:`gas_useage.app.check_password`.

``st.session_state`` is replaced with a plain dict, ``st.sidebar`` with a
MagicMock whose ``text_input`` and ``button`` return values are controlled
per-call, and ``st.secrets`` with a nested dict.  ``st.rerun`` is a no-op so
the full side-effects (state mutation) are visible after each call.
"""

# Core Package
from unittest.mock import MagicMock

# 3rd Party Packages
import pytest
import streamlit as st

# User Defined Packages
from gas_useage.app import check_password


def _make_sidebar(
    *, password: str = "", login_clicked: bool = False, logout_clicked: bool = False
) -> MagicMock:
    """Return a sidebar mock with controllable text_input and button results."""
    sidebar = MagicMock()
    sidebar.text_input.return_value = password

    def _button(label: str, **kwargs: object) -> bool:
        if label == "Login":
            return login_clicked
        if label == "Logout":
            return logout_clicked
        return False

    sidebar.button.side_effect = _button
    return sidebar


@pytest.fixture()
def state() -> dict:
    """Fresh session-state dict for each test."""
    return {}


# ---------------------------------------------------------------------------
# Fails-closed behaviour
# ---------------------------------------------------------------------------


class TestCheckPasswordFailsClosed:
    def test_missing_auth_section_returns_false(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN st.secrets has no [auth] section
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar())
        monkeypatch.setattr(st, "secrets", {})
        monkeypatch.setattr(st, "rerun", lambda: None)

        # WHEN check_password is called
        result = check_password()

        # THEN it fails closed — no form is shown, False is returned
        assert result is False

    def test_missing_password_key_in_auth_section_returns_false(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN [auth] exists but "password" key is absent
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar())
        monkeypatch.setattr(st, "secrets", {"auth": {}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        result = check_password()

        assert result is False


# ---------------------------------------------------------------------------
# Correct password / authenticated flow
# ---------------------------------------------------------------------------


class TestCheckPasswordLogin:
    def test_correct_password_sets_authenticated_true(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the correct password is entered and Login is clicked
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar(login_clicked=True, password="secret"))
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "secret"}})
        monkeypatch.setattr(st, "rerun", lambda: None)  # no-op so we can inspect state

        check_password()

        # st.rerun() is a no-op so the function returns False, but session
        # state is mutated — on the next real run the app will see authenticated=True
        assert state["authenticated"] is True
        assert state["login_attempts"] == 0

    def test_authenticated_session_returns_true(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the session is already authenticated (simulates the run after st.rerun)
        state["authenticated"] = True
        state["login_attempts"] = 0
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar(logout_clicked=False))
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "secret"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        result = check_password()

        assert result is True

    def test_whitespace_stripped_on_entered_password(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the user pastes the password with surrounding spaces
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar(login_clicked=True, password="  secret  "))
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "secret"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        check_password()

        assert state.get("authenticated") is True

    def test_wrong_password_does_not_authenticate(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN a wrong password is submitted
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar(login_clicked=True, password="wrong"))
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "secret"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        result = check_password()

        assert result is False
        assert state.get("authenticated") is not True


# ---------------------------------------------------------------------------
# Lockout behaviour
# ---------------------------------------------------------------------------


class TestCheckPasswordLockout:
    def test_attempt_counter_increments_on_each_failure(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN two consecutive wrong-password submissions
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "correct"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        for expected_count in range(1, 3):
            monkeypatch.setattr(st, "session_state", state)
            monkeypatch.setattr(st, "sidebar", _make_sidebar(login_clicked=True, password="wrong"))
            check_password()
            assert state["login_attempts"] == expected_count

    def test_lockout_fires_after_three_failures(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN three failed attempts have already been recorded
        state["authenticated"] = False
        state["login_attempts"] = 3
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar(login_clicked=True, password="correct"))
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "correct"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        result = check_password()

        # Even with the correct password, the lockout gate fires first
        assert result is False
        assert state.get("authenticated") is not True

    def test_fourth_attempt_does_not_reset_counter(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the counter is already at the lockout threshold
        state["authenticated"] = False
        state["login_attempts"] = 3
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar())
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "correct"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        check_password()

        # Counter must not decrease on subsequent calls in the locked state
        assert state["login_attempts"] >= 3


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestCheckPasswordLogout:
    def test_logout_clears_authenticated_state(
        self, state: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN the user is authenticated and clicks Logout
        state["authenticated"] = True
        state["login_attempts"] = 0
        monkeypatch.setattr(st, "session_state", state)
        monkeypatch.setattr(st, "sidebar", _make_sidebar(logout_clicked=True))
        monkeypatch.setattr(st, "secrets", {"auth": {"password": "secret"}})
        monkeypatch.setattr(st, "rerun", lambda: None)

        check_password()

        # After logout (with rerun as no-op), session is cleared
        assert state["authenticated"] is False
