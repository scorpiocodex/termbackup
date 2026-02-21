"""Cryptographic operations for TermBackup.

v1: AES-256-CBC + PBKDF2 + HMAC-SHA256 (legacy, preserved for backward compat)
v2: AES-256-GCM + Argon2id (new default)
"""

import secrets

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ── v1 Constants (legacy) ────────────────────────────────────────────────────
PBKDF2_ITERATIONS = 600_000
SALT_LENGTH = 32
KEY_LENGTH = 64  # 32 for AES, 32 for HMAC
AES_KEY_LENGTH = 32
HMAC_KEY_LENGTH = 32

# ── v2 Constants (Argon2id + AES-GCM) ────────────────────────────────────────
ARGON2_MEMORY_COST = 65536  # 64 MiB
ARGON2_TIME_COST = 3
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32  # 256-bit AES key
ARGON2_SALT_LENGTH = 32
GCM_NONCE_LENGTH = 12  # 96-bit standard


# ═══════════════════════════════════════════════════════════════════════════════
# v1 Functions (legacy — preserved verbatim for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════════


def derive_keys(password: str, salt: bytes) -> tuple[bytes, bytes]:
    """Derives encryption and HMAC keys from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    derived_key = kdf.derive(password.encode())

    aes_key = derived_key[:AES_KEY_LENGTH]
    hmac_key = derived_key[AES_KEY_LENGTH:]

    return aes_key, hmac_key


def encrypt(data: bytes, password: str) -> tuple[bytes, bytes, bytes, bytes]:
    """Encrypts data with AES-256-CBC and signs it with HMAC-SHA256."""
    salt = secrets.token_bytes(SALT_LENGTH)
    aes_key, hmac_key = derive_keys(password, salt)

    iv = secrets.token_bytes(16)
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Add padding to the data
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Sign the ciphertext (Encrypt-then-MAC)
    h = hmac.HMAC(hmac_key, hashes.SHA256(), backend=default_backend())
    h.update(iv + ciphertext)
    hmac_signature = h.finalize()

    return salt, iv, ciphertext, hmac_signature


def decrypt(
    password: str, salt: bytes, iv: bytes, ciphertext: bytes, hmac_signature: bytes
) -> bytes:
    """Decrypts data after verifying the HMAC signature."""
    aes_key, hmac_key = derive_keys(password, salt)

    # Verify HMAC
    h = hmac.HMAC(hmac_key, hashes.SHA256(), backend=default_backend())
    h.update(iv + ciphertext)
    h.verify(hmac_signature)

    # Decrypt
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove padding
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext


# ═══════════════════════════════════════════════════════════════════════════════
# v2 Functions (AES-256-GCM + Argon2id)
# ═══════════════════════════════════════════════════════════════════════════════


def derive_key_argon2id(password: str, salt: bytes) -> bytes:
    """Derives a 256-bit AES key using Argon2id."""
    from argon2.low_level import Type, hash_secret_raw

    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def encrypt_v2(data: bytes, password: str) -> tuple[bytes, bytes, bytes]:
    """Encrypts data with AES-256-GCM using Argon2id key derivation.

    Returns:
        (salt, nonce, ciphertext_with_tag) — GCM tag is appended (16 bytes).
    """
    salt = secrets.token_bytes(ARGON2_SALT_LENGTH)
    nonce = secrets.token_bytes(GCM_NONCE_LENGTH)
    key = derive_key_argon2id(password, salt)

    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)

    return salt, nonce, ciphertext_with_tag


def decrypt_v2(password: str, salt: bytes, nonce: bytes, ciphertext_with_tag: bytes) -> bytes:
    """Decrypts AES-256-GCM data. Raises InvalidTag on tamper."""
    key = derive_key_argon2id(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext_with_tag, None)
