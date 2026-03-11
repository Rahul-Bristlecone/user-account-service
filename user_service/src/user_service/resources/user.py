import json

from flask_smorest import Blueprint, abort
from flask.views import MethodView
from passlib.hash import pbkdf2_sha256
from flask_jwt_extended import create_access_token, get_jwt, jwt_required, get_jwt_identity
from user_service.blocklist import BLOCKLIST

from user_service.src.user_service.extensions.redis_client import redis_client
from user_service.src.user_service.extensions.db import db
from user_service.src.user_service.models.user_db import UserModel
from user_service.src.user_service.schemas.user_schema import UserSchema

blp = Blueprint("Users", __name__, description="operations on user")

@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        if UserModel.query.filter(UserModel.username == user_data["username"]).first():
            abort(409, message="User already exists")

        user = UserModel(username=user_data["username"],
                         password=pbkdf2_sha256.hash(user_data["password"]), )

        db.session.add(user)
        db.session.commit()

        return {"message": "User created successfully",
                "Username": user.username}, 201


@blp.route("/login")
class UserAuthLogin(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        # checking if the user exists
        user = UserModel.query.filter(UserModel.username == user_data["username"]).first()
        # verifying if the password provided (payload) matches with the password saved in db
        if user and pbkdf2_sha256.verify(user_data["password"], user.password):
            # generated token will be used for the specific end-points
            access_token = create_access_token(identity=str(user.user_id))
            # Cache session/token in Redis
            redis_client.setex(f"session:{user.user_id}", 3600, json.dumps({"token":access_token, "username":user.username}))
            return {"Token": access_token,
                    "Username": user.username}, 200
        return {"message": "Invalid credentials"}


@blp.route("/users")
class UserList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        return UserModel.query.all()


@blp.route("/active")
class ActiveUsers(MethodView):
    def get(self):
        active_users = []
        # Scan Redis for keys that match session pattern
        for key in redis_client.scan_iter("session:*"):
            user_id = key.split(":")[1]
            data = json.loads(redis_client.get(key))
            active_users.append({"user_id": user_id, "Username":data["username"]})

        return {"active_users": active_users}, 200


@blp.route("/user/<string:user_id>")
class User(MethodView):
    @blp.response(200, UserSchema(many=True))
    def delete(self, user_id):
        try:
            user = UserModel.query.get_or_404(user_id)
            db.session.delete(user)
            db.session.commit()
            return {"message" : f"User deleted with user id  user_id {user_id}"}
        except KeyError:
            # return {"message": "store not found"}, 404
            abort(404, message="User does not exists")


@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        # jti = get_jwt()["jti"]  # Add to BLOCKLIST (immediate block)
        # BLOCKLIST.add(jti)

        user_id = get_jwt_identity()
        redis_client.delete(f"session:{user_id}")
        return {"message": "Logged out successfully"}, 200