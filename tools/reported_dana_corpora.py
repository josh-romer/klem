"""Verify unchanged gold partitions against complete captured word analyses."""

import copy, gzip, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    p = ROOT / name
    return json.loads(gzip.decompress(p.read_bytes()))


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def verify(current):
    previous = read("docs/reported-deoni-prototype-corpora.json.gz")
    assert current["prototype"] and current["inputs_unchanged"]
    assert current["previous_report_sha256"] == sha(
        "docs/reported-deoni-prototype-corpora.json.gz"
    )
    assert current["after_words"] == previous["after_words"]
    assert len(current["after_words"]) == 32096
    assert current["changed_words"] == {} and current["candidate_changes"] == []
    assert current["actual_prior_companions"] == {}
    assert (
        current["after_word_sha256"]
        == hashlib.sha256(
            json.dumps(
                current["after_words"], ensure_ascii=False, sort_keys=True
            ).encode()
        ).hexdigest()
    )
    assert (
        hashlib.sha256(current["producer"]["text"].encode()).hexdigest()
        == current["producer"]["sha256"]
    )
    source = read("docs/reported-dana-prototype-source-streams.json.gz")
    assert (
        source["frozen_inputs"][
            "/home/josh/projects/klem/web/test-results/reported-dana-prototype-cargo/debug/klem"
        ]
        == current["cli_sha256"]
    )
    assert (
        source["frozen_inputs"][
            "/nix/store/p0xh9pk9m2nm8373vzicgdpx5w1yz6z7-klem-0.1.0/bin/klem"
        ]
        == current["before_cli_sha256"]
    )
    assert len(current["corpora"]) == len(previous["corpora"]) == 4
    checks = []
    for actual, old in zip(current["corpora"], previous["corpora"], strict=True):
        assert all(
            actual[k] == old[k]
            for k in ["corpus", "partition", "source", "source_sha256", "report_lines"]
        )
        assert actual["exit_code"] == 0 and actual["command"][1:] == [
            actual["corpus"],
            actual["source"],
        ]
        assert actual["before_jsonl"] == old["after_jsonl"]
        rows = [json.loads(line) for line in actual["after_jsonl"].splitlines()]
        before = [json.loads(line) for line in actual["before_jsonl"].splitlines()]
        assert rows == before and len(rows) == actual["report_lines"]
        assert (
            actual["changed_gold_outcomes"] == []
            and actual["changed_summary_fields"] == {}
        )
        assert (
            hashlib.sha256(actual["original_source_text"].encode()).hexdigest()
            == actual["source_sha256"]
        )
        for summary in [rows[0], before[0]]:
            assert (
                summary["input_sha256"] == actual["source_sha256"]
                and summary["input"] == actual["source"]
            )
        checks.append(
            {
                "corpus": actual["corpus"],
                "partition": actual["partition"],
                "before": verify_rows(before, previous["after_words"]),
                "after": verify_rows(rows, current["after_words"]),
            }
        )
    assert (
        sum(row["after"]["rows"] for row in checks)
        == current["converted_rows"]
        == 66570
    )
    return checks


def reject(action, label):
    try:
        action()
    except (AssertionError, KeyError):
        print("Rejected corruption:", label, flush=True)
        return
    raise AssertionError("Accepted corruption: " + label)


def verify_rows(rows, word_results):
    counts = []
    matched = 0
    recovered = 0
    gold_total = 0
    transformed = 0
    transformed_matches = 0
    misses = {}
    for row in rows[1:]:
        word = word_results[row["surface"]]
        gold = row["expected"]
        sets = set()
        exact = False
        counts.append(len(word["analyses"]))
        for analysis in word["analyses"]:
            lemmas = [lemma["text"] for lemma in analysis["lemmas"]]
            exact = exact or lemmas == gold
            indices = []
            for lemma in lemmas:
                unused = next(
                    (i for i, g in enumerate(gold) if g == lemma and i not in indices),
                    None,
                )
                if unused is not None:
                    indices.append(unused)
            if indices:
                sets.add(tuple(sorted(indices)))
        maximal = sorted(
            s for s in sets if not any(set(s) < set(other) for other in sets)
        )
        assert row["matched"] == exact, (row["id"], "matched")
        assert row["recovered_sets"] == [list(s) for s in maximal], (
            row["id"],
            "recovered_sets",
        )
        best = max(map(len, maximal), default=0)
        assert row["recovered"] == best, (row["id"], "recovered")
        matched += exact
        recovered += best
        gold_total += len(gold)
        if gold != [word["normalized"]]:
            transformed += 1
            transformed_matches += exact
        if not exact:
            key = (row["surface"], tuple(gold))
            misses[key] = misses.get(key, 0) + 1
    counts.sort()
    n = len(counts)
    summary = rows[0]
    expected = {
        "converted_rows": n,
        "grouped_matches": matched,
        "gold_lemmas": gold_total,
        "recovered_gold_lemmas": recovered,
        "transformed_rows": transformed,
        "transformed_matches": transformed_matches,
        "mean_candidates": sum(counts) / n if n else 0.0,
        "p95_candidates": counts[min(n * 95 // 100, n - 1)] if n else 0,
        "max_candidates": max(counts, default=0),
        "grouped_lemma_recall": matched / n if n else 0.0,
        "lemma_recall": recovered / gold_total if gold_total else 0.0,
        "transformed_grouped_recall": transformed_matches / transformed
        if transformed
        else 0.0,
        "adapter_coverage": n / (summary["rows"] - summary["excluded_rows"])
        if summary["rows"] != summary["excluded_rows"]
        else 0.0,
        "common_misses": [
            {"surface": surface, "expected": list(gold), "count": count}
            for (surface, gold), count in sorted(
                misses.items(), key=lambda pair: (-pair[1], pair[0])
            )[:30]
        ],
    }
    for key, value in expected.items():
        actual = summary[key]
        if isinstance(value, float):
            assert abs(value - actual) <= 1e-12, (key, value, actual)
        else:
            assert actual == value, (key, value, actual)
    return {
        "rows": n,
        "gold_outcomes_verified": True,
        "summary_fields_verified": sorted(expected),
        "candidate_count_sum": sum(counts),
    }


if __name__ == "__main__":
    report = read("docs/reported-dana-prototype-corpora.json.gz")
    print(
        "Verified all66570 gold outcomes and independent candidate metrics;32096 complete words unchanged:",
        verify(report),
        flush=True,
    )
    changed = copy.deepcopy(report)
    changed["corpora"][0]["original_source_text"] += "fabricated"
    reject(lambda: verify(changed), "altered original annotated text")
    changed = copy.deepcopy(report)
    rows = changed["corpora"][0]["after_jsonl"].splitlines()
    changed["corpora"][0]["after_jsonl"] = "\n".join(rows[:-1]) + "\n"
    reject(lambda: verify(changed), "missing gold row")
    changed = copy.deepcopy(report)
    changed["corpora"][1] = copy.deepcopy(changed["corpora"][0])
    reject(lambda: verify(changed), "duplicate partition")
    changed = copy.deepcopy(report)
    word = next(
        w for w, value in changed["after_words"].items() if len(value["analyses"]) > 1
    )
    changed["after_words"][word]["analyses"].reverse()
    reject(lambda: verify(changed), "altered candidate order")
