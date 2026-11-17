"""Single source of truth for the six independently deployed frontends."""
FRONTEND_PORTS={'magalu:web': 8181, 'magalu:app': 8182, 'netshoes:web': 8183, 'netshoes:app': 8184, 'magalupay:web': 8185, 'magalupay:app': 8186}

import os
from urllib.parse import urlsplit

FRONTEND_URL_ENV = {
    "magalu:web": "MAGALU_WEB_URL",
    "magalu:app": "MAGALU_MOBILE_URL",
    "netshoes:web": "NETSHOES_WEB_URL",
    "netshoes:app": "NETSHOES_MOBILE_URL",
    "magalupay:web": "PAY_WEB_URL",
    "magalupay:app": "PAY_MOBILE_URL",
}

def storefront_origin(client_key):
    default = f"http://localhost:{FRONTEND_PORTS[client_key]}"
    origin = os.environ.get(FRONTEND_URL_ENV[client_key], default)

    if not origin or any(c.isspace() for c in origin):
        raise ValueError("Invalid storefront origin")

    origin = origin.rstrip("/")
    parsed = urlsplit(origin)

    if (parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment):
        raise ValueError("Invalid storefront origin")

    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Invalid storefront port") from exc

    if parsed.scheme == "http" and origin != default:
        raise ValueError("Public storefronts must use HTTPS")

    return origin

def callback_uri(client_key):
    return storefront_origin(client_key) + "/callback"
