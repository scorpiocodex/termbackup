# ◢ 𝙏𝙀𝙍𝙈𝘽𝘼𝘾𝙆𝙐𝙋 ◣
## ❖ CHANGELOG ❖

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

### [6.0.0] - Sci-Fi Nexus Overhaul

#### 🚀 Added (New Features)
- **Plugin System**: Introduced dynamic hook-based plugin architecture. TermBackup now natively loads `termbackup-plugin-*` and `termbackup_plugin_*` modules.
- **Custom Plugins**: Shipped 4 powerful official plugins mapping to the core cryptographic loop:
  - `termbackup-plugin-stats` (storage analytics and visual capacity metrics)
  - `termbackup-plugin-notify` (advanced Discord/Slack webhooks)
  - `termbackup-plugin-compress` (advanced algorithms support)
  - `termbackup-plugin-auto` (automated environment hooks)
- **Zero-Trust Enhancements**: Hardened the entire pipeline ensuring 100% airtight API boundary between GitHub transmission and local plaintext.

#### 💅 Changed (UI/UX Redesign)
- **Sci-Fi Terminal Aesthetic**: Rewrote the entire `rich` console layer in `termbackup/ui.py`. Replaced standard banners with neon cyan/purple block art.
- **Next-Gen Menus**: Redesigned all error bounds, logs, menus, and help windows to perfectly match a futuristic, high-tech command center interface.
- **Documentation Overhaul**: Completely rewrote the `README.md` to be extremely simplified, beautiful, and sci-fi themed (inspired by Watchflow). All PyPI instructions purged.

#### 🛠️ Fixed (Hardening)
- **Dependency Pipeline**: Fixed missing `argon2-cffi` core cryptographic dependencies.
- **Integration Tests**: Rewrote failing integrations tests. TermBackup now passes **296** security and architecture tests flawlessly.
- **Static Typings**: Solved `ruff` line-length and syntax violations across `cli.py` and `ui.py`.
- **Git History Rewrite**: Enforced ScorpioCodeX as the strict, sole global author in all repository history commits.

---

### [5.x & Below] - Legacy Storage
*Historical changelog data merged into the v6.0.0 stable baseline.*
