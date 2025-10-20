"""
CLI application entry point for LiveKit MVP Agent
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from .config import get_settings
from .logging_setup import setup_logging
from .pipeline import VoiceAgentPipeline

console = Console()


@click.command()
@click.option(
    "--config", 
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
@click.option(
    "--room-name",
    type=str,
    help="LiveKit room name to join"
)
@click.option(
    "--participant-name",
    type=str,
    default="VoiceAgent",
    help="Agent participant name"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run in dry-run mode (no actual connections)"
)
@click.version_option(version="0.1.0")
def main(
    config: Optional[Path],
    log_level: str,
    room_name: Optional[str],
    participant_name: str,
    dry_run: bool,
) -> None:
    """
    LiveKit MVP Agent - Local bilingual voice agent
    
    A production-ready voice agent that runs entirely locally with LiveKit,
    faster-whisper, Ollama, and TTS systems (Kokoro/Piper).
    """
    
    # Setup logging
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    # Load settings
    try:
        settings = get_settings(config_file=config)
        if room_name:
            settings.livekit_room_name = room_name
        if participant_name:
            settings.livekit_participant_name = participant_name
            
        logger.info("Configuration loaded successfully")
        logger.info(f"LLM Model: {settings.llm_model}")
        logger.info(f"Whisper Model: {settings.whisper_model}")
        logger.info(f"TTS Primary: {settings.tts_primary}")
        
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)
    
    # Validate required settings
    if not dry_run:
        if not settings.livekit_url:
            console.print("[red]Error: LIVEKIT_URL is required[/red]")
            console.print("Please set it in .env or config/settings.toml")
            sys.exit(1)
            
        if not settings.livekit_api_key:
            console.print("[yellow]Warning: LIVEKIT_API_KEY not set[/yellow]")
            console.print("Some features may not work without proper LiveKit credentials")
    
    # Run the agent
    try:
        if dry_run:
            console.print("[yellow]Running in dry-run mode...[/yellow]")
            run_dry_run(settings)
        else:
            console.print("[green]Starting LiveKit MVP Agent...[/green]")
            asyncio.run(run_agent(settings))
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Agent stopped by user[/yellow]")
    except Exception as e:
        logger.error(f"Agent failed: {e}", exc_info=True)
        console.print(f"[red]Agent failed: {e}[/red]")
        sys.exit(1)


def run_dry_run(settings) -> None:
    """Run a dry-run test of the agent components"""
    console.print("🧪 Testing agent components...")
    
    # Test imports
    try:
        from .adapters.stt_whisper import WhisperSTT
        from .adapters.llm_ollama import OllamaLLM
        from .adapters.tts_kokoro import KokoroTTS
        from .adapters.vad_silero import SileroVAD
        console.print("✓ All modules import successfully")
    except ImportError as e:
        console.print(f"✗ Import error: {e}")
        return
    
    # Test component initialization
    try:
        # VAD
        vad = SileroVAD(threshold=settings.vad_threshold)
        console.print("✓ VAD initialized")
        
        # STT
        stt = WhisperSTT(
            model=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type
        )
        console.print("✓ STT initialized")
        
        # LLM
        llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
            fallback_model=settings.llm_fallback
        )
        console.print("✓ LLM initialized")
        
        # TTS
        tts = KokoroTTS()  # Will fallback to NoOp if not available
        console.print("✓ TTS initialized")
        
        console.print("[green]✓ All components initialized successfully[/green]")
        console.print("Agent is ready to run with: make run")
        
    except Exception as e:
        console.print(f"✗ Component initialization error: {e}")


async def run_agent(settings) -> None:
    """Run the actual voice agent"""
    logger = logging.getLogger(__name__)
    
    # Setup signal handling
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        for task in asyncio.all_tasks():
            task.cancel()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Create and run pipeline
    pipeline = VoiceAgentPipeline(settings)
    
    try:
        await pipeline.start()
        logger.info("Agent started successfully")
        
        # Keep running until cancelled
        await pipeline.run()
        
    except asyncio.CancelledError:
        logger.info("Agent shutdown requested")
    finally:
        await pipeline.stop()
        logger.info("Agent stopped")


if __name__ == "__main__":
    main()