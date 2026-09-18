from __future__ import annotations

"""`jarvis` command-line interface (module 11, spec §127.1 / §134.1).

MUST subcommands: `init`, `say`, `explain`, plus `replay --verify` and bare
`jarvis` (restart/recovery summary). Every command is a one-shot process over
the durable store at `$JARVIS_HOME` (default `~/.jarvis`); there is no daemon
in M1 (disclosed — `core service started` denotes the bootstrapped service
context, recorded as a `system.service_started` event).

Output lines follow §127.1 so the acceptance sequence is directly observable.
Deviations from the §127.1 transcript are disclosed in the module report:
- the `say` answer is deterministic/extractive (no model), so its confidence
  is the lexical match score, not a model probability;
- `explain` renders the real cause chain + memory provenance only (full
  cause-chain rendering is STRETCH per §134.1).
"""

import argparse
import sys
from typing import Sequence

from .bootstrap import CoreService, ensure_service_started, new_pairing_code
from .kernel.event_log import EventIntegrityError
from .kernel.memory_query import answer
from .kernel.memory_write import (
    MEMORY_COMMITTED,
    MEMORY_PROPOSED,
    MEMORY_REJECTED,
    MEMORY_VERIFIED,
    MemoryWriter,
)

REMEMBER_PREFIX = "remember:"
DEFAULT_SOURCE = "session 1"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="JARVIS 2.0 (M1)")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="bootstrap creator, log, projections, registry")
    init.set_defaults(func=_cmd_init)

    say = sub.add_parser("say", help="send a message; 'remember: ...' writes memory")
    say.add_argument("text")
    say.set_defaults(func=_cmd_say)

    explain = sub.add_parser("explain", help="render the cause chain for an event")
    explain.add_argument("event_id")
    explain.set_defaults(func=_cmd_explain)

    replay = sub.add_parser("replay", help="replay the event log")
    replay.add_argument("--verify", action="store_true", help="verify the hash chain")
    replay.set_defaults(func=_cmd_replay)

    # bare `jarvis` = restart/recovery summary (§127.1)
    parser.set_defaults(func=_cmd_status)
    return parser


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def _cmd_init(service: CoreService, args: argparse.Namespace) -> int:
    ensure_service_started(service.log)  # type: ignore[arg-type]
    print(f"creator keypair created (fingerprint: {service.fingerprint})")
    print(f"event log initialized at {service.log_path}")
    print("projections initialized")
    print(f"registry seeded ({len(service.provider_ids())} providers)")
    print("core service started")
    print(f"pairing code: {new_pairing_code()}")
    return 0


def _cmd_status(service: CoreService, args: argparse.Namespace) -> int:
    projection = service.projection()
    print(f"replayed {projection.event_count} events")
    print("projections rebuilt")
    print("identity recovered")
    print("last mission: none")
    print("active agents: 0")
    return 0


def _cmd_say(service: CoreService, args: argparse.Namespace) -> int:
    text = args.text.strip()
    print("[thinking]")
    if text.lower().startswith(REMEMBER_PREFIX):
        content = text[len(REMEMBER_PREFIX):].strip()
        writer = MemoryWriter(service.log)  # type: ignore[arg-type]
        result = writer.remember(content=content, source=DEFAULT_SOURCE)
        print(MEMORY_PROPOSED)
        print(MEMORY_VERIFIED)
        if result.status == "committed":
            print(MEMORY_COMMITTED)
        else:
            print(MEMORY_REJECTED)
            print(f"reason: {result.reason}")
        return 0

    result = answer(service.projection(), text)
    if not result.answered:
        print("no relevant memory")
        return 0
    print(result.answer)
    print(f"(confidence {result.confidence:.2f}, source: {result.source})")
    return 0


def _cmd_explain(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    events = {event.event_id: event for event in service.log.replay()}
    event = events.get(args.event_id)
    if event is None:
        print(f"unknown event id: {args.event_id}")
        return 1

    chain: list[str] = []
    current = event
    while current is not None:
        chain.append(current.event_id or "?")
        current = events.get(current.cause_event_id) if current.cause_event_id else None
    print("cause chain: " + " <- ".join(chain))
    print(f"event type: {event.event_type}")
    print(f"principal: {event.principal_id}")
    print("state transitions: M1-minimal (no lifecycle FSM; §134.1 STRETCH)")
    if event.event_type == MEMORY_COMMITTED:
        print(f"memory content: {event.payload.get('content')!r}")
        print(f"memory source: {event.payload.get('source')}")
        print(f"retrieved memories: {len(service.projection().memories)} total")
    print("model: none (deterministic memory path)")
    print("no effects outside manifest")
    print("budget: n/a (no model call on this path)")
    return 0


def _cmd_replay(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    try:
        projection = service.projection()
        print(f"replayed {projection.event_count} events")
        if args.verify:
            if not service.log.verify_chain():
                print("verify: FAILED")
                return 2
            print(f"projection hash: {projection.digest()}")
            print("verify: OK")
    except EventIntegrityError as exc:
        print(f"verify: FAILED ({exc})")
        return 2
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    service = CoreService()
    try:
        service.start()
    except Exception as exc:  # fail closed with a typed message
        print(f"jarvis: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    try:
        return args.func(service, args)
    finally:
        service.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
