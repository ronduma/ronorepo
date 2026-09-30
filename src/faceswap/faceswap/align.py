"""5-point landmark alignment helpers."""

from __future__ import annotations

import cv2
import numpy as np

# insightface ArcFace template for a 112x112 crop
ARCFACE_112 = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]],
    dtype=np.float32,
)

# FFHQ template (normalised) used by GFPGAN
FFHQ = np.array(
    [[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904], [0.39308822, 0.72541100], [0.61150205, 0.72490465]],
    dtype=np.float32,
)


def umeyama(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Least-squares similarity transform (rotation, uniform scale, translation) mapping src -> dst.

    Returns a 2x3 affine matrix. Same maths as skimage's SimilarityTransform.estimate.
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    num, dim = src.shape
    src_mean, dst_mean = src.mean(0), dst.mean(0)
    src_d, dst_d = src - src_mean, dst - dst_mean
    a = dst_d.T @ src_d / num

    d = np.ones(dim)
    if np.linalg.det(a) < 0:
        d[-1] = -1
    u, s, vt = np.linalg.svd(a)
    rank = np.linalg.matrix_rank(a)
    t = np.eye(dim + 1)
    if rank == 0:
        raise ValueError("degenerate landmarks")
    if rank == dim - 1 and np.linalg.det(u) * np.linalg.det(vt) <= 0:
        dd = d.copy()
        dd[-1] = -1
        t[:dim, :dim] = u @ np.diag(dd) @ vt
    elif rank == dim - 1:
        t[:dim, :dim] = u @ vt
    else:
        t[:dim, :dim] = u @ np.diag(d) @ vt

    scale = (s @ d) / src_d.var(0).sum()
    t[:dim, dim] = dst_mean - scale * (t[:dim, :dim] @ src_mean)
    t[:dim, :dim] *= scale
    return t[:2].astype(np.float32)


def arcface_matrix(kps: np.ndarray, size: int) -> np.ndarray:
    """Matrix mapping image space -> an arcface-style crop of `size` (112 for recognition, 128 for inswapper)."""
    if size % 112 == 0:
        ratio, diff_x = size / 112.0, 0.0
    else:
        ratio, diff_x = size / 128.0, 8.0 * size / 128.0
    dst = ARCFACE_112 * ratio
    dst[:, 0] += diff_x
    return umeyama(kps, dst)


def ffhq_matrix(kps: np.ndarray, size: int) -> np.ndarray:
    return umeyama(kps, FFHQ * size)


def warp(img: np.ndarray, m: np.ndarray, size: int) -> np.ndarray:
    return cv2.warpAffine(img, m, (size, size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def paste_back(frame: np.ndarray, crop: np.ndarray, crop_mask: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Inverse-warp `crop` onto `frame` using a soft float mask in crop space (values 0..1).

    Only the bounding box of the face is touched, so this stays fast on large photos.
    """
    h, w = frame.shape[:2]
    size = crop.shape[0]
    inv = cv2.invertAffineTransform(m)

    corners = np.array([[0, 0, 1], [size, 0, 1], [0, size, 1], [size, size, 1]], dtype=np.float32) @ inv.T
    x0, y0 = np.floor(corners.min(0)).astype(int) - 2
    x1, y1 = np.ceil(corners.max(0)).astype(int) + 2
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
    if x1 <= x0 or y1 <= y0:
        return frame

    inv_roi = inv.copy()
    inv_roi[:, 2] -= (x0, y0)
    roi_size = (x1 - x0, y1 - y0)
    warped = cv2.warpAffine(crop, inv_roi, roi_size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mask = cv2.warpAffine(crop_mask.astype(np.float32), inv_roi, roi_size, flags=cv2.INTER_LINEAR, borderValue=0.0)
    mask = np.clip(mask, 0.0, 1.0)[..., None]

    out = frame.copy()
    roi = out[y0:y1, x0:x1].astype(np.float32)
    out[y0:y1, x0:x1] = np.clip(mask * warped.astype(np.float32) + (1.0 - mask) * roi, 0, 255).astype(np.uint8)
    return out


def box_mask(size: int, border: int | tuple[int, int, int, int], sigma: float) -> np.ndarray:
    """Soft square mask: zero `border` px at the edges (int, or top/right/bottom/left), gaussian-feathered."""
    top, right, bottom, left = (border,) * 4 if isinstance(border, int) else border
    mask = np.zeros((size, size), dtype=np.float32)
    mask[top : size - bottom, left : size - right] = 1.0
    if sigma > 0:
        mask = cv2.GaussianBlur(mask, (0, 0), sigma)
    return mask
