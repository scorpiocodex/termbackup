"""Tests for the utils module."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from termbackup.utils import (
    BACKUP_EXTENSION,
    calculate_data_hash,
    calculate_file_hash,
    format_size,
    generate_backup_name,
    matches_pattern,
    normalize_backup_id,
    parse_backup_name,
    scan_directory,
    should_exclude,
    validate_backup_id,
)


class TestBackupNaming:
    def test_generate_backup_name_format(self) -> None:
        name = generate_backup_name()
        assert name.startswith("backup_")
        assert name.endswith(BACKUP_EXTENSION)
        assert len(name) == len("backup_YYYYMMDD_HHMMSS.tbk")

    def test_parse_backup_name_valid(self) -> None:
        name = "backup_20240101_120000.tbk"
        result = parse_backup_name(name)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0

    def test_parse_backup_name_invalid(self) -> None:
        assert parse_backup_name("invalid.tbk") is None
        assert parse_backup_name("backup_invalid.tbk") is None
        assert parse_backup_name("backup_20240101.tbk") is None

    def test_validate_backup_id_valid(self) -> None:
        assert validate_backup_id("backup_20240101_120000.tbk") is True
        assert validate_backup_id("backup_20240101_120000") is True

    def test_validate_backup_id_invalid(self) -> None:
        assert validate_backup_id("invalid") is False
        assert validate_backup_id("backup_invalid.tbk") is False

    def test_normalize_backup_id(self) -> None:
        assert normalize_backup_id("backup_20240101_120000") == "backup_20240101_120000.tbk"
        assert normalize_backup_id("backup_20240101_120000.tbk") == "backup_20240101_120000.tbk"


class TestHashing:
    def test_calculate_data_hash(self) -> None:
        data = b"test data"
        hash1 = calculate_data_hash(data)
        hash2 = calculate_data_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_calculate_data_hash_different_data(self) -> None:
        hash1 = calculate_data_hash(b"data1")
        hash2 = calculate_data_hash(b"data2")

        assert hash1 != hash2

    def test_calculate_file_hash(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"file content")

        hash_value = calculate_file_hash(test_file)
        assert len(hash_value) == 64


class TestFormatSize:
    def test_bytes(self) -> None:
        assert format_size(0) == "0.0 B"
        assert format_size(100) == "100.0 B"
        assert format_size(1023) == "1023.0 B"

    def test_kilobytes(self) -> None:
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"

    def test_megabytes(self) -> None:
        assert format_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self) -> None:
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"


class TestPatternMatching:
    def test_matches_pattern_glob(self) -> None:
        assert matches_pattern(Path("test.py"), "*.py") is True
        assert matches_pattern(Path("test.txt"), "*.py") is False

    def test_matches_pattern_directory(self) -> None:
        assert matches_pattern(Path(".git/config"), ".git/") is True
        assert matches_pattern(Path("src/.git/config"), ".git/") is True

    def test_should_exclude_default_patterns(self) -> None:
        assert should_exclude(Path(".git/config"), []) is True
        assert should_exclude(Path("__pycache__/module.pyc"), []) is True
        assert should_exclude(Path("node_modules/package/index.js"), []) is True
        assert should_exclude(Path("src/main.py"), []) is False

    def test_should_exclude_custom_patterns(self) -> None:
        patterns = ["*.log", "temp/"]
        assert should_exclude(Path("debug.log"), patterns) is True
        assert should_exclude(Path("temp/file.txt"), patterns) is True
        assert should_exclude(Path("src/main.py"), patterns) is False


class TestScanDirectory:
    def test_scan_directory_basic(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        files = list(scan_directory(tmp_path))
        assert len(files) == 3

    def test_scan_directory_excludes(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.pyc").write_bytes(b"bytecode")

        files = list(scan_directory(tmp_path))
        file_names = [f.name for f in files]

        assert "file.txt" in file_names
        assert "config" not in file_names
        assert "module.pyc" not in file_names

    def test_scan_directory_custom_excludes(self, tmp_path: Path) -> None:
        (tmp_path / "keep.txt").write_text("keep")
        (tmp_path / "exclude.log").write_text("exclude")

        files = list(scan_directory(tmp_path, exclude_patterns=["*.log"]))
        file_names = [f.name for f in files]

        assert "keep.txt" in file_names
        assert "exclude.log" not in file_names
