#!/usr/bin/env python3
"""Display DWM3001CDK ranges live and save measurements to CSV."""

import argparse
import csv
import datetime as dt
import os
from pathlib import Path
import re
import select
import signal
import termios


MEASUREMENT = re.compile(
    r"mac_address=0x(?P<peer>[0-9a-fA-F]+),\s*status=\"(?P<status>[^\"]+)\""
    r"(?:,\s*distance\[cm\]=(?P<distance>-?\d+))?"
)
SEQUENCE = re.compile(r"sequence_number=(?P<sequence>\d+),\s*block_index=(?P<block>\d+)")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="macOS serial port, for example /dev/cu.usbmodemABC")
    parser.add_argument("--output", default="data/uwb/live-ranging.csv")
    parser.add_argument("--initiator", type=int, default=0)
    parser.add_argument("--responder", type=int, default=1)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    new_file = not output.exists() or output.stat().st_size == 0
    csv_file = output.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(
        csv_file,
        fieldnames=["timestamp", "sequence", "block", "peer", "status", "distance_cm"],
    )
    if new_file:
        writer.writeheader()

    fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    configure(fd)
    running = True

    def stop(_signum=None, _frame=None):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    command = f"INITF -ADDR={args.initiator} -PADDR={args.responder}\r\n"
    os.write(fd, command.encode("ascii"))
    print(f"Live ranging: 0x{args.initiator:04x} -> 0x{args.responder:04x}")
    print(f"Saving CSV: {output.resolve()}")
    print("Move either board; press Ctrl-C to stop.\n")

    pending = ""
    sequence = ""
    block = ""
    try:
        while running:
            ready, _, _ = select.select([fd], [], [], 0.25)
            if not ready:
                continue
            pending += os.read(fd, 4096).decode("utf-8", errors="replace")
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                seq_match = SEQUENCE.search(line)
                if seq_match:
                    sequence = seq_match.group("sequence")
                    block = seq_match.group("block")
                match = MEASUREMENT.search(line)
                if not match:
                    continue
                distance = match.group("distance") or ""
                status = match.group("status")
                now = dt.datetime.now().astimezone().isoformat(timespec="milliseconds")
                row = {
                    "timestamp": now,
                    "sequence": sequence,
                    "block": block,
                    "peer": f"0x{match.group('peer')}",
                    "status": status,
                    "distance_cm": distance,
                }
                writer.writerow(row)
                csv_file.flush()
                if distance:
                    print(f"{now[11:23]}  {int(distance):5d} cm  {status}", flush=True)
                else:
                    print(f"{now[11:23]}      --  {status}", flush=True)
    finally:
        try:
            os.write(fd, b"STOP\r\n")
        finally:
            os.close(fd)
            csv_file.close()
    print(f"\nStopped. Data saved to {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
