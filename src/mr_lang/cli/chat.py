"""Interactive chat REPL with token-level streaming."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.markdown import Markdown

from mr_lang.cli.setup import setup_agent
from mr_lang.exceptions import MrLangError

console = Console(stderr=True)


async def run_chat(
    workspace: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    plugin: str | None = None,
    stream: bool = True,
) -> None:
    """Run the interactive chat loop."""
    thread_id = "cli-session"

    components = await setup_agent(
        workspace=workspace,
        provider=provider,
        model=model,
        plugin_name=plugin,
    )
    runner = components.runner
    console.print("[dim]Type 'quit' or 'exit' to end. 'clear' to reset.[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]you>[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break
        if user_input.strip().lower() == "clear":
            thread_id = f"cli-session-{id(object())}"
            console.print("[dim]Conversation cleared.[/dim]")
            continue

        try:
            if stream:
                console.print()
                full_response = ""
                async for token in runner.stream_tokens(message=user_input, thread_id=thread_id):
                    sys.stderr.write(token)
                    sys.stderr.flush()
                    full_response += token
                if full_response:
                    sys.stderr.write("\n\n")
                    sys.stderr.flush()
                else:
                    console.print("[dim]No response.[/dim]")
            else:
                result = await runner.run(message=user_input, thread_id=thread_id)
                messages = result.get("messages", [])
                if messages:
                    last = messages[-1]
                    content = last.content if hasattr(last, "content") else str(last)
                    console.print()
                    console.print(Markdown(content))
                    console.print()
        except MrLangError as e:
            console.print(f"[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"[red]Unexpected error:[/red] {e}")
