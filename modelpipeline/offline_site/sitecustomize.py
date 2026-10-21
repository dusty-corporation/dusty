"""Fail conversion if a Python dependency tries to open a network socket."""

import socket


def reject_connection(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Network access attempted during offline model conversion")


socket.socket.connect = reject_connection
socket.create_connection = reject_connection
