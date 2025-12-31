# TermBackup v1.0

Secure cloud-backed backup CLI using GitHub as encrypted storage.

## What is TermBackup?

TermBackup is a command-line tool that creates encrypted backups of your files and stores them securely in a GitHub repository you control. All encryption happens locally before any data leaves your machine.

**Core Philosophy:** *Encrypt locally. Upload safely. Restore reliably.*

## How It Works

1. **Scan** - TermBackup scans your source directory based on your profile configuration
2. **Compress** - Files are compressed into a gzip tar archive
3. **Encrypt** - The archive is encrypted with AES-256 using your password
4. **Upload** - Only the encrypted `.tbk` file is uploaded to your GitHub repository

Your GitHub repository only ever contains encrypted blobs. No plaintext filenames, no passwords, no sensitive metadata.

```
your-backup-repo/
├── backups/
│   ├── backup_20240115_143022.tbk
│   ├── backup_20240116_090000.tbk
│   └── ...
└── README.md
```

## Security Model

| Location | Trust Level | What's Stored |
|----------|-------------|---------------|
| Local Machine | Trusted | Plaintext files, passwords, temp archives |
| GitHub | Untrusted | Encrypted `.tbk` blobs only |

### Encryption Details

- **Algorithm**: AES-256 via Fernet
- **Key Derivation**: PBKDF2-HMAC-SHA256 (600,000 iterations)
- **Compression**: gzip

## Installation

Requires Python 3.11+

```bash
pip install termbackup
```

Or install from source:

```bash
git clone https://github.com/yourusername/termbackup
cd termbackup
pip install -e .
```

## Quick Start

### 1. Initialize TermBackup

```bash
termbackup init
```

This will prompt you for:
- GitHub username
- Repository name (will be created if it doesn't exist)
- GitHub Personal Access Token (requires `repo` scope)

Create a PAT at: https://github.com/settings/tokens

### 2. Create a Backup Profile

```bash
termbackup profile create
```

Enter:
- Profile name (e.g., `documents`)
- Source directory to backup (e.g., `~/Documents`)
- Exclusion patterns (optional, comma-separated globs)

### 3. Run Your First Backup

Preview what will be backed up:

```bash
termbackup run documents --dry-run
```

Create the backup:

```bash
termbackup run documents
```

You'll be prompted for an encryption password. **Remember this password** - it's required to restore your backup.

## Commands

### Initialize

```bash
termbackup init
```

Configure GitHub repository connection. Run once before using other commands.

### Profile Management

```bash
# Create a new profile
termbackup profile create

# List all profiles
termbackup profile list

# Show profile details
termbackup profile show <name>

# Delete a profile
termbackup profile delete <name>
```

### Backup

```bash
# Run backup with a profile
termbackup run <profile>

# Preview backup without creating it
termbackup run <profile> --dry-run
```

### List Backups

```bash
termbackup list
```

Shows all backups stored in your GitHub repository.

### Delete Backups

```bash
termbackup delete <backup-id>
```

Permanently deletes a backup from your GitHub repository. This action cannot be undone.

### Restore

```bash
# Restore to original location
termbackup restore <backup-id>

# Preview restore without extracting
termbackup restore <backup-id> --dry-run

# Restore to different location
termbackup restore <backup-id> --dest /path/to/restore
```

The backup ID is shown in `termbackup list` (e.g., `backup_20240115_143022`).

### Verify

```bash
termbackup verify <backup-id>
```

Downloads and verifies backup integrity without extracting files.

### Status

```bash
termbackup status
```

Shows current configuration status and tests GitHub connectivity.

## Example Workflow

```bash
# Initial setup
termbackup init
termbackup profile create
# Enter: myprojects, ~/projects, *.log,*.tmp

# Create backup
termbackup run myprojects
# Enter encryption password

# Later: check available backups
termbackup list

# Verify a backup is intact
termbackup verify backup_20240115_143022

# Restore when needed
termbackup restore backup_20240115_143022 --dest ~/restored
```

## Configuration

Configuration is stored in `~/.termbackup/config.json`.

### Using Environment Variables

During setup, you can choose to store your GitHub token in an environment variable:

```bash
export TERMBACKUP_GITHUB_TOKEN=ghp_your_token_here
```

Similarly, profile passwords can be stored in environment variables:

```bash
export TERMBACKUP_MYPROFILE_PASSWORD=your_secure_password
```

## Default Exclusions

The following patterns are always excluded:

- `.git/`
- `__pycache__/`
- `node_modules/`
- `*.pyc`, `*.pyo`
- `.DS_Store`
- `Thumbs.db`

Add custom patterns per-profile during profile creation.

## Security Warnings

1. **Password Loss = Data Loss**: There is no password recovery. If you forget your encryption password, your backups cannot be restored.

2. **Token Security**: Your GitHub PAT has repository access. Store it securely and never commit it to version control.

3. **Local Security**: Encryption happens locally. Ensure your local machine is secure.

4. **Backup Verification**: Periodically run `termbackup verify` to ensure your backups are intact.

## Limitations

- **Full backups only**: No incremental or differential backups
- **Single repository**: All backups go to one configured GitHub repo
- **GitHub only**: No other storage backends
- **No scheduling**: Use cron or task scheduler for automated backups
- **File size limits**: GitHub has a 100MB file size limit per file in the repository

## Requirements

- Python 3.11+
- GitHub account with a Personal Access Token (`repo` scope)
- Internet connection for backup/restore operations

## License

MIT License - See [LICENSE](LICENSE) for details.
