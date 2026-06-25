"""
Unit tests for user_service.main (create_app factory + built-in routes)
"""
import pytest
from flask import Flask

from user_service.main import create_app


class TestCreateApp:
    def test_returns_flask_instance(self, app):
        """create_app() must return a Flask application instance."""
        assert isinstance(app, Flask)

    def test_testing_mode_enabled(self, app):
        """TESTING config flag must be True."""
        assert app.config["TESTING"] is True

    def test_api_title_configured(self, app):
        """API_TITLE must be set to the expected value."""
        assert app.config["API_TITLE"] == "User Service API"

    def test_api_version_configured(self, app):
        """API_VERSION must be set to 'v1'."""
        assert app.config["API_VERSION"] == "v1"

    def test_openapi_version_configured(self, app):
        """OPENAPI_VERSION must follow the 3.x spec."""
        assert app.config["OPENAPI_VERSION"].startswith("3.")

    def test_jwt_token_location_is_headers(self, app):
        """JWT_TOKEN_LOCATION must be configured to read from headers."""
        assert "headers" in app.config["JWT_TOKEN_LOCATION"]

    def test_propagate_exceptions_enabled(self, app):
        """PROPAGATE_EXCEPTIONS must be True so errors surface correctly."""
        assert app.config["PROPAGATE_EXCEPTIONS"] is True

    def test_sqlalchemy_uri_configured(self, app):
        """SQLALCHEMY_DATABASE_URI must be present (overridden to SQLite in tests)."""
        assert app.config.get("SQLALCHEMY_DATABASE_URI") is not None


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        """GET /health must respond with HTTP 200."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_json(self, client):
        """GET /health must return JSON content."""
        resp = client.get("/health")
        assert resp.content_type == "application/json"

    def test_health_body_status_healthy(self, client):
        """GET /health body must contain {"status": "healthy"}."""
        resp = client.get("/health")
        assert resp.get_json() == {"status": "healthy"}


class TestJwtBlocklistLoader:
    def test_blocklisted_jti_is_rejected(self, app, client):
        """A token whose JTI is in BLOCKLIST must be treated as invalid."""
        from flask_jwt_extended import create_access_token, decode_token
        from user_service.blocklist import BLOCKLIST

        with app.app_context():
            token = create_access_token(identity="99")
            jti = decode_token(token)["jti"]
            BLOCKLIST.add(jti)

        # /logout is a @jwt_required endpoint — blocked token should yield 401
        resp = client.post(
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        BLOCKLIST.discard(jti)

    def test_expired_token_returns_401(self, app, client):
        """An expired JWT must trigger the expired_token_loader (401)."""
        from datetime import timedelta
        from flask_jwt_extended import create_access_token

        with app.app_context():
            token = create_access_token(
                identity="1", expires_delta=timedelta(seconds=-1)
            )

        resp = client.post(
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
