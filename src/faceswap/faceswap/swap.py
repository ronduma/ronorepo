"""inswapper_128 identity swap + paste back."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnx
from onnx import numpy_helper

from .align import arcface_matrix, box_mask, paste_back, warp
from .runtime import create_session


def _load_emap(path: Path) -> np.ndarray:
    # the swapper expects the ArcFace embedding projected through a matrix stored
    # as the graph's last initializer; cache it next to the model after first read
    cache = path.with_suffix(".emap.npy")
    if cache.is_file() and cache.stat().st_mtime >= path.stat().st_mtime:
        return np.load(cache)
    emap = numpy_helper.to_array(onnx.load(str(path)).graph.initializer[-1]).astype(np.float32)
    try:
        np.save(cache, emap)
    except OSError:
        pass
    return emap


class Swapper:
    size = 128

    def __init__(self, path: Path, providers: list):
        self.session = create_session(path, providers)
        inputs = self.session.get_inputs()
        self.target_name, self.source_name = inputs[0].name, inputs[1].name
        self.emap = _load_emap(path)
        # extra top padding keeps the source's hairline from bleeding onto the forehead
        pad = self.size // 20
        self.mask = box_mask(self.size, border=(self.size // 8, pad, pad, pad), sigma=self.size / 50)

    def latent(self, embedding: np.ndarray) -> np.ndarray:
        lat = embedding.reshape(1, -1) @ self.emap
        return (lat / np.linalg.norm(lat)).astype(np.float32)

    def swap(self, frame: np.ndarray, target_kps: np.ndarray, source_embedding: np.ndarray) -> np.ndarray:
        m = arcface_matrix(target_kps, self.size)
        crop = warp(frame, m, self.size)
        blob = cv2.dnn.blobFromImage(crop, 1.0 / 255.0, (self.size, self.size), (0.0, 0.0, 0.0), swapRB=True)
        pred = self.session.run(None, {self.target_name: blob, self.source_name: self.latent(source_embedding)})[0]
        fake = np.clip(pred[0].transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)[:, :, ::-1]
        return paste_back(frame, np.ascontiguousarray(fake), self.mask, m)
