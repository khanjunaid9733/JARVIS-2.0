"""Guard: the canonical truth ledger (project_state.yaml) must parse and expose
the paths the workflow depends on. The ledger lay silently unparseable from
838d182 (unterminated string + un-nested M2 block) while the suite stayed green;
this pin makes that failure impossible (creator-ruled 2026-09-19: dev-only
pyyaml per AGENTS.md §2.6)."""
import yaml

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ledger() -> dict:
    text = (REPO_ROOT / "project_state.yaml").read_text("utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict), "project_state.yaml must parse to a mapping"
    return data


def test_ledger_parses_and_has_mandatory_paths():
    data = _ledger()
    assert data["project"]["name"] == "JARVIS"
    assert data["status"]["m2_memory_os"]["status"]
    assert "packages" in data["status"]["m2_memory_os"]
    assert data["current_task"]["phase"]
    assert data["constraints"]["architecture_freeze"] is True


def test_m2_block_is_nested_not_flattened():
    data = _ledger()
    assert "status" not in data["status"]
    assert "creator_rulings_accepted" not in data["status"]
    assert "packages" not in data["status"]
    assert data["status"]["m2_memory_os"]["creator_rulings_accepted"]