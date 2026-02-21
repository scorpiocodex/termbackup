"""
Plugin Architecture for TermBackup
==================================
Dynamically loads external plugins prefixed with `termbackup-plugin-` or `termbackup_plugin_`.
"""

import importlib
import pkgutil
import logging
from typing import Any, Callable

from termbackup import ui

logger = logging.getLogger(__name__)

# Registry for plugin hooks
_HOOKS: dict[str, list[Callable[..., Any]]] = {
    "pre_backup": [],
    "post_backup": [],
    "cli_commands": [],
}


def register_hook(event: str, callback: Callable[..., Any]) -> None:
    """Registers a callback function for a specific plugin hook event."""
    if event in _HOOKS:
        _HOOKS[event].append(callback)
    else:
        logger.warning(f"Attempted to register callback for unknown hook: {event}")


def trigger_hook(event: str, *args, **kwargs) -> list[Any]:
    """Triggers all callbacks registered for a given hook event."""
    results = []
    if event in _HOOKS:
        for callback in _HOOKS[event]:
            try:
                results.append(callback(*args, **kwargs))
            except Exception as e:
                logger.error(f"Plugin error in hook '{event}': {e}")
                ui.warning(f"Plugin hook '{event}' raised an error: {e}")
    return results


def discover_plugins() -> list[str]:
    """Finds all installed plugins."""
    plugins = []
    # Discover via namespace / prefix
    for _, name, is_pkg in pkgutil.iter_modules():
        if name.startswith("termbackup_plugin_") or name.startswith("termbackup-plugin-"):
            plugins.append(name)
    return plugins


def load_plugins() -> None:
    """Loads all discovered plugins and executes their 'setup' function if present."""
    plugins = discover_plugins()
    loaded_count = 0
    for name in plugins:
        try:
            module = importlib.import_module(name)
            if hasattr(module, "setup"):
                module.setup()
                loaded_count += 1
                logger.info(f"Loaded plugin: {name}")
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            ui.warning(f"Failed to load plugin '{name}': {e}")
    if loaded_count > 0:
        ui.info(f"Loaded {loaded_count} plugin(s).")
