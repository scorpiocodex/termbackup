<div align="center">

# ▰▰▰ 𝙏𝙀𝙍𝙈𝘽𝘼𝘾𝙆𝙐𝙋 ▰▰▰
## ◈ NEXUS ZERO-TRUST ENGINE ◈

A sleek, next-generation encrypted backup platform that secures your files to GitHub with military-grade zero-trust cryptography and a holographic terminal UI.

[![Code Quality](https://img.shields.io/badge/Code_Quality-Pristine-purple.svg?style=for-the-badge)](https://github.com/scorpiocodex/termbackup)
[![Version](https://img.shields.io/badge/Version-6.0.0-blue.svg?style=for-the-badge)](https://github.com/scorpiocodex/termbackup)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

*Author:* **ScorpioCodeX**  
*Contact:* **scorpiocodex0@gmail.com**

</div>

---

## ⚡ WHAT IS TERMBACKUP?

**TermBackup** is a modern, powerful tool designed to make backing up your important files effortless and completely secure. If you have files you cannot afford to lose—or let anyone else see—TermBackup is your ultimate defense.

It sits securely on your machine. Before any file ever leaves your computer, TermBackup locks it down using advanced military-grade cryptography (AES-256-GCM + Argon2id). It packages everything into a tamper-proof archive and safely uploads it to a private GitHub repository. 

**Your files never leave your machine unencrypted. Not once. Not ever.**

---

## 🌌 NEXT-GENERATION FEATURES

- 🛡️ **Zero-Trust Security**: Everything happens on your PC. GitHub never sees your actual files, and nobody can read them without your exact password.
- ⚡ **Lightning Fast & Smart**: Only uploads files that have changed since your last backup, saving massive amounts of time and bandwidth.
- 🛸 **Live Holographic Dashboard**: Run your backups and watch a stunning visual dashboard in your terminal showing live progress, file scanning, and system performance.
- 🕒 **Time-Travel Restore**: Easily list your past backups and restore your entire project to exactly how it looked at that moment in time.
- 👻 **Ghost Mode (Daemon)**: Run TermBackup completely silently in the background (`termbackup daemon`), automatically backing up on a smooth schedule.
- 🧪 **Safe Simulation (Dry-Run)**: Test your backup sweeps without actually uploading anything safely using the `--dry-run` flag.
- 🧩 **Modular Plugins**: Extend TermBackup natively with built-in analytics, GUI launchers, data export tools, and security audits!

---

## 🧑‍🚀 INSTALLATION PROTOCOL

TermBackup is maintained securely on GitHub. *(It is exclusively hosted on GitHub and is not available on PyPI).*

### The Best Way (`pipx`)
If you want TermBackup to be available anywhere on your computer as a standalone command line tool, use `pipx` (recommended):
```bash
pipx install git+https://github.com/scorpiocodex/Termbackup.git
```

### The Standard Way (`pip`)
If you are using a Python environment, `pip` works perfectly:
```bash
pip install git+https://github.com/scorpiocodex/Termbackup.git
```

---

## 🚀 QUICK START GUIDE

Ready to experience the future of secure backups? Getting started takes less than a minute.

**1. Initialize your system**
Open your terminal and connect TermBackup to your GitHub account:
```bash
termbackup init
```
*It will securely ask for your GitHub Personal Access Token (PAT) and set up your local vault.*

**2. Create a Tracker Profile**
Tell TermBackup what folder to protect and where to store it on GitHub:
```bash
termbackup profile create my-project --source /path/to/my-project --repo scorpiocodex/my-project-backup
```

**3. Boot the Orchestrator!**
Start the live dashboard and lock down your files:
```bash
termbackup run my-project
```
*You will be asked to create a powerful password. TermBackup instantly encrypts and stores your files safely.*

---

## 🔌 THE EXTENSION METAVERSE (PLUGINS)

TermBackup natively supports dynamic plugins that run seamlessly alongside the core cryptographic engine.

We have bundled 4 highly powerful custom plugins for you to use instantly! Run `termbackup plugins list` to verify they are active.

### Official Native Plugins Included:
- 📊 `termbackup-plugin-stats`: Parses your encrypted metadata ledger to provide real-time metrics on deduplication, file counts, and average backup sizes across all your profiles. Run `termbackup plugins stats`.
- 🖥️ `termbackup-plugin-tui`: Launches a rich, interactive text-based user interface (TUI) dashboard to review the telemetry and health of all configured project profiles. Run `termbackup plugins tui`.
- 📁 `termbackup-plugin-export`: Need to keep a local archive of your backup history? Run `termbackup plugins export <profile>` to immediately extract your backup ledger into a clean JSON log file for your own data science integration.
- 🛡️ `termbackup-plugin-strict_audit`: A deep security simulator that verifies your cryptographic boundaries post-backup.

---

## 🛠️ CORE COMMAND UPLINK

| Command | What it does |
| --- | --- |
| `termbackup run <profile>` | Starts the live visual dashboard and runs a secure backup. |
| `termbackup list <profile>` | Lists all successful past backups for a profile. |
| `termbackup restore <id> -p <profile>` | Downloads, decrypts, and restores your files magically. |
| `termbackup verify <id> -p <profile>` | Checks the health and integrity of a backup remotely without downloading the whole file. |
| `termbackup daemon <profile>` | Starts TermBackup silently in the background for continuous protection. |
| `termbackup doctor` | Runs a 12-point health diagnostic scan on your entire system. |
| `termbackup plugins list` | Lists all active loaded plug-in extension modules. |

Run `termbackup --help` in your terminal to see the beautifully themed sci-fi help manual.

---

<div align="center">
  <p><b>Engineered with passion by ScorpioCodeX.</b></p>
  <p><i>The future of zero-trust security has arrived.</i></p>
</div>
