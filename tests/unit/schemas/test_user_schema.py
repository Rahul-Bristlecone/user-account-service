"""
Unit tests for user_service.schemas.user_schema (UserSchema)
"""
import pytest
from marshmallow import ValidationError

from user_service.schemas.user_schema import UserSchema


@pytest.fixture()
def schema():
    return UserSchema()


class TestUserSchemaLoad:
    def test_load_valid_payload(self, schema):
        """Valid username + password should deserialise without errors."""
        data = schema.load({"username": "alice", "password": "secret123"})
        assert data["username"] == "alice"
        assert data["password"] == "secret123"

    def test_load_missing_username_raises(self, schema):
        """Missing username must raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            schema.load({"password": "secret123"})
        assert "username" in exc.value.messages

    def test_load_missing_password_raises(self, schema):
        """Missing password must raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            schema.load({"username": "alice"})
        assert "password" in exc.value.messages

    def test_load_empty_payload_raises(self, schema):
        """Both fields missing must raise ValidationError with both keys."""
        with pytest.raises(ValidationError) as exc:
            schema.load({})
        assert "username" in exc.value.messages
        assert "password" in exc.value.messages

    def test_load_extra_fields_ignored(self, schema):
        """Marshmallow 3 raises ValidationError for unknown fields by default."""
        with pytest.raises(ValidationError) as exc:
            schema.load({"username": "bob", "password": "pw", "role": "admin"})
        assert "role" in exc.value.messages

    def test_user_id_excluded_on_load(self, schema):
        """dump_only fields are rejected during load (marshmallow 3 default unknown=RAISE)."""
        with pytest.raises(ValidationError) as exc:
            schema.load({"username": "carol", "password": "pw", "user_id": 99})
        assert "user_id" in exc.value.messages


class TestUserSchemaDump:
    def test_dump_excludes_password(self, schema):
        """password is load_only and must NOT appear in serialised output."""
        obj = {"user_id": 1, "username": "dave", "password": "hidden"}
        result = schema.dump(obj)
        assert "password" not in result

    def test_dump_includes_user_id(self, schema):
        """user_id is dump_only and must appear in serialised output."""
        obj = {"user_id": 7, "username": "eve", "password": "hidden"}
        result = schema.dump(obj)
        assert result["user_id"] == 7

    def test_dump_includes_username(self, schema):
        """username must appear in serialised output."""
        obj = {"user_id": 2, "username": "frank", "password": "hidden"}
        result = schema.dump(obj)
        assert result["username"] == "frank"

    def test_dump_many(self, schema):
        """many=True variant should serialise a list of objects correctly."""
        objs = [
            {"user_id": 1, "username": "g1", "password": "pw"},
            {"user_id": 2, "username": "g2", "password": "pw"},
        ]
        results = UserSchema(many=True).dump(objs)
        assert len(results) == 2
        assert all("password" not in r for r in results)
        assert {r["username"] for r in results} == {"g1", "g2"}


class TestUserSchemaFields:
    def test_user_id_field_is_int(self, schema):
        """user_id must be declared as an Int field."""
        from marshmallow import fields
        assert isinstance(schema.fields["user_id"], fields.Int)

    def test_username_field_is_str(self, schema):
        """username must be declared as a Str field."""
        from marshmallow import fields
        assert isinstance(schema.fields["username"], fields.Str)

    def test_password_field_is_str(self, schema):
        """password must be declared as a Str field."""
        from marshmallow import fields
        assert isinstance(schema.fields["password"], fields.Str)

    def test_password_is_load_only(self, schema):
        """password must have load_only=True."""
        assert schema.fields["password"].load_only is True

    def test_user_id_is_dump_only(self, schema):
        """user_id must have dump_only=True."""
        assert schema.fields["user_id"].dump_only is True
