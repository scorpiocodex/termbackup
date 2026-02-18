<div align="center">

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                              ║
║   ████████╗███████╗██████╗ ███╗   ███╗██████╗  █████╗  ██████╗██╗  ██╗██╗   ██╗██████╗       ║
║   ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██║   ██║██╔══██╗      ║
║      ██║   █████╗  ██████╔╝██╔████╔██║██████╔╝███████║██║     █████╔╝ ██║   ██║██████╔╝      ║
║      ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══██╗██╔══██║██║     ██╔═██╗ ██║   ██║██╔═══╝       ║
║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║██████╔╝██║  ██║╚██████╗██║  ██╗╚██████╔╝██║           ║
║      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝           ║
║                                                                                              ║
║                        [ ZERO-TRUST ENCRYPTED GITHUB BACKUP ENGINE ]                         ║
║                                   v6.0.0  //  MIT License                                    ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

<br>

<img src="https://img.shields.io/badge/VERSION-6.0.0-00d4ff?style=for-the-badge&labelColor=0d1117" alt="Version">
<img src="https://img.shields.io/badge/PYTHON-3.11+-a855f7?style=for-the-badge&logo=python&logoColor=white&labelColor=0d1117" alt="Python">
<img src="https://img.shields.io/badge/LICENSE-MIT-22c55e?style=for-the-badge&labelColor=0d1117" alt="License">
<img src="https://img.shields.io/badge/ENCRYPTION-AES--256--GCM-ef4444?style=for-the-badge&labelColor=0d1117" alt="Encryption">
<img src="https://img.shields.io/badge/KDF-ARGON2ID-f97316?style=for-the-badge&labelColor=0d1117" alt="KDF">
<img src="https://img.shields.io/badge/SIGNING-ED25519-eab308?style=for-the-badge&labelColor=0d1117" alt="Signing">
<img src="https://img.shields.io/badge/TESTS-296%20PASSED-22c55e?style=for-the-badge&labelColor=0d1117" alt="Tests">
<img src="https://img.shields.io/badge/COVERAGE-71%25-06b6d4?style=for-the-badge&labelColor=0d1117" alt="Coverage">
<img src="https://img.shields.io/badge/PLATFORM-WIN%20%7C%20MAC%20%7C%20LINUX-8b5cf6?style=for-the-badge&labelColor=0d1117" alt="Platform">

<br><br>

**Your files never leave your machine unencrypted. Not once. Not ever.**

*Military-grade encryption. Git-native storage. One command. Zero trust.*

<br>

