from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CADDYFILE = ROOT / "infra" / "caddy" / "Caddyfile"


def test_caddyfile_enforces_https_redirect_and_tls13() -> None:
	content = CADDYFILE.read_text(encoding="utf-8")

	assert "http:// {" in content
	assert "redir https://{host}{uri} permanent" in content
	assert "https:// {" in content
	assert "tls internal {" in content
	assert "protocols tls1.3" in content


def test_caddyfile_routes_api_and_frontend_to_separate_upstreams() -> None:
	content = CADDYFILE.read_text(encoding="utf-8")

	assert "@api path /api/* /metrics /health" in content
	assert "reverse_proxy {$API_UPSTREAM:backend:8000}" in content
	assert "reverse_proxy {$FRONTEND_UPSTREAM:frontend:3000}" in content