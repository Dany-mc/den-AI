"""Local credential handling for den-AI.

den-AI talks to Claude through the Claude Code runtime, which accepts either
an ANTHROPIC_API_KEY or a Claude subscription login. This module adds a thin
local config (~/.denai/config.json, chmod 600) so the key can be entered once
— e.g. from den-AI studio — instead of exporting env vars by hand.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _config_file() -> Path:
    base = os.environ.get("DENAI_CONFIG_DIR")
    root = Path(base) if base else Path.home() / ".denai"
    return root / "config.json"


def _read_config() -> dict:
    path = _config_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_config(config: dict) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    path.chmod(0o600)


def apply_stored_key() -> None:
    """Export the stored API key to the environment, if one is saved.

    Call once at process start, before any agent call. A key already present
    in the environment always wins.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    key = _read_config().get("api_key")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key


def save_api_key(key: str) -> None:
    key = key.strip()
    if not key.startswith("sk-ant-"):
        raise ValueError("That doesn't look like an Anthropic API key (sk-ant-…).")
    config = _read_config()
    config["api_key"] = key
    _write_config(config)
    os.environ["ANTHROPIC_API_KEY"] = key


def mark_subscription_ok() -> None:
    config = _read_config()
    config["subscription_ok"] = True
    _write_config(config)


def auth_source() -> str | None:
    """Best-effort guess of how den-AI will authenticate, without calling Claude."""
    config = _read_config()
    if os.environ.get("ANTHROPIC_API_KEY") and not config.get("api_key"):
        return "env"
    if config.get("api_key"):
        return "stored_key"
    if config.get("subscription_ok"):
        return "subscription"
    return None


def probe(model: str) -> tuple[bool, str]:
    """Make one tiny real call to Claude to verify credentials end-to-end."""
    import shutil

    from denai.agent import run_agent

    if shutil.which("claude") is None:
        return False, (
            "Claude Code CLI not found on this machine — den-AI talks to Claude "
            "through it. Install it from claude.com/claude-code "
            "(npm install -g @anthropic-ai/claude-code), then retry."
        )
    try:
        run_agent("Reply with exactly: OK", "You reply with exactly: OK", model)
        return True, "ok"
    except Exception as exc:
        detail = str(exc)
        lowered = detail.lower()
        if "not logged in" in lowered or "/login" in lowered:
            detail += (
                " → Open a terminal, run `claude`, type /login and pick your "
                "Claude account — or paste an API key below instead."
            )
        elif "invalid" in lowered and "key" in lowered:
            detail += " → Check the key on console.anthropic.com, or use the subscription login."
        return False, detail
