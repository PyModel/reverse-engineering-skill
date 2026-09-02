#!/usr/bin/env bash
# Wrapper for Ghidra's Headless Analyzer: batch decompilation without a GUI.
#
# Usage:
#   ./scripts/ghidra_headless.sh <project_dir> <project_name> <target_binary> \
#       [--script decompile_functions.py] [--symbols 'regex'] [--out ./decompiled/]
#
# Requires: Ghidra on PATH (or set GHIDRA_HOME). The --script is a Ghidra post-script
# run against the imported program; see scripts/decompile_functions.py.
set -euo pipefail

PROJECT_DIR="${1:?project dir required}"
PROJECT_NAME="${2:?project name required}"
TARGET="${3:?target binary required}"
shift 3

SCRIPT="decompile_functions.py"
SYMBOLS=".*"
OUT="./decompiled"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --script) SCRIPT="$2"; shift 2;;
    --symbols) SYMBOLS="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown arg: $1"; shift;;
  esac
done

GHIDRA=$(command -v analyzeHeadless || echo "${GHIDRA_HOME:-}/support/analyzeHeadless")
if ! command -v "$GHIDRA" >/dev/null 2>&1 && [ ! -x "$GHIDRA" ]; then
  echo "Error: Ghidra analyzeHeadless not found on PATH and GHIDRA_HOME not set." >&2
  echo "Set GHIDRA_HOME=/path/to/ghidra or add analyzeHeadless to PATH." >&2
  exit 1
fi

mkdir -p "$OUT"

"$GHIDRA" "$PROJECT_DIR" "$PROJECT_NAME" \
  -import "$TARGET" \
  -postScript "$SCRIPT" \
  -postScriptArgs "$SYMBOLS|$OUT" \
  -deleteProject

echo "Decompiled output written to: $OUT"
