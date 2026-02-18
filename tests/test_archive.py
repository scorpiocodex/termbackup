"""Tests for the .tbk archive format (v1 and v2)."""

import struct
from pathlib import Path

import pytest

from termbackup import archive, crypto


def test_create_and_read_v2_archive(tmp_path: Path):
    """Test creating and reading a TBK2 archive."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("hello world")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "file2.txt").write_text("nested content")

    manifest_data = {
        "version": "1.0",
        "backup_id": "test123",
        "created_at": "2024-01-01T00:00:00+00:00",
        "files": [
            {"relative_path": "file1.txt", "size": 11, "sha256": "abc"},
            {"relative_path": "subdir/file2.txt", "size": 14, "sha256": "def"},
        ],
    }

    archive_path = tmp_path / "test.tbk"
    password = "testpassword"

    archive.create_archive(archive_path, source_dir, manifest_data, password)

    assert archive_path.exists()
    assert archive_path.stat().st_size > 0

    # Read header — should be v2
    header = archive.read_archive_header(archive_path)
    assert header.version == 2
    assert header.kdf_algorithm == "argon2id"
    assert len(header.salt) == crypto.ARGON2_SALT_LENGTH
    assert len(header.iv_or_nonce) == crypto.GCM_NONCE_LENGTH
    assert header.payload_len > 0

    # Read and decrypt payload
    payload = archive.read_archive_payload(archive_path, password, header)
    assert len(payload) > 0


def test_archive_magic_validation(tmp_path: Path):
    bad_archive = tmp_path / "bad.tbk"
    bad_archive.write_bytes(b"XXXX" + b"\x00" * 100)

    from termbackup.errors import ArchiveError
    with pytest.raises(ArchiveError, match="Not a valid .tbk archive"):
        archive.read_archive_header(bad_archive)


def test_v1_magic_with_bad_version(tmp_path: Path):
    """TBK1 magic with unsupported version should raise."""
    bad_archive = tmp_path / "bad.tbk"
    bad_archive.write_bytes(archive.MAGIC_V1 + struct.pack("!B", 99) + b"\x00" * 100)

    with pytest.raises(ValueError, match="Unsupported v1 archive version"):
        archive.read_archive_header(bad_archive)


def test_v2_magic_with_bad_version(tmp_path: Path):
    """TBK2 magic with unsupported version should raise."""
    bad_archive = tmp_path / "bad.tbk"
    bad_archive.write_bytes(archive.MAGIC_V2 + struct.pack("!B", 99) + b"\x00" * 100)

    with pytest.raises(ValueError, match="Unsupported v2 archive version"):
        archive.read_archive_header(bad_archive)


def test_v2_roundtrip_with_manifest_model(tmp_path: Path):
    """Test roundtrip with ManifestData Pydantic model."""
    from termbackup.models import FileMetadata, ManifestData

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test.txt").write_text("test data")

    manifest = ManifestData(
        version="1.0",
        os_name="Test",
        python_version="3.12",
        architecture="x86_64",
        created_at="2024-01-01T00:00:00+00:00",
        backup_id="test_id",
        files=[
            FileMetadata(
                relative_path="test.txt",
                size=9,
                sha256="a" * 64,
                permissions=33206,
                modified_at=1700000000.0,
            )
        ],
    )

    archive_path = tmp_path / "model_test.tbk"
    archive.create_archive(archive_path, source_dir, manifest, "password")

    header = archive.read_archive_header(archive_path)
    payload = archive.read_archive_payload(archive_path, "password", header)
    assert len(payload) > 0
