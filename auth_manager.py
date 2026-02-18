from werkzeug.security import check_password_hash, generate_password_hash

from exceptions import AuthenticationError, ValidationError


class UserAuth:
    def __init__(self, db_manager, logger):
        self.db = db_manager
        self.logger = logger

    def register_user(self, username, password):
        if not username or not password:
            raise ValidationError("Username and password are required.")
        existing = self.db.get_user_by_username(username)
        if existing:
            raise ValidationError("Username already exists.")
        password_hash = generate_password_hash(password)
        self.db.create_user(username, password_hash)

    def authenticate_user(self, username, password):
        if not username or not password:
            raise AuthenticationError("Username and password are required.")
        user = self.db.get_user_by_username(username)
        if not user:
            return None
        if not check_password_hash(user["password"], password):
            return None
        return user
