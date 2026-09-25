# M7 — Ambient Multimodal Computer-Use & Spatial Desktop Companion

**Status:** ACCEPTED DESIGN — architectural contract for Milestone M7.  
**Author/owner:** Antigravity (Gemini) architectural design & verification; Big Pickle (OpenCode) implementation.  
**Milestone:** Phase 6: Milestone M7 (Ambient Multimodal Computer-Use & Spatial Desktop Companion).  
**Baseline:** `main @ ac93185`, **890 passed in 219s**, 0 failed.  
**Specification Grounding:** `docs/MASTER_BUILD_SPEC.md` §24 (Computer-Use System) & §6.1 (Perception Pipeline).

---

## 1. Architectural Vision & Paradigm Synthesis

Open-source computer-use systems have traditionally suffered from fragmented trade-offs: either they hijack the physical mouse and disrupt human work, or they transmit unredacted screenshots to third-party clouds, or they lack transactional safety and verification.

Milestone M7 unifies the four breakthrough open-source paradigms into a single, cohesive architecture built directly on JARVIS 2.0's deterministic kernel:

```text
               ┌─────────────────────────────────────────────────────────────┐
               │                JARVIS 2.0 COMPANION STACK                   │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
         【PARADIGM 1 & 3: PERCEPTION】                  【PARADIGM 2 & 4: ACTION】
      ┌───────────────────────────────┐               ┌───────────────────────────────┐
      │  Single-Pipeline Streaming    │               │  Background Headless Control  │
      │  - Full-duplex voice loop     │               │  - Win32 / UIA background msgs│
      │  - Ambient screen diffing     │               │  - Zero cursor hijacking      │
      ├───────────────────────────────┤               ├───────────────────────────────┤
      │  Air-Gapped Local Privacy     │               │  Spatial HUD Guidance         │
      │  - Local VLM (Ollama/llama.cpp│               │  - Transparent bounding boxes │
      │  - Deterministic PII redactor │               │  - Laser/cursor guidance      │
      └───────────────────────────────┘               └───────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │           DETERMINISTIC SAFETY & AUDIT LEDGER               │
               │   - M5.5 Hardware E-Stop Latch      - M1 Hash-Chained Log   │
               │   - M2.5 Privacy Enforcement Gate   - M1 Effect Envelopes   │
               └─────────────────────────────────────────────────────────────┘
```

### The 4 Synthesized Paradigms:
1. **Air-Gapped Local Screen Privacy**: Screen frames are captured locally, diffed for changes, and filtered through JARVIS's deterministic PII redaction engine. Frames never leave local memory without explicit user consent.
2. **Background Headless Computer-Use**: Interacts with target applications via background UI Automation (UIA) and native window messaging (`SendMessage`/`PostMessage`), performing clicks, keystrokes, and data extraction without moving the user's physical mouse cursor or stealing active window focus.
3. **Continuous Real-Time Voice Pairing**: Extends the M4 voice loop and M6 wake-word coordinator into an ambient "over-the-shoulder" pairing mode. The creator talks freely while JARVIS correlates speech with the active window state without requiring repetitive hotkeys.
4. **Spatial Desktop HUD & Visual Guidance**: A lightweight, non-intrusive transparent HUD overlay that paints highlights, bounding boxes, and guidance rings around target elements, providing immediate visual feedback and a physical on-screen Emergency Stop / Blind button.

---

## 2. Work Packages for Milestone M7

| Package | Component | Key Deliverables | Target Test Suite |
|:---|:---|:---|:---|
| **M7.1** | **Air-Gapped Screen Perception & Privacy Shutter** | `src/jarvis/perception/screen.py` | `tests/perception/test_screen.py` |
| **M7.2** | **Background Headless Computer-Use Seam** | `src/jarvis/effects/computer_use.py` | `tests/effects/test_computer_use.py` |
| **M7.3** | **Continuous Real-Time Voice-Screen Pairing Loop** | `src/jarvis/live/continuous_tutor.py` | `tests/live/test_continuous_tutor.py` |
| **M7.4** | **Spatial Desktop HUD & Visual Guidance Overlay** | `src/jarvis/ui/overlay.py` | `tests/ui/test_overlay.py` |
| **M7.5** | **Closed-Loop Autonomous Computer-Use Engine** | `src/jarvis/kernel/computer_use.py` | `tests/kernel/test_computer_use.py` |

