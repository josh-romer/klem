#!/usr/bin/env bash
# Explicit download only; requires Bash, curl, jq, unzip, sha256sum.
set -euo pipefail
cd "$(dirname "$0")/.."
verify_only=false
if [[ "${1:-}" == --verify && $# -eq 1 ]]; then verify_only=true
elif [[ $# -ne 0 ]]; then echo 'usage: bash tools/fetch-krdict.sh [--verify]' >&2; exit 2; fi
manifest=data/krdict.lock.json
destination=data/dictionaries/krdict
# Importing a directory includes every JSON file. Reject unpinned extras rather
# than quietly mixing another release into the verified snapshot.
for file in "$destination/json/"*.json; do
  [[ -e "$file" ]] || continue
  jq -e --arg name "${file##*/}" '.files | any(.name == $name)' "$manifest" > /dev/null || {
    echo "Unpinned JSON file in dictionary directory: $file" >&2; exit 1;
  }
done
verify_files() {
  local name expected
  while IFS=$'\t' read -r name expected; do
    [[ -f "$destination/json/$name" ]] || return 1
    [[ "$(sha256sum "$destination/json/$name" | cut -d ' ' -f1)" == "$expected" ]] || return 1
  done < <(jq -r '.files[] | [.name,.sha256] | @tsv' "$manifest")
}
if verify_files; then echo 'Pinned dictionary JSON verified.' >&2; exit 0; fi
if $verify_only; then echo 'Missing or mismatched dictionary JSON.' >&2; exit 1; fi
mkdir -p "$destination"
temporary=$(mktemp -d "$destination/.fetch.XXXXXX")
trap 'rm -rf "$temporary"' EXIT
archive=$(jq -r .archive "$manifest")
expected=$(jq -r .archive_sha256 "$manifest")
if [[ -f "$destination/$archive" ]] && [[ "$(sha256sum "$destination/$archive" | cut -d ' ' -f1)" == "$expected" ]]; then
  archive_path="$destination/$archive"
else
  curl --fail --silent --show-error --location --retry 2 -A 'Mozilla/5.0' \
    "$(jq -r .url "$manifest")" -o "$temporary/archive.zip"
  [[ "$(sha256sum "$temporary/archive.zip" | cut -d ' ' -f1)" == "$expected" ]] || { echo 'Dictionary archive checksum mismatch.' >&2; exit 1; }
  archive_path="$temporary/archive.zip"
fi
mkdir "$temporary/json"
while IFS=$'\t' read -r name expected; do
  [[ "$name" =~ ^[0-9]+_[0-9]+_[0-9]+\.json$ ]] || { echo 'Unexpected dictionary filename.' >&2; exit 1; }
  unzip -p "$archive_path" "$name" > "$temporary/json/$name"
  [[ "$(sha256sum "$temporary/json/$name" | cut -d ' ' -f1)" == "$expected" ]] || { echo "Dictionary checksum mismatch: $name" >&2; exit 1; }
done < <(jq -r '.files[] | [.name,.sha256] | @tsv' "$manifest")
mkdir -p "$destination/json"
for file in "$temporary/json/"*.json; do mv "$file" "$destination/json/"; done
if [[ "$archive_path" == "$temporary/archive.zip" ]]; then mv "$archive_path" "$destination/$archive"; fi
echo 'Pinned dictionary downloaded and verified.' >&2
