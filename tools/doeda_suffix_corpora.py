"""Compare every held-out gold row and independently attribute suffix additions.

Original annotations and previous reports remain immutable. Whole-parent
inversion checks every changed word; ambiguity and contextual gold outcomes
are retained separately from structural candidate proposals.
"""

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from doeda_suffix_audit import SOURCE
from doeda_suffix_diagnostics import REPORT as DIAGNOSTICS
from doeda_suffix_diagnostics import attributable, components_for, validate_components
from doeda_suffix_package import REPORT as PACKAGE
from doeda_suffix_regressions import effective_formations
from lexical_nada_audit import ROOT, read, sha, write

PREVIOUS = ROOT / "docs/doeda-complement-corpora.json.gz"
REPORT = ROOT / "docs/doeda-suffix-corpora.json.gz"
AMBIGUITY = {"mean_candidates", "p95_candidates", "max_candidates"}
OUTCOMES = {
    "grouped_matches",
    "recovered_gold_lemmas",
    "transformed_matches",
    "grouped_lemma_recall",
    "lemma_recall",
    "transformed_grouped_recall",
    "common_misses",
}


def digest(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def contexts(path):
    """Use the adapter's stable row identities; retain complete source sentences."""
    return contexts_text(path.read_text())


def contexts_text(text):
    result = {}
    for ordinal, sentence in enumerate(text.strip().split("\n\n"), 1):
        lines = sentence.splitlines()
        ids = [
            line.removeprefix("# sent_id = ")
            for line in lines
            if line.startswith("# sent_id = ")
        ]
        assert len(ids) <= 1
        prefix = "id:" + ids[0] if ids else f"ordinal:{ordinal}"
        for line in lines:
            row = line.split("\t")
            if len(row) == 10 and row[0].isdigit() and int(row[0]) > 0:
                ident = prefix + "/" + row[0]
                assert ident not in result
                result[ident] = {"complete_sentence": sentence, "original_row": row}
    return result


def gold_changes(before, after, context):
    changes = []
    assert len(before) == len(after)
    for b, a in zip(before, after, strict=True):
        assert {k: b[k] for k in ("id", "surface", "expected")} == {
            k: a[k] for k in ("id", "surface", "expected")
        }
        assert not b["matched"] or a["matched"]
        assert a["recovered"] >= b["recovered"]
        for row in (b, a):
            assert isinstance(row["matched"], bool)
            assert row["recovered"] == max(map(len, row["recovered_sets"]), default=0)
            assert all(
                s == sorted(set(s))
                and all(isinstance(i, int) and 0 <= i < len(row["expected"]) for i in s)
                for s in row["recovered_sets"]
            )
        assert all(
            any(set(old) <= set(new) for new in a["recovered_sets"])
            for old in b["recovered_sets"]
        )
        if b != a:
            changes.append({"id": b["id"], "before": b, "after": a, **context[b["id"]]})
    return changes


def candidate_changes(surface, before, after, occurrences, components, formations):
    assert before.keys() == after.keys()
    assert {k: v for k, v in before.items() if k != "analyses"} == {
        k: v for k, v in after.items() if k != "analyses"
    }
    old, new = before["analyses"], after["analyses"]
    assert [a for a in new if a in old] == old, (surface, "candidate loss/order")
    changes = []
    for a in new:
        if a in old:
            continue
        attributable(before["analyses"], a, components, formations)
        key = json.dumps([surface, a], ensure_ascii=False, sort_keys=True)
        changes.append(
            {
                "id": "doeda-suffix-corpus-" + digest(key)[:24],
                "surface": surface,
                "before": None,
                "after": a,
                "occurrences": occurrences,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return changes


def inspect(previous, report):
    components = report["original_parent_components"]
    formations = {p["head"]: p for p in effective_formations()}
    assert len(previous["corpora"]) == len(report["corpora"]) == 4
    # The source preflight predates implementation and independently anchors
    # each changed sentence even inside Nix, where downloaded corpora are absent.
    frozen_corpora = {c["source"]: c for c in read(SOURCE)["corpora"]}
    total = 0
    occurrences = {}
    original_contexts = {}
    for old, current in zip(previous["corpora"], report["corpora"], strict=True):
        for field in (
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ):
            assert current[field] == old[field]
        path = ROOT / current["source"]
        # In the offline Nix check the original corpora are not distributed.
        # Complete changed contexts are embedded below; compare to disk when present.
        original_text = report["original_corpus_texts"][current["source"]]
        assert digest(original_text) == current["source_sha256"]
        context = contexts_text(original_text)
        original_contexts[current["source"]] = context
        if path.exists():
            assert sha(path) == current["source_sha256"]
            assert path.read_text() == original_text
        assert current["before_jsonl"] == old["after_jsonl"]
        assert current["before_report_sha256"] == old["after_report_sha256"]
        parsed = []
        for name in ("before", "after"):
            raw = current[name + "_jsonl"]
            assert digest(raw) == current[name + "_report_sha256"]
            rows = [json.loads(line) for line in raw.splitlines()]
            assert len(rows) == current["report_lines"] == current["converted_rows"] + 1
            summary = rows[0]
            assert summary["input_sha256"] == current["source_sha256"]
            assert summary["corpus"] == current["corpus"]
            assert summary["converted_rows"] == current["converted_rows"]
            assert summary["grouped_matches"] == sum(r["matched"] for r in rows[1:])
            assert summary["gold_lemmas"] == sum(len(r["expected"]) for r in rows[1:])
            assert summary["recovered_gold_lemmas"] == sum(
                r["recovered"] for r in rows[1:]
            )
            assert summary["grouped_lemma_recall"] == summary["grouped_matches"] / len(
                rows[1:]
            )
            assert (
                summary["lemma_recall"]
                == summary["recovered_gold_lemmas"] / summary["gold_lemmas"]
            )
            assert (
                summary["transformed_grouped_recall"]
                == summary["transformed_matches"] / summary["transformed_rows"]
            )
            assert len({r["id"] for r in rows[1:]}) == len(rows) - 1
            counts = current[name + "_candidate_counts"]
            assert len(counts) == len(rows) - 1
            assert all(isinstance(n, int) and n > 0 for n in counts)
            assert sum(counts) / len(counts) == summary["mean_candidates"]
            ordered = sorted(counts)
            assert ordered[len(counts) * 95 // 100] == summary["p95_candidates"]
            assert max(counts) == summary["max_candidates"]
            parsed.append(rows)
        before, after = parsed
        assert before[0].keys() == after[0].keys()
        changes = {
            k: {"before": before[0][k], "after": after[0][k]}
            for k in before[0]
            if before[0][k] != after[0][k]
        }
        assert set(changes) <= AMBIGUITY | OUTCOMES, changes
        assert current["changed_summary_fields"] == changes
        supplied = {
            r["id"]: {k: r[k] for k in ("complete_sentence", "original_row")}
            for r in current["changed_gold_outcomes"]
        }
        assert all(context[ident] == value for ident, value in supplied.items())
        assert current["changed_gold_outcomes"] == gold_changes(
            before[1:], after[1:], context
        )
        for b, a, bn, an in zip(
            before[1:],
            after[1:],
            current["before_candidate_counts"],
            current["after_candidate_counts"],
            strict=True,
        ):
            assert an >= bn
            if an != bn:
                pair = report["changed_words"][b["surface"]]
                assert (bn, an) == (
                    len(pair["before"]["analyses"]),
                    len(pair["after"]["analyses"]),
                )
                key = (current["source"], b["id"])
                occurrences[key] = (b["surface"], current["source_sha256"])
        total += current["converted_rows"]
    assert total == report["converted_rows"] == 66570
    seen = {}
    changes = []
    for surface, pair in report["changed_words"].items():
        assert pair["before"] != pair["after"]
        for occurrence in pair["occurrences"]:
            key = (occurrence["source"], occurrence["id"])
            assert key not in seen and occurrences[key] == (
                surface,
                occurrence["source_sha256"],
            )
            seen[key] = (surface, occurrence["source_sha256"])
            row = occurrence["original_row"]
            assert len(row) == 10 and row[1] == surface
            assert "\t".join(row) in occurrence["complete_sentence"].splitlines()
            frozen = frozen_corpora[occurrence["source"]]
            assert occurrence["source_sha256"] == frozen["sha256"]
            # All contexts are immutable original corpus rows. The source
            # preflight additionally anchors its derivational-tagged subset.
            if occurrence["complete_sentence"] in {
                s["complete_sentence"] for s in frozen["sentences"]
            }:
                assert any(
                    "\t".join(row) in s["complete_sentence"].splitlines()
                    for s in frozen["sentences"]
                    if s["complete_sentence"] == occurrence["complete_sentence"]
                )
            assert {
                k: occurrence[k] for k in ("complete_sentence", "original_row")
            } == original_contexts[occurrence["source"]][occurrence["id"]]
        changes.extend(
            candidate_changes(
                surface,
                pair["before"],
                pair["after"],
                pair["occurrences"],
                components,
                formations,
            )
        )
    assert seen == occurrences
    assert changes == report["candidate_changes"]
    return total


def words_from_cli(cli, surfaces):
    text = "\n".join(surfaces) + "\n"
    result = subprocess.run(
        [str(cli), "text", "-"], input=text, text=True, capture_output=True, check=True
    )
    records = [json.loads(line) for line in result.stdout.splitlines() if line]
    assert "".join(r["surface"] for r in records) == text
    starts = {}
    offset = 0
    for surface in surfaces:
        starts[offset] = surface
        offset += len(surface.encode()) + 1
    whole = {
        r["surface"]: r["analysis"]
        for r in records
        if r["kind"] == "word"
        and starts.get(r["span"]["start"]) == r["surface"]
        and r["span"]["end"] == r["span"]["start"] + len(r["surface"].encode())
    }
    missing = [s for s in surfaces if s not in whole]

    # CoNLL-U tokens can contain punctuation. Preserve the exact original
    # word interface for them rather than rewriting gold token boundaries.
    def analyze(surface):
        out = subprocess.run(
            [str(cli), "word", surface], text=True, capture_output=True, check=True
        )
        return surface, json.loads(out.stdout)

    with ThreadPoolExecutor(max_workers=4) as pool:
        whole.update(pool.map(analyze, missing))
    assert set(whole) == set(surfaces)
    print(
        len(surfaces) - len(missing),
        "exact text tokens and",
        len(missing),
        "punctuation-bearing original word calls",
        flush=True,
    )
    return whole


def freeze(args):
    assert not args.output.exists()
    previous, source, diagnostic, package = (
        read(PREVIOUS),
        read(SOURCE),
        read(DIAGNOSTICS),
        read(PACKAGE),
    )
    assert sha(args.before_cli) == source["cli_sha256"] == previous["cli_sha256"]
    assert sha(args.cli) == package["cli_sha256"]
    assert sha(ROOT / "src/engine.rs") == diagnostic["engine_sha256"]
    corpora, locations = [], {}
    for old in previous["corpora"]:
        path = ROOT / old["source"]
        assert sha(path) == old["source_sha256"]
        context = contexts(path)
        current = subprocess.run(
            [str(args.evaluator.resolve()), old["corpus"], old["source"]],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        before = [json.loads(line) for line in old["after_jsonl"].splitlines()]
        after = [json.loads(line) for line in current.splitlines()]
        changed = gold_changes(before[1:], after[1:], context)
        for row in before[1:]:
            original = context[row["id"]]
            assert original["original_row"][1] == row["surface"]
            locations.setdefault(row["surface"], []).append(
                {
                    "source": old["source"],
                    "source_sha256": old["source_sha256"],
                    "id": row["id"],
                    **original,
                }
            )
        corpora.append(
            {
                **{
                    k: old[k]
                    for k in (
                        "corpus",
                        "partition",
                        "source",
                        "source_sha256",
                        "converted_rows",
                        "report_lines",
                    )
                },
                "before_jsonl": old["after_jsonl"],
                "after_jsonl": current,
                "before_report_sha256": old["after_report_sha256"],
                "after_report_sha256": digest(current),
                "changed_gold_outcomes": changed,
                "changed_summary_fields": {
                    k: {"before": before[0][k], "after": after[0][k]}
                    for k in before[0]
                    if before[0][k] != after[0][k]
                },
            }
        )
        print(
            old["corpus"],
            old["partition"],
            len(before) - 1,
            "original gold rows compared",
            flush=True,
        )
    ordered = sorted(locations)
    before = words_from_cli(args.before_cli, ordered)
    after = words_from_cli(args.cli, ordered)
    changed_words = {
        word: {
            "before": before[word],
            "after": after[word],
            "occurrences": locations[word],
        }
        for word in ordered
        if before[word] != after[word]
    }
    print(
        len(ordered),
        "exact surfaces compared;",
        len(changed_words),
        "changed words",
        flush=True,
    )
    components = components_for(
        [p["before"] for p in changed_words.values()], args.bridge
    )
    validate_components(components, [p["before"] for p in changed_words.values()])
    formations = {p["head"]: p for p in effective_formations()}
    changes = [
        c
        for word, pair in changed_words.items()
        for c in candidate_changes(
            word,
            pair["before"],
            pair["after"],
            pair["occurrences"],
            components,
            formations,
        )
    ]
    for c in corpora:
        for name, mapping in (("before", before), ("after", after)):
            rows = [json.loads(line) for line in c[name + "_jsonl"].splitlines()[1:]]
            c[name + "_candidate_counts"] = [
                len(mapping[r["surface"]]["analyses"]) for r in rows
            ]
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "source_sha256": sha(SOURCE),
        "diagnostics_sha256": sha(DIAGNOSTICS),
        "package_sha256": sha(PACKAGE),
        "previous_report_sha256": sha(PREVIOUS),
        "evaluator_sha256": sha(args.evaluator),
        "before_cli_sha256": sha(args.before_cli),
        "cli_sha256": sha(args.cli),
        "engine_sha256": sha(ROOT / "src/engine.rs"),
        "adapter_sha256": sha(ROOT / "tools/corpus.rs"),
        "converted_rows": 66570,
        "unique_surfaces": len(ordered),
        "word_stream_order": "unique surfaces sorted by Unicode code point; exact CLI text tokens with CLI word fallback for punctuation-bearing original tokens",
        "before_word_stream_sha256": digest(
            json.dumps(before, ensure_ascii=False, sort_keys=True)
        ),
        "after_word_stream_sha256": digest(
            json.dumps(after, ensure_ascii=False, sort_keys=True)
        ),
        "corpora": corpora,
        "original_corpus_texts": {
            c["source"]: (ROOT / c["source"]).read_text() for c in corpora
        },
        "changed_words": changed_words,
        "candidate_changes": changes,
        "original_parent_components": components,
        "scope": "Four complete original held-out gold reports, all 66,570 rows, independent original contexts/ten columns and before/after CLI analyses for every distinct convertible surface. All original paths/recovered groups retained. Each addition reconstructs from original whole-source owners; ambiguity changes and sentence-context outcomes remain individually visible. Native entry/context/register/formal-history/independent judgments remain separate.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    inspect(previous, report)
    write(args.output, report)
    print(
        "Archived",
        len(changed_words),
        "changed corpus words and",
        len(changes),
        "individually attributed candidates.",
        flush=True,
    )


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    for key, path in (
        ("source_sha256", SOURCE),
        ("diagnostics_sha256", DIAGNOSTICS),
        ("package_sha256", PACKAGE),
        ("previous_report_sha256", PREVIOUS),
    ):
        assert report[key] == sha(path)
    assert report["before_cli_sha256"] == read(SOURCE)["cli_sha256"]
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert report["engine_sha256"] == read(DIAGNOSTICS)["engine_sha256"]
    all_surfaces = {
        json.loads(line)["surface"]
        for c in report["corpora"]
        for line in c["before_jsonl"].splitlines()[1:]
    }
    assert report["unique_surfaces"] == len(all_surfaces)
    validate_components(
        report["original_parent_components"],
        [p["before"] for p in report["changed_words"].values()],
    )
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    total = inspect(read(PREVIOUS), report)
    print(
        "Verified",
        total,
        "original held-out gold rows,",
        len(report["changed_words"]),
        "changed words and",
        len(report["candidate_changes"]),
        "source-parent-attributed additions.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in ("evaluator", "before-cli", "cli", "bridge", "output"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert (
            args.evaluator
            and args.before_cli
            and args.cli
            and args.bridge
            and args.output
        )
        freeze(args)
