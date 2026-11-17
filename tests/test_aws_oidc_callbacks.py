import pytest
import yaml
from pathlib import Path
from bootstrap.storefront_ports import (
    FRONTEND_PORTS, FRONTEND_URL_ENV, callback_uri
)
from bootstrap.storefront_provision import _registered_callbacks

ROOT = Path(__file__).parents[1]

def test_local_callbacks(monkeypatch):
    for name in FRONTEND_URL_ENV.values():
        monkeypatch.delenv(name, raising=False)
    for key, port in FRONTEND_PORTS.items():
        assert callback_uri(key) == f"http://localhost:{port}/callback"

def test_public_callbacks(monkeypatch):
    for key, name in FRONTEND_URL_ENV.items():
        host = name.lower().replace("_url", "").replace("_", "-")
        monkeypatch.setenv(name, f"https://{host}.example.test")
    urls = [callback_uri(key) for key in FRONTEND_PORTS]
    assert len(set(urls)) == 6
    for uri in urls:
        assert uri.startswith("https://")
        assert uri.endswith("/callback")
        assert _registered_callbacks([uri], uri) == [uri]

def test_insecure_remote_http_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "MAGALU_WEB_URL", "http://public.example.test"
    )
    with pytest.raises(ValueError):
        callback_uri("magalu:web")

def test_unexpected_callback_is_rejected(monkeypatch):
    for name in FRONTEND_URL_ENV.values():
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="non-allowlisted"):
        _registered_callbacks(
            ["http://localhost:8181/callback"],
            "https://attacker.example.test/callback"
        )

def test_bootstrap_compose_passes_six_origins():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    bootstrap = compose["services"]["bootstrap"]["environment"]
    frontends = yaml.safe_load(
        (ROOT / "compose.frontends.yaml").read_text()
    )["services"]
    for key, name in FRONTEND_URL_ENV.items():
        port = FRONTEND_PORTS[key]
        assert bootstrap[name] == (
            f"${{{name}:-http://localhost:{port}}}"
        )
        brand, channel = key.split(":")
        service = f"store-{brand}-{'app' if channel == 'app' else 'web'}"
        assert frontends[service]["environment"]["STORE_PUBLIC_URL"] == (
            f"${{{name}:-http://localhost:{port}}}"
        )
