"""Tests for the crypto module."""

import pytest
from pathlib import Path
import tempfile

from termbackup.crypto import (
    CryptoError,
    decrypt_data,
    decrypt_file,
    derive_key,
    encrypt_data,
    encrypt_file,
    generate_salt,
    secure_delete,
    verify_password,
    SALT_SIZE,
)


class TestSaltGeneration:
    def test_generate_salt_length(self) -> None:
        salt = generate_salt()
        assert len(salt) == SALT_SIZE

    def test_generate_salt_randomness(self) -> None:
        salt1 = generate_salt()
        salt2 = generate_salt()
        assert salt1 != salt2


class TestKeyDerivation:
    def test_derive_key_consistency(self) -> None:
        password = "test_password"
        salt = generate_salt()

        key1 = derive_key(password, salt)
        key2 = derive_key(password, salt)

        assert key1 == key2

    def test_derive_key_different_salts(self) -> None:
        password = "test_password"
        salt1 = generate_salt()
        salt2 = generate_salt()

        key1 = derive_key(password, salt1)
        key2 = derive_key(password, salt2)

        assert key1 != key2

    def test_derive_key_different_passwords(self) -> None:
        salt = generate_salt()

        key1 = derive_key("password1", salt)
        key2 = derive_key("password2", salt)

        assert key1 != key2


class TestEncryptDecrypt:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        data = b"Hello, World! This is a test message."
        password = "secure_password_123"

        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == data

    def test_encrypted_data_different_from_original(self) -> None:
        data = b"Test data"
        password = "password"

        encrypted = encrypt_data(data, password)

        assert encrypted != data
        assert len(encrypted) > len(data)

    def test_decrypt_with_wrong_password(self) -> None:
        data = b"Secret message"
        password = "correct_password"
        wrong_password = "wrong_password"

        encrypted = encrypt_data(data, password)

        with pytest.raises(CryptoError):
            decrypt_data(encrypted, wrong_password)

    def test_decrypt_corrupted_data(self) -> None:
        data = b"Test data"
        password = "password"

        encrypted = encrypt_data(data, password)
        corrupted = encrypted[:-10] + b"corrupted!"

        with pytest.raises(CryptoError):
            decrypt_data(corrupted, password)

    def test_decrypt_too_short_data(self) -> None:
        with pytest.raises(CryptoError):
            decrypt_data(b"short", "password")

    def test_empty_data(self) -> None:
        data = b""
        password = "password"

        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == data

    def test_large_data(self) -> None:
        data = b"x" * (1024 * 1024)
        password = "password"

        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == data

    def test_unicode_password(self) -> None:
        data = b"Test data"
        password = "pässwörd_日本語"

        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == data


class TestFileEncryption:
    def test_encrypt_decrypt_file(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        encrypted_path = tmp_path / "encrypted.bin"
        decrypted_path = tmp_path / "decrypted.txt"

        original_content = b"File content to encrypt"
        source.write_bytes(original_content)
        password = "file_password"

        encrypt_file(source, encrypted_path, password)
        assert encrypted_path.exists()
        assert encrypted_path.read_bytes() != original_content

        decrypt_file(encrypted_path, decrypted_path, password)
        assert decrypted_path.exists()
        assert decrypted_path.read_bytes() == original_content


class TestSecureDelete:
    def test_secure_delete_removes_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "to_delete.txt"
        test_file.write_bytes(b"sensitive data")

        assert test_file.exists()
        secure_delete(test_file)
        assert not test_file.exists()

    def test_secure_delete_nonexistent_file(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent.txt"
        secure_delete(nonexistent)


class TestVerifyPassword:
    def test_verify_correct_password(self) -> None:
        data = b"Test data"
        password = "correct"

        encrypted = encrypt_data(data, password)
        assert verify_password(encrypted, password) is True

    def test_verify_wrong_password(self) -> None:
        data = b"Test data"
        password = "correct"

        encrypted = encrypt_data(data, password)
        assert verify_password(encrypted, "wrong") is False
