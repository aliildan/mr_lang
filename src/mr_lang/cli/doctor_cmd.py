"""CLI command: mr-lang doctor — diagnose common issues."""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console
from rich.table import Table

from mr_lang.config import MrLangConfig

console = Console(stderr=True)


def run_doctor() -> None:
    """Run all diagnostic checks and report results."""
    console.print("\n[bold]mr-lang doctor[/bold] — checking your setup...\n")

    checks: list[tuple[str, str, str]] = []  # (name, status, detail)

    # 1. Python version
    import sys

    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python", "ok", pyver))

    # 2. Config loading
    config_detail = ""
    config_ok = True
    try:
        cfg = MrLangConfig()
        config_detail = "loaded"
    except Exception as exc:
        config_ok = False
        config_detail = str(exc)[:80]
    checks.append(("Config", "ok" if config_ok else "fail", config_detail))

    # 3. .env file
    env_path = Path(".env")
    if env_path.exists():
        issues = _check_env_file(env_path)
        if issues:
            checks.append(("Env file", "warn", "; ".join(issues)))
        else:
            checks.append(("Env file", "ok", str(env_path.resolve())))
    else:
        checks.append(("Env file", "skip", "no .env (using env vars or defaults)"))

    # 4. Provider / model
    if config_ok:
        provider = cfg.default_provider
        model = cfg.default_model
        provider_status, provider_detail = _check_provider(cfg)
        checks.append(("Provider", provider_status, f"{provider}/{model} — {provider_detail}"))
    else:
        checks.append(("Provider", "skip", "config failed to load"))

    # 5. Ollama connectivity
    if config_ok and cfg.default_provider == "ollama":
        ollama_status, ollama_detail = _check_ollama(cfg)
        checks.append(("Ollama", ollama_status, ollama_detail))

    # 6. Telegram
    if config_ok:
        tg_status, tg_detail = _check_telegram(cfg)
        checks.append(("Telegram", tg_status, tg_detail))

    # 7. Workspace
    if config_ok and cfg.workspace_dir:
        ws_status, ws_detail = _check_workspace(cfg.workspace_dir)
        checks.append(("Workspace", ws_status, ws_detail))

    # 8. Plugin discovery
    plugin_status, plugin_detail = _check_plugins()
    checks.append(("Plugins", plugin_status, plugin_detail))

    # 9. Dependencies
    for pkg, extra in [
        ("langchain_ollama", "ollama"),
        ("langchain_openai", "openai"),
        ("langchain_anthropic", "anthropic"),
        ("telegram", "telegram"),
        ("fastmcp", "mcp"),
    ]:
        installed = _module_exists(pkg)
        checks.append(
            (
                f"Extra [{extra}]",
                "ok" if installed else "skip",
                "installed" if installed else f"pip install mr-lang[{extra}]",
            )
        )

    # 10. Observability logs
    log_dir = Path(".mr_lang/logs")
    if log_dir.exists():
        log_count = len(list(log_dir.glob("*.jsonl")))
        checks.append(("Logs", "ok", f"{log_count} session(s) in {log_dir}"))
    else:
        checks.append(("Logs", "skip", "no sessions recorded yet"))

    # Print results
    _print_results(checks)


def _check_env_file(path: Path) -> list[str]:
    """Check .env file for common issues."""
    issues: list[str] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            # Inline comment detection
            if "#" in value and not value.startswith('"') and not value.startswith("'"):
                # Check if it looks like a real inline comment (not part of a URL)
                before_hash = value.split("#")[0].rstrip()
                if before_hash != value.rstrip():
                    issues.append(
                        f"line {lineno}: inline comment in {key.strip()} "
                        f"(will be included as value)"
                    )
            # Empty value for required-ish fields
            if key.strip() == "MR_LANG_TELEGRAM_BOT_TOKEN" and not value.strip():
                issues.append("TELEGRAM_BOT_TOKEN is empty")
    return issues


def _check_provider(cfg: MrLangConfig) -> tuple[str, str]:
    """Check if the configured provider module is importable."""
    provider_modules = {
        "ollama": "langchain_ollama",
        "openai": "langchain_openai",
        "anthropic": "langchain_anthropic",
    }
    module = provider_modules.get(cfg.default_provider)
    if not module:
        return "warn", f"unknown provider '{cfg.default_provider}'"
    if _module_exists(module):
        return "ok", "module installed"
    return "fail", f"pip install mr-lang[{cfg.default_provider}]"


