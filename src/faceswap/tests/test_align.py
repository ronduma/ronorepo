import numpy as np

from faceswap.align import ARCFACE_112, arcface_matrix, box_mask, paste_back, umeyama
from faceswap.offline import _is_local


def test_umeyama_recovers_similarity_transform():
    theta, scale, shift = 0.3, 1.7, np.array([12.0, -4.0])
    rot = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    src = ARCFACE_112.astype(np.float64)
    dst = (scale * src @ rot.T) + shift
    m = umeyama(src, dst)
    np.testing.assert_allclose(m[:, :2], scale * rot, atol=1e-4)
    np.testing.assert_allclose(m[:, 2], shift, atol=1e-3)


def test_arcface_matrix_is_identity_on_template():
    m = arcface_matrix(ARCFACE_112, 112)
    np.testing.assert_allclose(m, np.hstack([np.eye(2), np.zeros((2, 1))]), atol=1e-4)
    # 128 crops shift the template 8px right
    m128 = arcface_matrix(ARCFACE_112, 128)
    np.testing.assert_allclose(m128[:, 2], [8.0, 0.0], atol=1e-4)


def test_paste_back_only_touches_face_region():
    frame = np.zeros((200, 300, 3), np.uint8)
    crop = np.full((64, 64, 3), 255, np.uint8)
    m = np.array([[1.0, 0, -100], [0, 1.0, -50]], np.float32)  # crop covers x 100..164, y 50..114
    out = paste_back(frame, crop, box_mask(64, 4, 0), m)
    assert out[80, 130].tolist() == [255, 255, 255]
    assert out[10, 10].tolist() == [0, 0, 0]
    assert out[150, 250].tolist() == [0, 0, 0]


def test_offline_host_check():
    for host in ("127.0.0.1", "localhost", "::1", "0.0.0.0", None, "[::1]"):
        assert _is_local(host), host
    for host in ("8.8.8.8", "huggingface.co", "192.168.1.10", "example.com"):
        assert not _is_local(host), host


def test_enforce_offline_blocks_outbound_but_allows_own_listeners():
    import subprocess
    import sys

    # run in a subprocess so the socket patch doesn't leak into other tests
    code = """
import socket, urllib.request
from faceswap.offline import enforce_offline, NetworkBlocked
outside = socket.socket(); outside.bind(("127.0.0.1", 0)); outside.listen()
port = outside.getsockname()[1]   # stands in for a local proxy started before us
enforce_offline()
for fn in (lambda: socket.getaddrinfo("example.com", 443),
           lambda: socket.create_connection(("1.1.1.1", 53), timeout=1),
           lambda: socket.create_connection(("127.0.0.1", port), timeout=1)):
    try:
        fn(); raise SystemExit("not blocked")
    except NetworkBlocked:
        pass
a, b = socket.socketpair(); a.sendall(b"x"); assert b.recv(1) == b"x"
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen()
socket.create_connection(srv.getsockname(), timeout=1).close()
print("ok")
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert out.stdout.strip() == "ok", out.stderr
