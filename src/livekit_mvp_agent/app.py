from __future__ import annotations

import argparse
import asyncio
import sys
from rich.console import Console

from .config import get_settings
from .pipeline import VoicePipeline  # <-- class name fixed

console = Console()


def run_dry_run(settings) -> None:
    console.print("[cyan]Dry-run: initializing components only (no network).[/cyan]")
    console.print(f"[green]LLM: {settings.llm_model}[/green]")
    console.print(f"[green]STT: {settings.whisper_model}[/green]")
    console.print(f"[green]TTS primary: {settings.tts_primary}[/green]")
    console.print("[green]OK: configuration & imports are healthy.[/green]")


async def run_agent(no_livekit: bool) -> None:
    settings = get_settings()
    pipeline = VoicePipeline(settings=settings, enable_livekit=not no_livekit)
    await pipeline.run()

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="livekit_mvp_agent", description="Local EN/FR voice agent"
    )
    parser.add_argument("--dry-run", action="store_true", help="Initialize and exit")
    parser.add_argument("--no-livekit", action="store_true", help="Run without LiveKit (standalone)")
    args = parser.parse_args()

    try:
        settings = get_settings()
        console.print("[bold green]Configuration loaded successfully[/bold green]")
        console.print(f"LLM Model: {settings.llm_model}")
        console.print(f"Whisper Model: {settings.whisper_model}")
        console.print(f"TTS Primary: {settings.tts_primary}")

        if args.dry_run:
            run_dry_run(settings)
            return

        asyncio.run(run_agent(no_livekit=args.no_livekit))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Agent failed: {e}[/red]")
        raise




if __name__ == "__main__":
    main()