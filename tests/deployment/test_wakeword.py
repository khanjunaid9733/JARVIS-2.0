from __future__ import annotations

from pathlib import Path
import time
import pytest

from jarvis.deployment.wakeword import MockWakeWordDetector, WakeWordCoordinator, WakeWordResult
from jarvis.kernel.event_log import EventLog
from jarvis.multimodal.streaming import StreamingVoiceLoop, VoiceTurnState


@pytest.fixture
def temp_log(tmp_path: Path):
    db_file = tmp_path / "voice_log.db"
    return EventLog(db_path=db_file)


def test_mock_wakeword_detector_detects_byte_pattern():
    detector = MockWakeWordDetector(keywords=("jarvis",), trigger_byte_pattern=b"WAKE")

    res_silent = detector.process_audio(b"\x00" * 320)
    assert not res_silent.detected

    res_wake = detector.process_audio(b"\x00\x00WAKE\x00\x00")
    assert res_wake.detected
    assert res_wake.keyword == "jarvis"
    assert res_wake.confidence == 0.95


def test_mock_wakeword_detector_manual_queue():
    detector = MockWakeWordDetector()
    detector.queue_trigger(keyword="hey_jarvis", confidence=0.88)

    res = detector.process_audio(b"\x00" * 320)
    assert res.detected
    assert res.keyword == "hey_jarvis"
    assert res.confidence == 0.88


def test_low_confidence_below_threshold_rejected():
    detector = MockWakeWordDetector(confidence_threshold=0.80)
    # Queue detection with 0.65 confidence (below 0.80 threshold)
    detector.queue_trigger(keyword="hey_jarvis", confidence=0.65)

    res = detector.process_audio(b"\x00" * 320)
    assert not res.detected


def test_coordinator_activates_voice_loop(temp_log: EventLog):
    detector = MockWakeWordDetector()
    loop = StreamingVoiceLoop(event_log=temp_log)
    assert loop.state == VoiceTurnState.IDLE

    wakes = []
    coordinator = WakeWordCoordinator(
        detector=detector,
        voice_loop=loop,
        event_log=temp_log,
        on_wake=lambda r: wakes.append(r),
    )

    # Feed trigger audio
    detector.queue_trigger(keyword="jarvis")
    result = coordinator.feed_audio(b"\x00" * 320)

    assert result.detected
    assert len(wakes) == 1
    assert coordinator.detection_count == 1
    # Voice loop automatically transitioned to LISTENING
    assert loop.state == VoiceTurnState.LISTENING

    # Audit event in EventLog
    cur = temp_log._conn.execute(
        "SELECT * FROM events WHERE stream_id = 'voice' AND event_type = 'wakeword.detected'"
    )
    ev = cur.fetchone()
    assert ev is not None
    assert temp_log.verify_chain()


def test_coordinator_debounce_window():
    detector = MockWakeWordDetector()
    coordinator = WakeWordCoordinator(
        detector=detector,
        debounce_seconds=0.5,
    )

    # First trigger: succeeds
    detector.queue_trigger(keyword="jarvis")
    res1 = coordinator.feed_audio(b"\x00" * 320)
    assert res1.detected
    assert coordinator.detection_count == 1

    # Immediate second trigger: suppressed by debounce window
    detector.queue_trigger(keyword="jarvis")
    res2 = coordinator.feed_audio(b"\x00" * 320)
    assert not res2.detected
    assert coordinator.detection_count == 1

    # Wait past debounce window
    time.sleep(0.55)
    detector.queue_trigger(keyword="jarvis")
    res3 = coordinator.feed_audio(b"\x00" * 320)
    assert res3.detected
    assert coordinator.detection_count == 2
