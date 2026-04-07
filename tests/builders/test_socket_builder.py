"""Tests for SocketBuilder."""

import pytest

from systemd_client.builders import SocketBuilder
from systemd_client.enums import UnitType
from systemd_client.exceptions import UnitFileValidationError


class TestSocketBuilder:
    def test_listen_stream_port(self):
        unit = SocketBuilder("app").listen_stream(8080).build()
        assert unit.name == "app.socket"
        assert unit.unit_type == UnitType.SOCKET
        assert "[Socket]" in unit.content
        assert "ListenStream=8080" in unit.content

    def test_listen_stream_path(self):
        unit = SocketBuilder("app").listen_stream("/run/app.sock").build()
        assert "ListenStream=/run/app.sock" in unit.content

    def test_listen_datagram(self):
        unit = SocketBuilder("app").listen_datagram(5000).build()
        assert "ListenDatagram=5000" in unit.content

    def test_full_socket(self):
        unit = (
            SocketBuilder("app")
            .description("App socket")
            .listen_stream(8080)
            .accept(False)
            .socket_user("appuser")
            .socket_group("appgroup")
            .socket_mode("0660")
            .service("app.service")
            .max_connections(100)
            .wanted_by("sockets.target")
            .build()
        )
        assert "ListenStream=8080" in unit.content
        assert "Accept=false" in unit.content
        assert "SocketUser=appuser" in unit.content
        assert "SocketGroup=appgroup" in unit.content
        assert "SocketMode=0660" in unit.content
        assert "Service=app.service" in unit.content
        assert "MaxConnections=100" in unit.content

    def test_template(self):
        unit = SocketBuilder("app", template=True).listen_stream(8080).build()
        assert unit.name == "app@.socket"


class TestSocketBuilderValidation:
    def test_no_listen_raises(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            SocketBuilder("app").build()
        assert "listen" in str(exc_info.value).lower()
