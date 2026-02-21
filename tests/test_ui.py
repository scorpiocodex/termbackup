"""Tests for the UI module."""

from io import StringIO

import pytest
from rich.console import Console

from termbackup import __version__, ui


@pytest.fixture(autouse=True)
def capture_console(monkeypatch):
    """Replaces the global console with one that writes to a StringIO buffer."""
    buffer = StringIO()
    test_console = Console(file=buffer, force_terminal=False, no_color=True, width=120)
    monkeypatch.setattr(ui, "console", test_console)
    return buffer


class TestStatusMessages:
    def test_info(self, capture_console):
        ui.info("Test info message")
        output = capture_console.getvalue()
        assert "Test info message" in output

    def test_success(self, capture_console):
        ui.success("Test success")
        output = capture_console.getvalue()
        assert "Test success" in output

    def test_warning(self, capture_console):
        ui.warning("Test warning")
        output = capture_console.getvalue()
        assert "Test warning" in output

    def test_error(self, capture_console):
        ui.error("Test error")
        output = capture_console.getvalue()
        assert "Test error" in output

    def test_step(self, capture_console):
        ui.step("Doing step")
        output = capture_console.getvalue()
        assert "Doing step" in output


class TestStepProgress:
    def test_step_progress(self, capture_console):
        ui.print_step_progress(2, 5, "Processing")
        output = capture_console.getvalue()
        assert "2/5" in output
        assert "Processing" in output


class TestStatusBadge:
    def test_success_badge(self):
        badge = ui.status_badge("verified", "success")
        assert "VERIFIED" in badge.plain

    def test_error_badge(self):
        badge = ui.status_badge("failed", "error")
        assert "FAILED" in badge.plain


class TestConfirm:
    def test_yes(self, monkeypatch, capture_console):
        monkeypatch.setattr(ui.console, "input", lambda *a, **kw: "y")
        assert ui.confirm("Continue?") is True

    def test_yes_full(self, monkeypatch, capture_console):
        monkeypatch.setattr(ui.console, "input", lambda *a, **kw: "yes")
        assert ui.confirm("Continue?") is True

    def test_no(self, monkeypatch, capture_console):
        monkeypatch.setattr(ui.console, "input", lambda *a, **kw: "n")
        assert ui.confirm("Continue?") is False

    def test_empty(self, monkeypatch, capture_console):
        monkeypatch.setattr(ui.console, "input", lambda *a, **kw: "")
        assert ui.confirm("Continue?") is False

    def test_other(self, monkeypatch, capture_console):
        monkeypatch.setattr(ui.console, "input", lambda *a, **kw: "maybe")
        assert ui.confirm("Continue?") is False


class TestCreateTable:
    def test_column_count(self, capture_console):
        table = ui.create_table("Col1", "Col2", "Col3")
        assert len(table.columns) == 3

    def test_with_title(self, capture_console):
        table = ui.create_table("A", "B", title="My Table")
        assert table.title is not None

    def test_with_row_numbers(self, capture_console):
        table = ui.create_table("A", "B", show_row_numbers=True)
        assert len(table.columns) == 3  # # + A + B


class TestPrintBanner:
    def test_contains_version(self, capture_console):
        ui.print_banner()
        output = capture_console.getvalue()
        assert __version__ in output

    def test_contains_encryption_info(self, capture_console):
        ui.print_banner()
        output = capture_console.getvalue()
        assert "AES-256-GCM" in output


class TestSummaryPanel:
    def test_summary_panel(self, capture_console):
        ui.print_summary_panel("Test Title", [
            ("Key1", "Value1"),
            ("Key2", "Value2"),
        ])
        output = capture_console.getvalue()
        assert "Test Title" in output
        assert "Key1" in output
        assert "Value1" in output


class TestChecklist:
    def test_checklist(self, capture_console):
        ui.print_checklist([
            ("Check 1", True, "Passed"),
            ("Check 2", False, "Failed"),
        ])
        output = capture_console.getvalue()
        assert "Check 1" in output
        assert "Check 2" in output


class TestPrintEmpty:
    def test_with_suggestion(self, capture_console):
        ui.print_empty("No data", suggestion="Try something")
        output = capture_console.getvalue()
        assert "No data" in output
        assert "Try something" in output
