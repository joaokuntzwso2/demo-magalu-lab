"""Verify public navigation uses configured application origins."""

from fastapi.testclient import TestClient
from bootstrap.storefront_ports import FRONTEND_PORTS, FRONTEND_URL_ENV
from demo import main as portal


def test_home_uses_configured_storefront_urls(monkeypatch):
    urls = []

    for key, env_name in FRONTEND_URL_ENV.items():
        port = 8444 + FRONTEND_PORTS[key] - 8181
        url = f"https://54.20.194.28:{port}"
        monkeypatch.setenv(env_name, url)
        urls.append(url)

    response = TestClient(portal.app).get("/")

    assert response.status_code == 200
    for url in urls:
        assert f'href="{url}"' in response.text


def test_compatibility_login_redirect(monkeypatch):
    monkeypatch.setenv(
        "MAGALU_WEB_URL",
        "https://54.20.194.28:8444",
    )

    response = TestClient(portal.app).get(
        "/auth/start/magalu/web",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "https://54.20.194.28:8444/login"
    )


def test_section7_stepup_return_url(monkeypatch):
    monkeypatch.setenv(
        "DEMO_SESSION_SECRET",
        "test-only-secret",
    )

    from demo import storefront

    monkeypatch.setattr(
        storefront,
        "DEMO_PUBLIC_URL",
        "https://54.20.194.28:8443",
    )

    assert storefront.section7_return_url("request id&x") == (
        "https://54.20.194.28:8443/m3/section7"
        "?tx=request+id%26x"
    )
