from pathlib import Path

from termbackup.utils import (
    canonicalize_dict,
    find_backup_in_ledger,
    format_size,
    format_timestamp,
    hash_file,
    is_path_safe,
)


def test_canonicalize_dict():
    result = canonicalize_dict({"b": 2, "a": 1})
    assert result == '{"a":1,"b":2}'


def test_canonicalize_dict_nested():
    result = canonicalize_dict({"z": {"b": 2, "a": 1}, "a": 0})
    assert result == '{"a":0,"z":{"a":1,"b":2}}'


def test_hash_file(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    result = hash_file(test_file)
    assert len(result) == 64
    # Known SHA-256 of "hello"
    assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_find_backup_in_ledger():
    ledger = {
        "backups": [
            {"id": "abc123def456", "filename": "backup.tbk"},
            {"id": "xyz789abc012", "filename": "backup2.tbk"},
        ]
    }
    result = find_backup_in_ledger(ledger, "abc123")
    assert result is not None
    assert result["filename"] == "backup.tbk"


def test_find_backup_in_ledger_not_found():
    ledger = {"backups": [{"id": "abc123", "filename": "backup.tbk"}]}
    result = find_backup_in_ledger(ledger, "notexist")
    assert result is None


def test_find_backup_in_ledger_empty():
    result = find_backup_in_ledger({}, "abc")
    assert result is None


def test_format_size():
    assert format_size(500) == "500 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1536) == "1.5 KB"
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.00 GB"


def test_format_timestamp():
    result = format_timestamp("2024-01-15T10:30:00+00:00")
    assert "2024-01-15" in result
    assert "10:30:00" in result


def test_format_timestamp_invalid():
    result = format_timestamp("not-a-date")
    assert result == "not-a-date"


def test_is_path_safe(tmp_path: Path):
    assert is_path_safe("subdir/file.txt", tmp_path) is True
    assert is_path_safe("file.txt", tmp_path) is True


def test_is_path_safe_traversal(tmp_path: Path):
    assert is_path_safe("../../etc/passwd", tmp_path) is False
    assert is_path_safe("../secret.txt", tmp_path) is False
