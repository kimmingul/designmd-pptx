#!/usr/bin/env bash
# Thin wrapper: staging-safe apply via designmd_pptx.apply_sequence
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
FILE="$ROOT/Apple-Keynote-Intro.pptx"
SEQ="$ROOT/recipes/deck.sequence.json"
FORCE=()
if [[ "${DESIGNMD_FORCE:-}" == "1" ]]; then FORCE=(--force); fi
PKG="$(cd "$ROOT/../.." && pwd)"
if [[ -d "$PKG/designmd_pptx" ]]; then export PYTHONPATH="$PKG${PYTHONPATH:+:$PYTHONPATH}"; fi
python -m designmd_pptx apply "$FILE" "$SEQ" ${FORCE[@]+"${FORCE[@]}"} --screenshot
echo "Done: $FILE"
