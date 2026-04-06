"""Shell execution tool."""

from __future__ import annotations

import logging
import subprocess

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Populated at startup by setup_agent() from MrLangConfig.get_tools_blocked_commands()
_blocked_commands: list[str] = []


def set_blocked_commands(patterns: list[str]) -> None:
    """Configure blocked shell command patterns."""
    global _blocked_commands  # noqa: PLW0603
    _blocked_commands = patterns


def _check_command(command: str) -> str | None:
    """Return an error string if command matches a blocked pattern, else None."""
    cmd_lower = command.lower().strip()
    for pattern in _blocked_commands:
        if pattern.lower() in cmd_lower:
            logger.warning("Blocked shell command matching '%s': %s", pattern, command[:100])
            return f"Error: Command blocked by safety policy (matches '{pattern}')"
    return None


@tool
def run_shell(command: str, timeout: int = 30) -> str:
    """Execute a shell command and return its output.

    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds (default: 30)
    """
    if err := _check_command(command):
        return err
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except OSError as exc:
        return f"Error: {exc}"
