"""ArcFace identity embedder (w600k_r50.onnx)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .align import arcface_matrix, warp
from .runtime import create_session


class Recognizer:
    size = 112
    input_mean = 127.5
    input_std = 127.5

    def __init__(self, path: Path, providers: list):
        self.session = create_session(path, providers)
        self.input_name = self.session.get_inputs()[0].name

    def embed(self, img: np.ndarray, kps: np.ndarray) -> np.ndarray:
        crop = warp(img, arcface_matrix(kps, self.size), self.size)
        blob = cv2.dnn.blobFromImage(crop, 1.0 / self.input_std, (self.size, self.size), (self.input_mean,) * 3, swapRB=True)
        emb = self.session.run(None, {self.input_name: blob})[0][0]
        return (emb / np.linalg.norm(emb)).astype(np.float32)
