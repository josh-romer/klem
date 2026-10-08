"""Replay all declared auxiliary spacing requirements against real CLI/API output.

A successful verification certifies the recorded observations and preservation
contracts. It does not certify coverage completion: missing requirements are
retained explicitly, and --require-complete makes them fail the command.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

RULE = "spacing.predicate_auxiliary"
KNOWN_GAPS = {"auxiliary-nominalization-topic"}
MODES = {"raw": [], "headword": ["--dict-only"], "compatible": ["--dict-compatible"]}


def read_json(path):
    with (gzip.open if path.suffix == ".gz" else open)(path, "rt") as stream:
        return json.load(stream)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cases(root):
    base = read_json(root / "tests/fixtures/predicate-auxiliary-spacing-cases.json")
    owners = read_json(root / "tests/fixtures/predicate-auxiliary-spacing-owner-cases.json")
    rows = base["cases"] + [
        {**c, "required_spaces": [c["required_space"]]} for c in owners["cases"]
    ]
    assert len(rows) == 30 and len({c["id"] for c in rows}) == 30
    return rows


def verify_segment(segment, text, replay):
    """Check UTF-8 ownership and exact independent Compatible readings."""
    start, end = segment["span"]["start"], segment["span"]["end"]
    assert 0 <= start < end <= len(text.encode()), "segment bounds"
    assert text.encode()[start:end].decode() == segment["surface"], "segment source bytes"
    original = replay[segment["surface"]]
    assert segment["analysis"]["normalized"] == original["normalized"]
    actual = segment["analysis"]["analyses"]
    assert actual and len(segment["dictionary"]["readings"]) == len(actual)
    assert len(segment["breakdowns"]) == len(actual)
    for analysis, reading, layout in zip(
        actual, segment["dictionary"]["readings"], segment["breakdowns"], strict=True
    ):
        index = original["analyses"].index(analysis)
        assert reading == original["dictionary"]["readings"][index], "independent assessment"
        assert reading["status"] != "incompatible"
        assert layout, "ordered breakdown missing"
        expected = [{"lemma": i} for i in range(len(analysis["lemmas"]))]
        expected += [{"morpheme": i} for i in range(len(analysis["morphemes"]))]
        assert sorted(map(json.dumps, layout)) == sorted(map(json.dumps, expected)), "layout indices"
    original_members = {json.dumps(m["lemma"], sort_keys=True): m for m in original["dictionary"]["lemmas"]}
    required_members = {json.dumps(lemma, sort_keys=True) for analysis in actual for lemma in analysis["lemmas"]}
    assert {json.dumps(m["lemma"], sort_keys=True) for m in segment["dictionary"]["lemmas"]} == required_members, "complete lemma annotations"
    assert segment["dictionary"]["source"] == original["dictionary"]["source"]
    assert segment["dictionary"]["fingerprint"] == original["dictionary"]["fingerprint"]
    for member in segment["dictionary"]["lemmas"]:
        assert member == original_members[json.dumps(member["lemma"], sort_keys=True)], "independent Native entries"


def verify_hypothesis(hypothesis, record, text, replay):
    assert hypothesis["rule"] == RULE
    segments = hypothesis["records"]
    assert len(segments) >= 2
    assert "".join(s["surface"] for s in segments) == record["surface"]
    assert " ".join(s["surface"] for s in segments) == hypothesis["spaced"]
    assert hypothesis["inserted_at"] == [s["span"]["start"] for s in segments[1:]]
    cursor = record["span"]["start"]
    for segment in segments:
        assert segment["span"]["start"] == cursor, "contiguous source segments"
        verify_segment(segment, text, replay)
        cursor = segment["span"]["end"]
    assert cursor == record["span"]["end"]
    contexts = hypothesis["joined_contexts"]
    assert contexts, "joined auxiliary witnesses missing"
    spans = [(c["span"]["start"], c["span"]["end"]) for c in contexts]
    assert len(spans) == len(set(spans)), "joined witnesses must be grouped by their own span"
    for context in contexts:
        assert record["span"]["start"] <= context["span"]["start"] < context["span"]["end"]
        assert context["span"]["end"] == record["span"]["end"]
        verify_segment(context, text, replay)
        for analysis, assessment in zip(context["analysis"]["analyses"], context["dictionary"]["readings"], strict=True):
            auxiliaries = [(i, lemma) for i, lemma in enumerate(analysis["lemmas"]) if lemma["kind"] == "auxiliary"]
            assert auxiliaries, "joined witness has no auxiliary"
            for i, lemma in auxiliaries:
                member = next(m for m in context["dictionary"]["lemmas"] if m["lemma"] == lemma)
                statuses = {a["id"]: a["status"] for a in assessment["lemmas"][i]["entries"]}
                assert any(
                    e["pos"] in {"보조 동사", "보조 형용사"}
                    and statuses.get(e["id"], "incompatible") != "incompatible"
                    for e in member["entries"]
                ), "auxiliary Native POS and assessment"


def verify(report, root):
    requirements = cases(root)
    assert report["requirements"] == requirements, "original requirements changed"
    assert report["inputs_unchanged"] and report["state"] == "verified"
    for relative, digest in report["fixture_sha256"].items():
        assert sha(root / relative) == digest, "fixture bytes changed"
    observations, unmet = [], set()
    expected_runs = {(encoding, mode, cache) for encoding in ["NFC", "NFD"] for mode in MODES for cache in [0, 1, 4096]}
    runs = report["runs"]
    assert len(runs) == len(expected_runs)
    assert {(r["encoding"], r["mode"], r["cache_bytes"]) for r in runs} == expected_runs
    reference_spacing = {}
    for run in runs:
        text = "前🙂「" + " ".join(unicodedata.normalize(run["encoding"], c["surface"]) for c in requirements) + "」"
        assert run["text"] == text
        before, after = run["before"], run["after"]
        assert before == [{k: v for k, v in r.items() if k != "spacing"} for r in after], "word candidate preservation"
        assert all(text.encode()[r["span"]["start"]:r["span"]["end"]].decode() == r["surface"] for r in after)
        words = {r["analysis"]["normalized"]: r for r in after if r.get("analysis")}
        assert set(words) == {c["surface"] for c in requirements} | {"前"}
        if run["encoding"] in reference_spacing:
            assert {w: r["spacing"] for w, r in words.items()} == reference_spacing[run["encoding"]], "filter/cache spacing parity"
        else:
            reference_spacing[run["encoding"]] = {w: r["spacing"] for w, r in words.items()}
        for case in requirements:
            record = words[case["surface"]]
            assert record["spacing"]["complete"], "finite requirement search incomplete"
            auxiliary = [h for h in record["spacing"]["alternatives"] if h.get("rule") == RULE]
            spaces = {unicodedata.normalize("NFC", h["spaced"]) for h in auxiliary}
            if not case["required_spaces"]:
                assert not auxiliary, (case["id"], "unexpected auxiliary option")
            missing = [s for s in case["required_spaces"] if s not in spaces]
            if missing:
                unmet.add(case["id"])
                assert case["id"] in KNOWN_GAPS, (case["id"], "new regression")
            observations.append({"case_id": case["id"], "encoding": run["encoding"], "mode": run["mode"], "cache_bytes": run["cache_bytes"], "missing": missing})
            for h in auxiliary:
                verify_hypothesis(h, record, text, report["independent_replay"])
    assert report["observations"] == observations, "individual requirement observations"
    assert report["unmet_requirements"] == sorted(unmet), "missing requirements hidden"
    assert report["coverage_complete"] == (not unmet), "completion claim"
    for encoding, response in report["api"].items():
        raw = next(r for r in runs if r["encoding"] == encoding and r["mode"] == "raw" and r["cache_bytes"] == 4096)
        assert response["records"] == raw["after"], "actual API/CLI parity"
        assert response["rules"][RULE] and response["rules"]["auxiliary"]
    if report["api"]:
        assert set(report["api"]) == {"NFC", "NFD"}
        assert len(report["native"]) == 105
        closure = read_json(root / "docs/predicate-auxiliary-spacing-owner-native-closure.json.gz")
        assert report["native"] == closure["complete_native_entries"], "complete Native endpoints"
    return {"runs": len(runs), "observations": len(observations), "unmet_requirements": sorted(unmet), "coverage_complete": not unmet}


def capture(args):
    root = args.root.resolve()
    requirements = cases(root)
    paths = [args.cli.resolve(), args.dictionary.resolve(), Path(__file__).resolve()]
    fixtures = [root / "tests/fixtures" / n for n in ["predicate-auxiliary-spacing-cases.json", "predicate-auxiliary-spacing-owner-cases.json", "predicate-auxiliary-spacing-native.json"]]
    frozen = {str(p): sha(p) for p in paths + fixtures}
    report = {"state": "verified", "requirements": requirements, "runs": [], "independent_replay": {}, "api": {}, "native": {}, "fixture_sha256": {str(p.relative_to(root)): sha(p) for p in fixtures}, "frozen_inputs": frozen, "scope": "Finite declared structural requirements and exact CLI/API/Native/cache/Unicode preservation. Intended spacing, contextual senses, broader distributions and independent Korean review remain separate."}

    def cli(command, text=None):
        return subprocess.check_output([str(args.cli.resolve()), *command, "--dictionary", str(args.dictionary.resolve())], input=None if text is None else text.encode())

    def post(route, body):
        request = urllib.request.Request(args.url.rstrip("/") + "/api/" + route, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    for encoding in ["NFC", "NFD"]:
        text = "前🙂「" + " ".join(unicodedata.normalize(encoding, c["surface"]) for c in requirements) + "」"
        if args.url:
            report["api"][encoding] = post("analyze", {"text": text, "suggest_spacing": True})
        for mode, flags in MODES.items():
            for cache in [0, 1, 4096]:
                command = ["text", "-", *flags, "--cache-bytes", str(cache)]
                before = [json.loads(line) for line in cli(command, text).splitlines()]
                after = [json.loads(line) for line in cli(command + ["--suggest-spacing"], text).splitlines()]
                report["runs"].append({"encoding": encoding, "mode": mode, "cache_bytes": cache, "text": text, "before": before, "after": after})
                for record in after:
                    for h in record.get("spacing", {}).get("alternatives", []):
                        if h.get("rule") == RULE:
                            for segment in h["records"] + h["joined_contexts"]:
                                surface = segment["surface"]
                                if surface not in report["independent_replay"]:
                                    report["independent_replay"][surface] = json.loads(cli(["word", surface, "--dict-compatible"]))
    if args.url:
        closure = read_json(root / "docs/predicate-auxiliary-spacing-owner-native-closure.json.gz")
        for ident in closure["complete_native_entries"]:
            report["native"][ident] = post("entry", {"id": ident})["entry"]
    observations, unmet = [], set()
    for run in report["runs"]:
        words = {r["analysis"]["normalized"]: r for r in run["after"] if r.get("analysis")}
        for case in requirements:
            spaces = {unicodedata.normalize("NFC", h["spaced"]) for h in words[case["surface"]]["spacing"]["alternatives"] if h.get("rule") == RULE}
            missing = [s for s in case["required_spaces"] if s not in spaces]
            if missing:
                unmet.add(case["id"])
            observations.append({"case_id": case["id"], "encoding": run["encoding"], "mode": run["mode"], "cache_bytes": run["cache_bytes"], "missing": missing})
    report.update(observations=observations, unmet_requirements=sorted(unmet), coverage_complete=not unmet, inputs_unchanged=all(sha(Path(p)) == h for p, h in frozen.items()))
    # Retain observations even if verification reveals a regression.
    raw = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    with args.output.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if args.output.suffix == ".gz" else raw)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    if args.verify:
        report = read_json(args.verify)
    else:
        if not (args.cli and args.dictionary and args.output):
            parser.error("capture requires --cli, --dictionary and --output")
        report = capture(args)
    result = verify(report, args.root.resolve())
    print(json.dumps(result))
    if args.require_complete and not result["coverage_complete"]:
        raise SystemExit("Unmet required spacing cases remain; coverage is incomplete.")


if __name__ == "__main__":
    main()
