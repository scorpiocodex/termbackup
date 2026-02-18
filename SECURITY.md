<div align="center">

```
╔═══════════════════════════════════════════════════════════╗
║                SECURITY POLICY                            ║
║                                                           ║
║   Vulnerability Reporting  //  Architecture  //  Model    ║
╚═══════════════════════════════════════════════════════════╝
```

</div>

---

## // SUPPORTED VERSIONS

| Version | Status | Support |
|:--------|:-------|:--------|
| **6.x** | Current | Full security support |
| **5.x** | Legacy | Critical security fixes only |
| **4.x** | EOL | No support |
| **< 4.0** | EOL | No support |

---

## // REPORTING A VULNERABILITY

If you discover a security vulnerability in TermBackup, **do not open a public issue**.

### Reporting Process

1. **Report privately** via email to the maintainer (see `pyproject.toml` for contact information)
2. **Include** in your report:
   - Clear description of the vulnerability
   - Steps to reproduce
   - Affected versions
   - Potential impact assessment (confidentiality, integrity, availability)
   - Proof of concept (if available)
   - Suggested fix or mitigation (if any)

### Response Timeline

| Stage | Timeline |
|:------|:---------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 7 days |
| Fix development | Depends on severity |
| Security advisory | Published with fix release |

### Severity Classification

| Severity | Description | Response |
|:---------|:------------|:---------|
| **Critical** | Key/password exposure, remote code execution | Immediate patch |
| **High** | Authentication bypass, data leakage | Patch within 7 days |
| **Medium** | Information disclosure, privilege escalation | Patch within 30 days |
| **Low** | Minor issues, hardening opportunities | Next scheduled release |

---

## // ENCRYPTION ARCHITECTURE

### Cryptographic Primitives

```
┌──────────────────────┬────────────────────┬───────────────────────────────────┐
│  COMPONENT           │  ALGORITHM         │  PARAMETERS                       │
├──────────────────────┼────────────────────┼───────────────────────────────────┤
│  Key Derivation      │  Argon2id          │  64 MiB memory, 3 iterations,    │
│                      │  (RFC 9106)        │  4 parallelism, 32-byte salt     │
├──────────────────────┼────────────────────┼───────────────────────────────────┤
│  Encryption          │  AES-256-GCM       │  12-byte random nonce,           │
│                      │  (NIST SP 800-38D) │  128-bit authentication tag      │
├──────────────────────┼────────────────────┼───────────────────────────────────┤
│  Signing             │  Ed25519           │  256-bit keys, PKCS8 storage,    │
│                      │  (RFC 8032)        │  password-encrypted private key  │
├──────────────────────┼────────────────────┼───────────────────────────────────┤
│  File Integrity      │  SHA-256           │  Per-file checksums in manifest  │
│                      │  (FIPS 180-4)      │                                   │
├──────────────────────┼────────────────────┼───────────────────────────────────┤
│  Legacy KDF          │  PBKDF2            │  600,000 iterations, 32-byte     │
│  (v1 only)           │  (RFC 2898)        │  salt, HMAC-SHA256               │
├──────────────────────┼────────────────────┼───────────────────────────────────┤
│  Legacy Encryption   │  AES-256-CBC       │  16-byte IV, PKCS7 padding,      │
│  (v1 only)           │                    │  HMAC-SHA256 for integrity       │
└──────────────────────┴────────────────────┴───────────────────────────────────┘
```

### Zero-Trust Storage Model

TermBackup treats the storage backend (GitHub) as **completely untrusted**:

- **All cryptographic operations happen locally** -- the server never sees plaintext
- **No key escrow** -- passwords are never stored, transmitted, or logged
- **No recovery mechanism** -- password loss means permanent data loss
- **Unique randomness per backup** -- each archive gets a fresh random salt and nonce
- **Authentication tag verification** -- any bit flip in the ciphertext causes decryption failure

### Credential Storage

