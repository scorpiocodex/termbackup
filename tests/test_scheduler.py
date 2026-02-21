"""Tests for the OS-native scheduler module."""

from unittest.mock import MagicMock, patch

import pytest

from termbackup import scheduler


class TestValidateProfileName:
    def test_valid_names(self):
        for name in ["my-profile", "test_123", "A-B-C", "simple"]:
            scheduler._validate_profile_name(name)

    def test_invalid_names(self):
        for name in ["bad name", "bad;name", "../etc", "bad$(cmd)", ""]:
            with pytest.raises(ValueError):
                scheduler._validate_profile_name(name)


class TestEnableSchedule:
    @patch("termbackup.scheduler.audit.log_operation")
    @patch("termbackup.scheduler.platform.system", return_value="Windows")
    @patch("termbackup.scheduler.subprocess.run")
    def test_windows(self, mock_run, mock_system, mock_audit):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        scheduler.enable_schedule("my-profile", "DAILY /ST 03:00")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "schtasks" in args
        assert "/Create" in args
        assert "TermBackup_my-profile" in args
        mock_audit.assert_called_once_with("schedule", "my-profile", "success", {"action": "enable"})

    @patch("termbackup.scheduler.audit.log_operation")
    @patch("termbackup.scheduler.platform.system", return_value="Linux")
    @patch("termbackup.scheduler.subprocess.run")
    def test_unix(self, mock_run, mock_system, mock_audit):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        scheduler.enable_schedule("my-profile", "0 3 * * *")

        assert mock_run.call_count == 2
        write_call = mock_run.call_args_list[1]
        assert "TERMBACKUP_START:my-profile" in write_call.kwargs.get("input", "")
        mock_audit.assert_called_once()

    @patch("termbackup.scheduler.audit.log_operation")
    @patch("termbackup.scheduler.platform.system", return_value="Windows")
    @patch("termbackup.scheduler.subprocess.run")
    def test_windows_failure(self, mock_run, mock_system, mock_audit):
        mock_run.return_value = MagicMock(returncode=1, stderr="Access denied")
        with pytest.raises(RuntimeError, match="Failed to create scheduled task"):
            scheduler.enable_schedule("my-profile", "DAILY /ST 03:00")


class TestDisableSchedule:
    @patch("termbackup.scheduler.audit.log_operation")
    @patch("termbackup.scheduler.platform.system", return_value="Windows")
    @patch("termbackup.scheduler.subprocess.run")
    def test_windows(self, mock_run, mock_system, mock_audit):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        scheduler.disable_schedule("my-profile")

        args = mock_run.call_args[0][0]
        assert "/Delete" in args
        assert "TermBackup_my-profile" in args
        mock_audit.assert_called_once_with("schedule", "my-profile", "success", {"action": "disable"})

    @patch("termbackup.scheduler.audit.log_operation")
    @patch("termbackup.scheduler.platform.system", return_value="Linux")
    @patch("termbackup.scheduler.subprocess.run")
    def test_unix(self, mock_run, mock_system, mock_audit):
        existing = "# TERMBACKUP_START:my-profile\n0 3 * * * cmd\n# TERMBACKUP_END:my-profile\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=existing, stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        scheduler.disable_schedule("my-profile")

        write_call = mock_run.call_args_list[1]
        written = write_call.kwargs.get("input", "")
        assert "TERMBACKUP_START" not in written


class TestGetScheduleStatus:
    @patch("termbackup.scheduler.platform.system", return_value="Windows")
    @patch("termbackup.scheduler.subprocess.run")
    def test_windows_found(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="TaskName: TermBackup_my-profile\nSchedule: Daily at 03:00")
        result = scheduler.get_schedule_status("my-profile")
        assert result is not None
        assert "TermBackup" in result

    @patch("termbackup.scheduler.platform.system", return_value="Windows")
    @patch("termbackup.scheduler.subprocess.run")
    def test_windows_not_found(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ERROR")
        result = scheduler.get_schedule_status("my-profile")
        assert result is None
