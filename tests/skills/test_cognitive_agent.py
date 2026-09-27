from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

from jarvis.skills.cognitive_agent import (
    AGENT_TOOLS,
    AgentTurnResult,
    CognitiveAgent,
    ToolExecutionRecord,
)
from jarvis.skills.registry import SkillRegistry


def _live_llm_available() -> bool:
    """True only when an LLM client actually resolves.

    Checking merely that an API key is *set* is not enough: on this machine
    `GEMINI_API_KEY` and `OPENAI_API_KEY` are both present, yet `_resolve()`
    still yields provider "offline" with no client (quota/network/provider probe
    failure). `process_turn` then takes the deterministic `_offline_process`
    fallback, which misreads a natural-language request as GUI actions and
    tries to "type" into a File Explorer window, so the live test below failed
    for reasons unrelated to its subject.
    """
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        return False
    try:
        from jarvis.multimodal.jarvis_voice import LLMEngine

        engine = LLMEngine()
        engine._resolve()
    except Exception:
        return False
    return engine._client is not None and engine._resolved_provider != "offline"


def test_cognitive_agent_init() -> None:
    agent = CognitiveAgent()
    assert agent.registry is not None
    assert agent.skill_engine is not None
    assert agent.llm_engine is not None
    assert len(AGENT_TOOLS) >= 7


def test_execute_tool_run_system_command() -> None:
    agent = CognitiveAgent()
    out, ok = agent.execute_tool("run_system_command", {"command": "Write-Output 'JARVIS_COGNITIVE_ACTIVE'"})
    assert ok is True
    assert "JARVIS_COGNITIVE_ACTIVE" in out.get("stdout", "")
    assert out.get("exit_code") == 0


def test_execute_tool_filesystem_operation(tmp_path: Path) -> None:
    agent = CognitiveAgent()
    test_file = tmp_path / "jarvis_test.txt"

    # Write
    w_out, w_ok = agent.execute_tool(
        "filesystem_operation",
        {"operation": "write_file", "path": str(test_file), "content": "Autonomous Agent Protocol"},
    )
    assert w_ok is True
    assert test_file.exists()

    # Read
    r_out, r_ok = agent.execute_tool(
        "filesystem_operation",
        {"operation": "read_file", "path": str(test_file)},
    )
    assert r_ok is True
    assert r_out.get("content") == "Autonomous Agent Protocol"

    # List Dir
    l_out, l_ok = agent.execute_tool(
        "filesystem_operation",
        {"operation": "list_dir", "path": str(tmp_path)},
    )
    assert l_ok is True
    assert any(item["name"] == "jarvis_test.txt" for item in l_out.get("items", []))


def test_execute_tool_find_skills() -> None:
    agent = CognitiveAgent()
    out, ok = agent.execute_tool("find_skills", {"query": "disk", "limit": 3})
    assert ok is True
    assert "skills" in out


def test_offline_process_fallback() -> None:
    agent = CognitiveAgent()
    # 1. System command execution
    res_cmd = agent._offline_process("cmd: echo OFFLINE_EXEC_OK")
    assert isinstance(res_cmd, AgentTurnResult)
    assert res_cmd.action == "system_command"
    assert "OFFLINE_EXEC_OK" in res_cmd.reply
    assert res_cmd.success is True

    # 2. Desktop input control
    res_mouse = agent._offline_process("mouse: get")
    assert isinstance(res_mouse, AgentTurnResult)
    assert res_mouse.action == "desktop_input"
    assert "Current cursor position" in res_mouse.reply

    # 3. Hardware control
    res_vol = agent._offline_process("volume up")
    assert isinstance(res_vol, AgentTurnResult)
    assert res_vol.action == "volume_up"
    assert "Volume increased" in res_vol.reply

    # 4. Vision-guided screen perception
    res_screen = agent._offline_process("inspect screen")
    assert isinstance(res_screen, AgentTurnResult)
    assert res_screen.action == "screen_perception"
    assert "Active window:" in res_screen.reply

    # 5. Multi-step task autonomy
    res_multi = agent._offline_process("cmd: echo STEP_1 and then cmd: echo STEP_2 and then cmd: echo STEP_3")
    assert isinstance(res_multi, AgentTurnResult)
    assert res_multi.action == "multi_step_executed"
    assert "Step 1:" in res_multi.reply and "STEP_1" in res_multi.reply
    assert "Step 2:" in res_multi.reply and "STEP_2" in res_multi.reply
    assert "Step 3:" in res_multi.reply and "STEP_3" in res_multi.reply
    assert len(res_multi.tools_executed) == 3
    assert res_multi.success is True

    # 6. Natural language type-into
    res_type = agent._offline_process("type 'JARVIS_AUTONOMY_PULSE' into NonExistentTargetWindowXYZ")
    assert isinstance(res_type, AgentTurnResult)
    assert res_type.action == "screen_perception"
    assert res_type.success is False

    # 7. Natural language file writing offline (no false GUI typing)
    res_file = agent._offline_process("Write a file named jarvis_offline_test.txt with the content 'Verified' in the current artifacts directory and confirm.")
    assert isinstance(res_file, AgentTurnResult)
    assert res_file.action == "filesystem_operation"
    assert res_file.success is True
    test_artifact = Path("artifacts") / "jarvis_offline_test.txt"
    assert test_artifact.exists()
    test_artifact.unlink(missing_ok=True)


def test_execute_tool_screen_perception() -> None:
    agent = CognitiveAgent()
    out, ok = agent.execute_tool("screen_perception", {"action": "inspect_screen"})
    assert ok is True
    assert "resolution" in out
    assert "active_window" in out
    assert "visible_windows" in out
    assert "active_window_controls" in out
    assert isinstance(out["active_window_controls"], list)


@pytest.mark.skipif(
    not _live_llm_available(),
    reason="Requires a resolvable live LLM client (key set AND provider online)",
)
def test_live_agent_turn_execution() -> None:
    agent = CognitiveAgent()
    res = agent.process_turn("Write a file named jarvis_agent_test.txt with the content 'Operational' in the current artifacts directory and confirm.")
    assert isinstance(res, AgentTurnResult)
    assert res.success is True
    assert len(res.reply) > 0
    # Clean up created file if present
    artifact_file = Path("artifacts/jarvis_agent_test.txt")
    if artifact_file.exists():
        artifact_file.unlink(missing_ok=True)
