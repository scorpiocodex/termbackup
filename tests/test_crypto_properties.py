"""Property-based tests for cryptographic functions using Hypothesis."""


import pytest

try:
    from hypothesis import given, settings
    from hypothesis.strategies import binary, text

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

from termbackup import crypto

pytestmark = pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")


class TestV2EncryptDecryptProperties:
    @given(data=binary(min_size=0, max_size=10000), password=text(min_size=1, max_size=50))
    @settings(max_examples=10, deadline=30000)
    def test_roundtrip(self, data, password):
        """Any binary data + any non-empty password should roundtrip."""
        salt, nonce, ciphertext = crypto.encrypt_v2(data, password)
        result = crypto.decrypt_v2(password, salt, nonce, ciphertext)
        assert result == data

    @given(data=binary(min_size=1, max_size=1000))
    @settings(max_examples=5, deadline=30000)
    def test_unique_salt_and_nonce(self, data):
        """Each encryption should produce unique salt and nonce."""
        salt1, nonce1, _ = crypto.encrypt_v2(data, "password")
        salt2, nonce2, _ = crypto.encrypt_v2(data, "password")
        assert salt1 != salt2 or nonce1 != nonce2

    @given(data=binary(min_size=1, max_size=1000))
    @settings(max_examples=5, deadline=30000)
    def test_different_passwords_different_ciphertext(self, data):
        """Different passwords should produce different ciphertext."""
        _, _, ct1 = crypto.encrypt_v2(data, "password1")
        _, _, ct2 = crypto.encrypt_v2(data, "password2")
        assert ct1 != ct2

    @given(data=binary(min_size=1, max_size=1000))
    @settings(max_examples=5, deadline=30000)
    def test_tampered_ciphertext_fails(self, data):
        """Flipping a bit in ciphertext should cause decryption to fail."""
        salt, nonce, ciphertext = crypto.encrypt_v2(data, "testpass")

        # Flip the first byte
        tampered = bytes([ciphertext[0] ^ 0xFF]) + ciphertext[1:]

        with pytest.raises(Exception):
            crypto.decrypt_v2("testpass", salt, nonce, tampered)


class TestV1EncryptDecryptProperties:
    @given(data=binary(min_size=1, max_size=1000), password=text(min_size=1, max_size=20))
    @settings(max_examples=3, deadline=120000)
    def test_roundtrip(self, data, password):
        """V1 encrypt/decrypt should roundtrip."""
        salt, iv, ciphertext, hmac_sig = crypto.encrypt(data, password)
        result = crypto.decrypt(password, salt, iv, ciphertext, hmac_sig)
        assert result == data
