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

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
