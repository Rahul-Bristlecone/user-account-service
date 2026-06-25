"""
Unit tests for user_service.resources.user

Covers every route class:
  POST /register      – UserRegister
  POST /login         – UserAuthLogin
  GET  /users         – UserList
  GET  /active        – ActiveUsers
  DELETE /user/<id>   – User
  POST /logout        – UserLogout
"""
import json
import pytest
from flask_jwt_extended import create_access_token

from user_service.extensions.db import db
from user_service.models.user_db import UserModel


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register(client, username="testuser", password="testpass"):
    return client.post(
        "/register",
        json={"username": username, "password": password},
    )


def _login(client, username="testuser", password="testpass"):
    return client.post(
        "/login",
        json={"username": username, "password": password},
    )


def _auth_header(app, user_id="1"):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


# ── /register ─────────────────────────────────────────────────────────────────

class TestUserRegister:
    def test_register_success(self, client):
        """POST /register with new credentials returns 201 and success message."""
        resp = _register(client)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["username"] == "testuser"
        assert "message" in body

    def test_register_duplicate_returns_409(self, client):
        """Registering with an already-existing username must return 409."""
        _register(client)
        resp = _register(client)
        assert resp.status_code == 409

    def test_register_missing_username_returns_422(self, client):
        """Payload without username must fail schema validation (422)."""
        resp = client.post("/register", json={"password": "pw"})
        assert resp.status_code == 422

    def test_register_missing_password_returns_422(self, client):
        """Payload without password must fail schema validation (422)."""
        resp = client.post("/register", json={"username": "alice"})
        assert resp.status_code == 422

    def test_register_password_is_hashed(self, app, client):
        """Stored password must not equal the plain-text value."""
        _register(client, username="hashme", password="plain123")
        with app.app_context():
            user = UserModel.query.filter_by(username="hashme").first()
            assert user.password != "plain123"


# ── /login ────────────────────────────────────────────────────────────────────

class TestUserAuthLogin:
    def test_login_success_returns_token(self, client, mock_redis):
        """POST /login with correct credentials returns a JWT and username."""
        _register(client)
        resp = _login(client)
        assert resp.status_code == 200
        body = resp.get_json()
        assert "Token" in body
        assert body["username"] == "testuser"

    def test_login_caches_session_in_redis(self, client, mock_redis):
        """Successful login must call redis_client.setex once."""
        _register(client)
        _login(client)
        mock_redis.setex.assert_called_once()

    def test_login_wrong_password(self, client):
        """Incorrect password must not return a token."""
        _register(client)
        resp = _login(client, password="wrongpass")
        body = resp.get_json()
        assert "Token" not in body

    def test_login_nonexistent_user(self, client):
        """Login for a user that was never registered must not return a token."""
        resp = _login(client, username="ghost", password="pw")
        body = resp.get_json()
        assert "Token" not in body

    def test_login_missing_fields_returns_422(self, client):
        """Payload missing password must fail schema validation."""
        resp = client.post("/login", json={"username": "alice"})
        assert resp.status_code == 422


# ── /users ────────────────────────────────────────────────────────────────────

class TestUserList:
    def test_get_users_empty(self, client):
        """GET /users on an empty DB must return an empty list."""
        resp = client.get("/users")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_get_users_returns_registered_users(self, client):
        """GET /users should include every registered user."""
        _register(client, username="u1")
        _register(client, username="u2")
        resp = client.get("/users")
        assert resp.status_code == 200
        usernames = [u["username"] for u in resp.get_json()]
        assert "u1" in usernames
        assert "u2" in usernames

    def test_get_users_excludes_passwords(self, client):
        """GET /users response must NOT include plaintext or hashed passwords."""
        _register(client, username="nopw")
        resp = client.get("/users")
        for user in resp.get_json():
            assert "password" not in user


# ── /active ───────────────────────────────────────────────────────────────────

class TestActiveUsers:
    def test_active_users_empty_when_no_sessions(self, client, mock_redis):
        """GET /active returns empty list when Redis has no session keys."""
        mock_redis.scan_iter.return_value = iter([])
        resp = client.get("/active")
        assert resp.status_code == 200
        assert resp.get_json()["active_users"] == []

    def test_active_users_returns_cached_sessions(self, client, mock_redis):
        """GET /active should list users whose session exists in Redis."""
        mock_redis.scan_iter.return_value = iter(["session:1"])
        mock_redis.get.return_value = json.dumps(
            {"token": "tok", "username": "alice"}
        )
        resp = client.get("/active")
        assert resp.status_code == 200
        active = resp.get_json()["active_users"]
        assert len(active) == 1
        assert active[0]["Username"] == "alice"
        assert active[0]["user_id"] == "1"

    def test_active_users_skips_expired_keys(self, client, mock_redis):
        """Keys that have expired (Redis returns None) must be skipped."""
        mock_redis.scan_iter.return_value = iter(["session:99"])
        mock_redis.get.return_value = None
        resp = client.get("/active")
        assert resp.get_json()["active_users"] == []

    def test_active_users_skips_bad_json(self, client, mock_redis):
        """Keys whose value is malformed JSON must be silently skipped."""
        mock_redis.scan_iter.return_value = iter(["session:5"])
        mock_redis.get.return_value = "not-json"
        resp = client.get("/active")
        assert resp.get_json()["active_users"] == []

    def test_active_users_skips_missing_username_key(self, client, mock_redis):
        """JSON without 'username' key must be silently skipped."""
        mock_redis.scan_iter.return_value = iter(["session:7"])
        mock_redis.get.return_value = json.dumps({"token": "tok"})
        resp = client.get("/active")
        assert resp.get_json()["active_users"] == []


# ── /user/<id> ────────────────────────────────────────────────────────────────

class TestUserDelete:
    def test_delete_existing_user(self, app, client):
        """DELETE /user/<id> for an existing user must remove them from the DB."""
        _register(client, username="todelete")
        with app.app_context():
            user = UserModel.query.filter_by(username="todelete").first()
            user_id = user.user_id

        resp = client.delete(f"/user/{user_id}")
        assert resp.status_code == 200

        with app.app_context():
            assert UserModel.query.get(user_id) is None

    def test_delete_nonexistent_user_returns_404(self, client):
        """DELETE /user/<id> for a non-existent id must return 404."""
        resp = client.delete("/user/99999")
        assert resp.status_code == 404


# ── /logout ───────────────────────────────────────────────────────────────────

class TestUserLogout:
    def test_logout_success(self, app, client, mock_redis):
        """POST /logout with a valid JWT must remove the Redis session and return 200."""
        _register(client, username="logoutme")
        with app.app_context():
            user = UserModel.query.filter_by(username="logoutme").first()
            token = create_access_token(identity=str(user.user_id))
            user_id = user.user_id

        resp = client.post(
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        mock_redis.delete.assert_called_once_with(f"session:{user_id}")

    def test_logout_without_token_returns_401(self, client):
        """POST /logout without Authorization header must return 401."""
        resp = client.post("/logout")
        assert resp.status_code == 401

    def test_logout_returns_success_message(self, app, client, mock_redis):
        """Logout response body must contain a message field."""
        _register(client, username="msgcheck")
        with app.app_context():
            user = UserModel.query.filter_by(username="msgcheck").first()
            token = create_access_token(identity=str(user.user_id))

        resp = client.post(
            "/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert "message" in resp.get_json()
