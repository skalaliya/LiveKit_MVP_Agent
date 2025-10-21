"""
FastAPI Web UI Server for French Tutor
Browser-based interface with teaching controls and multilingual support
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Optional, Literal, TYPE_CHECKING
from dataclasses import dataclass, asdict

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
import soundfile as sf
from io import BytesIO

from livekit_mvp_agent.config import get_settings
from livekit_mvp_agent.adapters.stt_whisper import WhisperSTT
from livekit_mvp_agent.adapters.llm_ollama import OllamaLLM
from livekit_mvp_agent.adapters.tts_elevenlabs import ElevenLabsTTS, TransientTTSError
from livekit_mvp_agent.utils.tts_helpers import resolve_elevenlabs_voice

if TYPE_CHECKING:  # pragma: no cover
    from livekit_mvp_agent.adapters.tts_piper import PiperTTS
    from livekit_mvp_agent.adapters.tts_kokoro import KokoroTTS

logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="French Tutor WebUI",
    description="Interactive language learning with A2/B1 teaching controls",
    version="1.0.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Settings
settings = get_settings()

# NOTE: Static files will be mounted AFTER API endpoints to avoid route conflicts

# Lazy singletons for adapters
_whisper_stt: Optional[WhisperSTT] = None
_ollama_llm: Optional[OllamaLLM] = None
_tts_manager: Optional["TTSManager"] = None


@dataclass
class SessionState:
    """In-memory session state"""
    last_reply: str = ""
    last_reply_lang: str = "fr"
    transcript: list[dict] = None
    vocab: list[dict] = None
    
    def __post_init__(self):
        if self.transcript is None:
            self.transcript = []
        if self.vocab is None:
            self.vocab = []


# Global session (single-user for now)
session = SessionState()


# TTS helper classes
class _NoOpTTS:
    """Fallback TTS when no real engine is available."""

    def available(self) -> bool:
        return True

    def synthesize(self, text: str) -> bytes:
        logger.info("[NoOpTTS] Synthesizing text locally: %s", text)
        return b""


class _NoOpEngine:
    name = "noop"
    media_type = "audio/mpeg"

    def __init__(self) -> None:
        self._adapter = _NoOpTTS()

    async def synthesize(self, text: str, language: str, speed: str) -> bytes:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._adapter.synthesize, text)


def _infer_media_type_from_format(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt.startswith("mp3"):
        return "audio/mpeg"
    if fmt.startswith("ogg"):
        return "audio/ogg"
    if fmt.startswith("pcm") or fmt.startswith("wav"):
        return "audio/wav"
    return "application/octet-stream"


def _np_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    buffer = BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV")
    return buffer.getvalue()


class _ElevenLabsEngine:
    name = "elevenlabs"

    def __init__(self, adapter: ElevenLabsTTS) -> None:
        self.adapter = adapter
        self.media_type = _infer_media_type_from_format(getattr(adapter, "output_format", "mp3"))

    async def synthesize(self, text: str, language: str, speed: str) -> bytes:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.adapter.synthesize, text)


class _PiperEngine:
    name = "piper"
    media_type = "audio/wav"

    def __init__(self, adapter: "PiperTTS", default_language: str = "fr") -> None:
        self.adapter = adapter
        self.default_language = default_language

    async def synthesize(self, text: str, language: str, speed: str) -> bytes:
        lang = language or self.default_language
        audio = await self.adapter.synthesize(text, language=lang)
        if audio is None or len(audio) == 0:
            return b""
        sample_rate = getattr(self.adapter, "sample_rate", 22050)
        return _np_to_wav_bytes(audio, sample_rate)


class _KokoroEngine:
    name = "kokoro"
    media_type = "audio/wav"

    def __init__(self, adapter: "KokoroTTS", default_language: str = "auto") -> None:
        self.adapter = adapter
        self.default_language = default_language

    async def synthesize(self, text: str, language: str, speed: str) -> bytes:
        lang = language or self.default_language
        audio = await self.adapter.synthesize(text, language=lang)
        if audio is None or len(audio) == 0:
            return b""
        sample_rate = getattr(self.adapter, "sample_rate", 24000)
        return _np_to_wav_bytes(audio, sample_rate)


class TTSManager:
    def __init__(self, engines: list[object]) -> None:
        self.engines = engines

    async def synthesize(self, text: str, language: str, speed: str) -> tuple[bytes, str, str]:
        last_media_type = "audio/mpeg"
        if not self.engines:
            return b"", last_media_type, "noop"

        for engine in self.engines:
            media_type = getattr(engine, "media_type", last_media_type)
            last_media_type = media_type
            try:
                audio = await engine.synthesize(text, language, speed)
                if audio:
                    return audio, media_type, getattr(engine, "name", "unknown")
            except TransientTTSError as exc:
                logger.warning("TTS engine %s transient error: %s", getattr(engine, "name", "unknown"), exc)
            except Exception as exc:  # pragma: no cover - unexpected failures
                logger.error(
                    "TTS engine %s failed: %s",
                    getattr(engine, "name", "unknown"),
                    exc,
                    exc_info=True,
                )

        logger.warning("No TTS configured")
        return b"", last_media_type, "noop"


def _maybe_create_piper_engine(settings) -> Optional[_PiperEngine]:
    try:
        from livekit_mvp_agent.adapters.tts_piper import PiperTTS
    except ImportError:
        return None

    try:
        adapter: PiperTTS = PiperTTS(voice=settings.tts_voice)
        return _PiperEngine(adapter, default_language="fr")
    except Exception as exc:  # pragma: no cover
        logger.debug("Piper engine unavailable: %s", exc)
        return None


def _maybe_create_kokoro_engine(settings) -> Optional[_KokoroEngine]:
    try:
        from livekit_mvp_agent.adapters.tts_kokoro import KokoroTTS
    except ImportError:
        return None

    try:
        adapter: KokoroTTS = KokoroTTS(voice=settings.tts_voice)
        return _KokoroEngine(adapter)
    except Exception as exc:  # pragma: no cover
        logger.debug("Kokoro engine unavailable: %s", exc)
        return None


def _build_tts_manager() -> TTSManager:
    """Create the configured TTS engine stack with fallbacks."""
    cfg = get_settings()
    primary = (cfg.tts_primary or "").lower()
    engines: list[object] = []
    fallback_engines: list[object] = []
    primary_engine: Optional[_ElevenLabsEngine] = None
    disable_reason: Optional[str] = None

    if primary == "elevenlabs":
        voice_id = resolve_elevenlabs_voice(cfg)
        try:
            adapter = ElevenLabsTTS(
                api_key=cfg.elevenlabs_api_key,
                voice_id=voice_id,
                model_id=cfg.elevenlabs_model or cfg.tts_model,
                timeout_s=float(cfg.elevenlabs_tts_timeout),
                voice_settings={
                    "stability": cfg.elevenlabs_tts_stability,
                    "similarity_boost": cfg.elevenlabs_tts_similarity,
                    "style": cfg.elevenlabs_tts_style,
                    "use_speaker_boost": cfg.elevenlabs_tts_use_speaker_boost,
                },
                output_format=cfg.elevenlabs_output_format,
                optimize_streaming_latency=cfg.elevenlabs_opt_latency,
            )
            if adapter.available():
                primary_engine = _ElevenLabsEngine(adapter)
                engines.append(primary_engine)
                logger.info(
                    "ElevenLabs TTS ready (voice=%s, model=%s, format=%s, latency=%s)",
                    voice_id,
                    adapter.model_id,
                    adapter.output_format,
                    adapter.optimize_streaming_latency,
                )
            else:
                disable_reason = "missing credentials"
        except Exception as exc:
            disable_reason = str(exc)
            logger.error("ElevenLabs TTS initialization failed: %s", exc, exc_info=True)
    else:
        disable_reason = f"primary={primary or 'none'}"

    piper_engine = _maybe_create_piper_engine(cfg)
    if piper_engine:
        fallback_engines.append(piper_engine)
    kokoro_engine = _maybe_create_kokoro_engine(cfg)
    if kokoro_engine:
        fallback_engines.append(kokoro_engine)

    engines.extend(fallback_engines)

    if primary == "elevenlabs" and primary_engine is None:
        fallback_label = fallback_engines[0].name if fallback_engines else "none"
        logger.warning(
            "ElevenLabs TTS disabled (reason=%s); fallback=%s",
            disable_reason or "unavailable",
            fallback_label,
        )

    if not engines:
        engines.append(_NoOpEngine())

    return TTSManager(engines)


def get_tts() -> TTSManager:
    """Lazy-init wrapper for whichever TTS engine is available."""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = _build_tts_manager()
    return _tts_manager


@app.on_event("startup")
async def warm_adapters() -> None:
    """Warm up heavy adapters asynchronously to reduce first-request latency."""
    tasks = []

    try:
        stt = get_whisper_stt()
        tasks.append(asyncio.create_task(stt.initialize()))
    except Exception as exc:  # pragma: no cover
        logger.warning("Whisper warm-up skipped: %s", exc)

    try:
        llm = get_ollama_llm()
        tasks.append(asyncio.create_task(llm.initialize()))
    except Exception as exc:  # pragma: no cover
        logger.warning("Ollama warm-up skipped: %s", exc)

    try:
        get_tts()
    except Exception as exc:  # pragma: no cover
        logger.warning("TTS warm-up skipped: %s", exc)

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.debug("Warm-up task finished with error: %s", result)



# Pydantic models
class TranscribeResponse(BaseModel):
    text: str
    language: str


class ReplyRequest(BaseModel):
    text: str
    level: Literal["A2", "B1"] = "A2"
    difficulty: int = Field(default=2, ge=1, le=5)
    topic: str = "free"
    target_lang: str = "fr"
    mode: Literal["normal", "repeat", "slower", "faster", "explain", "translate"] = "normal"
    translate_to: Optional[str] = None


class ReplyResponse(BaseModel):
    text: str
    language: str


class SpeakRequest(BaseModel):
    text: str
    language: Optional[str] = "fr"
    speed: Literal["slow", "normal", "fast"] = "normal"


class VocabRequest(BaseModel):
    term: str
    context: Optional[str] = None


class VocabResponse(BaseModel):
    vocab: list[dict]


def get_whisper_stt() -> WhisperSTT:
    """Singleton STT loader for the WebUI."""
    global _whisper_stt
    if _whisper_stt is None:
        logger.info("Initializing Whisper STT...")
        _whisper_stt = WhisperSTT(
            model=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            sample_rate=settings.sample_rate,
            language="auto",
        )
    return _whisper_stt


def get_ollama_llm() -> OllamaLLM:
    """Singleton LLM loader for the WebUI."""
    global _ollama_llm
    if _ollama_llm is None:
        logger.info("Initializing Ollama LLM...")
        _ollama_llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
            fallback_model=settings.llm_fallback,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    return _ollama_llm




def build_system_prompt(
    level: str,
    difficulty: int,
    topic: str,
    target_lang: str,
) -> str:
    """Build French tutor system prompt with parameters"""
    
    # Language-specific guidance
    lang_guidance = {
        "fr": "Respond in French. Use 'tu' for A2, 'vous' for B1 when appropriate.",
        "en": "Respond in English. Use clear, simple language.",
        "es": "Responde en español. Usa lenguaje claro y sencillo.",
        "de": "Antworte auf Deutsch. Verwende klare, einfache Sprache.",
        "it": "Rispondi in italiano. Usa un linguaggio chiaro e semplice.",
    }
    
    # Topic context
    topic_context = {
        "travel": "Focus on travel vocabulary and situations (airport, hotel, directions).",
        "cafe": "Focus on café/restaurant ordering and small talk.",
        "shopping": "Focus on shopping vocabulary (sizes, colors, prices).",
        "work": "Focus on professional/workplace vocabulary.",
        "doctor": "Focus on health-related vocabulary and medical situations.",
        "directions": "Focus on asking for and giving directions.",
        "restaurant": "Focus on dining out and food vocabulary.",
        "smalltalk": "Focus on casual conversation and social interactions.",
        "free": "Adapt to the learner's topic of interest.",
    }
    
    # Difficulty guidance
    difficulty_guidance = {
        1: "Use very simple sentences (3-5 words). Avoid idioms.",
        2: "Use simple sentences (5-8 words). Minimal idioms.",
        3: "Use moderate complexity (8-12 words). Some common idioms ok.",
        4: "Use varied sentence structures. Include idioms and expressions.",
        5: "Use complex sentences. Challenge the learner with advanced vocabulary.",
    }
    
    prompt = f"""You are a patient, encouraging language tutor specializing in {target_lang.upper()} for {level} level learners.

