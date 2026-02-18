import pytest
from cryptography.exceptions import InvalidSignature, InvalidTag

from termbackup import crypto

# ═══════════════════════════════════════════════════════════════════════════════
# v1 Tests (legacy AES-CBC + PBKDF2)
# ═══════════════════════════════════════════════════════════════════════════════

def test_derive_keys():
    password = "testpassword"
    salt = b"12345678901234567890123456789012"
    aes_key, hmac_key = crypto.derive_keys(password, salt)

    assert len(aes_key) == crypto.AES_KEY_LENGTH
    assert len(hmac_key) == crypto.HMAC_KEY_LENGTH

    # Determinism: same inputs produce same keys
    aes_key2, hmac_key2 = crypto.derive_keys(password, salt)
    assert aes_key == aes_key2
    assert hmac_key == hmac_key2


def test_derive_keys_different_passwords():
    salt = b"12345678901234567890123456789012"
    aes1, hmac1 = crypto.derive_keys("password1", salt)
    aes2, hmac2 = crypto.derive_keys("password2", salt)
    assert aes1 != aes2
    assert hmac1 != hmac2


def test_derive_keys_different_salts():
    password = "testpassword"
    aes1, hmac1 = crypto.derive_keys(password, b"a" * 32)
    aes2, hmac2 = crypto.derive_keys(password, b"b" * 32)
    assert aes1 != aes2
    assert hmac1 != hmac2


def test_encrypt_decrypt():
    password = "testpassword"
    data = b"This is a secret message."

    salt, iv, ciphertext, hmac_signature = crypto.encrypt(data, password)
    decrypted_data = crypto.decrypt(password, salt, iv, ciphertext, hmac_signature)

    assert data == decrypted_data


def test_encrypt_decrypt_large_payload():
    password = "strongpassword"
    data = b"X" * (1024 * 1024)  # 1MB

    salt, iv, ciphertext, hmac_signature = crypto.encrypt(data, password)
    decrypted_data = crypto.decrypt(password, salt, iv, ciphertext, hmac_signature)

    assert data == decrypted_data


def test_encrypt_decrypt_empty_data():
    password = "testpassword"
    data = b""

    salt, iv, ciphertext, hmac_signature = crypto.encrypt(data, password)
    decrypted_data = crypto.decrypt(password, salt, iv, ciphertext, hmac_signature)

    assert data == decrypted_data


def test_decrypt_invalid_hmac():
    password = "testpassword"
    data = b"This is a secret message."

    salt, iv, ciphertext, hmac_signature = crypto.encrypt(data, password)

    tampered_ciphertext = ciphertext + b"tampered"

    with pytest.raises(InvalidSignature):
        crypto.decrypt(password, salt, iv, tampered_ciphertext, hmac_signature)


def test_decrypt_wrong_password():
    password = "testpassword"
    data = b"This is a secret message."

    salt, iv, ciphertext, hmac_signature = crypto.encrypt(data, password)

    with pytest.raises(InvalidSignature):
        crypto.decrypt("wrongpassword", salt, iv, ciphertext, hmac_signature)


def test_encrypt_produces_unique_salt_and_iv():
    password = "testpassword"
    data = b"Hello"

    salt1, iv1, _, _ = crypto.encrypt(data, password)
    salt2, iv2, _, _ = crypto.encrypt(data, password)

    assert salt1 != salt2
    assert iv1 != iv2


# ═══════════════════════════════════════════════════════════════════════════════
# v2 Tests (AES-256-GCM + Argon2id)
# ═══════════════════════════════════════════════════════════════════════════════

def test_derive_key_argon2id():
    password = "testpassword"
    salt = b"a" * crypto.ARGON2_SALT_LENGTH
    key = crypto.derive_key_argon2id(password, salt)
    assert len(key) == crypto.ARGON2_HASH_LEN

    # Determinism
    key2 = crypto.derive_key_argon2id(password, salt)
    assert key == key2


def test_derive_key_argon2id_different_passwords():
    salt = b"a" * crypto.ARGON2_SALT_LENGTH
    key1 = crypto.derive_key_argon2id("password1", salt)
    key2 = crypto.derive_key_argon2id("password2", salt)
    assert key1 != key2


def test_encrypt_v2_decrypt_v2():
    password = "testpassword"
    data = b"This is a secret message for GCM."

    salt, nonce, ciphertext_with_tag = crypto.encrypt_v2(data, password)
    decrypted = crypto.decrypt_v2(password, salt, nonce, ciphertext_with_tag)

    assert data == decrypted


def test_encrypt_v2_decrypt_v2_large():
    password = "strongpassword"
    data = b"Y" * (1024 * 1024)

    salt, nonce, ciphertext_with_tag = crypto.encrypt_v2(data, password)
    decrypted = crypto.decrypt_v2(password, salt, nonce, ciphertext_with_tag)

    assert data == decrypted


def test_encrypt_v2_decrypt_v2_empty():
    password = "testpassword"
    data = b""

    salt, nonce, ciphertext_with_tag = crypto.encrypt_v2(data, password)
    decrypted = crypto.decrypt_v2(password, salt, nonce, ciphertext_with_tag)

    assert data == decrypted


def test_v2_tampered_ciphertext():
    password = "testpassword"
    data = b"Secret data"

    salt, nonce, ciphertext_with_tag = crypto.encrypt_v2(data, password)

    # Flip a byte
    tampered = bytearray(ciphertext_with_tag)
    tampered[0] ^= 0xFF
    tampered = bytes(tampered)

    with pytest.raises(InvalidTag):
        crypto.decrypt_v2(password, salt, nonce, tampered)


def test_v2_wrong_password():
    password = "testpassword"
    data = b"Secret data"

    salt, nonce, ciphertext_with_tag = crypto.encrypt_v2(data, password)

    with pytest.raises(InvalidTag):
        crypto.decrypt_v2("wrongpassword", salt, nonce, ciphertext_with_tag)


def test_v2_unique_salt_and_nonce():
    password = "testpassword"
    data = b"Hello"

    salt1, nonce1, _ = crypto.encrypt_v2(data, password)
    salt2, nonce2, _ = crypto.encrypt_v2(data, password)

    assert salt1 != salt2
    assert nonce1 != nonce2


def test_v2_nonce_length():
    password = "testpassword"
    data = b"Hello"

    salt, nonce, _ = crypto.encrypt_v2(data, password)

    assert len(salt) == crypto.ARGON2_SALT_LENGTH
    assert len(nonce) == crypto.GCM_NONCE_LENGTH