def _check_ollama(cfg: MrLangConfig) -> tuple[str, str]:
    """Check Ollama server connectivity and model availability."""
    import httpx

    base_url = cfg.ollama_base_url or "http://127.0.0.1:11434"
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        if cfg.default_model in models:
            return "ok", f"reachable, model '{cfg.default_model}' available"
        available = ", ".join(models[:5])
        return "warn", (
            f"reachable but model '{cfg.default_model}' not found. Available: {available}"
        )
    except httpx.ConnectError:
        return "fail", f"cannot connect to {base_url}"
    except Exception as exc:
        return "fail", str(exc)[:80]


def _check_telegram(cfg: MrLangConfig) -> tuple[str, str]:
    """Check Telegram bot token and for conflicting instances."""
    token = cfg.telegram_bot_token
    if not token:
        return "skip", "no token configured"

    if not _module_exists("telegram"):
        return "fail", "pip install mr-lang[telegram]"

    import httpx

    # Validate token with getMe
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        data = resp.json()
        if not data.get("ok"):
            return "fail", f"invalid token: {data.get('description', 'unknown error')}"
        bot_name = data["result"].get("username", "unknown")
    except Exception as exc:
        return "fail", f"cannot reach Telegram API: {exc}"

    # Check for conflicting polling
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"limit": 1, "timeout": 1},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok") and "Conflict" in data.get("description", ""):
            return "warn", (
                f"@{bot_name} — another instance is already polling. "
                f"Stop it before starting mr-lang telegram"
            )
        return "ok", f"@{bot_name} — token valid, no conflicts"
    except Exception:
        return "ok", f"@{bot_name} — token valid"


def _check_workspace(workspace_dir: Path) -> tuple[str, str]:
    """Check workspace directory structure."""
    if not workspace_dir.exists():
        return "fail", f"{workspace_dir} does not exist"
    identity = workspace_dir / "IDENTITY.md"
    if not identity.exists():
        return "fail", f"IDENTITY.md missing in {workspace_dir}"
    files = [f.stem for f in workspace_dir.glob("*.md")]
    return "ok", f"files: {', '.join(sorted(files))}"


def _check_plugins() -> tuple[str, str]:
    """Check plugin discovery."""
    manifests: list[str] = []
    # Check CWD
    if Path("mr_lang_plugin.toml").exists():
        manifests.append("cwd")
    # Check env var
    env_plugins = os.environ.get("MR_LANG_PLUGINS", "")
    if env_plugins:
        for p in env_plugins.split(":"):
            p = p.strip()
            if p and Path(p).exists():
                manifests.append(p)
    if manifests:
        return "ok", f"found: {', '.join(manifests)}"
    return "skip", "no plugins discovered"


def _module_exists(module: str) -> bool:
    """Check if a Python module is importable."""
    from importlib.util import find_spec

    return find_spec(module) is not None


def _print_results(checks: list[tuple[str, str, str]]) -> None:
    """Print diagnostic results as a Rich table."""
    table = Table(show_header=True, border_style="dim")
    table.add_column("Check", style="bold", width=16)
    table.add_column("Status", width=6, justify="center")
    table.add_column("Details")

    status_style = {
        "ok": "[green]OK[/green]",
        "warn": "[yellow]WARN[/yellow]",
        "fail": "[red]FAIL[/red]",
        "skip": "[dim]SKIP[/dim]",
    }

    fail_count = 0
    warn_count = 0
    for name, status, detail in checks:
        table.add_row(name, status_style.get(status, status), detail)
        if status == "fail":
            fail_count += 1
        elif status == "warn":
            warn_count += 1

    console.print(table)
    console.print()

    if fail_count:
        console.print(f"[red]{fail_count} issue(s) need fixing.[/red]")
    elif warn_count:
        console.print(f"[yellow]{warn_count} warning(s), but should work.[/yellow]")
    else:
        console.print("[green]All checks passed.[/green]")
    console.print()
