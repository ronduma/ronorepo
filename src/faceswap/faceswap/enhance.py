"""GFPGAN 1.4 face restoration, applied to the swapped face only."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .align import box_mask, ffhq_matrix, paste_back, warp
from .runtime import create_session


class Enhancer:
    size = 512

    def __init__(self, path: Path, providers: list):
        self.session = create_session(path, providers)
        self.input_name = self.session.get_inputs()[0].name
        self.mask = box_mask(self.size, border=38, sigma=19.0)

    def enhance(self, frame: np.ndarray, kps: np.ndarray, blend: float = 0.8) -> np.ndarray:
        m = ffhq_matrix(kps, self.size)
        crop = warp(frame, m, self.size)
        x = crop[:, :, ::-1].astype(np.float32) / 255.0
        x = ((x - 0.5) / 0.5).transpose(2, 0, 1)[None]
        y = self.session.run(None, {self.input_name: np.ascontiguousarray(x)})[0][0]
        y = ((np.clip(y, -1.0, 1.0) + 1.0) / 2.0).transpose(1, 2, 0)
        restored = np.clip(y * 255.0, 0, 255).astype(np.uint8)[:, :, ::-1]
        return paste_back(frame, np.ascontiguousarray(restored), self.mask * float(np.clip(blend, 0.0, 1.0)), m)
