"""Verify the excluded written-form cohort against immutable CLI/API packages."""

import argparse
import gzip
import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--url")
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Refusing to overwrite runtime evidence."
    root, cli = args.root.resolve(), args.cli.resolve()
    fixture_path = root / "tests/fixtures/excluded-paradigm-sources.json"
    source = json.loads(fixture_path.read_text())
    database = root / "data/dictionaries/krdict/krdict.db"
    assert sha(database) == source["dictionary_sha256"]
    server = None
    try:
        if args.url:
            base = args.url
        else:
            server = subprocess.Popen(
                [
                    str(args.server),
                    "--port",
                    "0",
                    "--assets",
                    str(args.assets),
                    "--dictionary",
                    str(database),
                ],
                stderr=subprocess.PIPE,
                text=True,
            )
            line = server.stderr.readline().strip()
            assert "http://127.0.0.1:" in line, line
            base = "http://" + line.split("http://", 1)[1].split()[0]

        def post(endpoint, body):
            request = urllib.request.Request(
                base + "/api/" + endpoint,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)

        words, texts, empty_checks = {}, {}, []
        for surface, modes in source["before_words"].items():
            actual = {}
            for mode, flags in [
                ("all", []),
                ("headword", ["--dict-only"]),
                ("compatible", ["--dict-compatible"]),
            ]:
                result = json.loads(
                    subprocess.check_output(
                        [
                            str(cli),
                            "word",
                            surface,
                            "--dictionary",
                            str(database),
                            *flags,
                        ]
                    )
                )
                assert result == modes[mode], (surface, mode, "full frozen CLI output")
                actual[mode] = result
            api = post("analyze", dict(text=surface, suggest_spacing=False))
            records = [
                json.loads(line)
                for line in subprocess.check_output(
                    [str(cli), "text", "--dictionary", str(database)],
                    input=surface.encode(),
                ).splitlines()
            ]
            assert api["records"] == records, (surface, "CLI/API records")
            assert len(api["breakdowns"][0]) == len(actual["all"]["analyses"])
            api.pop("elapsed_ms")
            actual["api"] = api
            words[surface] = actual
        for review in source["reviews"]:
            written = review["original_observation"]["written"]
            if not written:
                try:
                    post("analyze", dict(text=written))
                except urllib.error.HTTPError as error:
                    assert error.code == 422
                    empty_checks.append(
                        dict(
                            review=review["id"],
                            status=error.code,
                            body=json.load(error),
                        )
                    )
                else:
                    raise AssertionError("An empty native field is not a sentence.")
                continue
            api = post("analyze", dict(text=written, suggest_spacing=False))
            assert api["records"] == source["before_text_records"][review["id"]]
            assert "".join(r["surface"] for r in api["records"]) == written
            offset = 0
            for record, breakdowns in zip(
                api["records"], api["breakdowns"], strict=True
            ):
                assert record["span"] == dict(
                    start=offset, end=offset + len(record["surface"].encode())
                )
                offset = record["span"]["end"]
                assert (
                    len(breakdowns) == len(record["analysis"]["analyses"])
                    if record["analysis"]
                    else not breakdowns
                )
            assert offset == len(written.encode())
            api.pop("elapsed_ms")
            texts[review["id"]] = api
        entries = {
            ident: post("entry", dict(id=ident))["entry"]
            for ident in source["complete_native_entries"]
        }
        assert entries == source["complete_native_entries"], (
            "complete native entry responses"
        )
        checks = []
        for case in source["cases"]:
            judgment = case["judgments"][0]
            lemmas = [
                dict(text=t, kind=k)
                for t, k in zip(
                    judgment["lemmas"], judgment["lemma_kinds"], strict=True
                )
            ]
            morphemes = [
                dict(form=t, kind=k)
                for t, k in zip(
                    judgment["morphemes"], judgment["morpheme_kinds"], strict=True
                )
            ]
            word = words[case["surface"]]
            indices = [
                i
                for i, a in enumerate(word["all"]["analyses"])
                if a["lemmas"] == lemmas and a["morphemes"] == morphemes
            ]
            required = judgment["verdict"] == "required"
            assert bool(indices) == required, case["id"]
            retained = {}
            for mode in ["headword", "compatible"]:
                retained[mode] = any(
                    a["lemmas"] == lemmas and a["morphemes"] == morphemes
                    for a in word[mode]["analyses"]
                )
                assert retained[mode] == required, (case["id"], mode)
            checks.append(
                dict(
                    case=case["id"],
                    raw_indices=indices,
                    filters=retained,
                    assessments=[
                        word["all"]["dictionary"]["readings"][i] for i in indices
                    ],
                    breakdowns=[word["api"]["breakdowns"][0][i] for i in indices],
                )
            )
        assets = []
        for file in sorted(args.assets.rglob("*")):
            if not file.is_file():
                continue
            relative = file.relative_to(args.assets)
            remote = "/" if str(relative) == "index.html" else "/" + str(relative)
            with urllib.request.urlopen(base + remote, timeout=30) as response:
                assert response.read() == file.read_bytes()
            assets.append(dict(path=str(relative), sha256=sha(file)))
        evidence = dict(
            words=words,
            padded_texts=texts,
            empty_api_checks=empty_checks,
            native_entries=entries,
            cases=checks,
            assets=assets,
        )
        if args.expected:
            with gzip.open(args.expected, "rt") as file:
                assert evidence == json.load(file)["evidence"], (
                    "preview/package mismatch"
                )
        report = dict(
            schema_version=1,
            checklist="COV-021r",
            fixture_sha256=sha(fixture_path),
            cli=str(cli),
            cli_sha256=sha(cli),
            server=str(args.server),
            server_sha256=sha(args.server),
            dictionary_sha256=sha(database),
            assets=str(args.assets),
            url=base,
            full_cli_responses=3 * len(words),
            word_api_responses=len(words),
            padded_text_api_responses=len(texts),
            empty_api_responses=len(empty_checks),
            complete_entry_responses=len(entries),
            ledger_cases=len(checks),
            evidence=evidence,
        )
        with gzip.open(args.output, "wt", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=False)
            file.write("\n")
        print(
            json.dumps(
                {key: val for key, val in report.items() if key != "evidence"},
                ensure_ascii=False,
            )
        )
    finally:
        if server:
            server.terminate()
            server.wait(timeout=30)


if __name__ == "__main__":
    main()
