"""Encryption and key derivation for TermBackup.

Uses AES-256 via Fernet with PBKDF2-HMAC-SHA256 for key derivation.
"""

import base64
import os
import secrets
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


SALT_SIZE = 16
ITERATIONS = 600_000


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


def generate_salt() -> bytes:
    """Generate a cryptographically secure random salt."""
    return secrets.token_bytes(SALT_SIZE)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from password using PBKDF2-HMAC-SHA256.

    Args:
        password: User-provided password.
        salt: Random salt bytes.

    Returns:
        Base64-encoded 32-byte key suitable for Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def encrypt_data(data: bytes, password: str) -> bytes:
    """Encrypt data using AES-256 (Fernet) with password-derived key.

    The salt is prepended to the encrypted output.

    Args:
        data: Plaintext data to encrypt.
        password: User-provided password.

    Returns:
        Salt + encrypted data.
    """
    salt = generate_salt()
    key = derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)
    return salt + encrypted


def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
    """Decrypt data using AES-256 (Fernet) with password-derived key.

    Expects salt to be prepended to encrypted data.

    Args:
        encrypted_data: Salt + encrypted data.
        password: User-provided password.

    Returns:
        Decrypted plaintext data.

    Raises:
        CryptoError: If decryption fails (wrong password or corrupted data).
    """
    if len(encrypted_data) < SALT_SIZE:
        raise CryptoError("Invalid encrypted data: too short")

    salt = encrypted_data[:SALT_SIZE]
    ciphertext = encrypted_data[SALT_SIZE:]

    key = derive_key(password, salt)
    fernet = Fernet(key)

    try:
        return fernet.decrypt(ciphertext)
    except InvalidToken as e:
        raise CryptoError("Decryption failed: wrong password or corrupted data") from e


def encrypt_file(source_path: Path, dest_path: Path, password: str) -> None:
    """Encrypt a file and write to destination.

    Args:
        source_path: Path to plaintext file.
        dest_path: Path to write encrypted file.
        password: User-provided password.
    """
    data = source_path.read_bytes()
    encrypted = encrypt_data(data, password)
    dest_path.write_bytes(encrypted)


def decrypt_file(source_path: Path, dest_path: Path, password: str) -> None:
    """Decrypt a file and write to destination.

    Args:
        source_path: Path to encrypted file.
        dest_path: Path to write decrypted file.
        password: User-provided password.

    Raises:
        CryptoError: If decryption fails.
    """
    encrypted_data = source_path.read_bytes()
    decrypted = decrypt_data(encrypted_data, password)
    dest_path.write_bytes(decrypted)


def secure_delete(path: Path, passes: int = 3) -> None:
    """Securely delete a file by overwriting with random data.

    Args:
        path: Path to file to delete.
        passes: Number of overwrite passes.
    """
    if not path.exists():
        return

    file_size = path.stat().st_size

    try:
        with open(path, "r+b") as f:
            for _ in range(passes):
                f.seek(0)
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
    except (OSError, IOError):
        pass
    finally:
        try:
            path.unlink()
        except (OSError, IOError):
            pass


def verify_password(encrypted_data: bytes, password: str) -> bool:
    """Verify if password can decrypt the data without returning plaintext.

    Args:
        encrypted_data: Salt + encrypted data.
        password: Password to verify.

    Returns:
        True if password is correct, False otherwise.
    """
    try:
        decrypt_data(encrypted_data, password)
        return True
    except CryptoError:
        return False
