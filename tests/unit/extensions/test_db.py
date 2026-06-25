"""
Unit tests for user_service.extensions.db
"""
import pytest
from flask_sqlalchemy import SQLAlchemy

from user_service.extensions.db import db


class TestDbExtension:
    def test_db_is_sqlalchemy_instance(self):
        """db must be a SQLAlchemy extension object."""
        assert isinstance(db, SQLAlchemy)

    def test_db_model_base_available(self):
        """db.Model should be accessible as the declarative base."""
        assert db.Model is not None

    def test_db_session_available(self):
        """db.session must be present (scoped session proxy)."""
        assert db.session is not None

    def test_db_bound_to_app(self, app):
        """After app creation the db engine is initialised inside app context."""
        with app.app_context():
            # engine is lazily created; accessing it should not raise
            engine = db.engine
            assert engine is not None

    def test_db_creates_tables(self, app):
        """db.create_all() inside app context must not raise."""
        with app.app_context():
            db.create_all()   # idempotent — tables already exist from fixture

    def test_db_metadata_contains_user_table(self, app):
        """The 'user' table must be reflected in the metadata after create_all."""
        with app.app_context():
            db.create_all()
            assert "user" in db.metadata.tables