**Core Principles:**
- {lang_guidance.get(target_lang, f"Respond in {target_lang}.")}
- Keep responses SHORT: 1-3 sentences maximum
- {difficulty_guidance[difficulty]}
- {topic_context.get(topic, "")}

**Teaching Style:**
- When learner makes an error:
  1. Acknowledge what they said
  2. Provide the CORRECT version
  3. Give ONE brief reason why (grammar/usage)
  Example: "Ah! You said 'je suis allé au magasin hier'. ✓ Perfect! Past tense with 'être' for movement verbs."

- Use IPA pronunciation ONLY for new/difficult words: "précis [pʁe.si]"
- End with a small follow-up question in {target_lang}
- Be encouraging! Celebrate progress, even small wins

**Level Guidance:**
- A2: Familiar topics, present/past tense, simple vocabulary
- B1: Opinions, future plans, conditional, more abstract topics

**Current Session:**
- Level: {level}
- Difficulty: {difficulty}/5
- Topic: {topic}
- Target Language: {target_lang}

Remember: SHORT responses. 1-3 sentences. Then ask a tiny follow-up question."""
    
    return prompt


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio file (WebM/WAV/MP3/etc)."""
    import av  # PyAV for audio decoding

    try:
        overall_start = perf_counter()
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio payload")
        logger.info("Received audio file: %d bytes, type: %s", len(audio_bytes), file.content_type)

        container = av.open(BytesIO(audio_bytes))
        audio_stream = container.streams.audio[0]

        audio_frames = [frame.to_ndarray() for frame in container.decode(audio=0)]
        container.close()

        if not audio_frames:
            raise HTTPException(status_code=400, detail="No audio data in file")

        audio_data = np.concatenate(audio_frames, axis=1)
        if audio_data.shape[0] > 1:
            audio_data = audio_data.mean(axis=0)
        else:
            audio_data = audio_data[0]

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        sample_rate = audio_stream.sample_rate or settings.sample_rate
        decode_end = perf_counter()

        wav_buffer = BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format="WAV")
        wav_bytes = wav_buffer.getvalue()

        stt = get_whisper_stt()
        loop = asyncio.get_running_loop()
        transcribe_start = perf_counter()
        result = await loop.run_in_executor(None, stt.transcribe_bytes, wav_bytes)
        transcribe_end = perf_counter()

        logger.info(
            "Transcribed (%s): %s",
            result.get("language", "und"),
            (result.get("text") or "").strip(),
        )
        logger.info(
            "Transcribe timings decode=%.1fms stt=%.1fms total=%.1fms",
            (decode_end - overall_start) * 1000,
            (transcribe_end - transcribe_start) * 1000,
            (transcribe_end - overall_start) * 1000,
        )

        return TranscribeResponse(
            text=result.get("text", ""),
            language=result.get("language", "und"),
        )

    except HTTPException:
        raise
    except av.AVError as exc:
        logger.error("PyAV decode error: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reply", response_model=ReplyResponse)
