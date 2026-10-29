#!/usr/bin/env python3
"""Send commands to the DWM3001CDK native USB CLI."""

import argparse
import os
import select
import termios
import time


def configure(fd: int) -> None:
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


def read_until_quiet(fd: int, timeout: float) -> bytes:
    output = bytearray()
    final_deadline = time.monotonic() + timeout
    quiet_deadline = final_deadline
    while time.monotonic() < min(final_deadline, quiet_deadline):
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            chunk = os.read(fd, 4096)
            if chunk:
                output.extend(chunk)
                quiet_deadline = time.monotonic() + 0.35
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("port")
    parser.add_argument("commands", nargs="+")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()

    fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        configure(fd)
        for command in args.commands:
            print(f"> {command}")
            os.write(fd, command.encode("ascii") + b"\r\n")
            response = read_until_quiet(fd, args.timeout)
            print(response.decode("utf-8", errors="replace"), end="")
    finally:
        os.close(fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
