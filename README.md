<p align="center">
  <img src="https://img.shields.io/badge/TermBackup-v2.0.0-00d4aa?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xOSA5aC01VjRINXYxNmgxNFY5ek0xMyAzbDYgNnYxMmMwIDEuMS0uOSAyLTIgMkg1Yy0xLjEgMC0yLS45LTItMlY0YzAtMS4xLjktMiAyLTJoOHoiLz48L3N2Zz4=" alt="TermBackup"/>
</p>

<h1 align="center">🔐 TermBackup</h1>

<p align="center">
  <strong>Secure cloud-backed backup CLI using GitHub as encrypted storage</strong>
</p>

<p align="center">
  <a href="#-features"><img src="https://img.shields.io/badge/AES--256-Encrypted-success?style=flat-square" alt="Encryption"/></a>
  <a href="#-installation"><img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License"/></a>
  <a href="https://github.com/scorpiocodex/termbackup"><img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform"/></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-commands">Commands</a> •
  <a href="#-security">Security</a> •
  <a href="#-configuration">Configuration</a>
</p>

---

## 📖 Overview

**TermBackup** is a command-line backup tool that creates **encrypted backups** of your files and stores them securely in a GitHub repository you control. All encryption happens locally before any data leaves your machine.

```
┌─────────────────────────────────────────────────────────────────┐
│                     🔐 TermBackup Workflow                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   📁 Local Files  →  📦 Compress  →  🔒 Encrypt  →  ☁️ GitHub   │
│                                                                 │
│   • Scan directory      • gzip archive    • AES-256      • API  │
│   • Apply exclusions    • Efficient       • PBKDF2       • Safe │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **Philosophy:** *Encrypt locally. Upload safely. Restore reliably.*

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔒 Security First
- **AES-256 Encryption** via Fernet
- **PBKDF2-HMAC-SHA256** key derivation (600K iterations)
- **Secure temp file deletion** (3-pass overwrite)
- Zero plaintext data leaves your machine

</td>
<td width="50%">

### 🚀 Developer Friendly
- **Rich CLI interface** with progress bars
- **Profile-based** backup configurations
- **Dry-run mode** for safe previews
- Cross-platform (Windows, macOS, Linux)

</td>
</tr>
<tr>
<td width="50%">

### 📦 Smart Compression
- **gzip compression** for efficient storage
- Automatic exclusion of common patterns
- Configurable file exclusions per profile

</td>
<td width="50%">

### ☁️ GitHub Storage
- Uses your **own repository** for storage
- Automatic repo creation and initialization
- Full backup history with Git versioning

</td>
</tr>
</table>

### 🆕 Version 2.0 Features

| Feature | Description |
|---------|-------------|
| 🔄 **Incremental Backups** | Only backup changed files since last backup |
| 🏷️ **Backup Tags** | Organize backups with custom labels |
| 🗑️ **Retention Policies** | Auto-cleanup old backups |
| 📊 **Backup Comparison** | Diff two backups to see changes |
| 📤 **Config Export/Import** | Share configurations easily |
| ⏰ **Schedule Generation** | Generate cron expressions for automation |

---

## 📥 Installation

### Requirements
- Python 3.11 or higher
- GitHub account with Personal Access Token

### Install via pip

```bash
pip install termbackup
```

### Install from source

```bash
git clone https://github.com/scorpiocodex/termbackup
cd termbackup
pip install -e .
```

---

## 🚀 Quick Start

### 1️⃣ Initialize TermBackup

```bash
termbackup init
```

You'll be prompted for:
- 👤 GitHub username
- 📁 Repository name (creates if needed)
- 🔑 GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))

### 2️⃣ Create a Backup Profile

```bash
termbackup profile create
```

Configure:
- Profile name (e.g., `documents`)
- Source directory (e.g., `~/Documents`)
- Exclusion patterns (optional)

### 3️⃣ Run Your First Backup

```bash
# Preview what will be backed up
termbackup run documents --dry-run