[Installation](#-installation) · [Quick Start](#-quick-start) · [Commands](#-command-reference) · [Security](#-security-model) · [Contributing](#-contributing)

</div>

---

<br>

## What is TermBackup?

**TermBackup** is a next-generation command-line backup engine that encrypts your files locally with **AES-256-GCM** authenticated encryption, derives keys through the memory-hard **Argon2id** KDF, packages everything into a tamper-proof binary `.tbk` archive, and stores it in a private GitHub repository over **HTTP/2**.

The server never sees your plaintext. No cloud trust. No third-party dependency. No compromise.

```
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
 │  YOUR FILES  │────>│  ARGON2ID    │────>│  AES-256-GCM │────>│  .TBK BINARY│────>│  GITHUB     │
 │  (plaintext) │     │  KDF 64 MiB  │     │  AEAD cipher │     │  archive    │     │  (encrypted)│
 └──────────────┘     │  3 iter, 4p  │     │  + GCM tag   │     │  + manifest │     │  at rest    │
                      │  32B salt    │     │  12B nonce   │     │  + signature│     │  HTTP/2     │
                      └──────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

<br>

---

<br>

## Table of Contents

- [What is TermBackup?](#what-is-termbackup)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Command Reference](#-command-reference)
- [Encryption Architecture](#-encryption-architecture)
- [Archive Format (TBK2)](#-archive-format--tbk2)
- [Security Model](#-security-model)
- [Health Diagnostics](#-health-diagnostics)
- [Webhook Notifications](#-webhook-notifications)
- [Audit System](#-audit-system)
- [Profile System](#-profile-system)
- [Daemon & Scheduling](#-daemon--scheduling)
- [Error Handling](#-error-handling)
- [Project Architecture](#-project-architecture)
- [Dependencies](#-dependencies)
- [Development](#-development)
- [Configuration Reference](#-configuration-reference)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [Security Policy](#-security-policy)
- [Changelog](#-changelog)
- [License](#-license)

<br>

---

<br>

## // FEATURES

<br>

### Cryptography & Security

| Feature | Spec | Description |
|:--------|:-----|:------------|
| **AES-256-GCM** | NIST SP 800-38D | Authenticated encryption with associated data (AEAD) |
| **Argon2id** | PHC Winner, RFC 9106 | Memory-hard KDF -- 64 MiB, 3 iterations, 4 parallelism lanes |
| **Ed25519** | RFC 8032 | Elliptic-curve digital signatures for backup authentication |
| **SHA-256** | FIPS 180-4 | Per-file integrity checksums in every manifest |
| **Zero-Trust** | -- | Server is untrusted; all crypto happens client-side |
| **Forward Secrecy** | -- | Unique random salt + nonce per backup; no key reuse |
| **OS Keyring** | Platform-native | macOS Keychain, Windows Credential Locker, Linux Secret Service |
| **Token Validation** | GitHub API | Auto-validates PAT scopes on `init` and `update-token` |

### Backup Operations

| Feature | Description |
|:--------|:------------|
| **Encrypted Backup** | Compress, encrypt, sign, and upload in one atomic operation |
| **Incremental Mode** | SHA-256 delta detection -- only changed files are re-processed |
| **Restore** | Download, decrypt, decompress, verify, and extract to original paths |
| **Verify** | Remote integrity check -- downloads and re-verifies GCM tag + SHA-256 + manifest |
| **Diff** | File-level comparison between any two backup snapshots |
| **Key Rotation** | Re-encrypt all backups with a new password in one operation |
| **Pruning** | Automatic cleanup by backup count or age retention policy |
| **Migration** | Upgrade legacy TBK1 (v1) archives to TBK2 (v2) format |

### Infrastructure & Automation

| Feature | Description |
|:--------|:------------|
| **Profile System** | Named configs with per-profile source dirs, repos, exclusions, and webhooks |
| **Profile Export/Import** | JSON-based profile migration between machines |
| **OS Scheduling** | Native crontab (Linux/macOS) and Windows Task Scheduler integration |
| **Daemon Mode** | Continuous background backups at configurable intervals with failure tracking |
| **Webhook Alerts** | Auto-detected Slack Block Kit, Discord Embeds, or generic HTTP POST |
| **12-Point Diagnostics** | `doctor` command validates config, token, API, keyring, profiles, deps, disk |
| **Audit Log** | Append-only JSONL log of every operation with timestamps and status |
| **Metadata Ledger** | Remote backup tracking with `metadata.json` in the GitHub repo |

### Developer Experience

| Feature | Description |
|:--------|:------------|
| **Rich Terminal UI** | Panels, tables, progress bars, spinners, and emoji icons via Rich |
| **Structured Errors** | `TermBackupError` hierarchy with actionable `hint` fields |
| **Pydantic v2 Models** | Strict data validation for all config, manifest, and ledger data |
| **Typed Package** | PEP 561 `py.typed` marker -- full `mypy --strict` compliance |
| **HTTP/2** | All GitHub API calls over multiplexed HTTP/2 via httpx |
| **Parallel Hashing** | `ThreadPoolExecutor` for concurrent SHA-256 file checksums |
| **Backward Compat** | TBK1 archives (AES-256-CBC + PBKDF2) auto-detected and fully supported |

<br>

---

<br>

## // INSTALLATION

### From PyPI

```bash
pip install termbackup
```

### With pipx (Isolated)

```bash
pipx install termbackup
```

### From Source

```bash
git clone https://github.com/scorpiocodex/Termbackup.git
cd termbackup
poetry install
```

### System Requirements

| Requirement | Minimum |
|:------------|:--------|
| **Python** | 3.11+ |
| **OS** | Windows 10+, macOS 12+, Linux (glibc 2.31+) |
| **GitHub** | Personal Access Token with `repo` scope |
| **Disk** | 50 MB free (plus space for local archive staging) |

<br>

---

<br>

## // QUICK START

### Step 1 -- Initialize

```bash
termbackup init
```

Creates `~/.termbackup/config.json`, prompts for your GitHub Personal Access Token, validates it against the GitHub API (checks scopes, rate limits, expiry), and optionally creates a private storage repository.

### Step 2 -- Create a Profile

```bash
termbackup profile create my-project \
  --source /path/to/my-project \
  --repo scorpiocodex/my-project-backup
```

### Step 3 -- Run a Backup

```bash
termbackup run my-project
```

You will be prompted for an encryption password. Your files are hashed, compressed, encrypted with AES-256-GCM, packaged into a `.tbk` archive, optionally signed with Ed25519, and uploaded to your private GitHub repository.

### Step 4 -- List Backups

```bash
termbackup list my-project
```

Displays a formatted table of all backups with IDs, timestamps, file counts, and sizes.

### Step 5 -- Restore a Backup

```bash
termbackup restore <backup-id> --profile my-project
```

Downloads the archive, verifies the GCM authentication tag, decrypts, decompresses, validates SHA-256 checksums against the manifest, and restores files to their original paths with permissions preserved.

### Step 6 -- Verify Integrity

```bash
termbackup verify <backup-id> --profile my-project
```

Performs a full remote integrity check without extracting files -- verifies the GCM tag, SHA-256 archive checksum, and manifest consistency.

<br>

---

<br>

## // COMMAND REFERENCE

### Backup Operations

```
COMMAND                                      DESCRIPTION
──────────────────────────────────────────── ─────────────────────────────────────────────
termbackup run <profile>                     Create and upload an encrypted backup
termbackup run <profile> --dry-run           Simulate backup without uploading
termbackup list <profile>                    List all backups for a profile
termbackup restore <id> -p <profile>         Restore a backup to disk
termbackup restore <id> -p <profile> --dry-run  Preview restore without writing files
termbackup verify <id> -p <profile>          Verify backup integrity remotely
termbackup diff <id1> <id2> -p <profile>     Compare two backup snapshots
termbackup prune <profile>                   Remove old backups by retention policy
termbackup prune <profile> --max-backups 10  Keep only the 10 most recent backups
termbackup prune <profile> --retention-days 30  Remove backups older than 30 days
```

### Key & Security Operations

```
COMMAND                                      DESCRIPTION
──────────────────────────────────────────── ─────────────────────────────────────────────
termbackup rotate-key <profile>              Re-encrypt all backups with a new password
termbackup generate-key                      Generate Ed25519 signing keypair
termbackup migrate                           Migrate GitHub token from config to keyring
```

### Configuration & Token Management

```
COMMAND                                      DESCRIPTION
──────────────────────────────────────────── ─────────────────────────────────────────────
termbackup init                              Initialize config and validate GitHub token
termbackup update-token                      Update GitHub token with re-validation
termbackup token-info                        Display token metadata, scopes, and expiry
termbackup profile create <name> [opts]      Create a new backup profile
termbackup profile list                      List all configured profiles
termbackup profile show <name>               Show detailed profile configuration
termbackup profile delete <name>             Delete a backup profile
termbackup profile export <name> <file>      Export profile to JSON
termbackup profile import <file>             Import profile from JSON
```

### Monitoring & Diagnostics

```
COMMAND                                      DESCRIPTION
──────────────────────────────────────────── ─────────────────────────────────────────────
termbackup status                            Show system status, token info, all profiles
termbackup doctor                            Run 12-point health diagnostic
termbackup audit-log                         View audit log (most recent 20 entries)
termbackup audit-log -n 50                   View last 50 audit entries
termbackup audit-log -o backup               Filter by operation type
termbackup audit-log -p my-project           Filter by profile name
termbackup clean                             Remove orphaned temporary files
```

### Automation

```
COMMAND                                      DESCRIPTION
──────────────────────────────────────────── ─────────────────────────────────────────────
termbackup daemon <profile> -i <minutes>     Run continuous background backups
termbackup schedule-enable <profile> --schedule <expr>  Enable OS-native scheduling
termbackup schedule-disable <profile>        Disable scheduled backups
termbackup schedule-status <profile>         Check schedule status
```

### Global Options

```
termbackup --version / -v                    Show version and system info
termbackup --help                            Show all available commands
```

<br>

---

<br>

## // ENCRYPTION ARCHITECTURE

```
╔════════════════════════════════════════════════════════════════════════╗
║                       ENCRYPTION PIPELINE                              ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║   Password (user input)                                                ║
║      │                                                                 ║
║      ▼                                                                 ║
║   ┌──────────────────────────────────────────────────────────┐         ║
║   │  ARGON2ID  (RFC 9106)                                    │         ║
║   │  ├── Memory cost:    65,536 KiB (64 MiB)                 │         ║
║   │  ├── Time cost:      3 iterations                        │         ║
║   │  ├── Parallelism:    4 lanes                             │         ║
║   │  ├── Salt:           32 bytes (cryptographically random) │         ║
║   │  └── Output:         256-bit derived key                 │         ║
║   └──────────────────────────────────────────────────────────┘         ║
║      │                                                                 ║
║      ▼                                                                 ║
║   ┌──────────────────────────────────────────────────────────┐         ║
║   │  AES-256-GCM  (NIST SP 800-38D)                          │         ║
║   │  ├── Nonce:     12 bytes (96-bit, random)                │         ║
║   │  ├── Mode:      Galois/Counter Mode (AEAD)               │         ║
║   │  ├── Tag:       128-bit authentication tag               │         ║
║   │  └── Output:    Ciphertext || GCM Tag                    │         ║
║   └──────────────────────────────────────────────────────────┘         ║
║      │                                                                 ║
║      ▼                                                                 ║
║   ┌──────────────────────────────────────────────────────────┐         ║
║   │  TBK2 BINARY ARCHIVE                                     │         ║
║   │  ├── Magic bytes: "TBK2" (4 bytes)                       │         ║
║   │  ├── Version + KDF params + salt + nonce                 │         ║
║   │  ├── Cipher suite identifier                             │         ║
║   │  ├── Payload length (8 bytes, big-endian)                │         ║
║   │  └── Encrypted payload (gzip tar + manifest.json)        │         ║
║   └──────────────────────────────────────────────────────────┘         ║
║      │                                                                 ║
║      ▼                                                                 ║
║   ┌──────────────────────────────────────────────────────────┐         ║
║   │  ED25519 SIGNATURE  (RFC 8032, optional)                 │         ║
║   │  ├── 256-bit private key (PKCS8, password-encrypted)     │         ║
║   │  └── 64-byte deterministic signature                     │         ║
║   └──────────────────────────────────────────────────────────┘         ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
```

### Why This Stack?

| Choice | Rationale |
|:-------|:----------|
| **Argon2id** over PBKDF2 | Memory-hard -- resists GPU/ASIC brute-force; PHC competition winner |
| **AES-256-GCM** over CBC | AEAD -- provides both encryption and authentication in a single pass; no separate HMAC needed |
| **Ed25519** over RSA | Compact keys (32 bytes), fast signatures, deterministic, no padding oracle attacks |
| **12-byte GCM nonce** | NIST-recommended size; safe for random generation with unique salt per backup |
| **64 MiB Argon2 memory** | Practical on modern machines; significantly raises cost of parallel attacks |

<br>

---

<br>

## // ARCHIVE FORMAT -- TBK2

The `.tbk` binary format is purpose-built for encrypted backup storage with self-describing headers:

```
╔═════════════════════════════════════════════════════════════════╗
║  OFFSET   FIELD                  SIZE       VALUE / DESCRIPTION ║
╠═════════════════════════════════════════════════════════════════╣
║  0x00     Magic                  4 bytes    "TBK2"              ║
║  0x04     Version                1 byte     0x02                ║
║  0x05     KDF Algorithm          1 byte     0x01 = Argon2id     ║
║  0x06     Argon2 Memory Cost     4 bytes    Big-endian KiB      ║
║  0x0A     Argon2 Time Cost       2 bytes    Big-endian          ║
║  0x0C     Argon2 Parallelism     1 byte     Lane count          ║
║  0x0D     Salt Length            1 byte     N                   ║
║  0x0E     Salt                   N bytes    Random bytes        ║
║  ....     Nonce Length           1 byte     M                   ║
║  ....     Nonce                  M bytes    Random GCM nonce    ║
║  ....     Cipher Suite           1 byte     0x01 = AES-256-GCM  ║
║  ....     Payload Length         8 bytes    Big-endian          ║
║  ....     Ciphertext + GCM Tag   P bytes    Encrypted payload   ║
╚═════════════════════════════════════════════════════════════════╝
```

**Payload contents** (after decryption and gzip decompression):

```
tar archive/
├── manifest.json          Per-file SHA-256 hashes, sizes, permissions, timestamps
├── file1.txt              Original file data
├── subdir/
│   └── file2.py           Preserves directory structure
└── ...
```

### Legacy Format -- TBK1

TBK1 archives use `AES-256-CBC + PBKDF2 + HMAC-SHA256`. They are auto-detected by the `"TBK1"` magic bytes and remain fully supported for restore and verify operations. New backups always use TBK2.

<br>

---

<br>

## // SECURITY MODEL

### Threat Model

TermBackup assumes the storage backend (GitHub) is **completely untrusted**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THREAT MODEL                                    │
├────────────────────┬───────────────────────────────────────────────────┤
│  PROPERTY          │  MECHANISM                                        │
├────────────────────┼───────────────────────────────────────────────────┤
│  Confidentiality   │  AES-256-GCM -- encrypted before leaving machine  │
│  Integrity         │  GCM auth tag + SHA-256 per-file checksums        │
│  Authenticity      │  Ed25519 digital signatures (optional)            │
│  Key Strength      │  Argon2id 64 MiB defeats GPU/ASIC attacks         │
│  Forward Secrecy   │  Unique random salt + nonce per backup            │
│  Non-repudiation   │  Ed25519 signature chain (optional)               │
│  Tamper Detection  │  GCM tag fails on any bit flip                    │
└────────────────────┴───────────────────────────────────────────────────┘
```

### Security Guarantees

- **Password loss = data loss.** There is no recovery mechanism, no backdoor, no master key, no key escrow.
- **GitHub token** is stored in your OS keyring (macOS Keychain / Windows Credential Locker / Linux Secret Service), never in plaintext config files.
- **Config file permissions** are set to `chmod 600` (owner read/write only) on Unix systems.
- **Profile names** are validated against `^[a-zA-Z0-9_-]+$` to prevent command injection in scheduled tasks.
- **Archive extraction** validates all file paths against directory traversal attacks (`../../`).
- **Token validation** checks scopes, permissions, and expiry on every `init` and `update-token`.
- **Signing key** is encrypted with a user password using PKCS8 serialization.
- **Audit log** records all operations but never logs passwords, tokens, or file contents.

### What TermBackup Does NOT Protect Against

| Threat | Why |
|:-------|:----|
| Weak passwords | Argon2id slows brute-force but cannot stop dictionary attacks on `password123` |
| Keyloggers | Password captured at input time |
| Root/admin compromise | Full memory access can extract keys |
| Malware on your machine | Running process can be inspected |

**Recommendation**: Use a password manager to generate 20+ character passwords. Enable full-disk encryption on your machine.

<br>

---

<br>

## // HEALTH DIAGNOSTICS

```bash
termbackup doctor
```

Runs a comprehensive 12-point diagnostic scan:

```
╔════╦══════════════════════╦═════════════════════════════════════════════════════╗
║  # ║  CHECK               ║  WHAT IT VERIFIES                                   ║
╠════╬══════════════════════╬═════════════════════════════════════════════════════╣
║  1 ║  Config File         ║  ~/.termbackup/config.json exists and is valid JSON ║
║  2 ║  GitHub Token        ║  Token present in keyring or config                 ║
║  3 ║  API Connectivity    ║  GitHub API is reachable and authenticated          ║
║  4 ║  OS Keyring          ║  Keyring backend is functional                      ║
║  5 ║  Profiles            ║  All profiles are valid and well-formed             ║
║  6 ║  Profile Sources     ║  Source directories exist on disk                   ║
║  7 ║  Signing Key         ║  Ed25519 keypair is present (if configured)         ║
║  8 ║  Audit Log           ║  Log file exists, is readable, reports size         ║
║  9 ║  Temp Files          ║  No orphaned files in ~/.termbackup/tmp/            ║
║ 10 ║  Dependencies        ║  cryptography, httpx, argon2, keyring, pydantic     ║
║ 11 ║  Disk Space          ║  Sufficient free space (warns below 500 MB)         ║
║ 12 ║  Token Validation    ║  Token scopes, permissions, and expiry              ║
╚════╩══════════════════════╩═════════════════════════════════════════════════════╝
```

The doctor also displays an environment info panel showing the TermBackup version, Python version, platform, and config directory path.

<br>

---

<br>

## // WEBHOOK NOTIFICATIONS

Configure webhooks to get notified after each backup:

```bash
termbackup profile create my-project \
  --source /path/to/project \
  --repo user/repo \
  --webhook-url https://hooks.slack.com/services/T00/B00/xxx
```

TermBackup auto-detects the webhook format based on the URL:

```
┌──────────────────────────────┬──────────────────────────┐
│  URL PATTERN                 │  FORMAT                  │
├──────────────────────────────┼──────────────────────────┤
│  hooks.slack.com/*           │  Slack Block Kit         │
│  discord.com/api/webhooks/*  │  Discord Rich Embeds     │
│  Any other URL               │  Generic JSON POST       │
└──────────────────────────────┴──────────────────────────┘
```

Webhook payloads include: backup ID, profile name, file count, archive size, timestamp, and success/failure status.

<br>

---

<br>

## // AUDIT SYSTEM

All operations are recorded to `~/.termbackup/audit.log` in append-only JSONL (one JSON object per line):

```json
{"timestamp": "2026-02-18T10:00:00+00:00", "operation": "backup", "profile": "my-project", "status": "success", "details": {"backup_id": "abc123def456", "file_count": 42}}
{"timestamp": "2026-02-18T10:05:00+00:00", "operation": "verify", "profile": "my-project", "status": "success", "details": {"backup_id": "abc123def456"}}
{"timestamp": "2026-02-18T11:00:00+00:00", "operation": "restore", "profile": "my-project", "status": "failure", "details": {"error": "incorrect password"}}
```

**Logged operations**: backup, restore, verify, prune, rotate-key, schedule-enable, schedule-disable

**Never logged**: passwords, tokens, file contents, file paths

View the audit log with:

```bash
termbackup audit-log                        # Last 20 entries
termbackup audit-log -n 100                 # Last 100 entries
termbackup audit-log -o backup              # Only backup operations
termbackup audit-log -p my-project          # Only entries for my-project
termbackup audit-log -o restore -p staging  # Combined filters
```

<br>

---

<br>

## // PROFILE SYSTEM

Profiles are named backup configurations stored at `~/.termbackup/profiles/<name>.json`:

```bash
# Create a profile
termbackup profile create my-project \
  --source /path/to/my-project \
  --repo scorpiocodex/my-project-backup \
  --exclude "node_modules" \
  --exclude ".git" \
  --exclude "__pycache__" \
  --webhook-url https://hooks.slack.com/services/T00/B00/xxx

# List all profiles
termbackup profile list

# Show profile details
termbackup profile show my-project

# Export profile to JSON (for sharing or migration)
termbackup profile export my-project ./my-project-profile.json

# Import profile from JSON
termbackup profile import ./my-project-profile.json

# Delete a profile
termbackup profile delete my-project
```

### Profile Configuration Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | string | Profile identifier (`^[a-zA-Z0-9_-]+$`) |
| `source_dir` | path | Directory to back up |
| `repo` | string | GitHub repository (`owner/repo`) |
| `backup_mode` | enum | `full` or `incremental` |
| `max_backups` | int | Maximum backups to retain (pruning) |
| `retention_days` | int | Maximum backup age in days (pruning) |
| `exclude_patterns` | list | Gitignore-style exclusion patterns |
| `webhook_url` | string | Optional webhook URL for notifications |

<br>

---

<br>

## // DAEMON & SCHEDULING

### Daemon Mode

Run continuous background backups at a configurable interval:

```bash
# Backup every 60 minutes (default)
termbackup daemon my-project

# Backup every 15 minutes
termbackup daemon my-project --interval 15
```

The daemon includes:
- **Consecutive failure tracking** -- warns after 3+ consecutive failures
- **Shutdown summary panel** -- displays uptime, total iterations, successes, and failures on exit

### OS-Native Scheduling

Register scheduled backups with your operating system's native scheduler:

```bash
# Enable scheduled backups (password stored securely in OS keyring)
termbackup schedule-enable my-project --schedule "0 2 * * *"

# Check schedule status
termbackup schedule-status my-project

# Disable scheduled backups
termbackup schedule-disable my-project
```

| Platform | Backend |
|:---------|:--------|
| Linux / macOS | `crontab` |
| Windows | Windows Task Scheduler (`schtasks`) |

<br>

---

<br>

## // ERROR HANDLING

TermBackup uses a structured error hierarchy with actionable hints:

```
TermBackupError (base)
├── ConfigError          Config file missing, invalid, or corrupted
├── ProfileError         Profile not found, invalid, or duplicate
├── CryptoError          Decryption failed, wrong password, corrupted data
├── ArchiveError         Invalid magic bytes, corrupted headers, bad format
├── GitHubError          API auth failure, rate limiting, network errors
│   └── .status_code     HTTP status code (401, 403, 404, 422, 500...)
├── TokenError           Token invalid, expired, or insufficient scope
├── RestoreError         Missing backup, path traversal detected
├── BackupError          Source not found, upload failed
└── IntegrityError       Checksum mismatch, tampered data detected
```

Every error type supports an optional `hint` field that provides actionable guidance:

```
[ERROR] Authentication failed (HTTP 401)
  Hint: Run 'termbackup update-token' to set a valid token.

[ERROR] Decryption failed: invalid GCM authentication tag
  Hint: The password may be incorrect, or the archive may be corrupted.
```

<br>

---

<br>

## // PROJECT ARCHITECTURE

```
termbackup/                        5,173 lines of source code
│
│   # ── Core ─────────────────────────────────────────────────────
├── __init__.py                    Version constant (6.0.0)
├── cli.py                         Typer app, 19 commands, error handling
├── errors.py                      Structured error hierarchy with hints
├── models.py                      Pydantic v2 data models (strict validation)
├── ui.py                          Rich terminal UI (icons, panels, progress)
│
│   # ── Cryptography ─────────────────────────────────────────────
├── crypto.py                      AES-256-GCM + Argon2id / AES-256-CBC + PBKDF2
├── archive.py                     TBK1/TBK2 binary archive format (read/write)
├── signing.py                     Ed25519 digital signatures (generate/sign/verify)
├── rotate_key.py                  Full-suite password rotation
├── rotation.py                    Key rotation utilities
│
│   # ── Backup Engine ────────────────────────────────────────────
├── engine.py                      Backup orchestration (incremental, parallel hash)
├── restore.py                     Restore logic with integrity verification
├── verify.py                      Remote backup integrity checking
├── diff.py                        Backup snapshot comparison
├── manifest.py                    Manifest generation (SHA-256, metadata)
├── ledger.py                      Metadata ledger (remote backup tracking)
│
│   # ── GitHub Integration ───────────────────────────────────────
├── github.py                      GitHub API via httpx (HTTP/2, retries)
├── listing.py                     Remote backup listing and display
├── token_validator.py             Token validation (classic PAT + fine-grained)
│
│   # ── Configuration ────────────────────────────────────────────
├── config.py                      Config management, GitHub init, token flow
├── profile.py                     Profile CRUD + Typer subcommand group
├── credentials.py                 OS keyring integration (read/write)
│
│   # ── Automation ───────────────────────────────────────────────
├── daemon.py                      Background backup daemon with failure tracking
├── scheduler.py                   OS-native scheduling (cron / Task Scheduler)
├── webhooks.py                    Webhook notifications (Slack/Discord/generic)
├── audit.py                       Audit logging (append-only JSONL)
│
│   # ── Utilities ────────────────────────────────────────────────
├── utils.py                       Shared helpers (formatting, sizing, timestamps)
└── py.typed                       PEP 561 typed package marker
```

```
tests/                             3,700 lines of test code
│                                  296 tests across 27 test files
├── conftest.py                    Shared fixtures (mock_config_dir, sample_manifest...)
├── test_archive.py                Archive format tests (v1, v2, roundtrip, corruption)
├── test_cli_integration.py        CLI integration tests (all 19 commands)
├── test_config.py                 Config loading, saving, validation
├── test_config_token.py           Token management (init, update, keyring, fallback)
├── test_credentials.py            OS keyring read/write
├── test_crypto.py                 Encryption/decryption roundtrip, edge cases
├── test_crypto_properties.py      Property-based crypto tests (Hypothesis)
├── test_diff.py                   Backup comparison tests
├── test_doctor.py                 Health check tests (all 12 checks)
├── test_e2e.py                    End-to-end workflow tests
├── test_engine.py                 Backup engine orchestration
├── test_errors.py                 Error hierarchy and inheritance
├── test_github.py                 GitHub API mock tests
├── test_ledger.py                 Metadata ledger tests
├── test_listing.py                Backup listing display
├── test_manifest.py               Manifest generation and validation
├── test_new_commands.py           New commands (generate-key, audit-log, clean)
├── test_restore_mod.py            Restore logic and integrity checks
├── test_rotation.py               Key rotation utilities
├── test_scheduler.py              OS-native scheduling
├── test_signing.py                Ed25519 signing tests
├── test_token_validator.py        Token validation (classic, fine-grained, edge cases)
├── test_ui.py                     Terminal UI output tests
├── test_utils.py                  Utility function tests
├── test_verify_mod.py             Backup verification tests
└── test_webhooks.py               Webhook notification tests
```

<br>

---

<br>

## // DEPENDENCIES

### Runtime

| Package | Version | Purpose |
|:--------|:--------|:--------|
| `typer` | >= 0.12.0 | CLI framework with automatic help generation |
| `rich` | ^13.7.0 | Terminal formatting (panels, tables, progress, spinners) |
| `cryptography` | ^42.0.5 | AES-256-GCM, PBKDF2, Ed25519 (backed by OpenSSL) |
| `httpx[http2]` | ^0.27.0 | HTTP/2 client for GitHub API with connection pooling |
| `argon2-cffi` | ^23.1.0 | Argon2id KDF (reference C implementation) |
| `pydantic` | ^2.6.0 | Data validation and settings management |
| `pathspec` | ^0.12.0 | Gitignore-style file matching for exclusion patterns |
| `keyring` | >= 25.0.0 | OS-native credential storage |

### Development

| Package | Version | Purpose |
|:--------|:--------|:--------|
| `pytest` | ^8.0.0 | Test framework |
| `pytest-cov` | ^5.0.0 | Coverage reporting |
| `pytest-mock` | ^3.15.1 | Mock fixture integration |
| `hypothesis` | ^6.100.0 | Property-based testing |
| `mypy` | ^1.8.0 | Static type checking (strict mode) |
| `ruff` | >= 0.4.0 | Linting and formatting |
| `bandit` | ^1.8.0 | Security-focused static analysis |
| `pre-commit` | ^3.7.0 | Git hook management |

<br>

---

<br>

## // DEVELOPMENT

### Setup

```bash
git clone https://github.com/scorpiocodex/Termbackup.git
cd termbackup
poetry install
pre-commit install
```

### Running Tests

```bash
# Full suite (296 tests)
poetry run pytest

# With coverage report
poetry run pytest --cov=termbackup --cov-report=term-missing

# Specific module
poetry run pytest tests/test_crypto.py -v

# Specific test
poetry run pytest tests/test_archive.py::test_create_and_read_v2_archive -v

# Property-based tests only
poetry run pytest tests/test_crypto_properties.py -v
```

### Code Quality

```bash
# Lint
poetry run ruff check termbackup/ tests/

# Auto-format
poetry run ruff format termbackup/ tests/

# Type check (strict mode)
poetry run mypy termbackup/

# Security scan
poetry run bandit -r termbackup/ -c pyproject.toml

# All pre-commit hooks
pre-commit run --all-files
```

### CI/CD Pipeline

The GitHub Actions CI pipeline runs on every push and PR:

```
┌────────────────────────────────────────────────────────────────────────┐
│  CI PIPELINE                                                           │
├─────────────────┬──────────────────────────────────────────────────────┤
│  Lint           │  ruff check + ruff format --check                    │
│  Type Check     │  mypy --strict                                       │
│  Test Matrix    │  pytest across Python 3.11/3.12/3.13                 │
│                 │  on Ubuntu, Windows, macOS                           │
│  Security Audit │  pip-audit (dependency vulnerability scan)           │
│  Security Lint  │  bandit (code-level security patterns)               │
└─────────────────┴──────────────────────────────────────────────────────┘
```

Releases are triggered by version tags (`v*`) and automatically publish to PyPI with a GitHub Release.

<br>

---

<br>

## // CONFIGURATION REFERENCE

### Config File

Location: `~/.termbackup/config.json`

```json
{
    "github_token": null,
    "default_repo": "scorpiocodex/termbackup-storage",
    "encryption_version": 2,
    "signing_enabled": true
}
```

> **Note**: The `github_token` field is `null` when the token is stored in the OS keyring (recommended). Legacy configs with inline tokens are supported but `termbackup migrate` should be used to move them to the keyring.

### Profile File

Location: `~/.termbackup/profiles/<name>.json`

```json
{
    "name": "my-project",
    "source_dir": "/path/to/my-project",
    "repo": "scorpiocodex/my-project-backup",
    "backup_mode": "incremental",
    "max_backups": 10,
    "retention_days": 90,
    "exclude_patterns": ["node_modules", ".git", "__pycache__", "*.pyc"],
    "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx"
}
```

### Environment

| Path | Purpose |
|:-----|:--------|
| `~/.termbackup/config.json` | Global configuration |
| `~/.termbackup/profiles/` | Profile configurations |
| `~/.termbackup/tmp/` | Temporary staging (cleaned by `termbackup clean`) |
| `~/.termbackup/audit.log` | Operation audit log (JSONL) |
| `~/.termbackup/signing_key.pem` | Ed25519 private key (PKCS8, password-encrypted) |
| `~/.termbackup/signing_key.pub` | Ed25519 public key |

<br>

---

<br>

## // FAQ

**Q: What happens if I lose my password?**
A: Your backups are irrecoverable. TermBackup uses zero-knowledge encryption with no backdoor or master key. Use a password manager.

**Q: Can I use a fine-grained GitHub token?**
A: Yes. TermBackup supports both classic PATs (`ghp_*`) and fine-grained tokens (`github_pat_*`). Fine-grained tokens need `Contents` read/write permission on the target repository.

**Q: Are my files safe if GitHub is compromised?**
A: Yes. All data is encrypted locally with AES-256-GCM before upload. An attacker with full access to your GitHub repository can only see encrypted binary blobs.

**Q: How does incremental backup work?**
A: TermBackup computes SHA-256 checksums of all source files and compares them against the parent backup's manifest. Only files with changed hashes are included in the new archive.

**Q: Can I back up to multiple repositories?**
A: Yes. Create multiple profiles, each targeting a different repository.

**Q: Does TermBackup work behind a corporate proxy?**
A: httpx (the HTTP client) respects `HTTPS_PROXY` and `HTTP_PROXY` environment variables.

**Q: What Python versions are supported?**
A: Python 3.11, 3.12, and 3.13 are tested in CI across Windows, macOS, and Linux.

**Q: How do I upgrade from v1 archives to v2?**
A: Use `termbackup rotate-key <profile>` to re-encrypt all backups, or `termbackup migrate` to upgrade the token storage.

<br>

---

<br>

## // CONTRIBUTING

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full development guide, including:

- Environment setup and prerequisites
- Branch naming conventions
- Code style and type annotation requirements
- Testing standards and coverage expectations
- Error handling patterns
- Security requirements
- Pull request process

<br>

---

<br>

## // SECURITY POLICY

See **[SECURITY.md](SECURITY.md)** for the complete security policy, including:

- Supported versions
- Vulnerability reporting process
- Encryption architecture details
- Trust model documentation
- Known security considerations
- Dependency security audit process

<br>

---

<br>

## // CHANGELOG

See **[CHANGELOG.md](CHANGELOG.md)** for the full version history.

### Recent Releases

| Version | Date | Highlights |
|:--------|:-----|:-----------|
| **6.0.0** | 2026-02-18 | Structured error hierarchy, 3 new commands, enhanced doctor/daemon/UI |
| **5.0.0** | 2025-02-10 | GitHub token validation, `update-token`, `token-info` commands |
| **4.0.0** | 2024-12-01 | AES-256-GCM + Argon2id, Ed25519 signing, TBK2 format, webhooks, daemon |

<br>

---

<br>

## // LICENSE

MIT License. See **[LICENSE](LICENSE)** for the full text.

```
Copyright (c) 2024-2026 TermBackup Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

<br>

---

<br>

<div align="center">

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   ENCRYPT EVERYTHING.  TRUST NOTHING.  BACK UP ALWAYS.         ║
║                                                                ║
║   TermBackup v6.0.0  //  296 tests  //  29 modules             ║
║   AES-256-GCM + Argon2id + Ed25519  //  Zero Trust             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

**Built with cryptographic precision. Designed for zero trust.**

</div>
