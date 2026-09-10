import hashlib
import secrets


class Password_Utils:

    @staticmethod
    def to_hash(clean_text_password):
        salt = secrets.token_hex(16)
        hash_password = hashlib.sha256(
            (salt + clean_text_password).encode("utf-8")
        ).hexdigest()
        return f"{salt}${hash_password}"

    @staticmethod
    def check_password(clean_text_password, stored_password):
        salt, hash_expected = stored_password.split("$")
        calculated_hash = hashlib.sha256(
            (salt + clean_text_password).encode("utf-8")
        ).hexdigest()
        return calculated_hash == hash_expected