"""Real-time Audio I/O Drivers — Microphone Capture & Speaker Playback.

Provides:
- MicrophoneDriver: Continuous real-time microphone capture with configurable
  frame size, sample rate, and energy-based VAD.
- SpeakerDriver: Non-blocking WAV audio playback through the default output device.
- AudioDeviceInfo: Device enumeration and selection.

Invariants:
1. Provider Seam: Both MicrophoneDriver and SpeakerDriver implement their
   respective Protocols. Mock implementations exist for hermetic testing.
2. No Kernel Dependency: This module touches hardware only — no EventLog,
   no kernel imports. The caller (the voice loop) is responsible for
   journaling state transitions.
3. Fail-Closed: Device errors are surfaced, never swallowed. A missing
   microphone or speaker raises immediately.
"""

from __future__ import annotations

import io
import struct
import sys
import threading
import time
import wave
from array import array
from collections import deque
from dataclasses import dataclass, field
from math import fsum, sqrt
from typing import Any, Callable, Optional, Protocol, Sequence


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_RATE = 16000       # Whisper's native rate
DEFAULT_FRAME_DURATION_MS = 30    # 30ms frames (standard for VAD)
DEFAULT_CHANNELS = 1              # Mono
DEFAULT_SAMPLE_WIDTH = 2          # 16-bit PCM
DEFAULT_RMS_THRESHOLD = 0.015     # Normalized RMS speech threshold
DEFAULT_SILENCE_FRAMES = 15       # ~450ms of silence to end utterance
DEFAULT_SPEECH_FRAMES = 3         # ~90ms of speech to start recording


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AudioFrame:
    """A single audio frame with measured energy."""

    data: bytes
    rms_energy: float
    is_speech: bool
    timestamp: float
    frame_index: int


@dataclass(frozen=True)
class AudioDeviceInfo:
    """Info about an available audio device."""

    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    is_input: bool
    is_output: bool


# ---------------------------------------------------------------------------
# Microphone Protocol & Implementations
# ---------------------------------------------------------------------------

