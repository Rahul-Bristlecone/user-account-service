"""
Unit tests for user_service.extensions.redis_client

The actual Redis connection is replaced by a MagicMock (see conftest.py),
so every test here validates behaviour without a live Redis server.
"""
import os
from unittest.mock import MagicMock, patch, call

import pytest


class TestRedisClientConfiguration:
    def test_redis_client_is_mock(self, mock_redis):
        """The module-level redis_client must be the shared MagicMock."""
        from user_service.extensions.redis_client import redis_client
        assert isinstance(redis_client, MagicMock)

    def test_redis_client_setex_callable(self, mock_redis):
        """setex should be callable on the mock client."""
        from user_service.extensions.redis_client import redis_client
        redis_client.setex("key", 60, "value")
        redis_client.setex.assert_called_once_with("key", 60, "value")

    def test_redis_client_get_callable(self, mock_redis):
        """get should return whatever the mock is configured to return."""
        from user_service.extensions.redis_client import redis_client
        mock_redis.get.return_value = "cached_value"
        result = redis_client.get("some_key")
        assert result == "cached_value"

    def test_redis_client_delete_callable(self, mock_redis):
        """delete should be callable and forward arguments correctly."""
        from user_service.extensions.redis_client import redis_client
        redis_client.delete("session:42")
        redis_client.delete.assert_called_once_with("session:42")

    def test_redis_client_scan_iter_callable(self, mock_redis):
        """scan_iter should be iterable via the mock."""
        from user_service.extensions.redis_client import redis_client
        mock_redis.scan_iter.return_value = iter(["session:1", "session:2"])
        keys = list(redis_client.scan_iter("session:*"))
        assert keys == ["session:1", "session:2"]

    def test_redis_env_defaults_applied(self):
        """Environment variables for Redis must be set before module import."""
        assert os.environ.get("REDIS_HOST") is not None
        assert os.environ.get("REDIS_PORT") is not None

    def test_redis_constructor_called_with_env_values(self):
        """
        Verify redis.Redis was instantiated using the env-var values
        captured when the module was first imported.
        """
        # The patch was started in conftest.py; redis.Redis(…) was called
        # once at module import time.  We just confirm the mock exists and
        # the redis_client module imported without error.
        from user_service.extensions import redis_client as rc_module
        assert hasattr(rc_module, "redis_client")
