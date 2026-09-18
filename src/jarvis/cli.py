from __future__ import annotations

"""`jarvis` command-line interface (module 11, spec §127.1 / §134.1).

MUST subcommands: `init`, `say`, `explain`, plus `replay --verify` and bare
`jarvis` (restart/recovery summary). Every command is a one-shot process over
the durable store at `$JARVIS_HOME` (default `~/.jarvis`); there is no daemon
in M1 (disclosed — `core service started` denotes the bootstrapped service
context, recorded as a `system.service_started` event).

Output lines follow §127.1 so the acceptance sequence is directly observable.
Deviations from the §127.1 transcript are disclosed:
- `say` answers deterministically/extractively when no model backend is
  configured; with `JARVIS_MODEL_API_KEY` + `JARVIS_MODEL_BASE_URL` set, the
  question is routed through the ModelGateway (module 15, STRETCH M1.1) and
  falls back to the deterministic answer on any typed failure (model calls
  are recorded as `question.asked` events; the offline acceptance path
  records nothing, so §127.1 event counts are unchanged);
- `explain` renders the full cause chain + state transitions + model/budget
  provenance via the module-17 renderer (STRETCH M1.1, §134.1).
"""

import argparse
import asyncio
import os
import sys
from typing import Sequence

from .bootstrap import CoreService, ensure_service_started, new_pairing_code
from .kernel.event_log import EventIntegrityError
from .kernel.explain import explain_event
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

    recall = sub.add_parser(
        "recall",
        help="deterministic recall over committed memories + episodic traces (M2.1)",
    )
    recall.add_argument("query")
    recall.set_defaults(func=_cmd_recall)

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


# ---------------------------------------------------------------------------
# model-backed question path (STRETCH M1.1, module 15)
# ---------------------------------------------------------------------------

# Current Groq chat model as of M1.1 (the module-6 adapter default,
# llama-3.3-70b-versatile, is decommissioned). Overridable per machine via
# JARVIS_MODEL_NAME; recorded as provenance on question.asked.
DEFAULT_MODEL_NAME = "openai/gpt-oss-120b"


def _model_name() -> str:
    return os.environ.get("JARVIS_MODEL_NAME") or DEFAULT_MODEL_NAME


def _build_model_gateway(service: CoreService):
    """Return a ready ModelGateway when the production backend is configured,
    else None (deterministic offline path, §127.1 unchanged).

    Reads `JARVIS_MODEL_API_KEY` / `JARVIS_MODEL_BASE_URL` (module-6 adapter)
    and `JARVIS_MODEL_NAME` (M1.1 model selection, default `DEFAULT_MODEL_NAME`),
    re-binds the seeded `model.adapter` metadata to the real backend via
    `register_groq_provider` (module-6 production seam; provider SET unchanged
    — the in-memory registry gains no new provider, so the §127.1 registry
    invariant holds), and wires `ModelGateway` on the service registry.
    """
    if not (
        os.environ.get("JARVIS_MODEL_API_KEY")
        and os.environ.get("JARVIS_MODEL_BASE_URL")
    ):
        return None
    registry = service.registry
    if registry is None:
        return None
    try:
        from .kernel.model_gateway import ModelGateway
        from .kernel.model_gateway import register_groq_provider
        from .providers.openai_compatible import OpenAICompatibleAdapter

        register_groq_provider(registry)
        adapter = OpenAICompatibleAdapter(model=_model_name())
    except Exception:
        return None
    return ModelGateway(resolver=registry, adapters={"model.adapter": adapter})


def _answer_question(service: CoreService, text: str):
    """Route the question through the gateway when configured (module 15);
    otherwise the deterministic extractive answer (module 11, unchanged)."""
    from .kernel.model_answer import answer_question

    gateway = _build_model_gateway(service)
    if gateway is None:
        return answer(service.projection(), text)
    return asyncio.run(
        answer_question(
            service.projection(),
            text,
            gateway=gateway,
            log=service.log,  # type: ignore[arg-type]
            model_name=_model_name(),
        )
    )


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

    result = _answer_question(service, text)
    if not result.answered:
        print("no relevant memory")
        return 0
    if getattr(result, "used_model", False):
        print(result.answer)
        print(f"(model-grounded; confidence {result.confidence:.2f}, provider: {result.provider_id})")
        return 0
    print(result.answer)
    print(f"(confidence {result.confidence:.2f}, source: {result.source})")
    return 0


def _cmd_explain(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    explanation = explain_event(service.log, service.projection(), args.event_id)
    if explanation is None:
        print(f"unknown event id: {args.event_id}")
        return 1

    print("cause chain: " + " <- ".join(link.event_id for link in explanation.chain))
    print(f"event type: {explanation.event_type}")
    print(f"principal: {explanation.principal_id}")
    if explanation.lifecycle_state is not None:
        detail = ""
        if explanation.lifecycle_transitions:
            detail = f" ({', '.join(explanation.lifecycle_transitions)})"
        print(f"state transitions: {explanation.lifecycle_state}{detail}")
    else:
        print("state transitions: none (no mission events for this stream)")

    if explanation.model_provenance is not None:
        p = explanation.model_provenance
        provider = p.get("provider_id") or "n/a"
        contract = (
            f"{p.get('contract_id')}@{p.get('contract_version')}"
            if p.get("contract_id")
            else "n/a"
        )
        print(f"model: {provider} ({contract})")
        if p.get("model_name"):
            print(f"model name: {p.get('model_name')}")
        path = p.get("fallback", "n/a")
        if p.get("failure_reason"):
            path = f"{path} (failure: {p.get('failure_reason')})"
        print(f"answer path: {path}")
        if explanation.recalled_memories:
            top = explanation.recalled_memories[0]
            print(
                f"retrieved memories: {len(explanation.recalled_memories)} "
                f"(top score {top.score:.2f})"
            )
    elif explanation.event_type == MEMORY_COMMITTED:
        print(f"memory content: {explanation.memory_content!r}")
        print(f"memory source: {explanation.memory_source}")
        print(f"retrieved memories: {len(service.projection().memories)} total")
        print("model: none (deterministic memory path)")

    if explanation.capability_check_count:
        print(f"capability checks: {explanation.capability_check_count}")
    else:
        print("capability checks: none recorded")
    if explanation.effect_count:
        print(f"effects executed within manifest: {explanation.effect_count}")
    else:
        print("no effects outside manifest")

    if explanation.budget is not None:
        b = explanation.budget
        print(
            f"budget: {b.model_calls} model call(s), {b.spent_tokens} tokens "
            f"accounted of allocation {b.allocation}"
        )
    else:
        print("budget: n/a (no model calls recorded)")
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


def _cmd_recall(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    from .kernel.memory_api import Memory

    hits = Memory(log=service.log).recall(args.query, limit=3)
    if not hits:
        print("no relevant memory")
        return 0
    for hit in hits:
        content = " ".join(hit.content.split())
        print(f"{hit.event_id}  {hit.score:.2f}  [{hit.source}]  {content}")
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
