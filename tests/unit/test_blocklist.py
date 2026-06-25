"""
Unit tests for user_service.blocklist
"""
import pytest

from user_service.blocklist import BLOCKLIST


class TestBlocklist:
    def setup_method(self):
        """Reset the BLOCKLIST before every test."""
        BLOCKLIST.clear()

    def test_blocklist_is_set(self):
        """BLOCKLIST must be a Python set."""
        assert isinstance(BLOCKLIST, set)

    def test_blocklist_starts_empty(self):
        """A freshly cleared BLOCKLIST must contain no entries."""
        assert len(BLOCKLIST) == 0

    def test_add_jti(self):
        """A JTI added to the BLOCKLIST must be present."""
        BLOCKLIST.add("some-jti-value")
        assert "some-jti-value" in BLOCKLIST

    def test_add_multiple_jtis(self):
        """Multiple JTIs can be stored and all must be present."""
        jtis = {"jti-1", "jti-2", "jti-3"}
        BLOCKLIST.update(jtis)
        assert jtis.issubset(BLOCKLIST)

    def test_contains_returns_false_for_unknown_jti(self):
        """A JTI that was never added must not appear in the BLOCKLIST."""
        assert "never-added-jti" not in BLOCKLIST

    def test_discard_jti(self):
        """A discarded JTI must no longer appear in the BLOCKLIST."""
        BLOCKLIST.add("to-remove")
        BLOCKLIST.discard("to-remove")
        assert "to-remove" not in BLOCKLIST

    def test_duplicate_add_is_idempotent(self):
        """Adding the same JTI twice must keep the set size at 1."""
        BLOCKLIST.add("dup-jti")
        BLOCKLIST.add("dup-jti")
        assert len(BLOCKLIST) == 1
