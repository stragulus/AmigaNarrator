#!/bin/sh
# SPDX-FileCopyrightText: 2026 AmigaNarrator contributors
# SPDX-License-Identifier: 0BSD
set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: extract-workbench13 /path/to/workbench-1.3.adf (mount output at /out)" >&2
    exit 2
fi
if [ ! -f "$1" ]; then
    echo "Workbench 1.3 ADF not found: $1" >&2
    exit 2
fi
if [ ! -d /out ] || [ ! -w /out ]; then
    echo "Mount a writable host directory at /out." >&2
    exit 2
fi

staging_dir=$(mktemp -d)
trap 'rm -rf "$staging_dir"' EXIT
trap 'exit 1' HUP INT TERM

# Extract both successfully before touching the host's runtime files.
if ! xdftool "$1" read devs/narrator.device "$staging_dir/narrator.device" \
    + read libs/translator.library "$staging_dir/translator.library"; then
    echo "Extraction failed. Use the Workbench 1.3 Workbench ADF, not the Extras disk or an archive." >&2
    exit 1
fi
mkdir -p /out/Devs /out/Libs
cp "$staging_dir/narrator.device" /out/Devs/narrator.device
cp "$staging_dir/translator.library" /out/Libs/translator.library
echo "Extracted Devs/narrator.device and Libs/translator.library to /out."
