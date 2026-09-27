"""Tests for Pure Native Windows Desktop Companion Application."""

import pytest
from jarvis.ui.desktop_companion import (
    NativeArcReactor,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_RED,
)


def test_native_arc_reactor_status_colors():
    """Verify Arc Reactor state machine transitions to correct HUD colors."""
    reactor = NativeArcReactor(canvas=None, cx=100, cy=100, radius=60)  # type: ignore[arg-type]
    assert reactor.get_color() == COLOR_CYAN

    reactor.set_status("listening")
    assert reactor.get_color() == COLOR_GREEN

    reactor.set_status("thinking")
    assert reactor.get_color() == COLOR_AMBER

    reactor.set_status("acting")
    assert reactor.get_color() == COLOR_BLUE

    reactor.set_status("emergency_stopped")
    assert reactor.get_color() == COLOR_RED


def test_cli_app_parser_defaults():
    """Verify jarvis app CLI parser defaults to pure native GUI mode."""
    from jarvis.cli import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["app"])
    assert args.command == "app"
    assert args.port == 7777
    assert args.web is False
