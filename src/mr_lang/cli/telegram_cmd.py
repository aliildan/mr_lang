"""CLI entrypoint for the Telegram bot adapter."""

from __future__ import annotations

import asyncio
import signal

from rich.console import Console

from mr_lang.adapters.telegram import AuthConfig, TelegramBot
from mr_lang.cli.setup import setup_agent
from mr_lang.exceptions import AdapterError
from mr_lang.plugins.loader import PluginLoader

console = Console(stderr=True)


async def run_telegram(
    workspace: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    plugin: str | None = None,
) -> None:
    """Wire up workspace/provider/graph/runner and start the Telegram bot."""
    # Discover plugins first to resolve workspace before agent setup
    manifests = PluginLoader.discover_plugins()
    telegram_plugins = [m for m in manifests if m.telegram is not None]

    manifest = None
    if plugin:
        matches = [m for m in telegram_plugins if m.name == plugin]
        if not matches:
            available = [m.name for m in manifests]
            raise AdapterError(
                f"Plugin '{plugin}' not found or has no [plugin.telegram] section. "
                f"Available plugins: {', '.join(available) or 'none'}"
            )
        manifest = matches[0]
    elif len(telegram_plugins) == 1:
        manifest = telegram_plugins[0]
        console.print(f"[dim]Auto-selected plugin: {manifest.name}[/dim]")
    elif len(telegram_plugins) > 1:
        names = ", ".join(m.name for m in telegram_plugins)
        raise AdapterError(
            f"Multiple plugins have [plugin.telegram] config: {names}. "
            f"Use --plugin <name> to select one."
        )

    # Use plugin's workspace if no explicit --workspace given
    if manifest and not workspace:
        ws_path = manifest.resolve_workspace()
        if ws_path and ws_path.is_dir():
            workspace = str(ws_path)
            console.print(f"[green]Workspace:[/green] {workspace}")

    components = await setup_agent(
        workspace=workspace,
        provider=provider,
        model=model,
        plugin_name=manifest.name if manifest else None,
    )
    config = components.config

    if manifest and manifest.telegram:
        # Plugin-sourced config
        tc = manifest.telegram
        token = tc.bot_token
        auth_config = AuthConfig(
            mode=tc.auth_mode or config.telegram_auth_mode,
            allowed_user_ids=tc.allowed_user_ids or config.get_telegram_allowed_user_ids(),
            admin_user_ids=tc.admin_user_ids or config.get_telegram_admin_user_ids(),
            invite_codes=tc.invite_codes or config.get_telegram_invite_codes(),
            max_uses_per_code=(
                tc.max_uses_per_code
                if tc.max_uses_per_code is not None
                else config.telegram_max_uses_per_code
            ),
        )
        console.print(f"[green]Plugin:[/green] {manifest.name}")
    else:
        # Legacy global config path
        token = config.telegram_bot_token
        if not token:
            raise AdapterError(
                "No Telegram bot token configured. Either add [plugin.telegram] "
                "to your plugin's mr_lang_plugin.toml, or set MR_LANG_TELEGRAM_BOT_TOKEN."
            )
        auth_config = AuthConfig(
            mode=config.telegram_auth_mode,
            allowed_user_ids=config.get_telegram_allowed_user_ids(),
            admin_user_ids=config.get_telegram_admin_user_ids(),
            invite_codes=config.get_telegram_invite_codes(),
            max_uses_per_code=config.telegram_max_uses_per_code,
        )

    console.print(f"[green]Auth mode:[/green] {auth_config.mode}")

    bot = TelegramBot(
        runner=components.runner,
        token=token,
        auth_config=auth_config,
        skills=components.skill_registry.list(),
    )

    # Handle graceful shutdown via signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))

    await bot.start()
