"""Model manifest: every file the app needs, where to get it, and its checksum.

The app itself never downloads anything. `python -m faceswap.download` fetches
these on an internet-connected machine; copy the resulting folder to the
airgapped PC.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelFile:
    key: str
    filename: str
    description: str
    required: bool
    # (url, sha256) pairs; mirrors may ship byte-different but equivalent files
    sources: tuple[tuple[str, str], ...]
    # set when the file lives inside a zip archive at the url
    zip_member: str | None = None

    @property
    def checksums(self) -> set[str]:
        return {sha for _, sha in self.sources}


_BUFFALO_L = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
_FACEFUSION = "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0"

MODELS: dict[str, ModelFile] = {
    m.key: m
    for m in (
        ModelFile(
            key="detector",
            filename="det_10g.onnx",
            description="SCRFD-10G face detector (insightface buffalo_l)",
            required=True,
            sources=((_BUFFALO_L, "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91"),),
            zip_member="det_10g.onnx",
        ),
        ModelFile(
            key="recognizer",
            filename="w600k_r50.onnx",
            description="ArcFace R50 identity embedder (insightface buffalo_l)",
            required=True,
            sources=((_BUFFALO_L, "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43"),),
            zip_member="w600k_r50.onnx",
        ),
        ModelFile(
            key="swapper",
            filename="inswapper_128.onnx",
            description="inswapper 128px face swapper",
            required=True,
            sources=(
                (
                    "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx",
                    "e4a3f08c753cb72d04e10aa0f7dbe3deebbf39567d4ead6dce08e98aa49e16af",
                ),
                (
                    f"{_FACEFUSION}/inswapper_128.onnx",
                    "a290273ed497312095dac48cdef20feec9d5208298223dd01288ab202b54bea7",
                ),
            ),
        ),
        ModelFile(
            key="enhancer",
            filename="gfpgan_1.4.onnx",
            description="GFPGAN 1.4 face restorer (optional, sharpens swapped faces)",
            required=False,
            sources=((f"{_FACEFUSION}/gfpgan_1.4.onnx", "accc4757b26bdb89b32b4d3500d4f79c9dff97c1dd7c7104bf9dcb95e3311385"),),
        ),
    )
}


def default_models_dir() -> Path:
    env = os.environ.get("FACESWAP_MODELS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    # src/faceswap/models when running from a checkout
    return (Path(__file__).resolve().parent.parent / "models").resolve()


def model_path(models_dir: Path, key: str) -> Path:
    return models_dir / MODELS[key].filename


def missing_required(models_dir: Path) -> list[ModelFile]:
    return [m for m in MODELS.values() if m.required and not (models_dir / m.filename).is_file()]
