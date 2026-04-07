"""SocketBuilder for creating .socket unit files."""

from __future__ import annotations

from typing import Self

from systemd_client.builders._base import _BaseBuilder
from systemd_client.enums import UnitType

_LISTEN_KEYS = frozenset({
    "ListenStream", "ListenDatagram", "ListenSequentialPacket", "ListenFIFO",
})


class SocketBuilder(_BaseBuilder):
    """Fluent builder for systemd socket unit files."""

    def __init__(self, name: str, *, template: bool = False) -> None:
        super().__init__(name, UnitType.SOCKET, template=template)

    # ── [Socket] section ────────────────────────────────────────

    def listen_stream(self, addr: int | str) -> Self:
        self._set(self._type_section, "ListenStream", str(addr))
        return self

    def listen_datagram(self, addr: int | str) -> Self:
        self._set(self._type_section, "ListenDatagram", str(addr))
        return self

    def listen_sequential_packet(self, addr: int | str) -> Self:
        self._set(self._type_section, "ListenSequentialPacket", str(addr))
        return self

    def listen_fifo(self, path: str) -> Self:
        self._set(self._type_section, "ListenFIFO", path)
        return self

    def accept(self, val: bool) -> Self:
        self._set(self._type_section, "Accept", "true" if val else "false")
        return self

    def socket_user(self, name: str) -> Self:
        self._set(self._type_section, "SocketUser", name)
        return self

    def socket_group(self, name: str) -> Self:
        self._set(self._type_section, "SocketGroup", name)
        return self

    def socket_mode(self, mode: str) -> Self:
        self._set(self._type_section, "SocketMode", mode)
        return self

    def service(self, name: str) -> Self:
        self._set(self._type_section, "Service", name)
        return self

    def max_connections(self, n: int) -> Self:
        self._set(self._type_section, "MaxConnections", str(n))
        return self

    def keep_alive(self, val: bool) -> Self:
        self._set(self._type_section, "KeepAlive", "true" if val else "false")
        return self

    # ── Validation ──────────────────────────────────────────────

    def _validate(self) -> None:
        errors: list[str] = []

        has_listen = any(k in self._type_section for k in _LISTEN_KEYS)
        if not has_listen:
            errors.append(
                "At least one listen directive is required "
                "(ListenStream, ListenDatagram, etc.)"
            )

        self._raise_validation(errors)