async def generate_reply(request: ReplyRequest):
    """Generate tutor reply"""
    try:
        llm = get_ollama_llm()

        if request.mode == "repeat":
            if not session.last_reply:
                return ReplyResponse(text="(Nothing to repeat yet)", language=request.target_lang)
            return ReplyResponse(text=session.last_reply, language=session.last_reply_lang)

        system_prompt = build_system_prompt(
            level=request.level,
            difficulty=request.difficulty,
            topic=request.topic,
            target_lang=request.target_lang,
        )

        user_text = request.text
        if request.mode == "slower":
            user_text = f"[Speak more slowly and simply] {request.text}"
        elif request.mode == "faster":
            user_text = f"[Speak faster with more complexity] {request.text}"
        elif request.mode == "explain":
            user_text = f"Explain this in simple English: {request.text or session.last_reply}"
        elif request.mode == "translate":
            target = request.translate_to or "en"
            user_text = f"Translate this to {target}: {request.text or session.last_reply}"

        messages = [{"role": "system", "content": system_prompt}]
        for turn in session.transcript[-5:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_text})

        llm_start = perf_counter()
        try:
            reply_text: Optional[str] = None

            chat_fn = getattr(llm, "chat", None)
            if chat_fn:
                if asyncio.iscoroutinefunction(chat_fn):
                    reply_text = await chat_fn(messages=messages, model=None, stream=False)
                else:
                    reply_text = chat_fn(messages=messages, model=None, stream=False)

            if reply_text is None:
                generate_fn = getattr(llm, "generate", None)
                if generate_fn:
                    flat_prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
                    if asyncio.iscoroutinefunction(generate_fn):
                        reply_text = await generate_fn(prompt=flat_prompt, system_prompt=None)
                    else:
                        reply_text = generate_fn(prompt=flat_prompt, system_prompt=None)

            if isinstance(reply_text, dict):
                reply_text = reply_text.get("text") or reply_text.get("response") or ""

            if reply_text is None:
                raise RuntimeError("LLM did not return a response.")

            reply_text = reply_text.strip()

        except Exception as llm_error:
            logger.error("LLM request failed: %s", llm_error, exc_info=True)
            if request.target_lang.lower().startswith("fr"):
                reply_text = (
                    "Désolé, je ne peux pas répondre pour le moment. "
                    "Vérifie que le serveur Ollama est démarré (`ollama serve`) puis réessaie."
                )
            else:
                reply_text = (
                    "Sorry, I can't reach the language model right now. "
                    "Please make sure Ollama is running (`ollama serve`) and try again."
                )
        finally:
            elapsed_ms = (perf_counter() - llm_start) * 1000
            logger.info(
                "LLM reply ready in %.1fms (mode=%s, user_chars=%d)",
                elapsed_ms,
                request.mode,
                len(request.text or ""),
            )

        session.last_reply = reply_text
        session.last_reply_lang = request.target_lang
        session.transcript.append({"role": "user", "content": request.text})
        session.transcript.append({"role": "assistant", "content": reply_text})

        logger.info(f"Generated reply: {reply_text}")

        return ReplyResponse(text=reply_text, language=request.target_lang)

    except Exception as e:
        logger.error(f"Reply generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/speak")
