#!/usr/bin/env bash
set -euo pipefail
# W3C / DAISY official EPUBCheck distribution; no success claim if unavailable.
OUT_DIR="${1:-qa_outputs}"
TOOL_DIR="${EPUBCHECK_HOME:-/tmp/gib-epubcheck}"
if [[ ! -f "$TOOL_DIR/epubcheck.jar" ]]; then
  mkdir -p "$TOOL_DIR"
  ZIP="$TOOL_DIR/official-epubcheck.zip"
  curl -L --fail --silent --show-error --retry 2 \
    'https://github.com/w3c/epubcheck/releases/download/v5.4.0/epubcheck-5.4.0.zip' -o "$ZIP"
  unzip -oq "$ZIP" -d "$TOOL_DIR/extract"
  JAR=$(find "$TOOL_DIR/extract" -name epubcheck.jar -type f -print -quit)
  if [[ -z "$JAR" ]]; then echo 'OFFICIAL_EPUBCHECK_NOT_FOUND' >&2;exit 6;fi
  cp -a "$(dirname "$JAR")"/* "$TOOL_DIR/"
fi
found=0
while IFS= read -r -d '' epub;do
  found=$((found+1))
  echo "EPUBCheck: $epub"
  java -jar "$TOOL_DIR/epubcheck.jar" "$epub"
done < <(find "$OUT_DIR" -name '*.epub' -type f -print0)
[[ "$found" -ge 2 ]] || { echo 'EXPECTED_TWO_EPUB_FILES' >&2; exit 7; }
echo "EPUBCHECK_PASSED count=$found"
