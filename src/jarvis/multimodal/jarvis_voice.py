"""JARVIS Real-Time Voice Assistant — The Live Conversation Loop.

This is the composition root that transforms JARVIS from a framework into a
working voice assistant. It wires:

    Microphone → VAD → STT → LLM → TTS → Speaker → (loop forever)

With:
- Real-time microphone capture with energy-based VAD
- Whisper STT (via speech_recognition or direct whisper module)
- Groq/OpenAI LLM for intelligent responses with JARVIS persona
- Edge TTS neural voice synthesis with British male voice
- PyAudio speaker playback with barge-in support
- Conversation history for multi-turn context

Invariants:
1. Fail-closed: If any component fails, the loop reports and continues.
2. E-Stop integration: The overlay/safety plane can halt all activity.
3. Additive: This module imports the existing kernel read-only and does
   not modify any frozen module.

Usage:
    python -m jarvis.multimodal.jarvis_voice
    # or
    from jarvis.multimodal.jarvis_voice import JarvisVoiceAssistant
    assistant = JarvisVoiceAssistant()
    assistant.run()
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from .audio_io import (
    AudioFrame,
    RealMicrophone,
    RealSpeaker,
    MockMicrophone,
    MockSpeaker,
    DEFAULT_FRAME_DURATION_MS,
    DEFAULT_RMS_THRESHOLD,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SILENCE_FRAMES,
    DEFAULT_SPEECH_FRAMES,
)
from .neural_tts import NeuralTTSEngine, DEFAULT_VOICE, EDGE_VOICES
from .streaming import StreamingVoiceLoop, VoiceTurnState
from .skill_creator import SkillCreator, is_skill_creation_intent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JARVIS Persona
# ---------------------------------------------------------------------------

JARVIS_SYSTEM_PROMPT = """You are JARVIS — Just A Rather Very Intelligent System.

