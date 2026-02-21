<div align="center">

# ◢ 𝙏𝙀𝙍𝙈𝘽𝘼𝘾𝙆𝙐𝙋 ◣
## ❖ NEXUS ZERO-TRUST ENGINE ❖

A sleek, next-generation encrypted backup platform that secures your files to GitHub with military-grade zero-trust cryptography.

[![Code Quality](https://img.shields.io/badge/Code_Quality-Pristine-purple.svg?style=for-the-badge)](https://github.com/scorpiocodex/termbackup)
[![Version](https://img.shields.io/badge/Version-6.0.0-blue.svg?style=for-the-badge)](https://github.com/scorpiocodex/termbackup)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

*Author:* **ScorpioCodeX**  
*Contact:* **scorpiocodex0@gmail.com**

</div>

---

## ⚡ WHAT IS TERMBACKUP?

**TermBackup** is a modern, powerful tool designed to make backing up your important files effortless and completely secure. If you have files you cannot afford to lose—or let anyone else see—TermBackup is your ultimate defense.

It sits securely on your machine. Before any file ever leaves your computer, TermBackup locks it down using advanced military-grade encryption. It then packages it into a tamper-proof archive and safely uploads it to a private GitHub repository. 

**Your files never leave your machine unencrypted. Not once. Not ever.**

---

## 🌌 NEXT-GENERATION FEATURES

- 🛡️ **Zero-Trust Security**: Everything happens on your PC. GitHub never sees your actual files, and nobody can read them without your exact password.
- ⚡ **Lightning Fast & Smart**: Only uploads files that have changed since your last backup, saving massive amounts of time and bandwidth.
- 🛸 **Live Holographic Dashboard**: Run your backups and watch a stunning visual dashboard in your terminal showing live progress, file scanning, and system performance.
- 🕒 **Time-Travel Restore**: Easily list your past backups and restore your entire project to exactly how it looked at that moment in time.
- 👻 **Ghost Mode (Daemon)**: Run TermBackup completely silently in the background (`termbackup daemon`), automatically backing up on a smooth schedule.
- 🧪 **Safe Simulation (Dry-Run)**: Test your backup sweeps without actually uploading anything safely using the `--dry-run` flag.
- 🧩 **Modular Plugins**: Extend the power of TermBackup with custom plugins for advanced analytics, Discord/Slack webhooks, and automation.

---

## 🧑‍🚀 INSTALLATION PROTOCOL

TermBackup is maintained securely on GitHub. To use it, simply install it directly from this repository using `pipx` or `pip`.

*(Note: TermBackup is exclusively hosted on GitHub. It is not available on PyPI.)*

### The Best Way (`pipx`)
If you want TermBackup to be available anywhere on your computer in any folder, use `pipx`:
```bash
pipx install git+https://github.com/scorpiocodex/termbackup.git
```

### The Standard Way (`pip`)
If you are using a Python environment, `pip` works perfectly:
```bash
pip install git+https://github.com/scorpiocodex/termbackup.git
```

---

## 🚀 QUICK START GUIDE

Ready to experience the future of secure backups? Getting started takes less than a minute.

**1. Initialize your system**
Open your terminal and connect TermBackup to your GitHub account:
```bash
termbackup init
```
*This asks for your GitHub token and sets up your secure local vault.*

**2. Create a Tracker Profile**
Tell TermBackup what folder to protect and where to put it:
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

## 🔌 CUSTOM PLUGINS

TermBackup natively supports dynamic extension plugins that run seamlessly alongside the core cryptographic engine.

To load a plugin, simply ensure its Python file (e.g., `termbackup_plugin_stats.py`) is located in your project or installed in your Python environment. TermBackup dynamically loads any package starting with `termbackup-plugin-` or module starting with `termbackup_plugin_`.

### Official Custom Plugins Available:
- 📊 `termbackup-plugin-stats`: Generates visual capacity planning charts and deduplication savings metrics. Run `termbackup plugins stats` to view.
- 🔔 `termbackup-plugin-notify`: Extends native functionality with ultra-rich Discord and Slack multi-field embeds after a backup finishes.
- 📦 `termbackup-plugin-compress`: Connects extreme-ratio algorithms (like Zstandard/Brotli) to the archiving engine.
- ⚙️ `termbackup-plugin-auto`: Automates system preparations (like triggering SQL database dumps) directly before your backup starts.

---

## 🛠️ USEFUL COMMANDS

| Command | What it does |
| --- | --- |
| `termbackup run <profile>` | Starts the live visual dashboard and runs a secure backup. |
| `termbackup list <profile>` | Lists all successful past backups for a profile. |
| `termbackup restore <id> -p <profile>` | Downloads, decrypts, and restores your files magically. |
| `termbackup verify <id> -p <profile>` | Checks the health and integrity of a backup remotely without downloading the whole file. |
| `termbackup daemon <profile>` | Starts TermBackup silently in the background for continuous protection. |
| `termbackup doctor` | Runs a 12-point health diagnostic scan on your entire system. |
| `termbackup plugins list` | Lists all active loaded plugins. |

---

<div align="center">
  <p><b>Created with passion by ScorpioCodeX.</b></p>
  <p><i>The future of zero-trust security has arrived.</i></p>
</div>
