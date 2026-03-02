import os
from dotenv import load_dotenv

from flask import Flask, jsonify
from flask_smorest import Api
from flask_jwt_extended import JWTManager

from user_service.blocklist import BLOCKLIST

from user_service.src.user_service.extensions.db import db
from user_service.src.user_service.resources.user import blp as UserBp

def create_app(db_url=None):
    user_service = Flask(__name__)
    user_service.config["PROPAGATE_EXCEPTIONS"] = True
    user_service.config["API_TITLE"] = "User Service API"
    user_service.config["API_VERSION"] = "v1"
    user_service.config["OPENAPI_VERSION"] = "3.0.3"
    user_service.config["OPENAPI_URL_PREFIX"] = "/"
    user_service.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    user_service.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    """ for SQLite, local database file is created in the data directory of the store service application.
        This is useful for development and testing purposes, as it allows the application to run without needing an 
        external database server. (not to be used in production)
    """
    # user-auth-service.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/user_data.db"
    # *** for SQLite - app directory is created inside container for data persistence but containers are ephemeral ***
    # user-auth-service.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/user-auth-service/src/user-auth-service/data/user_data.db"
    """
        for MySQL, the database is created in a separate container and the store service container connects to it 
        using the MySQL driver.
        Note: The database connection string is in the format:
        "mysql+pymysql://<username>:<password>@<host>/<database_name>"
        where:
        - <username> is the MySQL username
        - <password> is the MySQL password
        - <host> is the hostname or IP address of the MySQL server
        - <database_name> is the name of the database to connect to
        user-auth-service.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://user_user:user_pass@mysql_user:3306/user_db"
    """

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    )
    print("Connecting to DB:", SQLALCHEMY_DATABASE_URI)  # helpful for debugging

    user_service.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    db.init_app(user_service)  # db is SQLAlchemy extension
    user_service.config['TESTING'] = True  # Enable testing mode for the Flask app

    api = Api(user_service)

    """
        Note: As the user service is issuing (signing/generating) JWT tokens, the following code
        configures JWT (JSON Web Token) handling for the user service. JWT is a compact, URL-safe means
        of representing claims to be transferred securely between two parties.
    
        According to JWT best practices and documentation:
        1. Assign a secret key (JWT_SECRET_KEY) that is used to sign (create) the JWT tokens, 
        proving they are issued by this application.
        2. Initialize JWTManager with the Flask application; it manages JWT tokens and their lifecycle.
        3. JWT_SECRET_KEY is used to create the cryptographic signature for each token — this signature asserts 
        that the token is genuine and unaltered.
        4. JWT_TOKEN_LOCATION specifies where the application should look for incoming JWT tokens in each request 
        (e.g., headers, cookies).
    
        *** To verify a token's validity and check it hasn't been tampered with, any trusted service recalculates 
        the token's cryptographic signature using the shared secret key. The newly computed signature is compared 
        with the signature part of the token; if they match, the token is authentic and untampered.
        (Note: The signature is not decrypted—JWT uses signature verification, not decryption.)
        ***
    """

    load_dotenv()
    user_service.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
    user_service.config["JWT_TOKEN_LOCATION"] = ["headers"]
    jwt = JWTManager(user_service)

    @jwt.token_in_blocklist_loader
    def verify_token_exist(jwt_header, jwt_payload):
        return jwt_payload["jti"] in BLOCKLIST

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"message": "Expired token"}), 401

    @user_service.before_request
    def create_tables():
        db.create_all()

    api.register_blueprint(UserBp)
    return user_service