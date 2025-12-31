"""Backup schedule generation for TermBackup v2.0."""

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Frequency(Enum):
    """Backup frequency options."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class Schedule:
    """Backup schedule configuration."""

    frequency: Frequency
    hour: int = 2  # Default: 2 AM
    minute: int = 0
    day_of_week: Optional[int] = None  # 0-6, Sunday=0
    day_of_month: Optional[int] = None  # 1-31

    def to_cron(self) -> str:
        """Convert to cron expression."""
        if self.frequency == Frequency.HOURLY:
            return f"{self.minute} * * * *"
        elif self.frequency == Frequency.DAILY:
            return f"{self.minute} {self.hour} * * *"
        elif self.frequency == Frequency.WEEKLY:
            dow = self.day_of_week if self.day_of_week is not None else 0
            return f"{self.minute} {self.hour} * * {dow}"
        elif self.frequency == Frequency.MONTHLY:
            dom = self.day_of_month if self.day_of_month is not None else 1
            return f"{self.minute} {self.hour} {dom} * *"
        return "0 2 * * *"  # Default: daily at 2 AM

    def describe(self) -> str:
        """Get human-readable description."""
        if self.frequency == Frequency.HOURLY:
            return f"Every hour at minute {self.minute}"
        elif self.frequency == Frequency.DAILY:
            return f"Daily at {self.hour:02d}:{self.minute:02d}"
        elif self.frequency == Frequency.WEEKLY:
            days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            dow = self.day_of_week if self.day_of_week is not None else 0
            return f"Weekly on {days[dow]} at {self.hour:02d}:{self.minute:02d}"
        elif self.frequency == Frequency.MONTHLY:
            dom = self.day_of_month if self.day_of_month is not None else 1
            suffix = "th"
            if dom == 1 or dom == 21 or dom == 31:
                suffix = "st"
            elif dom == 2 or dom == 22:
                suffix = "nd"
            elif dom == 3 or dom == 23:
                suffix = "rd"
            return f"Monthly on the {dom}{suffix} at {self.hour:02d}:{self.minute:02d}"
        return "Unknown schedule"


def generate_cron_command(
    profile_name: str,
    password_env_var: Optional[str] = None,
) -> str:
    """Generate the command to run in cron."""
    cmd = f"termbackup run {profile_name}"
    if password_env_var:
        # Password will be read from env var
        return cmd
    return cmd


def generate_crontab_entry(
    profile_name: str,
    schedule: Schedule,
    password_env_var: Optional[str] = None,
    log_file: Optional[str] = None,
) -> str:
    """Generate a complete crontab entry."""
    cron_expr = schedule.to_cron()
    cmd = generate_cron_command(profile_name, password_env_var)

    if log_file:
        cmd = f"{cmd} >> {log_file} 2>&1"

    return f"{cron_expr} {cmd}"


def generate_windows_task_xml(
    profile_name: str,
    schedule: Schedule,
    password_env_var: Optional[str] = None,
) -> str:
    """Generate Windows Task Scheduler XML."""
    # Convert schedule to Windows format
    if schedule.frequency == Frequency.DAILY:
        trigger = f"""
    <CalendarTrigger>
      <StartBoundary>2024-01-01T{schedule.hour:02d}:{schedule.minute:02d}:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""
    elif schedule.frequency == Frequency.WEEKLY:
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        dow = schedule.day_of_week if schedule.day_of_week is not None else 0
        trigger = f"""
    <CalendarTrigger>
      <StartBoundary>2024-01-01T{schedule.hour:02d}:{schedule.minute:02d}:00</StartBoundary>
      <ScheduleByWeek>
        <DaysOfWeek>
          <{days[dow]} />
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>"""
    else:
        trigger = f"""
    <CalendarTrigger>
      <StartBoundary>2024-01-01T{schedule.hour:02d}:{schedule.minute:02d}:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""

    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>TermBackup scheduled backup for {profile_name}</Description>
  </RegistrationInfo>
  <Triggers>{trigger}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>termbackup</Command>
      <Arguments>run {profile_name}</Arguments>
    </Exec>
  </Actions>
</Task>"""


def generate_schedule_instructions(
    profile_name: str,
    schedule: Schedule,
    password_env_var: Optional[str] = None,
) -> str:
    """Generate setup instructions for scheduled backups."""
    cron_entry = generate_crontab_entry(
        profile_name, schedule, password_env_var, "/var/log/termbackup.log"
    )

    instructions = f"""
# TermBackup Schedule Setup
# Profile: {profile_name}
# Schedule: {schedule.describe()}

"""

    if sys.platform == "win32":
        instructions += f"""## Windows Task Scheduler

1. Open Task Scheduler (taskschd.msc)
2. Click "Create Task..."
3. Name: "TermBackup - {profile_name}"
4. Trigger: {schedule.describe()}
5. Action: Start a program
   - Program: termbackup
   - Arguments: run {profile_name}
6. Conditions: Check "Start only if network connection is available"

Or use PowerShell:
```powershell
$action = New-ScheduledTaskAction -Execute "termbackup" -Argument "run {profile_name}"
$trigger = New-ScheduledTaskTrigger -Daily -At {schedule.hour:02d}:{schedule.minute:02d}
Register-ScheduledTask -TaskName "TermBackup-{profile_name}" -Action $action -Trigger $trigger
```
"""
    else:
        instructions += f"""## Linux/macOS Cron Setup

1. Open crontab for editing:
   ```bash
   crontab -e
   ```

2. Add this line:
   ```
   {cron_entry}
   ```

3. Save and exit

## Cron Expression Breakdown
   {schedule.to_cron()}
   │ │ │ │ │
   │ │ │ │ └─ Day of week (0-6, Sunday=0)
   │ │ │ └─── Month (1-12)
   │ │ └───── Day of month (1-31)
   │ └─────── Hour (0-23)
   └───────── Minute (0-59)
"""

    if password_env_var:
        instructions += f"""
## Password Configuration

Set the password in your environment:
```bash
export {password_env_var}="your-password-here"
```

Add to your shell profile (~/.bashrc, ~/.zshrc, etc.) for persistence.
"""
    else:
        instructions += """
## Interactive Password Note

Your profile requires an interactive password prompt.
For automated backups, consider using a password environment variable:

```bash
termbackup profile create
# Choose "Use environment variable for password"
```
"""

    return instructions
