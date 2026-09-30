"""Loads all models once and exposes detect / swap operations."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from .detect import Detector, Face
from .enhance import Enhancer
from .models import missing_required, model_path
from .recognize import Recognizer
from .runtime import resolve_providers
from .swap import Swapper

log = logging.getLogger(__name__)


class Engine:
    def __init__(self, models_dir: Path, provider: str = "auto", device_id: int = 0):
        missing = missing_required(models_dir)
        if missing:
            names = ", ".join(m.filename for m in missing)
            raise FileNotFoundError(
                f"missing model files in {models_dir}: {names}\n"
                "run `python -m faceswap.download` on a machine with internet and copy the folder over"
            )
        providers = resolve_providers(provider, device_id)
        self.detector = Detector(model_path(models_dir, "detector"), providers)
        self.recognizer = Recognizer(model_path(models_dir, "recognizer"), providers)
        self.swapper = Swapper(model_path(models_dir, "swapper"), providers)
        enhancer_path = model_path(models_dir, "enhancer")
        self.enhancer = Enhancer(enhancer_path, providers) if enhancer_path.is_file() else None
        self.active_provider = self.swapper.session.get_providers()[0]
        # onnxruntime sessions are thread-safe, but serialising keeps GPU memory predictable
        self._lock = threading.Lock()

    def detect(self, img: np.ndarray, thorough: bool = False) -> list[Face]:
        with self._lock:
            # bigger input finds small faces in group shots / wide photos
            det_size = 640
            if thorough:
                det_size = int(min(max(img.shape[:2]), 1920) // 32 * 32) or 640
                det_size = max(det_size, 640)
            return self.detector.detect(img, det_size=det_size)

    def embedding(self, img: np.ndarray, face: Face) -> np.ndarray:
        if face.embedding is None:
            with self._lock:
                face.embedding = self.recognizer.embed(img, face.kps)
        return face.embedding

    def swap(self, target: np.ndarray, jobs: list[tuple[Face, np.ndarray, Face]], enhance: bool = False, blend: float = 0.8) -> np.ndarray:
        """jobs: (target_face, source_image, source_face) triples, applied in order."""
        embeddings = [self.embedding(src_img, src_face) for _, src_img, src_face in jobs]
        out = target.copy()
        with self._lock:
            for (tface, _, _), emb in zip(jobs, embeddings):
                out = self.swapper.swap(out, tface.kps, emb)
                if enhance and self.enhancer is not None:
                    out = self.enhancer.enhance(out, tface.kps, blend)
        return out
