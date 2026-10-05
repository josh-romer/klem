"""Verify an additional typed-base projection without changing coarse corpus gold."""
from doeda_native_corpora import contexts_text
from lexical_nada_audit import ROOT, read, sha

FIXTURE = ROOT / "docs/ssik-morphology-projection.json"
TEXTS = ROOT / "docs/doeda-originless-corpora.json.gz"
PRIOR = ROOT / "docs/hada-remaining-packaged-corpora.json.gz"
NOMINAL = ROOT / "docs/ssik-corpora.json.gz"
ROLES = {"nbu": "nominal", "ncn": "nominal", "NNB": "nominal", "MAG": "adverbial"}


def inspect():
    fixture = read(FIXTURE)
    assert fixture["schema_version"] == 1 and fixture["checklist"] == "COV-022v"
    assert fixture["preparation_only"] is True
    assert fixture["tag_projection"] == ROLES
    assert fixture["original_texts_sha256"] == sha(TEXTS)
    assert fixture["before_corpora_sha256"] == sha(PRIOR)
    assert fixture["nominal_corpora_sha256"] == sha(NOMINAL)
    original = read(TEXTS)["original_corpus_texts"]
    prior, nominal = read(PRIOR)["after_words"], read(NOMINAL)["after_words"]
    rows = fixture["rows"]
    assert len(rows) == len({r["id"] for r in rows}) == 12
    locations = {(r["source"], r["original_id"]): r for r in rows}
    assert len(locations) == len(rows)
    observed, projected, missing = set(), 0, []
    for source, text in original.items():
        for ident, context in contexts_text(text).items():
            fields = context["original_row"]
            forms, tags = fields[2].split("+"), fields[4].split("+")
            if "씩" not in forms:
                continue
            observed.add((source, ident))
            row = locations[(source, ident)]
            assert row["original_row"] == fields
            assert row["complete_sentence"] == context["complete_sentence"]
            import hashlib
            assert row["source_sha256"] == hashlib.sha256(text.encode()).hexdigest()
            assert row["id"] == "ssik-morphology-" + hashlib.sha256((source + "\n" + ident).encode()).hexdigest()[:24]
            eligible = len(forms) == len(tags) == 2 and forms[1] == "씩" and tags[0] in ROLES and tags[1].lower() == "xsn"
            if not eligible:
                assert row["expected"] is None
                assert row["disposition"] == "no_explicit_base_in_original_row"
                continue
            projected += 1
            expected = {"lemmas": [{"text": forms[0], "kind": ROLES[tags[0]]}],
                        "morphemes": [{"form": "씩", "kind": "suffix"}]}
            assert row["expected"] == expected
            for words, key in [(prior, "before_matches"), (nominal, "nominal_batch_matches")]:
                paths = [a for a in words[fields[1]]["analyses"]
                         if a["lemmas"] == expected["lemmas"] and a["morphemes"] == expected["morphemes"]]
                assert row[key] == paths
            assert row["disposition"] == ("covered" if row["nominal_batch_matches"] else "missing_typed_base")
            if not row["nominal_batch_matches"]:
                missing.append(row["id"])
    assert observed == locations.keys()
    assert projected == 9 and len(missing) == 1
    return len(rows), projected, projected - len(missing), missing


if __name__ == "__main__":
    print("Verified original suffix rows, explicit typed projections, nominal coverage and retained missing IDs:", inspect())
