from marshmallow import Schema, fields


class UserSchema(Schema):
    user_id = fields.Int(dump_only=True)  # excluded while serializing
    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)  # excluded while deserializing