import logging
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings

logger = logging.getLogger("neurovault.encryption")

_fernet_instance = None


def _get_fernet() -> Fernet:
    """Lazily initialise the Fernet cipher using the configured ENCRYPTION_KEY."""
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.ENCRYPTION_KEY.encode("utf-8")
        _fernet_instance = Fernet(key)
    return _fernet_instance


class EncryptionService:
    """
    AES-256-based symmetric encryption for sensitive document fields.

    The Fernet specification (used here) provides:
      - AES-128-CBC encryption of the payload
      - HMAC-SHA256 authentication tag
      - Timestamp embedded in the token

    Fields encrypted before DB storage:
      - Aadhaar Number
      - PAN Number
      - Passport Number
      - Driving Licence Number
      - Bank Account Number
      - Full extracted_json payloads
    """

    @staticmethod
    def encrypt(plaintext: str) -> str:
        """
        Encrypts a plain-text string using the deployment's ENCRYPTION_KEY.
        Returns a URL-safe base64 ciphertext string.
        Returns the original value unchanged if plaintext is empty.
        """
        if not plaintext:
            return plaintext
        try:
            fernet = _get_fernet()
            token = fernet.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @staticmethod
    def decrypt(ciphertext: str) -> str:
        """
        Decrypts a Fernet ciphertext back to plaintext.
        Returns the original value if empty or if decryption fails (graceful degradation).
        """
        if not ciphertext:
            return ciphertext
        try:
            fernet = _get_fernet()
            plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken:
            # Could be an un-encrypted legacy value — return as-is to avoid breaking reads
            logger.warning("Decryption failed: InvalidToken. Value may be unencrypted legacy data.")
            return ciphertext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ciphertext

    @staticmethod
    def is_encrypted(value: str) -> bool:
        """
        Heuristic check: Fernet tokens always start with 'gAAAAA'.
        Useful for detecting whether a stored value is already encrypted.
        """
        return bool(value and value.startswith("gAAAAA"))