# Create the backup
termbackup run documents
```

> 💡 **Tip:** Use `--dry-run` to preview without creating a backup

---

## 📋 Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `termbackup init` | 🔧 Initialize with GitHub configuration |
| `termbackup status` | 📊 Show configuration and connectivity status |
| `termbackup run <profile>` | ▶️ Run a backup using specified profile |
| `termbackup list` | 📋 List all backups in the repository |
| `termbackup restore <id>` | 📥 Restore a backup |
| `termbackup verify <id>` | ✅ Verify backup integrity |
| `termbackup delete <id>` | 🗑️ Delete a backup permanently |

### Profile Management

| Command | Description |
|---------|-------------|
| `termbackup profile create` | ➕ Create a new backup profile |
| `termbackup profile list` | 📋 List all profiles |
| `termbackup profile show <name>` | 👁️ Show profile details |
| `termbackup profile delete <name>` | 🗑️ Delete a profile |

### v2.0 Commands

| Command | Description |
|---------|-------------|
| `termbackup run <profile> --incremental` | 🔄 Run incremental backup |
| `termbackup tag <id> <label>` | 🏷️ Add tag to backup |
| `termbackup diff <id1> <id2>` | 📊 Compare two backups |
| `termbackup retention set <days>` | ⏰ Set retention policy |
| `termbackup config export` | 📤 Export configuration |
| `termbackup config import <file>` | 📥 Import configuration |
| `termbackup schedule <profile>` | 🕐 Generate cron schedule |

---

## 🔒 Security

### Encryption Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    🔐 Security Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Password ──→ PBKDF2-HMAC-SHA256 ──→ 256-bit Key               │
│                  (600,000 iterations)                           │
│                         │                                       │
│                         ▼                                       │
│  Plaintext ──→ Fernet (AES-256-CBC) ──→ Ciphertext ──→ GitHub  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Trust Model

| Location | Trust Level | What's Stored |
|----------|:-----------:|---------------|
| 💻 Local Machine | ✅ Trusted | Plaintext files, passwords |
| ☁️ GitHub | ⚠️ Untrusted | Encrypted `.tbk` blobs only |

### ⚠️ Security Warnings

> **🔴 Password Loss = Data Loss**
> There is NO password recovery. If you forget your encryption password, your backups cannot be restored.

> **🔴 Token Security**
> Your GitHub PAT has repository access. Never commit it to version control.

---

## ⚙️ Configuration

### Config Location

```
~/.termbackup/
└── config.json    # Main configuration file
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TERMBACKUP_GITHUB_TOKEN` | GitHub PAT (alternative to config storage) |
| `TERMBACKUP_<PROFILE>_PASSWORD` | Profile-specific encryption password |

### Example Configuration

```json
{
  "github_username": "your-username",
  "github_repo": "termbackup-storage",
  "github_token_env_var": "TERMBACKUP_GITHUB_TOKEN",
  "profiles": {
    "documents": {
      "name": "documents",
      "source_directory": "/home/user/Documents",
      "exclude_patterns": ["*.log", "*.tmp", "cache/"]
    }
  },
  "initialized": true
}
```

---

## 🔧 Default Exclusions

The following patterns are **always excluded**:

```
.git/           # Git repository data
__pycache__/    # Python cache
node_modules/   # Node.js dependencies
*.pyc, *.pyo    # Python bytecode
.DS_Store       # macOS metadata
Thumbs.db       # Windows thumbnails
```

---

## 📊 Example Workflow

```bash
# Initial setup
termbackup init
termbackup profile create
# → Enter: myprojects, ~/projects, *.log,*.tmp,node_modules/

# Create backup with tag
termbackup run myprojects
termbackup tag backup_20240115_143022 "pre-refactor"

# Check available backups
termbackup list

# Verify backup integrity
termbackup verify backup_20240115_143022

# Compare backups
termbackup diff backup_20240115_143022 backup_20240116_090000

# Restore when needed
termbackup restore backup_20240115_143022 --dest ~/restored

# Set retention policy (keep last 30 days)
termbackup retention set 30
```

---

## 📁 Repository Structure

Your backup repository will look like:

```
your-backup-repo/
├── README.md
├── backups/
│   ├── backup_20240115_143022.tbk    # Encrypted backup
│   ├── backup_20240116_090000.tbk
│   └── ...
└── metadata/                          # v2.0
    ├── tags.json                      # Backup tags
    └── checksums.json                 # For incremental backups
```

---

## ⚡ Limitations

| Limitation | Description |
|------------|-------------|
| 📦 Full backups | v1.0 only supports full backups (v2.0 adds incremental) |
| 📁 Single repository | All backups stored in one GitHub repo |
| ☁️ GitHub only | No other storage backends (yet) |
| ⏰ No built-in scheduling | Use cron/Task Scheduler (v2.0 generates expressions) |
| 📏 100MB file limit | GitHub's per-file size restriction |

---

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/scorpiocodex/termbackup
cd termbackup

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=termbackup --cov-report=html
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built with ❤️ for secure backups</sub>
</p>

<p align="center">
  <a href="https://github.com/scorpiocodex/termbackup/issues">Report Bug</a> •
  <a href="https://github.com/scorpiocodex/termbackup/issues">Request Feature</a>
</p>