---

## 3. Detailed Technical Contracts

### M7.1: Air-Gapped Screen Perception & Privacy Shutter (`screen.py`)
- **Frame Grabber**: Captures full desktop or target window using platform-native APIs (DXGI Desktop Duplication on Windows with `mss` fallback).
- **Perception Cache & Dirty Diffing**: Computes fast perceptual hashes (dHash/pHash) across 16x16 grid tiles. Only modified regions trigger downstream processing, reducing idle CPU/GPU consumption to <1%.
- **Deterministic PII Redaction**: Integrates with `jarvis.kernel.privacy.PrivacyPolicyEngine` to identify sensitive bounding boxes (password fields, auth tokens, banking patterns) and masks them before VLM ingestion.
- **Local VLM Seam**: Versioned `ScreenVisionAdapter` protocol supporting local models (Ollama, llama.cpp, local ONNX/DirectML endpoints).

### M7.2: Background Headless Computer-Use Seam (`computer_use.py`)
- **Seam Contract**: `ComputerUseProvider` protocol behind `CapabilityRegistry`.
- **Background Delivery (Default)**:
  - Dispatches clicks, keystrokes, and selections directly to target window handles (`HWND`) via UIA invoke patterns or background `PostMessageW(WM_LBUTTONDOWN / WM_LBUTTONUP)`.
  - **Zero Cursor Hijacking**: The human creator's physical mouse cursor remains entirely undisturbed.
- **Foreground Emulation (Explicit)**:
  - If target software rejects background messages, executes physical mouse/keyboard events.
  - **Fail-Closed Safety**: Any movement of the physical hardware mouse during an autonomous action or cursor movement into a safety corner trips the `EStopLatch` and aborts instantly.
- **Effect Envelopes**: All actions executed through `EffectEnvelopeEngine` and audited to `EventLog` stream `effects.computer_use`.

### M7.3: Continuous Real-Time Voice-Screen Pairing Loop (`continuous_tutor.py`)
- **Continuous Mode**: Activated via wake-word `"Hey JARVIS, let's pair"` or CLI `--pairing`.
- **Single-Pipeline Coordination**:
  - Connects `StreamingVoiceLoop` (M4) directly to `ScreenPerceptionEngine` (M7.1).
  - When the user speaks, the active window image and element hierarchy are attached as multimodal context to the reasoning engine.
  - Generates streaming voice replies via Piper TTS without blocking active screen perception.

### M7.4: Spatial Desktop HUD & Visual Guidance Overlay (`overlay.py`)
- **Zero-Friction Transparent HUD**:
  - Transparent, click-through overlay window on top of the desktop.
  - Renders visual bounding boxes around elements JARVIS is analyzing or recommending.
  - Renders ambient state indicators: `IDLE`, `LISTENING`, `THINKING`, `ACTING`.
- **Physical Controls**:
  - Includes a floating interactive pill with an instant **"EMERGENCY HALT"** (trips E-Stop) and **"PRIVACY SHUTTER"** (blinds screen perception immediately).

### M7.5: Closed-Loop Autonomous Computer-Use Engine (`computer_use.py`)
- Implements Section 24 of Master Build Spec:
  $$\text{OBSERVE} \longrightarrow \text{PLAN} \longrightarrow \text{GATE (Policy + E-Stop)} \longrightarrow \text{ACT} \longrightarrow \text{VERIFY}$$
- After executing a background click or typing action, takes a post-action diff to deterministically verify that the UI responded (e.g. window opened, button state changed).
- Emits complete audit telemetry to `EventLog`.

---

## 4. Acceptance Invariants

1. **Air-Gap Invariant**: No raw screen pixel buffers or OCR text may ever be sent to external networks without explicit, cryptographic creator authorization.
2. **Non-Disruptive Cursor Invariant**: Background computer-use tasks MUST NOT move the physical system cursor or steal foreground keyboard focus from the active window.
3. **Fail-Closed E-Stop Invariant**: Any physical mouse disturbance, panic hotkey, or overlay halt button MUST immediately terminate active automation within $\le 50\text{ms}$.
4. **Deterministic Auditability**: Every screen perception event and UI action MUST be recorded to the tamper-evident hash-chained event store.
5. **Zero Regressions**: All 890 baseline tests from Milestones M0 through M6 must remain 100% green.
