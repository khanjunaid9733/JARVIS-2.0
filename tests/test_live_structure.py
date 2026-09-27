from __future__ import annotations

"""Structure tests: one owner per concern on the live path.

The live loop used to be a single grown module (composition, bootstrap, the step
model, capability resolution, the worker/verifier seam and every printed label in
one file). These tests pin the split so the ownership cannot quietly dissolve
again:

* each concern is DEFINED exactly once, in the module documented to own it,
* `jarvis.live` (and the dispatch seam) only RE-EXPORT the owners' objects - never
  redefine them, so the two import paths cannot drift,
* the composition root holds no printed label of its own - wording lives in
  `jarvis.live_report`,
* the voice turn is defined by `jarvis.live_voice` and only delegated to,
* no compatibility re-export surface survives: a name this repo's CLI, tests and
  scripts do not import through `jarvis.live` is NOT re-exported there (checked
  before deleting it: only `LiveRuntime` and the two engine resolvers are
  imported from `jarvis.live` anywhere in this repo),
* rebinding an engine resolver at `jarvis.live` (the historical patch point) still
  binds the runtime built by `jarvis.live_boot.boot_runtime`.

Structural by design: behaviour is asserted by the command-line driven tests in
`tests/test_live*.py`, which run the real `jarvis mission` / `jarvis voice`.
"""

import importlib
import pathlib
from types import ModuleType

import pytest

from jarvis import cli

MODULES = (
    "live",
    "live_boot",
    "live_steps",
    "live_capability",
    "live_report",
    "live_voice",
    "live_dispatch",
)

#: Names each owner defines, and which may only be re-exported elsewhere.
OWNERS = {
    "live_boot": ("def boot_runtime(", "def _resolve_stt_engine(", "class RuntimeBoot"),
    "live_steps": ("def step_payload(", "def step_expectations(", "def step_capability("),
    "live_capability": ("class CapabilityResolver", "class CapabilityDatum"),
    "live_report": ("def step_line(", "def components_lines(", "def capability_line("),
    "live_voice": ("class VoiceTurn",),
    "live_dispatch": ("class ExternalWorker", "class IndependentVerifier", "class LocalWorker"),
}

#: Names that moved to an owner module and are deliberately NOT re-exported by
#: `jarvis.live` any more (nothing in this repo imports them through it).
NO_LONGER_REEXPORTED = (
    "WORKSPACE_DIRNAME",
    "WORK_ORDER_DIRNAME",
    "CAPABILITY_CANDIDATE_LIMIT",
    "CAPABILITY_AUDIT_STREAM",
    "SKILL_TIMEOUT_SECONDS",
    "first_sha256_token",
    "CapabilityDatum",
    "step_capability",
    "PLAN_STEP",
    "DELIVER_STEP",
    "ATTEST_STEP",
    "_wav_facts",
    "_wav_vad_frames",
    "answer_line",
    "vad_line",
    "vad_real_line",
    "stt_typed_line",
    "tts_wrote_line",
    "voice_loop_line",
    "_HISTORICAL_IMPORT_SURFACE",
)

#: Literal label fragments the composition root must NOT contain any more.
FORBIDDEN_LABEL_FRAGMENTS = (
    'f"step ',
    'f"worker',
    'f"verifier',
    'f"capability',
    'f"recover',
    'f"intake',
    'f"completion',
    'f"recall',
    'f"daemon',
    'f"tts',
    'f"stt',
    'f"vad',
)


@pytest.fixture(scope="module")
def mods() -> dict[str, ModuleType]:
    return {name: importlib.import_module(f"jarvis.{name}") for name in MODULES}


