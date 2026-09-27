from __future__ import annotations

"""JARVIS 2.0 — Native OS-Level Background Voice Listener.

Continuously listens for hands-free acoustic wake words ("Hey JARVIS", "JARVIS")
at the operating system hardware level, independently of browser window focus,
minimized tabs, or desktop application states.

When triggered:
1. Plays instant holographic sci-fi wake chime via winsound (D5 -> A5).
2. Summons / focuses the desktop HUD overlay window (HWND_TOPMOST).
3. Transcribes user voice commands via SpeechRecognition.
4. Routes intents to the JARVIS Core Service / Skill Engine.
5. Synthesizes articulate spoken responses using Edge TTS / Windows SAPI.
"""

import os
import re
import sys
import threading
import time
from typing import Any, Callable, Optional

from jarvis.ui.hotkey import launch_or_focus_hud
from jarvis.ui.overlay import CompanionStatus


def _play_wake_chime() -> None:
    """Play two-tone ascending sci-fi chime (D5 -> A5) via winsound."""
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.Beep(587, 90)   # D5 (587.33 Hz)
        winsound.Beep(880, 160)  # A5 (880.00 Hz)
    except Exception:
        pass


def _play_confirm_chime() -> None:
    """Play single high confirmation tone via winsound."""
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.Beep(1046, 120)  # C6 (1046.5 Hz)
    except Exception:
        pass


class VoiceSpeaker:
    """Synthesizes speech aloud using Neural TTS or Windows SAPI."""

    def __init__(self) -> None:
        self._sapi: Any = None
        self._sapi_checked = False
        self._neural_engine: Any = None
        self._neural_checked = False

    def _get_neural(self) -> Any:
        if not self._neural_checked:
            self._neural_checked = True
            try:
                from jarvis.multimodal.neural_tts import NeuralTTSEngine
                self._neural_engine = NeuralTTSEngine(voice="en-GB-RyanNeural")
            except Exception:
                self._neural_engine = None
        return self._neural_engine

    def _get_sapi(self) -> Any:
        if not self._sapi_checked:
            self._sapi_checked = True
            if sys.platform == "win32":
                try:
                    import win32com.client
                    self._sapi = win32com.client.Dispatch("SAPI.SpVoice")
                except Exception:
                    self._sapi = None
        return self._sapi

    def speak(self, text: str) -> None:
        """Speak text aloud to the default audio output device."""
        if not text:
            return

        # Clean text of markdown, URLs, and asterisks
        clean = re.sub(r"[*_#`~\[\]]", "", text)
        clean = re.sub(r"https?://\S+", "a web link", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if not clean:
            return

        # 1. Try Next-Gen Windows HD Voice (Mark / David)
        if sys.platform == "win32":
            try:
                clean_q = clean.replace('"', "'")[:280]
                ps_script = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    "$found = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -like '*Mark*' -or $_.VoiceInfo.Name -like '*David*' } | Select-Object -First 1; "
                    "if ($found) { $synth.SelectVoice($found.VoiceInfo.Name) }; "
                    "$synth.Rate = 1; "
                    f"$synth.Speak(\"{clean_q}\")"
                )
                import subprocess
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    timeout=10,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000,
                )
                return
            except Exception:
                pass

        # 2. Try Windows SAPI (instant, 0ms latency, 100% offline)
        sapi = self._get_sapi()
        if sapi is not None:
            try:
                sapi.Speak(clean)
                return
            except Exception:
                pass

        # 3. Try pyttsx3 fallback
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(clean)
            engine.runAndWait()
            return
        except Exception:
            pass

        # 4. Try Neural TTS Engine (Edge TTS)
        neural = self._get_neural()
        if neural is not None:
            try:
                res = neural.synthesize(clean)
                if res.audio_bytes:
                    from jarvis.multimodal.audio_io import RealSpeaker
                    spk = RealSpeaker()
                    spk.play_wav(res.audio_bytes, blocking=True)
                    return
            except Exception:
                pass