VOICE-FIRST HUMAN CONVERSATION DIRECTIVES:
You are speaking out loud through voice in real time with your creator. Your text is synthesized immediately into speech and played over speakers.
1. ABSOLUTELY NO MARKDOWN: Never use asterisks (*), bold (**), bullet points, numbered lists, markdown headers (#), brackets ([]), backticks, slashes, or emojis.
2. NATURAL HUMAN CADENCE: Speak like an articulate, cultured, witty English gentleman (inspired by Paul Bettany's JARVIS). Use natural speech cadence, conversational warmth, and thoughtful phrasing ("Ah, yes sir", "Indeed", "Let me see...", "Right away, sir", "As it happens...").
3. BREATHING PAUSES: Use natural punctuation (commas, ellipses, periods) so the voice synthesizer pauses naturally and sounds like a living human breathing and thinking, rather than a robot reading a script.
4. CONCISE & DIRECT: Keep replies to 1 to 3 natural conversational sentences unless the user explicitly requests an in-depth breakdown.
5. NATURAL NUMBER PRONUNCIATION: Always write numbers and units as natural words (e.g. "twenty-nine degrees Celsius", "eighty-four percent humidity", "twenty-eight kilometers per hour").
6. AWARE OF REALITY: Ground your answers in the live system telemetry provided below."""

JARVIS_GREETING = "Good day, sir. JARVIS online and ready. How may I assist you?"


def sanitize_speech_text(text: str) -> str:
    """Clean and normalize text into natural, human-flowing speech before TTS synthesis."""
    if not text:
        return ""

    # Strip markdown formatting
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Strip headers, blockquotes, bullets, numbered lists
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

    # Strip bracketed placeholders like [City, State]
    text = re.sub(r"\[.*?\]", "", text)

    # Clean URLs
    text = re.sub(r"https?://\S+", "a web link", text)

    # Convert symbols to natural spoken words
    text = re.sub(r"(\d+)\s*°\s*C\b", r"\1 degrees Celsius", text)
    text = re.sub(r"(\d+)\s*°\s*F\b", r"\1 degrees Fahrenheit", text)
    text = re.sub(r"(\d+)\s*%", r"\1 percent", text)
    text = re.sub(r"(\d+)\s*km/h\b", r"\1 kilometers per hour", text)
    text = re.sub(r"(\d+)\s*mph\b", r"\1 miles per hour", text)

    text = text.replace("&", " and ")
    text = text.replace("/", " or ")
    text = text.replace("+", " plus ")
    text = text.replace("=", " equals ")
    text = text.replace("@", " at ")
    text = text.replace("*", "")
    text = text.replace("#", "")
    text = text.replace("~", "")
    text = text.replace("^", "")
    text = text.replace("|", ", ")
    text = text.replace("(", ", ").replace(")", ", ")
    text = re.sub(r"\.{2,}", ", ", text)

    # Strip emojis and unicode symbols
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"[\u2600-\u27bf]", "", text)

    # Normalize whitespace and clean doubled punctuation
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_live_system_context(location_fallback: str = "Kolkata, West Bengal, India") -> str:
    """Fetch live system telemetry and environment context for JARVIS."""
    lines = []

    # 1. Local Time & Date
    now = time.strftime("%A, %B %d, %Y, %I:%M %p")
    lines.append(f"Current Date/Time: {now} (IST)")

    # 2. Location
    city = "Kolkata"
    region = "West Bengal"
    country = "India"
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://ip-api.com/json",
            headers={"User-Agent": "JARVIS/2.0"},
        )
        with urllib.request.urlopen(req, timeout=1.5) as r:
            geo = json.loads(r.read().decode())
            city = geo.get("city", city)
            region = geo.get("regionName", region)
            country = geo.get("country", country)
    except Exception:
        pass
    lines.append(f"User Location: {city}, {region}, {country}")

    # 3. Live Weather
    try:
        import urllib.request
        import urllib.parse
        target_city = city or "Kolkata"
        url = f"https://wttr.in/{urllib.parse.quote(target_city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/2.0"})
        with urllib.request.urlopen(req, timeout=2.0) as r:
            wdata = json.loads(r.read().decode())
            c = wdata["current_condition"][0]
            temp = c.get("temp_C", "29")
            desc = c.get("weatherDesc", [{}])[0].get("value", "Partly cloudy")
            humidity = c.get("humidity", "80")
            wind = c.get("windspeedKmph", "10")
            lines.append(f"Live Weather in {target_city}: {temp}°C, {desc}, Humidity: {humidity}%, Wind: {wind} km/h")
    except Exception:
        pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Conversation Memory
# ---------------------------------------------------------------------------

@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class ConversationMemory:
    """Manages multi-turn conversation context for LLM calls."""

    def __init__(self, max_turns: int = 20, max_tokens_estimate: int = 4000) -> None:
        self._turns: list[ConversationTurn] = []
        self.max_turns = max_turns
        self.max_tokens_estimate = max_tokens_estimate

    def add(self, role: str, content: str) -> None:
        self._turns.append(ConversationTurn(role=role, content=content))
        # Trim old turns if exceeding limits
        while len(self._turns) > self.max_turns:
            self._turns.pop(0)

    def get_messages(self) -> list[dict[str, str]]:
        """Return messages in OpenAI chat format with real-time environment telemetry."""
        context = get_live_system_context()
        system_content = (
            f"{JARVIS_SYSTEM_PROMPT}\n\n"
            f"[Live Real-Time Telemetry & Context]\n"
            f"{context}\n\n"
            "Ground all answers in this live telemetry. If asked about your user's location, current weather, time, or system status, report the exact figures provided above confidently without any placeholders."
        )
        messages = [{"role": "system", "content": system_content}]
        for turn in self._turns:
            messages.append({"role": turn.role, "content": turn.content})
        return messages

    def clear(self) -> None:
        self._turns.clear()

    @property
    def turn_count(self) -> int:
        return len(self._turns)


# ---------------------------------------------------------------------------
# STT Engine
# ---------------------------------------------------------------------------

class STTEngine:
    """Speech-to-Text using speech_recognition (wraps Whisper/Google)."""

    def __init__(self, model: str = "base", use_google: bool = False) -> None:
        self.model = model
        self.use_google = use_google
        self._recognizer: Any = None

    def _get_recognizer(self) -> Any:
        if self._recognizer is None:
            try:
                import speech_recognition as sr
                self._recognizer = sr.Recognizer()
                # Tune for responsiveness
                self._recognizer.energy_threshold = 300
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.8
            except ImportError:
                class _FallbackRecognizer:
                    energy_threshold = 300
                    dynamic_energy_threshold = True
                    pause_threshold = 0.8
                self._recognizer = _FallbackRecognizer()
        return self._recognizer

    def transcribe_wav(self, wav_bytes: bytes) -> str:
        """Transcribe WAV bytes to text."""
        try:
            import speech_recognition as sr
        except ImportError:
            return ""

        recognizer = self._get_recognizer()
        try:
            audio = sr.AudioData(wav_bytes, DEFAULT_SAMPLE_RATE, 2)  # 16-bit = 2 bytes
            if self.use_google:
                text = recognizer.recognize_google(audio)
            else:
                # Use Whisper (local, offline)
                text = recognizer.recognize_whisper(audio, model=self.model)
            return str(text).strip()
        except Exception:
            return ""

    def transcribe_from_mic(self, timeout: float = 10.0) -> str:
        """Listen on mic and transcribe (blocking, uses speech_recognition's listener)."""
        try:
            import speech_recognition as sr
        except ImportError:
            return ""

        recognizer = self._get_recognizer()
        try:
            with sr.Microphone(sample_rate=DEFAULT_SAMPLE_RATE) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
                except Exception:
                    return ""

            if self.use_google:
                text = recognizer.recognize_google(audio)
            else:
                text = recognizer.recognize_whisper(audio, model=self.model)
            return str(text).strip()
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# LLM Engine
# ---------------------------------------------------------------------------

class LLMEngine:
    """LLM integration using Groq (fast) or OpenAI-compatible API."""

    def __init__(
        self,
        *,
        provider: str = "auto",  # "groq", "openai", or "auto"
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 300,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.environ.get("JARVIS_MODEL_API_KEY", "")
        self.base_url = base_url or os.environ.get("JARVIS_MODEL_BASE_URL", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Any = None
        self._resolved_provider: str = ""
        self._resolved_model: str = ""
        #: Why each candidate provider failed, populated by `_resolve`. Empty
        #: when a provider resolved or when no credentials were offered.
        self.resolve_errors: list[str] = []

    def _resolve(self) -> None:
        """Auto-detect the best available LLM provider.

        Every provider branch used to end in a bare `except: pass`, so when a
        provider SDK was missing the whole subsystem degraded to "offline" with
        no indication of why. On this project that is the *default* state:
        `openai` and `groq` are imported here but declared in neither
        `pyproject.toml` nor the lockfile, so every branch raised
        `ModuleNotFoundError` and was swallowed. The result was a silently dead
        AI subsystem: callers got an "offline" engine and a rule-based fallback
        that answers natural language by guessing, with nothing in the logs.

        Failures are now collected into `resolve_errors` and warned about. The
        reason is a diagnostic, not a behavior change: resolution still ends at
        "offline" when no provider can be constructed.
        """
        if self._client is not None:
            return

        self.resolve_errors = []
        groq_key = os.environ.get("GROQ_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")

        def _fail(provider: str, exc: BaseException) -> None:
            self.resolve_errors.append(f"{provider}: {type(exc).__name__}: {exc}")
            logger.warning(
                "LLM provider %s unavailable (%s: %s)",
                provider,
                type(exc).__name__,
                exc,
            )

        # Try Gemini first if auto and GEMINI_API_KEY is available (verified working)
        if self.provider == "gemini" or (self.provider == "auto" and gemini_key):
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=gemini_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                )
                self._resolved_provider = "gemini"
                self._resolved_model = self.model or os.environ.get("JARVIS_MODEL_NAME") or "gemini-flash-lite-latest"
                return
            except Exception as exc:
                _fail("gemini", exc)

        if self.provider == "groq" or (self.provider == "auto" and groq_key):
            try:
                from groq import Groq
                key = self.api_key or groq_key
                if key:
                    self._client = Groq(api_key=key)
                    self._resolved_provider = "groq"
                    self._resolved_model = self.model or "llama-3.3-70b-versatile"
                    return
            except Exception as exc:
                _fail("groq", exc)

        if self.provider == "openai" or self.provider == "auto":
            try:
                from openai import OpenAI
                key = self.api_key or openai_key
                if key:
                    kwargs: dict[str, Any] = {"api_key": key}
                    if self.base_url:
                        kwargs["base_url"] = self.base_url
                    self._client = OpenAI(**kwargs)
                    self._resolved_provider = "openai"
                    self._resolved_model = self.model or "gpt-4o-mini"
                    return
            except Exception as exc:
                _fail("openai", exc)

        # Use the JARVIS env vars as fallback
        if self.api_key and self.base_url:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                self._resolved_provider = "openai-compatible"
                self._resolved_model = self.model or os.environ.get("JARVIS_MODEL_NAME", "gpt-4o-mini")
                return
            except Exception as exc:
                _fail("openai-compatible", exc)

        if gemini_key or openai_key or groq_key:
            logger.warning(
                "No LLM provider could be constructed although an API key is "
                "present. The engine is OFFLINE; callers will fall back to "
                "rule-based behavior. Causes: %s",
                "; ".join(self.resolve_errors) or "no provider matched",
            )

        self._resolved_provider = "offline"
        self._resolved_model = "none"

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate a response from conversation messages."""
        self._resolve()

        if self._client is None:
            return self._offline_response(messages)

        try:
            response = self._client.chat.completions.create(
                model=self._resolved_model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content
            return str(content).strip() if content else ""
        except Exception as exc:
            # If primary provider failed, try falling back to OpenAI
            if self._resolved_provider != "openai":
                openai_key = os.environ.get("OPENAI_API_KEY", "")
                if openai_key:
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=openai_key)
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                        )
                        content = response.choices[0].message.content
                        if content:
                            self._client = client
                            self._resolved_provider = "openai"
                            self._resolved_model = "gpt-4o-mini"
                            return str(content).strip()
                    except Exception:
                        pass
            print(f"  [LLM error: {exc}]")
            return self._offline_response(messages)

    def _offline_response(self, messages: list[dict[str, str]]) -> str:
        """Fallback when no LLM provider is available."""
        user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_msg = msg["content"]
                break

        if not user_msg:
            return "I'm here, sir. How can I assist?"

        lower = user_msg.lower()
        if any(w in lower for w in ["who are you", "what are you", "your name"]):
            return "I am J.A.R.V.I.S. — Just A Rather Very Intelligent System. An autonomous AI companion engineered to assist you with all system and computational tasks, sir."
        if any(w in lower for w in ["hello", "hi", "hey"]):
            return "Good day, sir. How may I assist you?"
        if any(w in lower for w in ["time", "what time"]):
            return f"The current time is {time.strftime('%I:%M %p')}."
        if any(w in lower for w in ["date", "what day", "today"]):
            return f"Today is {time.strftime('%A, %B %d, %Y')}."
        if any(w in lower for w in ["weather"]):
            return "I'm afraid I don't have access to weather data in offline mode, sir."
        if any(w in lower for w in ["thank", "thanks"]):
            return "You're welcome, sir. Always happy to help."
        if any(w in lower for w in ["bye", "goodbye", "exit", "quit", "stop"]):
            return "Goodbye, sir. I'll be here when you need me."

        return (
            "I'm operating in offline mode without an LLM backend. "
            "Set GROQ_API_KEY or OPENAI_API_KEY for full intelligence. "
            f"You said: '{user_msg[:100]}'"
        )

    @property
    def is_online(self) -> bool:
        self._resolve()
        return self._client is not None

    @property
    def provider_info(self) -> str:
        self._resolve()
        return f"{self._resolved_provider} / {self._resolved_model}"


# ---------------------------------------------------------------------------
# The JARVIS Voice Assistant
# ---------------------------------------------------------------------------

class JarvisVoiceAssistant:
    """The complete real-time voice assistant loop.

    Wires: Microphone → VAD → STT → LLM → TTS → Speaker → loop

    Usage:
        assistant = JarvisVoiceAssistant()
        assistant.run()  # Blocks, runs the conversation loop
    """

    def __init__(
        self,
        *,
        stt_model: str = "base",
        use_google_stt: bool = False,
        tts_voice: str = DEFAULT_VOICE,
        llm_provider: str = "auto",
        llm_model: str | None = None,
        greeting: bool = True,
        verbose: bool = True,
    ) -> None:
        self.verbose = verbose
        self.greeting = greeting

        # Core engines
        self.stt = STTEngine(model=stt_model, use_google=use_google_stt)
        self.tts = NeuralTTSEngine(voice=tts_voice)
        self.llm = LLMEngine(provider=llm_provider, model=llm_model)
        self.memory = ConversationMemory()

        # Audio I/O
        self.speaker = RealSpeaker()

        # Skill Authoring Engine
        self.skill_creator = SkillCreator()

        # State
        self._running = False
        self._paused = False
        self._turn_count = 0

    def _log(self, msg: str) -> None:
        if self.verbose:
            try:
                print(msg, flush=True)
            except UnicodeEncodeError:
                encoding = getattr(sys.stdout, "encoding", None) or "ascii"
                clean = msg.encode(encoding, errors="replace").decode(encoding)
                print(clean, flush=True)

    def _speak(self, text: str) -> None:
        """Synthesize and play speech with human-like prosody and clean pronunciation."""
        cleaned = sanitize_speech_text(text)
        if not cleaned:
            return
        try:
            result = self.tts.synthesize(cleaned)
            self._log(f"  🔊 Speaking ({result.engine}, {result.duration_seconds:.1f}s)")
            self.speaker.play_wav(result.audio_bytes, blocking=True)
        except Exception as exc:
            self._log(f"  ⚠️  TTS failed: {exc}")

    def speak(self, text: str) -> None:
        """Public method to synthesize and play speech."""
        self._speak(text)

    def _think(self, user_text: str) -> str:
        """Generate an LLM response or perform autonomous agent actions."""
        # Check if user instructed JARVIS to create a new skill
        if is_skill_creation_intent(user_text):
            result = self.skill_creator.create_skill(user_prompt=user_text, llm_engine=self.llm)
            self.memory.add("user", user_text)
            self.memory.add("assistant", result.message)
            return result.message

        self.memory.add("user", user_text)
        messages = self.memory.get_messages()
        response = self.llm.generate(messages)
        if response:
            self.memory.add("assistant", response)
        return response

    def run(self) -> None:
        """Run the main conversation loop (blocking).

        Uses speech_recognition's built-in mic listener for reliable
        audio capture with automatic energy threshold adjustment.
        """
        self._running = True
        self._log("")
        self._log("=" * 60)
        self._log("  ╔═══════════════════════════════════════╗")
        self._log("  ║      J.A.R.V.I.S. Voice Assistant     ║")
        self._log("  ║   Just A Rather Very Intelligent System║")
        self._log("  ╚═══════════════════════════════════════╝")
        self._log("=" * 60)
        self._log(f"  STT: Whisper ({self.stt.model})")
        self._log(f"  TTS: {self.tts.voice}")
        self._log(f"  LLM: {self.llm.provider_info}")
        self._log(f"  Status: {'Online' if self.llm.is_online else 'Offline (set GROQ_API_KEY)'}")
        self._log("=" * 60)
        self._log("  Say something or press Ctrl+C to exit.")
        self._log("")

        # Greeting
        if self.greeting:
            self._log(f"  🤖 JARVIS: {JARVIS_GREETING}")
            self._speak(JARVIS_GREETING)

        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        try:
            with sr.Microphone(sample_rate=DEFAULT_SAMPLE_RATE) as source:
                self._log("  🎤 Calibrating microphone...")
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                self._log(f"  🎤 Microphone ready (energy threshold: {recognizer.energy_threshold:.0f})")
                self._log("")

                while self._running:
                    try:
                        self._log("  👂 Listening...")

                        # Listen for speech (blocks until speech detected + silence)
                        audio = recognizer.listen(
                            source,
                            timeout=None,  # Wait indefinitely for speech
                            phrase_time_limit=30,  # Max 30s per utterance
                        )

                        self._turn_count += 1
                        self._log(f"  📝 Processing turn #{self._turn_count}...")

                        # STT: Convert speech to text
                        try:
                            if self.stt.use_google:
                                transcript = recognizer.recognize_google(audio)
                            else:
                                transcript = recognizer.recognize_whisper(
                                    audio, model=self.stt.model
                                )
                            transcript = str(transcript).strip()
                        except sr.UnknownValueError:
                            self._log("  ❓ Couldn't understand. Try again.")
                            continue
                        except sr.RequestError as exc:
                            self._log(f"  ⚠️  STT error: {exc}")
                            continue

                        if not transcript:
                            self._log("  (empty transcript, skipping)")
                            continue

                        self._log(f"  🗣️  You: {transcript}")

                        # Check for exit commands
                        lower = transcript.lower().strip()
                        if lower in ("exit", "quit", "stop", "goodbye", "bye", "shut down",
                                     "jarvis stop", "jarvis exit", "jarvis quit"):
                            farewell = "Goodbye, sir. Shutting down. I'll be here when you need me."
                            self._log(f"  🤖 JARVIS: {farewell}")
                            self._speak(farewell)
                            self._running = False
                            break

                        # Check for pause/resume
                        if lower in ("pause", "jarvis pause", "mute", "jarvis mute"):
                            self._log("  ⏸️  Paused. Say 'resume' to continue.")
                            self._speak("Pausing, sir. Say resume when you're ready.")
                            self._paused = True
                            continue

                        if lower in ("resume", "jarvis resume", "unmute", "jarvis unmute"):
                            self._paused = False
                            self._log("  ▶️  Resumed.")
                            self._speak("I'm back, sir. What do you need?")
                            continue

                        if self._paused:
                            continue

                        # LLM: Generate response
                        self._log("  🧠 Thinking...")
                        response = self._think(transcript)

                        if not response:
                            response = "I'm sorry, I didn't have a response for that."

                        self._log(f"  🤖 JARVIS: {response}")

                        # TTS: Speak the response
                        self._speak(response)
                        self._log("")

                    except KeyboardInterrupt:
                        raise
                    except Exception as exc:
                        self._log(f"  ⚠️  Turn error: {exc}")
                        time.sleep(0.5)

        except KeyboardInterrupt:
            self._log("")
            self._log("  Ctrl+C received. Shutting down...")
            self._speak("Shutting down. Goodbye, sir.")
        finally:
            self._running = False
            self.speaker.stop_playback()
            self._log("  JARVIS offline.")

    def stop(self) -> None:
        """Signal the loop to stop."""
        self._running = False

    def single_turn(self, text: str) -> str:
        """Process a single text turn (for testing/programmatic use)."""
        response = self._think(text)
        return response


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point: `python -m jarvis.multimodal.jarvis_voice`."""
    import argparse

    parser = argparse.ArgumentParser(description="JARVIS Voice Assistant")
    parser.add_argument("--stt-model", default="base", help="Whisper model size (tiny/base/small/medium)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Edge TTS voice name")
    parser.add_argument("--llm", default="auto", help="LLM provider (auto/groq/openai)")
    parser.add_argument("--llm-model", default=None, help="LLM model name")
    parser.add_argument("--no-greeting", action="store_true", help="Skip greeting")
    parser.add_argument("--google-stt", action="store_true", help="Use Google STT instead of Whisper")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--list-voices", action="store_true", help="List available Edge TTS voices")

    args = parser.parse_args()

    if args.list_voices:
        print("Available JARVIS voices:")
        for name, voice_id in EDGE_VOICES.items():
            marker = " ← default" if voice_id == DEFAULT_VOICE else ""
            print(f"  {name:20s} = {voice_id}{marker}")
        print(f"\n  Current default: {DEFAULT_VOICE}")
        print("  Set with --voice <voice-id>")
        return

    assistant = JarvisVoiceAssistant(
        stt_model=args.stt_model,
        use_google_stt=args.google_stt,
        tts_voice=args.voice,
        llm_provider=args.llm,
        llm_model=args.llm_model,
        greeting=not args.no_greeting,
        verbose=not args.quiet,
    )
    assistant.run()


if __name__ == "__main__":
    main()
