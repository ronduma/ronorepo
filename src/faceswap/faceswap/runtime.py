"""ONNX Runtime session factory with GPU provider auto-selection."""

from __future__ import annotations

import logging
from pathlib import Path

import onnxruntime as ort

log = logging.getLogger(__name__)

# preference order when --provider=auto
_AUTO_ORDER = ("CUDAExecutionProvider", "DmlExecutionProvider", "CoreMLExecutionProvider", "CPUExecutionProvider")
_ALIASES = {
    "cuda": "CUDAExecutionProvider",
    "directml": "DmlExecutionProvider",
    "dml": "DmlExecutionProvider",
    "coreml": "CoreMLExecutionProvider",
    "cpu": "CPUExecutionProvider",
}

_dlls_preloaded = False


def _preload_cuda_dlls() -> None:
    # onnxruntime-gpu >= 1.21 can load CUDA/cuDNN from the nvidia-* pip wheels
    global _dlls_preloaded
    if _dlls_preloaded:
        return
    _dlls_preloaded = True
    preload = getattr(ort, "preload_dlls", None)
    if preload is not None:
        try:
            preload()
        except Exception as exc:
            log.debug("ort.preload_dlls failed: %s", exc)


def resolve_providers(choice: str = "auto", device_id: int = 0) -> list:
    available = ort.get_available_providers()
    if choice == "auto":
        picked = next(p for p in _AUTO_ORDER if p in available or p == "CPUExecutionProvider")
    else:
        picked = _ALIASES.get(choice.lower(), choice)
        if picked not in available:
            raise RuntimeError(f"provider {picked} is not available in this onnxruntime build (have: {available})")

    if picked == "CUDAExecutionProvider":
        _preload_cuda_dlls()
        # DEFAULT avoids a slow exhaustive cuDNN search every time the detector input size changes
        opts = {"device_id": device_id, "cudnn_conv_algo_search": "DEFAULT"}
        return [(picked, opts), "CPUExecutionProvider"]
    if picked == "DmlExecutionProvider":
        return [(picked, {"device_id": device_id}), "CPUExecutionProvider"]
    if picked == "CPUExecutionProvider":
        return [picked]
    return [picked, "CPUExecutionProvider"]


def create_session(path: Path, providers: list) -> ort.InferenceSession:
    so = ort.SessionOptions()
    so.log_severity_level = 3
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(str(path), sess_options=so, providers=providers)
    log.info("loaded %s on %s", path.name, sess.get_providers()[0])
    return sess
