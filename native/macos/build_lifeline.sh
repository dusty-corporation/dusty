#!/usr/bin/env bash
# Build the dusty-lifeline helper (ADR 0037) into a new output directory.
set -euo pipefail
export LC_ALL=C

fail() { echo "$1" >&2; exit 1; }
[[ $# -eq 1 ]] || fail 'Usage: build_lifeline.sh <new-output-directory>'
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || fail 'Native Mac arm64 required'
source_file="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lifeline/lifeline.c"
[[ -f "$source_file" ]] || fail 'Lifeline source is missing'

out_parent="$(cd "$(dirname "$1")" && pwd -P)"
out_name="$(basename "$1")"
[[ "$out_name" != . && "$out_name" != .. ]] || fail 'Output must be a new directory'
out_dir="$out_parent/$out_name"
[[ ! -e "$out_dir" && ! -L "$out_dir" ]] || fail 'Refusing existing output directory'

clang="$(xcrun --find clang)"
sdk="$(xcrun --show-sdk-path)"
mkdir "$out_dir"
mkdir "$out_dir/lifeline"
"$clang" -isysroot "$sdk" -arch arm64 -mmacosx-version-min=13.0 \
  -std=c11 -O2 -Wall -Wextra -Werror -o "$out_dir/lifeline/dusty-lifeline" "$source_file"
(cd "$out_dir" && shasum -a 256 lifeline/dusty-lifeline > SHA256SUMS)
echo "Built lifeline/dusty-lifeline"
