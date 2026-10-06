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
        # Senha guardada ausente (None) ou fora do formato "salt$hash":
        # nunca deve estourar erro no login, apenas negar o acesso.
        if not stored_password or "$" not in stored_password:
            return False

        salt, hash_expected = stored_password.split("$", 1)
        calculated_hash = hashlib.sha256(
            (salt + clean_text_password).encode("utf-8")
        ).hexdigest()

        # compare_digest evita ataque de temporização na comparação.
        return secrets.compare_digest(
            calculated_hash.encode("utf-8"),
            hash_expected.encode("utf-8")
        )
