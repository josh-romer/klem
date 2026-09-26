#!/usr/bin/env bash
# Explicit download only. Requires Bash, curl, jq, sha256sum.
set -euo pipefail
cd "$(dirname "$0")/.."
verify_only=false
if [[ "${1:-}" == --verify && $# -eq 1 ]]; then verify_only=true
elif [[ $# -ne 0 ]]; then echo 'usage: bash tools/fetch-novel.sh [--verify]' >&2; exit 2; fi
expected=$(jq -r .text_sha256 data/novel.lock.json)
destination=data/books/mujeong.txt
if [[ -f "$destination" ]] && [[ "$(sha256sum "$destination" | cut -d ' ' -f 1)" == "$expected" ]]; then
  echo 'Pinned novel text verified.' >&2; exit 0
fi
if $verify_only; then echo "Missing or checksum mismatch: $destination" >&2; exit 1; fi
mkdir -p data/books
temporary=$(mktemp -d data/books/.fetch.XXXXXX)
trap 'rm -rf "$temporary"' EXIT
: > "$temporary/book.txt"
while IFS=$'\t' read -r revision expected_raw; do
  curl --fail --silent --show-error --retry 2 --get 'https://ko.wikisource.org/w/api.php' \
    --data-urlencode 'action=query' --data-urlencode 'format=json' \
    --data-urlencode 'prop=revisions' --data-urlencode 'rvprop=ids|content' \
    --data-urlencode 'rvslots=main' --data-urlencode "revids=$revision" -o "$temporary/page.json"
  jq -er --argjson revision "$revision" '.query.pages[] | .revisions[] | select(.revid == $revision) | .slots.main["*"]' \
    "$temporary/page.json" > "$temporary/raw.txt"
  if [[ "$(sha256sum "$temporary/raw.txt" | cut -d ' ' -f 1)" != "$expected_raw" ]]; then
    echo "Novel section checksum mismatch: $revision" >&2; exit 1
  fi
  jq -Rsr -f tools/extract-novel.jq "$temporary/raw.txt" >> "$temporary/book.txt"
done < <(jq -r '.sections[] | [.revision, .raw_sha256] | @tsv' data/novel.lock.json)
if [[ "$(sha256sum "$temporary/book.txt" | cut -d ' ' -f 1)" != "$expected" ]]; then
  echo 'Extracted novel checksum mismatch.' >&2; exit 1
fi
mv "$temporary/book.txt" "$destination"
echo 'Pinned novel downloaded and verified.' >&2
