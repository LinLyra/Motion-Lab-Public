#!/bin/sh
set -eu

found=0
for port in /dev/cu.usbmodem* /dev/cu.usbserial*; do
    if [ -e "$port" ]; then
        printf '%s\n' "$port"
        found=1
    fi
done

if [ "$found" -eq 0 ]; then
    echo "No USB serial port found. Connect the cable to J20 (the upper Micro-USB port) after flashing." >&2
    exit 1
fi
