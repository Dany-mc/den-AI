"""Tests for the guided auth flow (probe mocked, config in a tmp dir)."""

import json
import os
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import denai.auth as auth
from denai.web.server import create_app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DENAI_CONFIG_DIR", str(tmp_path))
    # make sure no real key leaks in, and that whatever the flow sets is undone
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sentinel")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setattr(auth, "probe", lambda model: (True, "ok"))
    return TestClient(create_app())


def test_status_unconfigured(client: TestClient) -> None:
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    assert res.json() == {"configured": False, "source": None}


def test_save_key_rejects_garbage(client: TestClient) -> None:
    res = client.post("/api/auth/key", json={"api_key": "not-a-key"})
    assert res.status_code == 400


def test_save_key_persists_and_configures(client: TestClient, tmp_path: Path) -> None:
    res = client.post("/api/auth/key", json={"api_key": "sk-ant-test123"})
    assert res.status_code == 200
    assert res.json()["source"] == "stored_key"

    config = tmp_path / "config.json"
    assert json.loads(config.read_text())["api_key"] == "sk-ant-test123"
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-test123"

    res = client.get("/api/auth/status")
    assert res.json() == {"configured": True, "source": "stored_key"}


def test_subscription_test_marks_ok(client: TestClient) -> None:
    res = client.post("/api/auth/test")
    assert res.status_code == 200
    assert res.json()["source"] == "subscription"
    assert client.get("/api/auth/status").json()["configured"] is True


def test_probe_failure_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth, "probe", lambda model: (False, "401 nope"))
    assert client.post("/api/auth/test").status_code == 401
    assert client.post("/api/auth/key", json={"api_key": "sk-ant-bad"}).status_code == 401
