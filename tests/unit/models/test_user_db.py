"""
Unit tests for user_service.models.user_db (UserModel)
"""
import pytest
from sqlalchemy.exc import IntegrityError

from user_service.extensions.db import db
from user_service.models.user_db import UserModel


class TestUserModelColumns:
    def test_tablename(self):
        """The mapped table must be named 'user'."""
        assert UserModel.__tablename__ == "user"

    def test_user_id_is_primary_key(self):
        """user_id column must be marked as primary key."""
        col = UserModel.__table__.c["user_id"]
        assert col.primary_key is True

    def test_username_is_unique(self):
        """username column must have a unique constraint."""
        col = UserModel.__table__.c["username"]
        assert col.unique is True

    def test_username_not_nullable(self):
        """username column must be NOT NULL."""
        col = UserModel.__table__.c["username"]
        assert col.nullable is False

    def test_password_not_nullable(self):
        """password column must be NOT NULL."""
        col = UserModel.__table__.c["password"]
        assert col.nullable is False

    def test_username_max_length(self):
        """username column length must be 40 characters."""
        col = UserModel.__table__.c["username"]
        assert col.type.length == 40

    def test_password_max_length(self):
        """password column length must be 255 characters."""
        col = UserModel.__table__.c["password"]
        assert col.type.length == 255


class TestUserModelCRUD:
    def test_create_user(self, app):
        """A valid UserModel instance should persist and get an auto-increment id."""
        with app.app_context():
            user = UserModel(username="alice", password="hashed_pw")
            db.session.add(user)
            db.session.commit()

            fetched = UserModel.query.filter_by(username="alice").first()
            assert fetched is not None
            assert fetched.user_id is not None
            assert fetched.username == "alice"
            assert fetched.password == "hashed_pw"

    def test_unique_username_constraint(self, app):
        """Inserting two users with the same username must raise IntegrityError."""
        with app.app_context():
            db.session.add(UserModel(username="bob", password="pw1"))
            db.session.commit()

            db.session.add(UserModel(username="bob", password="pw2"))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_delete_user(self, app):
        """Deleted user must no longer be found in the database."""
        with app.app_context():
            user = UserModel(username="carol", password="hashed")
            db.session.add(user)
            db.session.commit()

            db.session.delete(user)
            db.session.commit()

            assert UserModel.query.filter_by(username="carol").first() is None

    def test_query_all_users(self, app):
        """query.all() should return every persisted user."""
        with app.app_context():
            db.session.add_all([
                UserModel(username="dave", password="pw"),
                UserModel(username="eve", password="pw"),
            ])
            db.session.commit()

            users = UserModel.query.all()
            usernames = {u.username for u in users}
            assert {"dave", "eve"}.issubset(usernames)

    def test_user_repr_attributes(self, app):
        """The model should expose username and password as plain attributes."""
        with app.app_context():
            user = UserModel(username="frank", password="secret")
            db.session.add(user)
            db.session.commit()
            assert user.username == "frank"
            assert user.password == "secret"
