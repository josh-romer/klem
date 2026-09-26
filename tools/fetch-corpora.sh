#!/usr/bin/env bash
# Explicit development action. Requires curl and sha256sum; never runs at build.
set -euo pipefail
cd "$(dirname "$0")/.."
verify_only=false
if [[ "${1:-}" == --verify ]]; then verify_only=true
elif [[ $# -ne 0 ]]; then echo 'usage: bash tools/fetch-corpora.sh [--verify]' >&2; exit 2
fi
while read -r expected path url; do
  [[ -z "$expected" || "$expected" == \#* ]] && continue
  destination="data/corpora/$path"
  if [[ -f "$destination" ]] && [[ "$(sha256sum "$destination" | cut -d ' ' -f 1)" == "$expected" ]]; then continue; fi
  if $verify_only; then echo "Missing or checksum mismatch: $destination" >&2; exit 1; fi
  mkdir -p "$(dirname "$destination")"
  temporary=$(mktemp "$destination.XXXXXX")
  trap 'rm -f "$temporary"' EXIT
  curl --fail --location --silent --show-error --retry 2 "$url" -o "$temporary"
  if [[ "$(sha256sum "$temporary" | cut -d ' ' -f 1)" != "$expected" ]]; then echo "Checksum mismatch: $url" >&2; exit 1; fi
  mv "$temporary" "$destination"
  trap - EXIT
done < data/corpora.lock
echo 'Pinned corpus checksums verified.' >&2