class NativeVoiceListener:
    """Continuous OS-level background microphone listener for hands-free wake."""

    WAKE_PATTERNS = [
        re.compile(r"\b(?:hey\s+|hi\s+|ok\s+)?jarvis\b", re.IGNORECASE),
        re.compile(r"\bwake\s+up(?:\s+jarvis)?\b", re.IGNORECASE),
        re.compile(r"\bj\.a\.r\.v\.i\.s\b", re.IGNORECASE),
    ]

    def __init__(
        self,
        port: int = 7777,
        server_engine: Any = None,
        on_wake: Optional[Callable[[], None]] = None,
    ) -> None:
        self.port = port
        self.server_engine = server_engine
        self.on_wake = on_wake
        self.speaker = VoiceSpeaker()

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_active = False

    def start(self) -> bool:
        """Start the background voice listener daemon thread."""
        if self._thread and self._thread.is_alive():
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_worker,
            name="JARVIS-NativeVoiceListener",
            daemon=True,
        )
        self._thread.start()
        self._is_active = True
        return True

    def stop(self) -> None:
        """Stop the background listener."""
        self._stop_event.set()
        self._is_active = False

    @property
    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _set_status(self, status: CompanionStatus | str) -> None:
        """Update overlay HUD state if server engine is available."""
        if self.server_engine and hasattr(self.server_engine, "overlay"):
            try:
                val = status if isinstance(status, CompanionStatus) else CompanionStatus(str(status).lower())
                self.server_engine.overlay.set_status(val)
            except Exception:
                pass

    def _listen_worker(self) -> None:
        """Background listening loop using speech_recognition."""
        try:
            import speech_recognition as sr
        except ImportError:
            print("[VoiceListener] speech_recognition not installed, background mic disabled.")
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.6
        recognizer.phrase_threshold = 0.3
        recognizer.non_speaking_duration = 0.4

        try:
            microphone = sr.Microphone()
        except Exception as exc:
            print(f"[VoiceListener] Could not open default microphone: {exc}")
            return

        # Initial ambient calibration
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
        except Exception:
            pass

        print(f"[VoiceListener] Background mic listening active on port {self.port}. Say 'Hey JARVIS' to trigger.")

        while not self._stop_event.is_set():
            try:
                with microphone as source:
                    # Listen for audio phrase with a 2-second timeout to check stop_event
                    try:
                        audio = recognizer.listen(source, timeout=2.0, phrase_time_limit=8.0)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception:
                        time.sleep(0.3)
                        continue

                # Transcribe captured audio via Google STT (fastest cloud/local bridge)
                try:
                    transcript = recognizer.recognize_google(audio, language="en-US").strip()
                except sr.UnknownValueError:
                    continue  # Inaudible / background noise
                except Exception:
                    continue

                if not transcript:
                    continue

                # Check for wake word trigger
                matched = False
                for pattern in self.WAKE_PATTERNS:
                    if pattern.search(transcript):
                        matched = True
                        break

                if not matched:
                    continue

                print(f"[VoiceListener] Wake word detected: '{transcript}'")

                # 1. Immediate sci-fi acoustic chime
                _play_wake_chime()

                # 2. Summon / Focus Desktop HUD overlay
                launch_or_focus_hud(self.port)
                self._set_status(CompanionStatus.LISTENING)

                if self.on_wake:
                    try:
                        self.on_wake()
                    except Exception:
                        pass

                # 3. Extract Command (if spoken in the same breath)
                cmd = re.sub(r"^.*?\b(?:hey\s+|hi\s+|ok\s+)?jarvis\b[,:\s]*", "", transcript, flags=re.IGNORECASE).strip()

                # If no command followed wake word, chime and listen for follow-up
                if not cmd:
                    _play_confirm_chime()
                    try:
                        with microphone as source:
                            followup_audio = recognizer.listen(source, timeout=6.0, phrase_time_limit=10.0)
                            cmd = recognizer.recognize_google(followup_audio, language="en-US").strip()
                    except Exception:
                        cmd = ""

                if not cmd:
                    self._set_status(CompanionStatus.IDLE)
                    continue

                print(f"[VoiceListener] Executing command: '{cmd}'")
                self._set_status(CompanionStatus.THINKING)

                # 4. Route command to server engine or say handler
                reply_text = self._process_command(cmd)

                # 5. Play confirmation and speak response aloud
                self._set_status(CompanionStatus.ACTING)
                self.speaker.speak(reply_text)

                # 6. Return HUD to idle
                self._set_status(CompanionStatus.IDLE)

            except Exception as loop_exc:
                print(f"[VoiceListener] Loop error: {loop_exc}")
                time.sleep(1.0)

    def _process_command(self, cmd: str) -> str:
        """Route user voice command through the JARVIS server engine."""
        if self.server_engine and hasattr(self.server_engine, "handle_say"):
            try:
                res = self.server_engine.handle_say(cmd)
                return str(res.get("reply", "Command acknowledged, sir."))
            except Exception as exc:
                return f"Error executing command: {exc}"

        # Fallback to local HTTP POST /api/say
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/say",
                data=json.dumps({"text": cmd}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return str(data.get("reply", "Command processed, sir."))
        except Exception:
            return f"Processed '{cmd}', sir. Core standing by."
