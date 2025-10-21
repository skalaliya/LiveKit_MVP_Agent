"""
FastAPI Web UI Server for French Tutor
Browser-based interface with teaching controls and multilingual support
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
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
_elevenlabs_tts: Optional[any] = None


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
    speed: Literal["slow", "normal", "fast"] = "normal"


class VocabRequest(BaseModel):
    term: str
    context: Optional[str] = None


class VocabResponse(BaseModel):
    vocab: list[dict]


def get_whisper_stt() -> WhisperSTT:
    """Lazy init Whisper STT"""
    global _whisper_stt
    if _whisper_stt is None:
        logger.info("Initializing Whisper STT...")
        _whisper_stt = WhisperSTT(
            model_name=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _whisper_stt


def get_ollama_llm() -> OllamaLLM:
    """Lazy init Ollama LLM"""
    global _ollama_llm
    if _ollama_llm is None:
        logger.info("Initializing Ollama LLM...")
        _ollama_llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model_name=settings.llm_model,
            fallback_model=settings.llm_fallback,
        )
    return _ollama_llm


def get_elevenlabs_tts():
    """Lazy init ElevenLabs TTS (optional)"""
    global _elevenlabs_tts
    if _elevenlabs_tts is None and settings.elevenlabs_api_key:
        try:
            logger.info("Initializing ElevenLabs TTS...")
            from livekit_mvp_agent.adapters.tts_elevenlabs import ElevenLabsTTS
            _elevenlabs_tts = ElevenLabsTTS(
                api_key=settings.elevenlabs_api_key,
                voice_id=settings.elevenlabs_voice_id,
            )
        except Exception as e:
            logger.warning(f"ElevenLabs TTS initialization failed: {e}")
            _elevenlabs_tts = None
    return _elevenlabs_tts


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
    """Transcribe uploaded audio file"""
    import tempfile
    import av  # PyAV for audio decoding
    
    try:
        # Read audio file
        audio_bytes = await file.read()
        logger.info(f"Received audio file: {len(audio_bytes)} bytes, type: {file.content_type}")
        
        # Create temp file for WebM input
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Decode audio using PyAV
            container = av.open(tmp_path)
            audio_stream = container.streams.audio[0]
            
            # Collect audio frames
            audio_frames = []
            for frame in container.decode(audio=0):
                # Convert frame to numpy array
                audio_frames.append(frame.to_ndarray())
            
            container.close()
            
            # Concatenate all frames
            if len(audio_frames) == 0:
                raise HTTPException(status_code=400, detail="No audio data found in file")
            
            audio_data = np.concatenate(audio_frames, axis=1)
            
            # Convert to mono if stereo (take mean across channels)
            if audio_data.shape[0] > 1:
                audio_data = audio_data.mean(axis=0)
            else:
                audio_data = audio_data[0]
            
            # Normalize to float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Get sample rate from audio stream
            sample_rate = audio_stream.sample_rate
            
            logger.info(f"Decoded audio: {len(audio_data)} samples at {sample_rate}Hz")
            
            # Transcribe
            stt = get_whisper_stt()
            text = stt.transcribe(audio_data, sample_rate=sample_rate)
            
            # Detect language (Whisper returns language in metadata)
            language = "fr"  # Could extract from Whisper result
            
            logger.info(f"Transcribed: {text}")
            
            return TranscribeResponse(text=text, language=language)
            
        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reply", response_model=ReplyResponse)
async def generate_reply(request: ReplyRequest):
    """Generate tutor reply"""
    try:
        llm = get_ollama_llm()
        
        # Handle special modes
        if request.mode == "repeat":
            # Return last reply unchanged
            if not session.last_reply:
                return ReplyResponse(text="(Nothing to repeat yet)", language=request.target_lang)
            return ReplyResponse(text=session.last_reply, language=session.last_reply_lang)
        
        # Build system prompt
        system_prompt = build_system_prompt(
            level=request.level,
            difficulty=request.difficulty,
            topic=request.topic,
            target_lang=request.target_lang,
        )
        
        # Modify prompt based on mode
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
        
        # Build conversation history
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add recent transcript context (last 5 turns)
        for turn in session.transcript[-5:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_text})
        
        # Generate response
        response = await llm.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=200,  # Keep responses short
        )
        
        # Store reply
        session.last_reply = response
        session.last_reply_lang = request.target_lang
        
        # Update transcript
        session.transcript.append({"role": "user", "content": request.text})
        session.transcript.append({"role": "assistant", "content": response})
        
        logger.info(f"Generated reply: {response}")
        
        return ReplyResponse(text=response, language=request.target_lang)
        
    except Exception as e:
        logger.error(f"Reply generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/speak")
async def synthesize_speech(request: SpeakRequest):
    """Synthesize speech from text"""
    try:
        tts = get_elevenlabs_tts()
        
        if not tts:
            # No TTS available - return empty MP3
            logger.warning("No TTS configured, returning empty audio")
            return Response(content=b"", media_type="audio/mpeg")
        
        # Speed control (ElevenLabs doesn't support rate directly)
        # Emulate with punctuation and pacing hints
        text = request.text
        if request.speed == "slow":
            text = text.replace(",", "...").replace(".", "...")
            text = f"(parle lentement) {text}"
        elif request.speed == "fast":
            # Remove pauses
            text = text.replace("...", ",")
        
        # Generate speech
        audio_bytes = await tts.synthesize(text)
        
        return Response(content=audio_bytes, media_type="audio/mpeg")
        
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
        "tts": _elevenlabs_tts is not None,
    }


# Mount static files LAST (so API routes take precedence)
www_path = Path(__file__).parent.parent.parent.parent / "www"
www_path.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(www_path), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
