"""Unit tests must never inherit the developer's live API credentials."""

import pytest


@pytest.fixture(autouse=True)
def isolate_provider_credentials(monkeypatch):
    for variable in ("NVIDIA_API_KEY", "TWELVE_DATA_API_KEY", "MARKETAUX_API_KEY", "SEC_USER_AGENT"):
        monkeypatch.setenv(variable, "")
