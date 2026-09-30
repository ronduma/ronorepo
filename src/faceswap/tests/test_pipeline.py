"""End-to-end tests against the real models. Skipped when models aren't downloaded.

Set FACESWAP_TEST_IMAGE to a photo with 2+ faces to run them.
"""

import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from faceswap.models import default_models_dir, missing_required

MODELS_DIR = default_models_dir()
IMAGE = os.environ.get("FACESWAP_TEST_IMAGE")

pytestmark = pytest.mark.skipif(
    bool(missing_required(MODELS_DIR)) or not IMAGE or not Path(IMAGE).is_file(),
    reason="needs downloaded models and FACESWAP_TEST_IMAGE",
)


@pytest.fixture(scope="module")
def engine():
    from faceswap.engine import Engine

    return Engine(MODELS_DIR, provider=os.environ.get("FACESWAP_TEST_PROVIDER", "auto"))


@pytest.fixture(scope="module")
def image():
    return cv2.imread(IMAGE)


def test_detects_every_face(engine, image):
    faces = engine.detect(image)
    assert len(faces) >= 2
    centers = [(f.bbox[0] + f.bbox[2]) / 2 for f in faces]
    assert centers == sorted(centers), "faces are numbered left to right"


def test_swap_transfers_identity_to_the_chosen_face_only(engine, image):
    faces = engine.detect(image)
    target, source = faces[0], faces[1]
    before = [engine.embedding(image, f) for f in faces]

    out = engine.swap(image, [(target, image, source)])

    after = engine.detect(out)
    assert len(after) == len(faces)
    new = [engine.embedding(out, f) for f in after]
    assert float(new[0] @ before[1]) > 0.5, "swapped face should look like the source"
    assert float(new[0] @ before[0]) < 0.3, "swapped face should no longer look like the original"
    for i in range(2, len(faces)):
        assert float(new[i] @ before[i]) > 0.9, f"face {i} should be untouched"


def test_http_flow(engine, image):
    from fastapi.testclient import TestClient

    from faceswap.server import create_app

    client = TestClient(create_app(engine, MODELS_DIR))
    ok, buf = cv2.imencode(".jpg", image)
    img_bytes = buf.tobytes()

    tgt = client.post("/api/images", files={"file": ("target.jpg", img_bytes, "image/jpeg")}).json()
    src = client.post("/api/images", files={"file": ("source.jpg", img_bytes, "image/jpeg")}).json()
    assert len(tgt["faces"]) >= 2 and tgt["faces"][0]["thumb"].startswith("data:image/jpeg")

    res = client.post(
        "/api/swap",
        json={"target_id": tgt["id"], "swaps": [{"target_face": 0, "source_id": src["id"], "source_face": 1}]},
    )
    assert res.status_code == 200 and res.headers["content-type"] == "image/png"
    out = cv2.imdecode(np.frombuffer(res.content, np.uint8), cv2.IMREAD_COLOR)
    assert out.shape == image.shape

    bad = client.post(
        "/api/swap",
        json={"target_id": tgt["id"], "swaps": [{"target_face": 99, "source_id": src["id"], "source_face": 0}]},
    )
    assert bad.status_code == 400
    assert client.post("/api/images", files={"file": ("x.txt", b"nope", "text/plain")}).status_code == 415
