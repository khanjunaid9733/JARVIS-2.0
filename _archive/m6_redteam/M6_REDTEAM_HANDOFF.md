# Module 6 Red-Team → Fix Handoff (Freebuff/DeepSeek → Big Pickle)

**Branch:** `review/intent-abi-v2` @ `8519120` · **Status:** PROPOSALS — apply nothing
to `src/` until the creator approves; evidence tests are uncommitted in
`tests/review/`.

**Canonical numbering:** F1–F12 from the primary review session; F13–F15 from the
addendum session (`tests/review/test_freebuff_redteam_m6_addendum.py`). F9/F10 here
absorb addendum F10/F8 (identical findings, discovered twice — independent confirmation).

## Fix queue (smallest change first)

| # | Severity | Target | Fix | Tests to flip after fix |
|---|----------|--------|-----|--------------------------|
| F1 | CRITICAL | `tests/providers/test_openai_compatible.py` | ✅ DONE this session: constant replaced with sentinel; **creator must rotate the original key if it was ever live** (no history rewrite per AGENTS.md rule 10) | n/a |
| F8 | HIGH | `pyproject.toml`, `tests/conftest.py` | ✅ DONE this session: pytest in `[dependency-groups].dev`, hard interpreter gate exits rc=3 outside `>=3.12,<3.14` | n/a |
| F2 | HIGH | `src/jarvis/providers/openai_compatible.py:143` | Wrap `resp.json()` in `try/except ValueError → ProviderTransportError`; handle `300 <= status < 400` explicitly (httpx default is `follow_redirects=False`) | `test_evidence_empty_200_body_leaks_raw_json_decode_error`, `test_evidence_redirect_302_body_mislabels_as_adapter_error` |
| F3 | HIGH | `src/jarvis/kernel/model_gateway.py:201` | Resolve `contract_version` from the **active** binding after `_select_adapter` (fallback runs on primary's version string today) | `test_evidence_fallback_records_primary_contract_version` |
| F13 | HIGH | `src/jarvis/kernel/model_gateway.py:201-204` | `next(...)` takes the FIRST contract_id match; a provider exposing the same contract at two versions must match the version the constraint resolved (see addendum F7 test) | addendum F7 evidence test |
| F14 | HIGH | `src/jarvis/kernel/model_gateway.py` | Fallback is adapter-map-only; a `ProviderTransportError` from the primary never tries `fallback_provider_id` at runtime. Decide: exercise the fallback chain on transport failure (ADR-004/§131.4) or document static-only for M1 | addendum F9 evidence test |
| F10 | LOW | `src/jarvis/kernel/model_gateway.py:249` | Catch `pydantic.ValidationError` specifically; other exceptions → `adapter_error` (today a broken validator is retried as if the model were wrong, and its text is fed back as feedback) | addendum F8 evidence test |
| F5 | MEDIUM | `src/jarvis/kernel/registry.py:229-240` | Reject `^0.*` (require exact on 0.x); require fully numeric-dotted versions for caret; cover the addendum's version-side whitespace edge | 3 caret dialect evidence tests |
| F6 | MEDIUM | `src/jarvis/kernel/model_gateway.py:220` | Add `schema_sha256` (of `schema.model_json_schema()`) to adapter args + `ValidatedOutput` | `test_evidence_same_schema_id_two_different_schemas` |
| F4 | MEDIUM | `src/jarvis/kernel/registry.py` | Document or change re-registration precedence (currently first-registered wins forever); one NAT pinning the rule | `test_evidence_reregistered_provider_keeps_old_precedence` |
| F9 | LOW | `src/jarvis/kernel/intent.py:185` | Docstring-only: `Manifest` docstring says `manifest_sha256` does NOT cover `created_at_utc`; the code at `:449-451` hashes it. Make the docstring match the code | n/a |
| F7 | MEDIUM | spec/ADR | ✅ DONE this session: ADR-010 records the LiteLLM deferral (amends §131.11) | n/a |
| F11/F12/F15 | LOW | various | F11: add NAT "registry reconstructs after restart" when the projection module lands. F12: adapter echoes `model` into its response → `ValidatedOutput` (forward-compat for ADR-005 `actor_model`). F15: caret whitespace asymmetry on the version side (addendum F11 test) | addendum F11 evidence test |

## Flip protocol

Every evidence test in `tests/review/` asserts CURRENT (defective) behavior with a
`SHOULD` comment. When a fix lands in `src/`, flip the corresponding assertion to the
SHOULD form and move the file out of `tests/review/` into the regular suite (or delete
and re-cover properly). Evidence tests that keep passing unchanged mean the fix is
incomplete.

## State of this worktree

Uncommitted, split by ownership:
- **Freebuff (review-authorized):** `tests/review/` (both evidence files), `pyproject.toml`, `tests/conftest.py`, `tests/providers/test_openai_compatible.py`, `docs/DECISIONS.md` (ADR-010), this handoff.
- **Big Pickle (post-approval):** all `src/` changes in the table above.
- Suite: **123 passed, 0 failed, 0 `[trio]`** under the pinned interpreter (Python 3.12.6 venv; conftest guard active).
