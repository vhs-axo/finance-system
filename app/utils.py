import binascii
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


def get_password_hash(password: str) -> str:
    """
    Generate a secure Scrypt hash for a password.
    Format: scrypt$salt_hex$hash_hex
    """
    # Generate a random 16-byte salt
    salt = os.urandom(16)

    # Scrypt parameters (tuned for a balance of security and performance)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1, backend=default_backend())
    key = kdf.derive(password.encode("utf-8"))

    # Encode salt and key to hex for storage
    salt_hex = binascii.hexlify(salt).decode("utf-8")
    key_hex = binascii.hexlify(key).decode("utf-8")

    return f"scrypt${salt_hex}${key_hex}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if the provided password matches the stored hash.
    """
    try:
        # Parse the stored string
        parts = hashed_password.split("$")
        if len(parts) != 3 or parts[0] != "scrypt":
            return False

        _, salt_hex, key_hex = parts

        salt = binascii.unhexlify(salt_hex)
        stored_key = binascii.unhexlify(key_hex)

        # Re-derive key using the same parameters and salt
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1, backend=default_backend())

        # verify() raises an exception if the key doesn't match
        kdf.verify(plain_password.encode("utf-8"), stored_key)
        return True

    except Exception:
        # Catch generic errors (bad format, verification failure, etc.)
        return False
