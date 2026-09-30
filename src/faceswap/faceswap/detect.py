"""SCRFD face detector (det_10g.onnx from insightface buffalo_l)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .runtime import create_session


@dataclass
class Face:
    bbox: np.ndarray  # x1, y1, x2, y2
    kps: np.ndarray  # 5x2: left eye, right eye, nose, left mouth, right mouth
    score: float
    embedding: np.ndarray | None = field(default=None, repr=False)  # L2-normalised ArcFace vector


def _nms(dets: np.ndarray, thresh: float) -> list[int]:
    x1, y1, x2, y2, scores = dets.T
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1 + 1) * np.maximum(0.0, yy2 - yy1 + 1)
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[1:][iou <= thresh]
    return keep


class Detector:
    input_mean = 127.5
    input_std = 128.0
    strides = (8, 16, 32)
    num_anchors = 2

    def __init__(self, path: Path, providers: list):
        self.session = create_session(path, providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]
        if len(self.output_names) != 9:
            raise RuntimeError(f"{path.name}: expected an SCRFD model with keypoints (9 outputs)")
        self._anchor_cache: dict[tuple[int, int, int], np.ndarray] = {}

    def _anchors(self, h: int, w: int, stride: int) -> np.ndarray:
        key = (h, w, stride)
        if key not in self._anchor_cache:
            centers = np.stack(np.mgrid[:h, :w][::-1], axis=-1).astype(np.float32)
            centers = (centers * stride).reshape(-1, 2)
            self._anchor_cache[key] = np.repeat(centers, self.num_anchors, axis=0)
        return self._anchor_cache[key]

    def detect(self, img: np.ndarray, det_size: int = 640, threshold: float = 0.5, nms_thresh: float = 0.4) -> list[Face]:
        h, w = img.shape[:2]
        # letterbox into a det_size square, padding bottom/right
        scale = min(det_size / h, det_size / w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        canvas = np.zeros((det_size, det_size, 3), dtype=np.uint8)
        canvas[:nh, :nw] = cv2.resize(img, (nw, nh))
        blob = cv2.dnn.blobFromImage(
            canvas, 1.0 / self.input_std, (det_size, det_size), (self.input_mean,) * 3, swapRB=True
        )
        outs = self.session.run(self.output_names, {self.input_name: blob})
        outs = [o[0] if o.ndim == 3 else o for o in outs]

        all_scores, all_boxes, all_kps = [], [], []
        for i, stride in enumerate(self.strides):
            scores = outs[i].reshape(-1)
            boxes = outs[i + 3] * stride
            kps = outs[i + 6] * stride
            anchors = self._anchors(det_size // stride, det_size // stride, stride)
            pos = np.where(scores >= threshold)[0]
            if pos.size == 0:
                continue
            a = anchors[pos]
            b = boxes[pos]
            all_boxes.append(np.stack([a[:, 0] - b[:, 0], a[:, 1] - b[:, 1], a[:, 0] + b[:, 2], a[:, 1] + b[:, 3]], axis=-1))
            k = kps[pos].reshape(-1, 5, 2)
            all_kps.append(a[:, None, :] + k)
            all_scores.append(scores[pos])

        if not all_scores:
            return []
        scores = np.concatenate(all_scores)
        boxes = np.concatenate(all_boxes) / scale
        kpss = np.concatenate(all_kps) / scale

        keep = _nms(np.hstack([boxes, scores[:, None]]), nms_thresh)
        faces = []
        for i in keep:
            box = boxes[i].copy()
            box[[0, 2]] = box[[0, 2]].clip(0, w)
            box[[1, 3]] = box[[1, 3]].clip(0, h)
            faces.append(Face(bbox=box.astype(np.float32), kps=kpss[i].astype(np.float32), score=float(scores[i])))
        # reading order: left to right, so face numbers match what you see
        faces.sort(key=lambda f: (f.bbox[0] + f.bbox[2]) / 2)
        return faces
