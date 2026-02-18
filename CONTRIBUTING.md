<div align="center">

```
╔═══════════════════════════════════════════════════════════╗
║             CONTRIBUTING TO TERMBACKUP                    ║
║                                                           ║
║   Development Guide  //  Standards  //  Workflow          ║
╚═══════════════════════════════════════════════════════════╝
```

</div>

---

Thank you for your interest in contributing to TermBackup. This guide covers everything you need to get started: environment setup, coding standards, testing requirements, architecture patterns, and the pull request process.

---

## // PREREQUISITES

| Requirement | Version |
|:------------|:--------|
| Python | 3.11+ |
| Poetry | Latest |
| Git | 2.30+ |
| OS | Windows 10+, macOS 12+, Linux |

---

## // SETUP

```bash
# Clone the repository
git clone https://github.com/scorpiocodex/Termbackup.git
cd termbackup

# Install all dependencies (runtime + dev)
poetry install

# Configure pre-commit hooks
pre-commit install

# Verify installation
poetry run pytest
poetry run termbackup --version
```

---

## // DEVELOPMENT WORKFLOW

### 1. Branch

```bash
git checkout -b <prefix>/short-description
```

| Prefix | Purpose | Example |
|:-------|:--------|:--------|
| `feature/` | New functionality | `feature/add-s3-backend` |
| `fix/` | Bug fixes | `fix/gcm-nonce-reuse` |
| `refactor/` | Structural changes, no behavior change | `refactor/extract-kdf-module` |
| `docs/` | Documentation only | `docs/update-security-model` |
| `test/` | Test additions or improvements | `test/add-archive-fuzzing` |
| `security/` | Security-related changes | `security/upgrade-argon2-params` |

### 2. Code

Follow the existing conventions:

```
┌───────────────────────────────────────────────────────────────────────────┐
│  STANDARD                    TOOL                CONFIGURATION           │
├───────────────────────────────────────────────────────────────────────────┤
│  Formatting                  Ruff Format          120 char line length    │
│  Linting                     Ruff Check           E, F, W, I, UP, S, B   │
│  Type Checking               mypy --strict        Pydantic plugin         │
│  Security Analysis           Bandit               tests/ excluded         │
│  Import Ordering             Ruff (isort)         Automatic               │
│  Python Target               3.11+                Type union syntax (|)   │
└───────────────────────────────────────────────────────────────────────────┘
```

**Key rules:**

- All public functions must have type annotations
- All terminal output goes through `ui.py` -- no direct `print()` or `console.print()` in domain modules
- All custom exceptions use the `errors.py` hierarchy with `hint` fields
- All encryption goes through `crypto.py` -- never implement custom cryptographic operations
- Never log or print secrets, tokens, passwords, or file contents
- Profile names are restricted to `^[a-zA-Z0-9_-]+$`
- File paths from archives must be validated against directory traversal

### 3. Test

Every change requires tests:

```bash
# Run the full suite (296 tests)
poetry run pytest

# With coverage
poetry run pytest --cov=termbackup --cov-report=term-missing

# Specific file
poetry run pytest tests/test_crypto.py -v

# Specific test
poetry run pytest tests/test_archive.py::test_create_and_read_v2_archive -v

# Property-based tests
poetry run pytest tests/test_crypto_properties.py -v
```

**Test standards:**

| Requirement | Standard |
|:------------|:---------|
| File naming | `tests/test_<module>.py` |
| Fixtures | Use `conftest.py` shared fixtures |
| External services | Always mocked (GitHub API, OS keyring) |
| File system | Use `tmp_path` fixture |
| Coverage | Both success and failure paths |
| Network calls | Never in tests |

### 4. Quality Checks

All checks must pass before committing:

```bash
# All checks in one command
pre-commit run --all-files

# Or individually:
poetry run ruff check termbackup/ tests/         # Lint
poetry run ruff format --check termbackup/ tests/ # Format check
poetry run mypy termbackup/                        # Type check
poetry run bandit -r termbackup/ -c pyproject.toml # Security lint
poetry run pytest --cov=termbackup                 # Tests + coverage
```

### 5. Commit

Write clear commit messages in imperative mood:

```
Add incremental backup delta detection

Implements SHA-256 based file change detection against the parent
backup manifest. Only modified files are included in the new archive,
reducing upload size and backup time.

Closes #42
```

| Component | Style |
|:----------|:------|
| Subject line | Imperative mood, max 72 chars, no period |
| Body | Wrapped at 72 chars, explains _why_ not _what_ |
| References | Issue/PR numbers on the last line |

### 6. Pull Request

- One concern per PR
- Clear title and description
- All CI checks passing
- Reference related issues
- Request review from maintainers

---

## // ARCHITECTURE PATTERNS

### Error Handling

```python
from termbackup.errors import CryptoError

# Always provide a hint for actionable guidance
raise CryptoError(
    "Decryption failed: invalid GCM authentication tag",
    hint="The password may be incorrect, or the archive may be corrupted.",
)
```

The error hierarchy:

```
TermBackupError (base, with optional hint)
├── ConfigError          Configuration issues
├── ProfileError         Profile CRUD issues
├── CryptoError          Encryption/decryption failures
├── ArchiveError         Archive format issues
├── GitHubError          API errors (includes status_code)
├── TokenError           Token validation failures
├── RestoreError         Restore operation failures
├── BackupError          Backup operation failures
└── IntegrityError       Data integrity failures
```

### Module Boundaries

```
┌─────────────────────────────────────────────────────────┐
│  cli.py         Command definitions, delegates to domain │
│  ui.py          ALL terminal output, no business logic   │
│  errors.py      Exception types, no business logic       │
│  models.py      Pydantic models, no side effects         │
│  engine.py      Orchestration, calls crypto/archive/git  │
│  crypto.py      ALL cryptographic operations             │
│  config.py      Config I/O, token management             │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- `cli.py` only defines commands and delegates to domain modules
- `ui.py` is the single terminal output point -- no module prints directly
- `crypto.py` owns all encryption -- no other module touches `cryptography` directly
- `models.py` contains pure data structures -- no I/O, no side effects
- `errors.py` contains only exception classes -- no business logic

---

## // REPORTING ISSUES

Include in bug reports:

1. **TermBackup version**: `termbackup --version`
2. **Python version**: `python --version`
3. **OS and version**
4. **Steps to reproduce**
5. **Expected vs actual behavior**
6. **Full error output** (redact tokens and passwords)

---

## // CODE OF CONDUCT

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). All contributors are expected to uphold a respectful and professional environment.

---

## // LICENSE

By contributing to TermBackup, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

<div align="center">

*Every contribution makes TermBackup stronger. Thank you.*

</div>
