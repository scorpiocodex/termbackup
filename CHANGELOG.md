<div align="center">

```
╔═══════════════════════════════════════════════════════════╗
║                    CHANGELOG                              ║
║                                                           ║
║          TermBackup Version History                       ║
╚═══════════════════════════════════════════════════════════╝
```

</div>

All notable changes to TermBackup are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) | Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [6.0.0] - 2026-02-18

> Structured error hierarchy, 3 new CLI commands, enhanced diagnostics, modernized UI.

### Added

- **Structured error hierarchy** (`errors.py`) -- `TermBackupError` base class with 9 specialized subclasses: `ConfigError`, `ProfileError`, `CryptoError`, `ArchiveError`, `GitHubError` (with `status_code`), `TokenError`, `RestoreError`, `BackupError`, `IntegrityError`
- **Actionable error hints** -- all error types support an optional `hint` field displayed to users with guidance
- **`generate-key` command** -- generate Ed25519 signing keypair with password-protected PKCS8 storage
- **`audit-log` command** -- view audit log with `--limit`, `--operation`, and `--profile` filters
- **`clean` command** -- scan and remove orphaned temporary files with size reporting and confirmation
- **3 new doctor checks** -- profile source directory validation, critical dependency verification (cryptography, httpx, argon2, keyring, pydantic, pathspec), disk space monitoring (warns below 500 MB)
- **Environment info panel** -- doctor now displays TermBackup version, Python version, platform, and config directory
- **Daemon failure tracking** -- consecutive failure counter with warning threshold at 3+ failures
- **Daemon shutdown summary** -- Rich panel showing total uptime, iteration count, successes, and failures on exit
- **Operation timing** -- elapsed time display on `run`, `restore`, `verify`, and `rotate-key` commands
- **Modernized UI** -- emoji icon system with Unicode/ASCII adaptive fallback, visual progress bars (`[2/5] =====-----`), system info in banner, LOCK icon for password prompts
- **`py.typed` marker** -- PEP 561 typed package support

### Changed

- `GitHubError` now carries `status_code` (int) and `hint` (str) fields for precise error diagnosis
- `ArchiveError` and `CryptoError` raised with descriptive hints in archive read/write operations
- CLI `_handle_error()` displays hints from `TermBackupError` subclasses below the error message
- Doctor checks now report file sizes for audit log and orphaned temp files
- Version bumped to 6.0.0 across `__init__.py`, `pyproject.toml`, `ledger.py`, `models.py`, `github.py`

### Fixed

- **Mock patching bug** in `config.py` -- lazy import inside function body (`from termbackup import github`) was not patchable via `unittest.mock.patch`; replaced with `_get_github()` lazy loader pattern
- All 296 tests passing with 0 failures (71% coverage across 2,700 statements)

---

## [5.0.0] - 2025-02-10

> GitHub token validation, fine-grained token support, token management commands.

### Added

- **GitHub token validation** -- automatic validation on `init` and `update-token` with 3-retry logic
- **`update-token` command** -- update GitHub token with full re-validation and keyring storage
- **`token-info` command** -- display token metadata, type (classic/fine-grained), scopes, username, and expiry
- **`token_validator.py` module** -- comprehensive token validation for classic PAT (`ghp_*`) and fine-grained tokens (`github_pat_*`)
- **Doctor token check** -- validates token scopes and permissions during health diagnostic
- **Fine-grained token support** -- auto-detects token type and validates appropriate scopes/permissions

### Changed

- Token storage uses OS keyring exclusively; config file fallback preserved for backward compatibility
- Doctor command enhanced with token validation as the 12th health check

---

## [4.0.0] - 2024-12-01

> Major cryptographic upgrade, new archive format, signing, automation, webhooks.

### Added

- **AES-256-GCM + Argon2id** encryption -- modern AEAD cipher with memory-hard KDF
- **TBK2 binary archive format** -- self-describing headers with magic bytes, KDF params, cipher suite
- **Ed25519 digital signatures** -- optional cryptographic backup authentication
- **Backup diffing** -- `diff` command for file-level comparison between snapshots
- **Key rotation** -- `rotate-key` command to re-encrypt all backups with a new password
- **Daemon mode** -- `daemon` command for continuous background backups at configurable intervals
- **Webhook notifications** -- auto-detected Slack Block Kit, Discord Rich Embeds, or generic HTTP POST
- **OS-native scheduling** -- crontab (Linux/macOS) and Windows Task Scheduler integration
- **Profile export/import** -- JSON-based profile migration between machines
- **Audit logging** -- append-only JSONL log of all operations
- **Metadata ledger** -- remote `metadata.json` tracking all backups in the GitHub repository
- **Doctor command** -- 9-point health diagnostic

### Changed

- Migrated default encryption from AES-256-CBC + PBKDF2 (v1) to AES-256-GCM + Argon2id (v2)
- Archive format upgraded from TBK1 to TBK2 with full backward compatibility
- v1 archives auto-detected by magic bytes and remain fully restorable

---

## [3.0.0] - 2024-08-01

> Incremental backups, verification, pruning, profile system.

### Added

- **Incremental backups** -- SHA-256 delta detection against parent manifest
- **Backup verification** -- remote integrity checking (download + re-verify)
- **Pruning** -- automatic backup cleanup by count (`--max-backups`) and age (`--retention-days`)
- **Profile system** -- named backup configurations with per-profile source dirs, repos, and exclusions

---

## [2.0.0] - 2024-05-01

> Encrypted storage, GitHub backend, keyring integration.

### Added

- **AES-256-CBC + PBKDF2** encryption -- TBK1 archive format with HMAC-SHA256 integrity
- **GitHub storage backend** -- httpx HTTP/2 client with connection pooling and retries
- **OS keyring integration** -- secure token storage via platform-native credential manager

---

## [1.0.0] - 2024-02-01

> Initial release.

### Added

- Basic backup and restore functionality
- GitHub repository as storage backend
- CLI interface with Typer

---

<div align="center">

*Every version makes your backups more secure.*

</div>
