"""Tests for the backup module."""

import gzip
import io
import json
import tarfile
import pytest
from pathlib import Path

from termbackup.backup import (
    BackupError,
    BackupManifest,
    FileEntry,
    create_archive,
    create_backup,
    scan_files,
)
from termbackup.config import Profile
from termbackup.crypto import decrypt_data


class TestScanFiles:
    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        profile = Profile(name="test", source_directory=str(tmp_path))

        files = scan_files(profile)
        assert len(files) == 0

    def test_scan_with_files(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        profile = Profile(name="test", source_directory=str(tmp_path))

        files = scan_files(profile)
        assert len(files) == 3

        paths = [f.relative_path for f in files]
        assert "file1.txt" in paths
        assert "file2.py" in paths

    def test_scan_excludes_git(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")

        profile = Profile(name="test", source_directory=str(tmp_path))

        files = scan_files(profile)
        paths = [f.relative_path for f in files]

        assert "file.txt" in paths
        assert ".git/config" not in paths
        assert ".git\\config" not in paths

    def test_scan_custom_excludes(self, tmp_path: Path) -> None:
        (tmp_path / "keep.txt").write_text("keep")
        (tmp_path / "exclude.log").write_text("exclude")

        profile = Profile(
            name="test",
            source_directory=str(tmp_path),
            exclude_patterns=["*.log"],
        )

        files = scan_files(profile)
        paths = [f.relative_path for f in files]

        assert "keep.txt" in paths
        assert "exclude.log" not in paths

    def test_scan_nonexistent_directory(self) -> None:
        profile = Profile(
            name="test",
            source_directory="/nonexistent/path",
        )

        with pytest.raises(BackupError):
            scan_files(profile)

    def test_file_entry_properties(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        profile = Profile(name="test", source_directory=str(tmp_path))

        files = scan_files(profile)
        assert len(files) == 1

        entry = files[0]
        assert entry.path == test_file
        assert entry.relative_path == "test.txt"
        assert entry.size == len("test content")
        assert entry.hash is not None
        assert len(entry.hash) == 64


class TestCreateArchive:
    def test_create_archive_basic(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        profile = Profile(name="test", source_directory=str(tmp_path))
        files = scan_files(profile)

        archive_data = create_archive(files, tmp_path)

        assert len(archive_data) > 0

        buffer = io.BytesIO(archive_data)
        with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
            with tarfile.open(fileobj=gz, mode="r") as tar:
                names = tar.getnames()
                assert "file1.txt" in names
                assert "file2.txt" in names

    def test_create_archive_preserves_content(self, tmp_path: Path) -> None:
        original_content = "Hello, World!"
        (tmp_path / "test.txt").write_text(original_content)

        profile = Profile(name="test", source_directory=str(tmp_path))
        files = scan_files(profile)

        archive_data = create_archive(files, tmp_path)

        buffer = io.BytesIO(archive_data)
        with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
            with tarfile.open(fileobj=gz, mode="r") as tar:
                member = tar.getmember("test.txt")
                f = tar.extractfile(member)
                assert f is not None
                content = f.read().decode("utf-8")
                assert content == original_content


class TestCreateBackup:
    def test_create_backup_dry_run(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("content")

        profile = Profile(name="test", source_directory=str(tmp_path))

        encrypted_data, manifest = create_backup(profile, "password", dry_run=True)

        assert encrypted_data is None
        assert manifest.backup_name.startswith("backup_")
        assert manifest.file_count == 1
        assert manifest.profile_name == "test"

    def test_create_backup_full(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        profile = Profile(name="test", source_directory=str(tmp_path))
        password = "secure_password"

        encrypted_data, manifest = create_backup(profile, password, dry_run=False)

        assert encrypted_data is not None
        assert len(encrypted_data) > 0
        assert manifest.file_count == 2
        assert manifest.encrypted_size == len(encrypted_data)
        assert manifest.compressed_size > 0
        assert manifest.total_size > 0

    def test_create_backup_can_decrypt(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("test content")

        profile = Profile(name="test", source_directory=str(tmp_path))
        password = "password123"

        encrypted_data, manifest = create_backup(profile, password, dry_run=False)

        decrypted = decrypt_data(encrypted_data, password)

        header_size = int.from_bytes(decrypted[:4], "big")
        manifest_json = decrypted[4 : 4 + header_size]
        archive_data = decrypted[4 + header_size :]

        parsed_manifest = json.loads(manifest_json.decode("utf-8"))
        assert parsed_manifest["backup_name"] == manifest.backup_name
        assert parsed_manifest["file_count"] == 1

        buffer = io.BytesIO(archive_data)
        with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
            with tarfile.open(fileobj=gz, mode="r") as tar:
                assert "file.txt" in tar.getnames()

    def test_create_backup_empty_directory(self, tmp_path: Path) -> None:
        profile = Profile(name="test", source_directory=str(tmp_path))

        with pytest.raises(BackupError):
            create_backup(profile, "password")


class TestBackupManifest:
    def test_manifest_to_dict(self) -> None:
        manifest = BackupManifest(
            backup_name="backup_20240101_120000.tbk",
            profile_name="test",
            source_directory="/data",
            file_count=5,
            total_size=1000,
            compressed_size=500,
            encrypted_size=520,
            files=[{"path": "file.txt", "size": 100, "hash": "abc123"}],
            checksum="xyz789",
        )

        data = manifest.to_dict()

        assert data["backup_name"] == "backup_20240101_120000.tbk"
        assert data["file_count"] == 5
        assert len(data["files"]) == 1

    def test_manifest_from_dict(self) -> None:
        data = {
            "backup_name": "backup_20240101_120000.tbk",
            "profile_name": "test",
            "source_directory": "/data",
            "file_count": 5,
            "total_size": 1000,
            "compressed_size": 500,
            "encrypted_size": 520,
            "files": [{"path": "file.txt", "size": 100, "hash": "abc123"}],
            "checksum": "xyz789",
        }

        manifest = BackupManifest.from_dict(data)

        assert manifest.backup_name == "backup_20240101_120000.tbk"
        assert manifest.file_count == 5
        assert len(manifest.files) == 1

    def test_manifest_to_json(self) -> None:
        manifest = BackupManifest(
            backup_name="backup_20240101_120000.tbk",
            profile_name="test",
            source_directory="/data",
            file_count=1,
            total_size=100,
            compressed_size=50,
            encrypted_size=60,
            files=[],
            checksum="abc",
        )

        json_str = manifest.to_json()
        parsed = json.loads(json_str)

        assert parsed["backup_name"] == "backup_20240101_120000.tbk"
