"""Audit complete candidate preservation and each original formal-ending witness."""

import gzip
import hashlib
import json
from pathlib import Path

from doeda_native_corpora import contexts_text
from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def inspect(report, previous, corpora, history, entries, native):
    assert report["state"] == "complete-corpus-history-preservation-passed"
    assert report["inputs_unchanged"] and not report["full_coverage_complete"]
    originals = {entry(value)["id"]:value for value in native["LexicalResource"]["Lexicon"]["LexicalEntry"]}
    assert digest(originals) == "948605da84839e0596467ec1e99fc8b7a57d81022fc911484c79dc49bca7357b", "pinned complete original distribution Native fields"
    assert {ident:entry(value) for ident,value in originals.items()} == entries and len(entries) == 170, "complete distribution Native projection"
    assert hashlib.sha256(report["producer"]["text"].encode()).hexdigest() == report["producer"]["sha256"], "actual cohort producer"
    assert all(capture["binary"] in report["frozen_inputs"] for run in report["runs"] for capture in run["captures"]), "actual frozen cohort executables"
    assert all(entries[ident] == value for ident,value in report["complete_native_entries"].items()), "complete original Native fields"
    corpus_occurrences = {}
    for partition in corpora["corpora"]:
        text = partition["original_source_text"]
        assert hashlib.sha256(text.encode()).hexdigest() == partition["source_sha256"]
        contexts = contexts_text(text)
        for row in partition["original_converted_rows"]:
            corpus_occurrences.setdefault(row["surface"], []).append(
                {
                    "kind": "corpus",
                    "corpus": partition["corpus"],
                    "partition": partition["partition"],
                    "source": partition["source"],
                    "source_sha256": partition["source_sha256"],
                    "original_gold_row": row,
                    **contexts[row["id"]],
                }
            )
    additions = []
    changed_counts = []
    assert len(report["runs"]) == len(previous["runs"]) == 2
    for current, prior, family, count in zip(
        report["runs"], previous["runs"], ["corpus", "history"], [32096, 21406], strict=True
    ):
        assert current["family"] == prior["family"] == family
        assert current["surfaces"] == count
        assert len(current["captures"]) == 2
        before, after = [capture["words"] for capture in current["captures"]]
        assert before == prior["captures"][1]["words"], "complete historical baseline"
        assert before.keys() == after.keys() and len(before) == count, "complete cohort surfaces"
        for capture in current["captures"]:
            assert capture["word_sha256"] == digest(capture["words"]), "complete capture digest"
        changed = {}
        for surface, old in before.items():
            new = after[surface]
            assert {k: v for k, v in old.items() if k != "analyses"} == {
                k: v for k, v in new.items() if k != "analyses"
            }, "original word fields"
            assert [p for p in new["analyses"] if p in old["analyses"]] == old["analyses"], "old candidate preservation and order"
            if old == new:
                continue
            record = current["changed_words"][surface]
            assert record["before"] == old and record["after"] == new
            bd, ad = record["before_dictionary"], record["after_dictionary"]
            assert {k: v for k, v in bd.items() if k not in ["lemmas", "readings"]} == {
                k: v for k, v in ad.items() if k not in ["lemmas", "readings"]
            }, "dictionary identity"
            assert all(owner in ad["lemmas"] for owner in bd["lemmas"]), "original Native owners"
            for index, path in enumerate(old["analyses"]):
                assert bd["readings"][index] == ad["readings"][new["analyses"].index(path)], "old dictionary assessments"
            for path in new["analyses"]:
                if path in old["analyses"]:
                    continue
                assert any(rule in path["rules"] for rule in ["ending.explanatory_se", "particle.familiar_gryeo"]), "new path attribution"
                owners = [next(o for o in ad["lemmas"] if o["lemma"] == lemma) for lemma in path["lemmas"]]
                ident = "explanatory-se-" + family + "-" + digest([surface, path])[:24]
                matches = [o for o in report["individual_additions"] if o["id"] == ident]
                assert len(matches) == 1, "individual addition identity"
                observation = matches[0]
                expected = {
                    "id": ident,
                    "family": family,
                    "surface": surface,
                    "analysis": path,
                    "dictionary_assessment": ad["readings"][new["analyses"].index(path)],
                    "dictionary_owners": owners,
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
                assert {k: v for k, v in observation.items() if k != "original_occurrences"} == expected, "individual original path and owner evidence"
                witnesses = observation["original_occurrences"]
                assert witnesses, "complete original witnesses"
                if family == "corpus":
                    assert witnesses == corpus_occurrences[surface], "complete original corpus occurrences"
                else:
                    origins = history["origins"][surface]
                    assert [{k: w[k] for k in ["source", "source_sha256", "pointer"]} for w in witnesses] == origins, "original history origins"
                    for witness in witnesses:
                        raw = (ROOT / witness["source"]).read_bytes()
                        assert hashlib.sha256(raw).hexdigest() == witness["source_sha256"], "original history fixture hash"
                        value = json.loads(raw)
                        for key in witness["pointer"].split("/")[1:]:
                            value = value[int(key)] if isinstance(value, list) else value[key]
                        assert witness["complete_original_record"] == value, "complete original history record"
                additions.append(observation)
            changed[surface] = record
        assert changed == current["changed_words"], "exact changed words"
        changed_counts.append(len(changed))
    assert additions == report["individual_additions"], "complete individual additions and order"
    assert len(additions) == len({o["id"] for o in additions})
    assert changed_counts == [4, 0] and len(additions) == 15, "exact complete cohort change counts"
    owners = {e["id"] for o in additions for lemma in o["dictionary_owners"] for e in lemma["entries"]}
    assert owners == set(report["complete_native_entries"]), "complete Native owner closure"
    for observation in additions:
        for owner in observation["dictionary_owners"]:
            for summary in owner["entries"]:
                full = report["complete_native_entries"][summary["id"]]
                assert all(summary[k] == full[k] for k in ["id", "headword", "homonym", "pos"]), "exact Native owner identity and role"
    return {
        "corpus_surfaces": 32096,
        "historical_surfaces": 21406,
        "changed_corpus_surfaces": changed_counts[0],
        "changed_historical_surfaces": changed_counts[1],
        "individual_unjudged_paths": len(additions),
        "matched_native_owners": len(owners),
        "contextual_and_independent_review": "pending",
    }


def inputs():
    return [read(ROOT / "docs" / name) for name in [
        "explanatory-se-cohorts.json.gz",
        "giroseo-cohorts.json.gz",
        "literary-question-geona-prototype-corpora.json.gz",
        "literary-question-geona-prototype-legacy-history.json.gz",
    ]] + [read(ROOT / "tests/fixtures/explanatory-se-distribution-entries.json"), read(ROOT / "tests/fixtures/explanatory-se-distribution-native.json")]


if __name__ == "__main__":
    print(inspect(*inputs()))
