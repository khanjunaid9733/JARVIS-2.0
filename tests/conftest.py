"""Shared pytest configuration.

The async tests are marked with ``pytest.mark.anyio``. Without an explicit
``anyio_backend`` fixture, the anyio plugin's default backend set is
environment-dependent and can parametrize the suite across both ``asyncio``
and ``trio``. trio is not a JARVIS dependency, so any environment that
includes it in the matrix fails at fixture setup with
``ModuleNotFoundError: No module named 'trio'`` — making plain ``pytest``
green or red depending on the machine.

Pin the backend to ``asyncio`` so the async suite is deterministic across
environments and requires no ``trio`` install.
"""

import sys

import pytest


# Red-team finding F8: a hard interpreter gate, not a packaging convention.
# `requires-python = ">=3.12,<3.14"` (ADR-008) constrains resolution, but a
# pytest installed outside the project venv ignores it and can run the suite
# under an unsupported interpreter. Fail fast with the remedy.
if not (3, 12) <= sys.version_info[:2] < (3, 14):
    pytest.exit(
        f"FATAL: pytest is running under Python {sys.version.split()[0]}, "
        "outside requires-python '>=3.12,<3.14' (ADR-008). Run the suite "
        "through the project venv: 'uv sync' then 'uv run python -m pytest'.",
        returncode=3,
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"
