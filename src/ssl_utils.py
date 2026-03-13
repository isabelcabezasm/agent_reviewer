"""SSL utilities for building httpx clients with custom CA bundles.

Controlled by two environment variables:
- USE_CERTS: Set to 'true' to enable custom CA bundle (default: false).
- CERTS_PATH: Path to the CA bundle file (default: /etc/ssl/certs/ca-certificates.crt).
"""

import os

import httpx

_DEFAULT_CERTS_PATH = "/etc/ssl/certs/ca-certificates.crt"


def build_httpx_client() -> httpx.Client:
    """Build an httpx client, optionally with a custom CA bundle.

    When USE_CERTS is 'true', uses the CA bundle at CERTS_PATH
    (or SSL_CERT_FILE) for SSL verification. This is needed in
    corporate environments with SSL-inspecting proxies.

    When USE_CERTS is not set or 'false', uses default SSL.
    """
    use_certs = os.environ.get("USE_CERTS", "false").lower() == "true"
    if not use_certs:
        return httpx.Client()

    ca_bundle = os.environ.get("CERTS_PATH", _DEFAULT_CERTS_PATH)
    if os.path.isfile(ca_bundle):
        return httpx.Client(verify=ca_bundle)
    return httpx.Client()
