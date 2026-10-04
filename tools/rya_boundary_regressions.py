"""Append Rust-readable projections without replacing native/before evidence."""

import argparse
import json

from lexical_nada_audit import ROOT, read, sha
from lexical_nada_fixtures import projection
from rya_boundary_audit import FIXTURE, LMF, SOURCE

REGRESSIONS = ROOT / "tests/fixtures/rya-boundary-regressions.json"


def generate():
    source, fixture = read(SOURCE), read(FIXTURE)
    selected = {
        ident: source["complete_native_entries"][ident]
        for ident in fixture["native_entry_ids"]
    }
    return {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "fixture_sha256": sha(FIXTURE),
        "lmf_sha256": sha(LMF),
        "source_entries": projection(selected),
        "before_words": {
            r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
            for r in source["before_streams"]["all"]
            if r["kind"] == "word"
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    value = generate()
    if args.verify:
        assert read(REGRESSIONS) == value
    else:
        with REGRESSIONS.open("x") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
    print(
        f"{len(value['source_entries'])} full English native projections and {len(value['before_words'])} original raw/entry annotations verified"
    )
