from __future__ import annotations

"""Unit tests for Vision Model Adapter (src/jarvis/multimodal/vision.py)."""

import base64
from pathlib import Path

import pytest

from jarvis.kernel.model_gateway import ProviderTransportError
from jarvis.multimodal.vision import VisionModelAdapter


@pytest.mark.anyio
async def test_vision_describe_image_bytes():
    adapter = VisionModelAdapter()
    res = await adapter.invoke(
        "vision.describe",
        "1.0.0",
        {"image_bytes": b"\x89PNG\r\n\x1a\nfake_image", "prompt": "Describe diagram"},
    )
    assert "description" in res
    assert "objects" in res
    assert res["contract"] == "vision.describe"


@pytest.mark.anyio
async def test_vision_analyze_base64():
    adapter = VisionModelAdapter()
    b64_img = base64.b64encode(b"\xff\xd8\xfffake_jpeg").decode("utf-8")
    res = await adapter.invoke(
        "vision.analyze",
        "1.0.0",
        {"image_bytes": b64_img, "query": "Find the submit button"},
    )
    assert "description" in res
    assert "objects" in res
    assert len(res["objects"]) >= 1


@pytest.mark.anyio
async def test_vision_file_path(tmp_path: Path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"sample_image_data")

    adapter = VisionModelAdapter()
    res = await adapter.invoke(
        "vision.describe",
        "1.0.0",
        {"image_path": str(img_file)},
    )
    assert "description" in res


@pytest.mark.anyio
async def test_vision_missing_image_raises_transport_error():
    adapter = VisionModelAdapter()
    with pytest.raises(ProviderTransportError) as exc_info:
        await adapter.invoke("vision.describe", "1.0.0", {"prompt": "what is this?"})
    assert "requires 'image_bytes'" in str(exc_info.value)


@pytest.mark.anyio
async def test_vision_unsupported_contract_raises_transport_error():
    adapter = VisionModelAdapter()
    with pytest.raises(ProviderTransportError) as exc_info:
        await adapter.invoke("vision.generate", "1.0.0", {"image_bytes": b"123"})
    assert "does not support contract" in str(exc_info.value)


def test_vision_health_check():
    adapter = VisionModelAdapter()
    assert adapter.health_check() is True

    broken = VisionModelAdapter(runner=lambda *args: {})
    assert broken.health_check() is False