```
┌─────────────────────┬──────────────────────────────────────────────────┐
│  PLATFORM           │  KEYRING BACKEND                                 │
├─────────────────────┼──────────────────────────────────────────────────┤
│  macOS              │  Keychain Services                               │
│  Windows            │  Windows Credential Locker                       │
│  Linux (GNOME)      │  GNOME Keyring / Secret Service                  │
│  Linux (KDE)        │  KWallet                                         │
│  Linux (headless)   │  keyrings.alt (file-based, encrypted)           │
└─────────────────────┴──────────────────────────────────────────────────┘
```

- Tokens are **never written to config files** in plaintext
- Legacy configs with inline tokens are supported; `termbackup migrate` moves them to the keyring
- Token validation checks scopes and permissions on `init` and `update-token`
- Both classic PATs (`ghp_*`) and fine-grained tokens (`github_pat_*`) are supported

### Input Validation & Hardening

| Surface | Protection |
|:--------|:-----------|
| Profile names | Restricted to `^[a-zA-Z0-9_-]+$` -- prevents command injection in scheduled tasks |
| Archive paths | Validated against directory traversal (`../../`) on extraction using `Path.resolve()` |
| Config files | Set to `chmod 600` (owner read/write only) on Unix systems |
| Token display | Tokens are masked in all UI output (`ghp_****...****abcd`) |
| Audit log | Never contains passwords, tokens, or file contents |
| Error messages | Never expose sensitive data; use `hint` fields for guidance |

---

## // KNOWN SECURITY CONSIDERATIONS

### Password Strength

Argon2id with 64 MiB memory cost significantly raises the cost of brute-force attacks, but cannot compensate for fundamentally weak passwords.

**Recommendation**: Use a password manager to generate passwords of 20+ random characters.

### GitHub Token Scope

Classic PATs require the `repo` scope (full access to private repositories). This is broad because TermBackup needs to create repositories, read/write file contents, and manage commits.

**Recommendation**: Use fine-grained tokens scoped to specific backup repositories, or create a dedicated GitHub account for backups.

### Local Machine Security

TermBackup does not protect against:

| Threat | Attack Vector |
|:-------|:-------------|
| **Keyloggers** | Capture encryption password at input time |
| **Malware** | Inspect running process memory for keys |
| **Root access** | Full memory and filesystem access |
| **Cold boot** | RAM contents persist briefly after shutdown |

**Recommendation**: Enable full-disk encryption (BitLocker, FileVault, LUKS). Keep your OS and dependencies updated. Use a hardware security key where possible.

### Nonce Safety

AES-256-GCM requires unique nonces. TermBackup generates 12-byte nonces using `secrets.token_bytes()` (cryptographically random). Combined with a unique 32-byte random salt per backup, nonce collision probability is negligible.

---

## // DEPENDENCY SECURITY

TermBackup's cryptographic stack:

| Library | Source | Notes |
|:--------|:-------|:------|
| `cryptography` | PyCA (Python Cryptographic Authority) | Backed by OpenSSL; widely audited |
| `argon2-cffi` | Reference C implementation | PHC competition winner |
| `keyring` | PyPI / jaraco | Platform-native credential storage |

### Audit Pipeline

- **`pip-audit`** runs in CI on every push -- scans all dependencies for known CVEs
- **`bandit`** runs in CI on every push -- scans source code for security anti-patterns
- **`detect-private-key`** pre-commit hook prevents accidental key commits
- **Dependabot** / manual review for dependency updates

---

## // AUDIT LOG

All operations are recorded to `~/.termbackup/audit.log` in append-only JSONL format:

```json
{"timestamp": "2026-02-18T10:00:00+00:00", "operation": "backup", "profile": "my-project", "status": "success", "details": {"backup_id": "abc123", "file_count": 42}}
```

**Logged operations**: backup, restore, verify, prune, rotate-key, schedule-enable, schedule-disable

**Never logged**: passwords, tokens, file contents, file paths, encryption keys

---

<div align="center">

*Security is not a feature. It is the foundation.*

</div>
