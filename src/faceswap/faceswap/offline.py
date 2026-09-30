"""Process-wide network kill switch.

Once `enforce_offline()` runs, resolving a hostname or opening a connection
anywhere raises, except loopback connections to sockets this process itself is
listening on (asyncio needs those on Windows). That also stops traffic being
relayed through a local proxy or VPN client. Binding the local web server still
works, so the UI stays reachable from this PC.
"""

from __future__ import annotations

import ipaddress
import os
import socket

_LOCAL_NAMES = {"localhost", "", "0.0.0.0", "::"}


class NetworkBlocked(OSError):
    pass


def _is_local(host: object) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode(errors="ignore")
    if not isinstance(host, str):
        return False
    host = host.strip("[]").split("%", 1)[0].lower()
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


_PROXY_VARS = ("http_proxy", "https_proxy", "all_proxy", "ftp_proxy", "no_proxy")


def enforce_offline() -> None:
    if getattr(socket, "_faceswap_offline", False):
        return

    for var in _PROXY_VARS:
        os.environ.pop(var, None)
        os.environ.pop(var.upper(), None)

    own_ports: set[int] = set()

    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_sendto = socket.socket.sendto
    real_listen = socket.socket.listen

    def getaddrinfo(host, *args, **kwargs):
        if not _is_local(host):
            raise NetworkBlocked(f"airgapped mode: refusing to resolve {host!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    def _check(sock: socket.socket, address) -> None:
        if sock.family not in (socket.AF_INET, socket.AF_INET6):
            return
        host, port = address[0], address[1]
        if not _is_local(host) or port not in own_ports:
            raise NetworkBlocked(f"airgapped mode: refusing to connect to {host}:{port}")

    def listen(self, *args):
        result = real_listen(self, *args)
        if self.family in (socket.AF_INET, socket.AF_INET6):
            own_ports.add(self.getsockname()[1])
        return result

    def connect(self, address):
        _check(self, address)
        return real_connect(self, address)

    def connect_ex(self, address):
        _check(self, address)
        return real_connect_ex(self, address)

    def sendto(self, data, *args):
        _check(self, args[-1])
        return real_sendto(self, data, *args)

    socket.getaddrinfo = getaddrinfo
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.socket.sendto = sendto
    socket.socket.listen = listen
    socket._faceswap_offline = True  # type: ignore[attr-defined]