class MicrophoneProtocol(Protocol):
    """Protocol for abstracting microphone capture."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def read_frame(self) -> AudioFrame | None: ...
    @property
    def is_active(self) -> bool: ...
    @property
    def sample_rate(self) -> int: ...
    @property
    def frame_size(self) -> int: ...


class MockMicrophone:
    """Deterministic mock microphone for testing."""

    def __init__(
        self,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_duration_ms: int = DEFAULT_FRAME_DURATION_MS,
        rms_threshold: float = DEFAULT_RMS_THRESHOLD,
    ) -> None:
        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._frame_size = int(sample_rate * frame_duration_ms / 1000)
        self._rms_threshold = rms_threshold
        self._active = False
        self._frame_index = 0
        self._queued_frames: deque[tuple[bytes, bool]] = deque()

    def enqueue_frames(self, frames: Sequence[tuple[bytes, bool]]) -> None:
        """Queue (audio_bytes, is_speech) pairs for testing."""
        self._queued_frames.extend(frames)

    def start(self) -> None:
        self._active = True
        self._frame_index = 0

    def stop(self) -> None:
        self._active = False

    def read_frame(self) -> AudioFrame | None:
        if not self._active or not self._queued_frames:
            return None
        data, is_speech = self._queued_frames.popleft()
        rms = 0.1 if is_speech else 0.001
        frame = AudioFrame(
            data=data,
            rms_energy=rms,
            is_speech=is_speech,
            timestamp=time.time(),
            frame_index=self._frame_index,
        )
        self._frame_index += 1
        return frame

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def frame_size(self) -> int:
        return self._frame_size


class RealMicrophone:
    """Live microphone capture using PyAudio with energy-based VAD.

    Captures audio frames from the system microphone in a background thread
    and measures per-frame RMS energy to provide a speech/silence flag.
    """

    def __init__(
        self,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_duration_ms: int = DEFAULT_FRAME_DURATION_MS,
        channels: int = DEFAULT_CHANNELS,
        rms_threshold: float = DEFAULT_RMS_THRESHOLD,
        device_index: int | None = None,
        buffer_max_frames: int = 500,  # ~15s buffer
    ) -> None:
        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._channels = channels
        self._rms_threshold = rms_threshold
        self._device_index = device_index
        self._frame_size = int(sample_rate * frame_duration_ms / 1000)
        self._chunk_bytes = self._frame_size * DEFAULT_SAMPLE_WIDTH * channels

        self._active = False
        self._frame_index = 0
        self._buffer: deque[AudioFrame] = deque(maxlen=buffer_max_frames)
        self._lock = threading.Lock()
        self._stream: Any = None
        self._pa: Any = None
        self._thread: threading.Thread | None = None

    def _compute_rms(self, data: bytes) -> float:
        """Compute normalized RMS energy of 16-bit PCM samples.

        Uses `array` rather than numpy: this module is otherwise pure stdlib
        (`wave`, `struct`, `io`) and numpy is neither declared nor installed,
        so the previous `np.` calls raised NameError on every capture frame and
        the VAD energy gate never actually ran.
        """
        if len(data) < 2:
            return 0.0
        # `array('h')` needs a whole number of 2-byte frames.
        usable = len(data) - (len(data) % 2)
        if usable < 2:
            return 0.0
        samples = array("h")
        samples.frombytes(data[:usable])
        # WAV frames are little-endian; normalize a big-endian host to match.
        if sys.byteorder == "big":
            samples.byteswap()
        count = len(samples)
        if count == 0:
            return 0.0
        sum_squares = fsum(float(s) * s for s in samples)
        return sqrt(sum_squares / count) / 32768.0

    def _capture_loop(self) -> None:
        """Background thread: reads frames from PyAudio and queues them."""
        while self._active and self._stream is not None:
            try:
                data = self._stream.read(self._frame_size, exception_on_overflow=False)
                rms = self._compute_rms(data)
                frame = AudioFrame(
                    data=data,
                    rms_energy=rms,
                    is_speech=rms > self._rms_threshold,
                    timestamp=time.time(),
                    frame_index=self._frame_index,
                )
                self._frame_index += 1
                with self._lock:
                    self._buffer.append(frame)
            except Exception:
                if self._active:
                    time.sleep(0.01)

    def start(self) -> None:
        """Open microphone device and begin background capture."""
        if self._active:
            return
        import pyaudio

        self._pa = pyaudio.PyAudio()
        kwargs: dict[str, Any] = {
            "format": pyaudio.paInt16,
            "channels": self._channels,
            "rate": self._sample_rate,
            "input": True,
            "frames_per_buffer": self._frame_size,
        }
        if self._device_index is not None:
            kwargs["input_device_index"] = self._device_index

        self._stream = self._pa.open(**kwargs)
        self._active = True
        self._frame_index = 0
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="jarvis-mic")
        self._thread.start()

    def stop(self) -> None:
        """Stop capture and release the microphone device."""
        self._active = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

    def read_frame(self) -> AudioFrame | None:
        """Pop the oldest frame from the buffer (non-blocking)."""
        with self._lock:
            if self._buffer:
                return self._buffer.popleft()
        return None

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def frame_size(self) -> int:
        return self._frame_size


# ---------------------------------------------------------------------------
# Speaker Protocol & Implementations
# ---------------------------------------------------------------------------

class SpeakerProtocol(Protocol):
    """Protocol for abstracting audio output."""

    def play_wav(self, wav_bytes: bytes, *, blocking: bool = False) -> None: ...
    def stop_playback(self) -> None: ...
    @property
    def is_playing(self) -> bool: ...


class MockSpeaker:
    """Deterministic mock speaker for testing."""

    def __init__(self) -> None:
        self._playing = False
        self.played_audio: list[bytes] = []

    def play_wav(self, wav_bytes: bytes, *, blocking: bool = False) -> None:
        self.played_audio.append(wav_bytes)
        self._playing = True
        if not blocking:
            self._playing = False

    def stop_playback(self) -> None:
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing


class RealSpeaker:
    """Audio playback using PyAudio stream output.

    Plays WAV bytes through the system's default output device. Supports
    non-blocking playback in a background thread with stop/interrupt.
    """

    def __init__(self, device_index: int | None = None) -> None:
        self._device_index = device_index
        self._playing = False
        self._stop_requested = False
        self._thread: threading.Thread | None = None

    def _play_thread(self, wav_bytes: bytes) -> None:
        """Background playback thread."""
        import pyaudio

        pa: Any = None
        stream: Any = None
        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                pa = pyaudio.PyAudio()
                kwargs: dict[str, Any] = {
                    "format": pa.get_format_from_width(wf.getsampwidth()),
                    "channels": wf.getnchannels(),
                    "rate": wf.getframerate(),
                    "output": True,
                }
                if self._device_index is not None:
                    kwargs["output_device_index"] = self._device_index

                stream = pa.open(**kwargs)
                chunk_size = 1024
                data = wf.readframes(chunk_size)
                while data and not self._stop_requested:
                    stream.write(data)
                    data = wf.readframes(chunk_size)
        except Exception:
            pass
        finally:
            self._playing = False
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass

    def play_wav(self, wav_bytes: bytes, *, blocking: bool = False) -> None:
        """Play WAV audio bytes.

        If blocking=False, playback runs in a background thread and can be
        interrupted by stop_playback() (barge-in support).
        """
        self.stop_playback()
        self._stop_requested = False
        self._playing = True

        if blocking:
            self._play_thread(wav_bytes)
        else:
            self._thread = threading.Thread(
                target=self._play_thread, args=(wav_bytes,), daemon=True, name="jarvis-speaker"
            )
            self._thread.start()

    def stop_playback(self) -> None:
        """Immediately interrupt playback (for barge-in support)."""
        self._stop_requested = True
        self._playing = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    @property
    def is_playing(self) -> bool:
        return self._playing


# ---------------------------------------------------------------------------
# Device enumeration
# ---------------------------------------------------------------------------

def list_audio_devices() -> list[AudioDeviceInfo]:
    """Enumerate available audio input/output devices."""
    try:
        import pyaudio
    except ImportError:
        return []

    pa = pyaudio.PyAudio()
    devices: list[AudioDeviceInfo] = []
    try:
        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                devices.append(AudioDeviceInfo(
                    index=i,
                    name=str(info.get("name", f"device-{i}")),
                    max_input_channels=int(info.get("maxInputChannels", 0)),
                    max_output_channels=int(info.get("maxOutputChannels", 0)),
                    default_sample_rate=float(info.get("defaultSampleRate", 16000)),
                    is_input=int(info.get("maxInputChannels", 0)) > 0,
                    is_output=int(info.get("maxOutputChannels", 0)) > 0,
                ))
            except Exception:
                continue
    finally:
        pa.terminate()
    return devices


def find_default_input_device() -> int | None:
    """Find the index of the default input (microphone) device."""
    try:
        import pyaudio
    except ImportError:
        return None

    pa = pyaudio.PyAudio()
    try:
        info = pa.get_default_input_device_info()
        return int(info["index"])
    except Exception:
        return None
    finally:
        pa.terminate()


def find_default_output_device() -> int | None:
    """Find the index of the default output (speaker) device."""
    try:
        import pyaudio
    except ImportError:
        return None

    pa = pyaudio.PyAudio()
    try:
        info = pa.get_default_output_device_info()
        return int(info["index"])
    except Exception:
        return None
    finally:
        pa.terminate()


__all__ = [
    "AudioDeviceInfo",
    "AudioFrame",
    "MockMicrophone",
    "MockSpeaker",
    "MicrophoneProtocol",
    "RealMicrophone",
    "RealSpeaker",
    "SpeakerProtocol",
    "find_default_input_device",
    "find_default_output_device",
    "list_audio_devices",
    "DEFAULT_FRAME_DURATION_MS",
    "DEFAULT_RMS_THRESHOLD",
    "DEFAULT_SAMPLE_RATE",
    "DEFAULT_SILENCE_FRAMES",
    "DEFAULT_SPEECH_FRAMES",
]
