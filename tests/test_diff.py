"""Tests for the diff / incremental change detection module."""


from termbackup.diff import compute_changes


def _file(path, sha="a" * 64, size=100):
    return {"relative_path": path, "sha256": sha, "size": size}


class TestComputeChanges:
    def test_no_changes(self):
        current = {"files": [_file("a.txt"), _file("b.txt")]}
        previous = {"files": [_file("a.txt"), _file("b.txt")]}
        result = compute_changes(current, previous)
        assert result["added"] == []
        assert result["modified"] == []
        assert result["deleted"] == []
        assert len(result["unchanged"]) == 2

    def test_new_files_added(self):
        current = {"files": [_file("a.txt"), _file("b.txt"), _file("c.txt")]}
        previous = {"files": [_file("a.txt")]}
        result = compute_changes(current, previous)
        assert len(result["added"]) == 2
        paths = [f["relative_path"] for f in result["added"]]
        assert "b.txt" in paths
        assert "c.txt" in paths

    def test_files_modified(self):
        current = {"files": [_file("a.txt", sha="b" * 64)]}
        previous = {"files": [_file("a.txt", sha="a" * 64)]}
        result = compute_changes(current, previous)
        assert len(result["modified"]) == 1
        assert result["modified"][0]["relative_path"] == "a.txt"

    def test_files_deleted(self):
        current = {"files": [_file("a.txt")]}
        previous = {"files": [_file("a.txt"), _file("b.txt")]}
        result = compute_changes(current, previous)
        assert len(result["deleted"]) == 1
        assert result["deleted"][0]["relative_path"] == "b.txt"

    def test_mixed_changes(self):
        current = {"files": [
            _file("kept.txt", sha="a" * 64),
            _file("modified.txt", sha="b" * 64),
            _file("new.txt", sha="c" * 64),
        ]}
        previous = {"files": [
            _file("kept.txt", sha="a" * 64),
            _file("modified.txt", sha="x" * 64),
            _file("removed.txt", sha="d" * 64),
        ]}
        result = compute_changes(current, previous)
        assert len(result["added"]) == 1
        assert len(result["modified"]) == 1
        assert len(result["deleted"]) == 1
        assert len(result["unchanged"]) == 1

    def test_empty_manifests(self):
        result = compute_changes({"files": []}, {"files": []})
        assert result == {"added": [], "modified": [], "deleted": [], "unchanged": []}
