"""Tests for the backup rotation / retention module."""

from datetime import UTC, datetime, timedelta

from termbackup.rotation import compute_backups_to_prune


def _make_backup(backup_id, days_ago=0):
    """Helper to create a backup entry with a timestamp N days ago."""
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    return {
        "id": backup_id,
        "filename": f"backup_{backup_id[:12]}.tbk",
        "created_at": ts.isoformat(),
        "size": 1024,
        "file_count": 5,
        "verified": False,
    }


class TestComputeBackupsToPrune:
    def test_no_limits_returns_empty(self):
        backups = [_make_backup("a" * 64), _make_backup("b" * 64)]
        result = compute_backups_to_prune(backups)
        assert result == []

    def test_max_backups_prunes_oldest(self):
        backups = [
            _make_backup("a" * 64, days_ago=3),
            _make_backup("b" * 64, days_ago=2),
            _make_backup("c" * 64, days_ago=1),
        ]
        result = compute_backups_to_prune(backups, max_backups=2)
        assert len(result) == 1
        assert result[0]["id"] == "a" * 64

    def test_under_limit_returns_empty(self):
        backups = [_make_backup("a" * 64)]
        result = compute_backups_to_prune(backups, max_backups=5)
        assert result == []

    def test_retention_days_prunes_old(self):
        backups = [
            _make_backup("old" + "0" * 61, days_ago=100),
            _make_backup("new" + "0" * 61, days_ago=1),
        ]
        result = compute_backups_to_prune(backups, retention_days=30)
        assert len(result) == 1
        assert result[0]["id"].startswith("old")

    def test_both_limits_combined(self):
        backups = [
            _make_backup("a" * 64, days_ago=100),  # Pruned by both
            _make_backup("b" * 64, days_ago=50),   # Pruned by retention
            _make_backup("c" * 64, days_ago=5),     # Pruned by max_backups
            _make_backup("d" * 64, days_ago=1),     # Kept
        ]
        result = compute_backups_to_prune(backups, max_backups=1, retention_days=30)
        pruned_ids = {b["id"] for b in result}
        assert "a" * 64 in pruned_ids
        assert "b" * 64 in pruned_ids
        assert "c" * 64 in pruned_ids
        assert "d" * 64 not in pruned_ids

    def test_empty_list(self):
        result = compute_backups_to_prune([], max_backups=5, retention_days=30)
        assert result == []

    def test_max_backups_zero_or_negative_ignored(self):
        backups = [_make_backup("a" * 64)]
        result = compute_backups_to_prune(backups, max_backups=0)
        assert result == []

    def test_retention_days_zero_or_negative_ignored(self):
        backups = [_make_backup("a" * 64, days_ago=100)]
        result = compute_backups_to_prune(backups, retention_days=0)
        assert result == []
