#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image_dir="$repo_dir/firmware/DW3_QM33_SDK/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Release"
image_name="DWM3001CDK-CLI-FreeRTOS.hex"
commander="$repo_dir/scripts/flash-dwm3001cdk.jlink"

if [ ! -f "$image_dir/$image_name" ]; then
    echo "Firmware image not found: $image_dir/$image_name" >&2
    exit 1
fi

if ! command -v JLinkExe >/dev/null 2>&1; then
    echo "JLinkExe is not installed or not on PATH." >&2
    exit 1
fi

serial_arg=""
if [ "${1:-}" != "" ]; then
    serial_arg="-SelectEmuBySN $1"
fi

echo "Flashing DWM3001CDK CLI firmware..."
echo "Do not disconnect the board until J-Link reports O.K."
cd "$image_dir"
# Intentional word splitting: serial_arg is either empty or two J-Link arguments.
# shellcheck disable=SC2086
JLinkExe $serial_arg -NoGui 1 -ExitOnError 1 -CommanderScript "$commander"

