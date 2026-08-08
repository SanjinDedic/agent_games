"""Tests for GET /config — the unauthenticated deploy-config endpoint that tells
the frontend which vocabulary to render."""

import importlib

import pytest

from backend import config


def test_config_returns_site_settings(client):
    """Public, no auth, and reports the three deploy settings."""
    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()

    assert set(data) == {"site_mode", "site_name", "site_icon"}
    assert data["site_mode"] in config.SITE_MODES
    assert data["site_name"]


def test_config_reflects_configured_mode(client, monkeypatch):
    """The response follows config.SITE_MODE rather than a hardcoded value."""
    monkeypatch.setattr(config, "SITE_MODE", "classroom")
    assert client.get("/config").json()["site_mode"] == "classroom"

    monkeypatch.setattr(config, "SITE_MODE", "competition")
    assert client.get("/config").json()["site_mode"] == "competition"


def test_invalid_site_mode_fails_at_import(monkeypatch):
    """A typo must stop the container, not render the wrong nouns for a term.

    Reloading the module re-runs its os.getenv; python-dotenv does not override
    an already-set variable, so the monkeypatched value is what config reads.
    """
    monkeypatch.setenv("SITE_MODE", "clasroom")
    with pytest.raises(RuntimeError, match="SITE_MODE must be one of"):
        importlib.reload(config)

    # A failed reload leaves the module half-initialized — restore it for every
    # later test in the session.
    monkeypatch.delenv("SITE_MODE", raising=False)
    importlib.reload(config)
    assert config.SITE_MODE in config.SITE_MODES
