"""Tests for the Ed25519 backup signing module."""


import pytest

from termbackup import signing


@pytest.fixture
def signing_dir(tmp_path, monkeypatch):
    """Redirects signing key paths to tmp directory."""
    monkeypatch.setattr(signing, "SIGNING_KEY_PATH", tmp_path / "signing_key.pem")
    monkeypatch.setattr(signing, "SIGNING_PUB_PATH", tmp_path / "signing_key.pub")
    monkeypatch.setattr(signing, "CONFIG_DIR", tmp_path)
    return tmp_path


class TestHasSigningKey:
    def test_no_keys(self, signing_dir):
        assert signing.has_signing_key() is False

    def test_only_private(self, signing_dir):
        (signing_dir / "signing_key.pem").write_text("dummy")
        assert signing.has_signing_key() is False

    def test_only_public(self, signing_dir):
        (signing_dir / "signing_key.pub").write_text("dummy")
        assert signing.has_signing_key() is False

    def test_both_keys(self, signing_dir):
        signing.generate_signing_key("testpass")
        assert signing.has_signing_key() is True


class TestGenerateSigningKey:
    def test_creates_keypair(self, signing_dir):
        signing.generate_signing_key("mypassword")

        assert signing.SIGNING_KEY_PATH.exists()
        assert signing.SIGNING_PUB_PATH.exists()

        # Private key should be PEM encrypted
        pem = signing.SIGNING_KEY_PATH.read_text()
        assert "ENCRYPTED" in pem

        # Public key should be PEM
        pub = signing.SIGNING_PUB_PATH.read_text()
        assert "PUBLIC KEY" in pub


class TestSignAndVerify:
    def test_roundtrip(self, signing_dir, tmp_path):
        signing.generate_signing_key("testpass")

        archive = tmp_path / "backup.tbk"
        archive.write_bytes(b"fake archive data for signing test")

        signature = signing.sign_archive(archive, "testpass")
        assert len(signature) == 64

        assert signing.verify_signature(archive, signature) is True

    def test_tampered_data_fails(self, signing_dir, tmp_path):
        signing.generate_signing_key("testpass")

        archive = tmp_path / "backup.tbk"
        archive.write_bytes(b"original data")

        signature = signing.sign_archive(archive, "testpass")

        # Tamper with the archive
        archive.write_bytes(b"tampered data")
        assert signing.verify_signature(archive, signature) is False

    def test_wrong_password_fails(self, signing_dir, tmp_path):
        signing.generate_signing_key("correctpass")

        archive = tmp_path / "backup.tbk"
        archive.write_bytes(b"test data")

        with pytest.raises(Exception):
            signing.sign_archive(archive, "wrongpass")

    def test_different_archives_different_signatures(self, signing_dir, tmp_path):
        signing.generate_signing_key("testpass")

        archive1 = tmp_path / "a.tbk"
        archive1.write_bytes(b"data1")
        archive2 = tmp_path / "b.tbk"
        archive2.write_bytes(b"data2")

        sig1 = signing.sign_archive(archive1, "testpass")
        sig2 = signing.sign_archive(archive2, "testpass")
        assert sig1 != sig2