async def synthesize_speech(request: SpeakRequest):
    """Synthesize speech from text"""
    try:
        tts_manager = get_tts()

        tts_start = perf_counter()
        # Speed control (ElevenLabs doesn't support rate directly)
        # Emulate with punctuation and pacing hints
        text = request.text
        if request.speed == "slow":
            text = text.replace(",", "...").replace(".", "...")
            text = f"(parle lentement) {text}"
        elif request.speed == "fast":
            # Remove pauses
            text = text.replace("...", ",")

        audio_bytes, media_type, engine_name = await tts_manager.synthesize(
            text=text,
            language=request.language or "fr",
            speed=request.speed,
        )
        audio_bytes = audio_bytes or b""
        elapsed_ms = (perf_counter() - tts_start) * 1000
        logger.info(
            "TTS synthesize completed in %.1fms (bytes=%d, engine=%s)",
            elapsed_ms,
            len(audio_bytes),
            engine_name,
        )

        return Response(content=audio_bytes, media_type=media_type)

    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        # Return empty audio instead of error
        return Response(content=b"", media_type="audio/mpeg")


@app.post("/api/vocab", response_model=VocabResponse)
async def save_vocab(request: VocabRequest):
    """Save vocabulary term"""
    try:
        # Create artifacts directory
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)
        
        vocab_file = artifacts_dir / "vocab.json"
        
        # Load existing vocab
        if vocab_file.exists():
            with open(vocab_file, "r", encoding="utf-8") as f:
                vocab_list = json.load(f)
        else:
            vocab_list = []
        
        # Add new term (de-duplicate)
        new_entry = {
            "term": request.term,
            "context": request.context,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Check if already exists
        if not any(v["term"] == request.term for v in vocab_list):
            vocab_list.append(new_entry)
            
            # Save
            with open(vocab_file, "w", encoding="utf-8") as f:
                json.dump(vocab_list, f, indent=2, ensure_ascii=False)
        
        return VocabResponse(vocab=vocab_list)
        
    except Exception as e:
        logger.error(f"Vocab save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vocab", response_model=VocabResponse)
async def get_vocab():
    """Get saved vocabulary"""
    try:
        vocab_file = Path("artifacts/vocab.json")
        
        if not vocab_file.exists():
            return VocabResponse(vocab=[])
        
        with open(vocab_file, "r", encoding="utf-8") as f:
            vocab_list = json.load(f)
        
        return VocabResponse(vocab=vocab_list)
        
    except Exception as e:
        logger.error(f"Vocab load error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/export")
async def export_session(fmt: str = Query("json", regex="^(json|csv)$")):
    """Export session transcript"""
    try:
        # Create artifacts directory
        artifacts_dir = Path("artifacts/sessions")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.{fmt}"
        filepath = artifacts_dir / filename
        
        if fmt == "json":
            # Export as JSON
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "transcript": session.transcript,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        else:  # csv
            # Export as CSV
            import csv
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Role", "Content", "Index"])
                for i, turn in enumerate(session.transcript):
                    writer.writerow([turn["role"], turn["content"], i])
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/octet-stream",
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/clear")
async def clear_session():
    """Clear session state"""
    global session
    session = SessionState()
    return {"status": "cleared"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "whisper": _whisper_stt is not None,
        "ollama": _ollama_llm is not None,
        "tts": _tts_manager is not None,
    }


# Mount static files LAST (so API routes take precedence)
www_path = Path(__file__).parent.parent.parent.parent / "www"
www_path.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(www_path), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
