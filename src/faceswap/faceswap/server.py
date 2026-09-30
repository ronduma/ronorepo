"""Local-only HTTP API + static UI."""

from __future__ import annotations

import base64
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .detect import Face
from .engine import Engine

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 60_000_000


@dataclass
class StoredImage:
    img: np.ndarray
    faces: list[Face]
    name: str


class ImageStore:
    """Small in-memory LRU of uploaded images and their detected faces."""

    def __init__(self, capacity: int = 32):
        self.capacity = capacity
        self._items: OrderedDict[str, StoredImage] = OrderedDict()
        self._lock = threading.Lock()

    def put(self, item: StoredImage) -> str:
        key = uuid.uuid4().hex
        with self._lock:
            self._items[key] = item
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
        return key

    def get(self, key: str) -> StoredImage:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                raise HTTPException(404, "image expired or unknown; upload it again")
            self._items.move_to_end(key)
            return item


def decode_image(data: bytes) -> np.ndarray:
    # IMREAD_COLOR honours EXIF orientation, drops alpha and expands greyscale
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(415, "could not read that file as an image (jpg, png, webp, bmp, tiff)")
    if img.shape[0] * img.shape[1] > MAX_PIXELS:
        raise HTTPException(413, "image is too large")
    return img


def face_thumb(img: np.ndarray, face: Face, size: int = 160) -> str:
    x1, y1, x2, y2 = face.bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half = max(x2 - x1, y2 - y1) * 0.75
    h, w = img.shape[:2]
    l, t = int(max(cx - half, 0)), int(max(cy - half, 0))
    r, b = int(min(cx + half, w)), int(min(cy + half, h))
    crop = img[t:b, l:r]
    scale = size / max(crop.shape[:2])
    if scale < 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


class SwapPair(BaseModel):
    target_face: int = Field(ge=0)
    source_id: str
    source_face: int = Field(ge=0)


class SwapRequest(BaseModel):
    target_id: str
    swaps: list[SwapPair] = Field(min_length=1)
    enhance: bool = False
    enhance_blend: float = Field(default=0.8, ge=0.0, le=1.0)
    format: str = Field(default="png", pattern="^(png|jpg)$")


def create_app(engine: Engine, models_dir: Path) -> FastAPI:
    app = FastAPI(title="faceswap", docs_url=None, redoc_url=None, openapi_url=None)
    store = ImageStore()

    @app.get("/api/status")
    def status():
        return {
            "provider": engine.active_provider,
            "gpu": engine.active_provider != "CPUExecutionProvider",
            "enhancer": engine.enhancer is not None,
            "models_dir": str(models_dir),
        }

    @app.post("/api/images")
    async def upload(file: UploadFile = File(...), thorough: bool = Form(False)):
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file is larger than 64 MB")
        img = decode_image(data)
        faces = engine.detect(img, thorough=thorough)
        key = store.put(StoredImage(img=img, faces=faces, name=file.filename or "image"))
        h, w = img.shape[:2]
        return {
            "id": key,
            "name": file.filename,
            "width": w,
            "height": h,
            "faces": [
                {"index": i, "bbox": [round(float(v), 1) for v in f.bbox], "score": round(f.score, 3), "thumb": face_thumb(img, f)}
                for i, f in enumerate(faces)
            ],
        }

    @app.get("/api/images/{key}/preview")
    def preview(key: str):
        # served from the decoded pixels so face boxes line up even for EXIF-rotated photos
        ok, buf = cv2.imencode(".jpg", store.get(key).img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return Response(buf.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

    @app.post("/api/swap")
    def swap(req: SwapRequest):
        target = store.get(req.target_id)
        jobs = []
        seen: set[int] = set()
        for pair in req.swaps:
            if pair.target_face >= len(target.faces):
                raise HTTPException(400, f"target face #{pair.target_face + 1} does not exist")
            if pair.target_face in seen:
                raise HTTPException(400, f"target face #{pair.target_face + 1} is assigned twice")
            seen.add(pair.target_face)
            src = store.get(pair.source_id)
            if pair.source_face >= len(src.faces):
                raise HTTPException(400, f"replacement face #{pair.source_face + 1} does not exist")
            jobs.append((target.faces[pair.target_face], src.img, src.faces[pair.source_face]))

        out = engine.swap(target.img, jobs, enhance=req.enhance, blend=req.enhance_blend)
        if req.format == "jpg":
            ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 95])
            media = "image/jpeg"
        else:
            ok, buf = cv2.imencode(".png", out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            media = "image/png"
        return Response(buf.tobytes(), media_type=media, headers={"Cache-Control": "no-store"})

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