def _source(module: ModuleType) -> str:
    return pathlib.Path(module.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("owner", sorted(OWNERS))
def test_each_concern_is_defined_in_its_owner_module(mods, owner):
    for definition in OWNERS[owner]:
        assert definition in _source(mods[owner]), f"{owner} must define {definition!r}"


@pytest.mark.parametrize("owner", sorted(OWNERS))
def test_the_composition_root_does_not_redefine_what_it_re_exports(mods, owner):
    root = _source(mods["live"])
    for definition in OWNERS[owner]:
        assert definition not in root, f"jarvis.live must not define {definition!r}"


def test_live_reexports_the_owners_objects_without_duplication(mods):
    live, boot = mods["live"], mods["live_boot"]
    steps, dispatch = mods["live_steps"], mods["live_dispatch"]
    report, voice = mods["live_report"], mods["live_voice"]

    # bootstrap: the resolvers stay bound in the composition root on purpose, so a
    # caller can rebind them there (the historical patch point, exercised below).
    assert live.boot_runtime is boot.boot_runtime
    assert live._resolve_stt_engine is boot._resolve_stt_engine
    assert live._resolve_tts_engine is boot._resolve_tts_engine
    # step model: used by the composition root, and re-exported by the dispatch
    # seam whose callers historically imported it there.
    for name in ("step_payload", "step_expectations"):
        assert getattr(live, name) is getattr(steps, name), name
    for name in ("step_payload", "step_expectations", "step_capability", "PLAN_STEP"):
        assert getattr(dispatch, name) is getattr(steps, name), name
    # reports and mission labels
    assert live.MissionReport is report.MissionReport
    assert live.VoiceTurnReport is report.VoiceTurnReport
    for name in (
        "step_line",
        "capability_line",
        "components_lines",
        "recovery_action_line",
        "completion_line",
        "recall_line",
        "daemon_line",
        "worker_line",
        "verifier_line",
    ):
        assert getattr(live, name) is getattr(report, name), name
    # voice labels belong to the voice owner (the composition root has none left)
    for name in ("answer_line", "vad_line", "vad_real_line", "stt_typed_line", "voice_loop_line"):
        assert getattr(voice, name) is getattr(report, name), name
        assert not hasattr(live, name), name
    # the voice turn is the voice owner's object
    assert voice.VoiceTurn is not None
    assert "class VoiceTurn" not in _source(live)


def test_no_compatibility_reexport_surface_survives(mods):
    """Nothing in this repo imports a moved name through `jarvis.live` any more."""
    live = mods["live"]
    for name in NO_LONGER_REEXPORTED:
        assert not hasattr(live, name), f"jarvis.live must not re-export {name}"


def test_the_voice_owner_does_not_reach_into_other_concerns(mods):
    source = _source(mods["live_voice"])
    assert "    def run(" in source
    assert "from .live import" not in source
    assert "live_dispatch" not in source
    assert "resolve_skill(" not in source


def test_the_composition_root_prints_nothing_it_would_have_to_word(mods):
    root = _source(mods["live"])
    for fragment in FORBIDDEN_LABEL_FRAGMENTS:
        assert fragment not in root, f"label {fragment!r} must be owned by live_report"


def test_capability_resolution_is_the_only_place_the_fabric_is_ranked(mods):
    assert "resolve_skill(" in _source(mods["live_capability"])
    for name in ("live", "live_report", "live_boot"):
        assert "resolve_skill(" not in _source(mods[name]), name


def test_engine_resolver_stays_rebindable_at_the_composition_root(tmp_path, monkeypatch):
    """The historical patch point still binds: `jarvis.live`'s resolver is used."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    for name in ("JARVIS_STT_CMD", "JARVIS_TTS_CMD", "JARVIS_MODEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    cli.main(["init"])
    service = cli.CoreService()
    service.start()
    try:
        monkeypatch.setattr(
            "jarvis.live._resolve_stt_engine", lambda: (None, "seam - rebound by the test")
        )
        monkeypatch.setattr(
            "jarvis.live._resolve_tts_engine", lambda: (None, "seam - rebound by the test")
        )
        from jarvis.live import LiveRuntime

        runtime = LiveRuntime(service)
        assert runtime.stt is None and runtime.tts is None
        assert runtime.stt_engine == "seam - rebound by the test"
        assert runtime.tts_engine == "seam - rebound by the test"
    finally:
        service.close()
