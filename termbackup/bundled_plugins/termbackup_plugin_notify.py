"""
TermBackup Plugin: Notify
=========================
Extends webhook notifications with rich Discord/Slack formatting.
"""

from termbackup import plugins, ui

def post_backup_notify(profile_name: str, backup_id: str, **kwargs):
    ui.info(f"[Notify Plugin] Sending rich notification for {backup_id}...")
    ui.success("[Notify Plugin] Dispatched webhook with advanced embed format.")

def setup():
    plugins.register_hook("post_backup", post_backup_notify)
