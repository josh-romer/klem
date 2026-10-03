"""Verify native POS policy against full CLI/API output and served assets."""

import argparse, copy, gzip, hashlib, json, sqlite3, subprocess, urllib.request
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--cli", type=Path, required=True)
p.add_argument("--before-cli", type=Path, required=True)
p.add_argument("--server", type=Path, required=True)
p.add_argument("--assets", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--expected", type=Path)
p.add_argument("--url")
a = p.parse_args()
R = Path(__file__).resolve().parents[1]
DB = R / "data/dictionaries/krdict/krdict.db"
src = json.load(open(R / "tests/fixtures/native-pos-sources.json"))
additional = json.load(open(R / "tests/fixtures/native-pos-boundaries.json"))
src["before_words"].update(additional["before_words"])
pol = json.load(open(R / "tests/fixtures/native-pos-policy.json"))
server = None
assert not a.output.exists()


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def word(cli, surface, flag):
    return json.loads(
        subprocess.check_output(
            [
                str(cli),
                "word",
                surface,
                "--dictionary",
                str(DB),
                *([flag] if flag else []),
            ]
        )
    )


def post(path, body):
    req = urllib.request.Request(
        base + "/api/" + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def path_matches(x, j):
    return x["lemmas"] == [
        dict(text=t, kind=k) for t, k in zip(j["lemmas"], j["lemma_kinds"])
    ] and x["morphemes"] == [
        dict(form=t, kind=k) for t, k in zip(j["morphemes"], j["morpheme_kinds"])
    ]


try:
    if a.url:
        base = a.url
    else:
        server = subprocess.Popen(
            [
                str(a.server),
                "--port",
                "0",
                "--assets",
                str(a.assets),
                "--dictionary",
                str(DB),
            ],
            stderr=subprocess.PIPE,
            text=True,
        )
        line = server.stderr.readline().strip()
        assert "http://127.0.0.1:" in line
        base = "http://" + line.split("http://", 1)[1].split()[0]
    expected = json.load(a.expected.open()) if a.expected else None
    values = {}
    changes = []
    checks = []
    for surface, frozen in src["before_words"].items():
        modes = {}
        for mode, flag in [
            ("raw", None),
            ("headword", "--dict-only"),
            ("compatible", "--dict-compatible"),
        ]:
            b, c = word(a.before_cli, surface, flag), word(a.cli, surface, flag)
            if mode != "compatible":
                assert b["analyses"] == c["analyses"], (surface, mode)
            if mode == "raw":
                assert {k: v for k, v in c.items() if k != "dictionary"} == frozen
            if expected:
                assert c == expected["words"][surface][mode]["after"], (
                    surface,
                    mode,
                    "packaged mismatch",
                )
            modes[mode] = dict(before=b, after=c)
        api = post("analyze", dict(text=surface))
        records = [
            json.loads(l)
            for l in subprocess.check_output(
                [str(a.cli), "text", "-", "--dictionary", str(DB)],
                input=surface.encode(),
            ).splitlines()
        ]
        assert api["records"] == records, surface
        if expected:
            assert {k: v for k, v in api.items() if k != "elapsed_ms"} == {
                k: v
                for k, v in expected["words"][surface]["api"].items()
                if k != "elapsed_ms"
            }, (surface, "full API")
        assert api["records"][0]["analysis"] == frozen
        assert len(api["breakdowns"][0]) == len(frozen["analyses"])
        for i, (b, c) in enumerate(
            zip(
                modes["raw"]["before"]["dictionary"]["readings"],
                modes["raw"]["after"]["dictionary"]["readings"],
            )
        ):
            if b != c:
                changes.append(
                    dict(
                        surface=surface,
                        raw_index=i,
                        analysis=frozen["analyses"][i],
                        breakdown=api["breakdowns"][0][i],
                        before=b,
                        after=c,
                        scope="Scoped class-policy observation; raw and contextual grammar unchanged.",
                    )
                )
        modes["api"] = api
        values[surface] = modes
    for case in pol["cases"]:
        j = case["judgments"][0]
        m = values[case["surface"]]
        raw = m["raw"]["after"]
        indices = [i for i, x in enumerate(raw["analyses"]) if path_matches(x, j)]
        assert indices, case["id"]
        index = indices[0]
        retained = any(path_matches(x, j) for x in m["compatible"]["after"]["analyses"])
        assert retained == (j["verdict"] == "required"), case["id"]
        assert any(path_matches(x, j) for x in m["headword"]["after"]["analyses"])
        checks.append(
            dict(
                case=case["id"],
                raw_index=index,
                headword_retained=True,
                compatible_retained=retained,
                reading=raw["dictionary"]["readings"][index],
            )
        )
    with sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True) as db:
        native = json.loads(
            db.execute(
                "SELECT data FROM entries WHERE id=?", ("krdict:600930",)
            ).fetchone()[0]
        )
    assert (
        native
        == src["source_entries"][0]
        == post("entry", dict(id="krdict:600930"))["entry"]
    )
    frontend = []
    for file in sorted(a.assets.rglob("*")):
        if file.is_file():
            relative = file.relative_to(a.assets)
            remote = "/" if str(relative) == "index.html" else "/" + str(relative)
            with urllib.request.urlopen(base + remote, timeout=30) as response:
                served = response.read()
            assert (
                served == file.read_bytes() == (R / "web/dist" / relative).read_bytes()
            ), relative
            frontend.append(
                dict(path=str(relative), sha256=hashlib.sha256(served).hexdigest())
            )
    report = dict(
        schema_version=1,
        checklist="COV-021q",
        cli=str(a.cli),
        cli_sha256=sha(a.cli),
        before_cli=str(a.before_cli),
        before_cli_sha256=sha(a.before_cli),
        server=str(a.server),
        server_sha256=sha(a.server),
        assets=str(a.assets),
        dictionary_sha256=sha(DB),
        source_fixture_sha256=sha(R / "tests/fixtures/native-pos-sources.json"),
        additional_fixture_sha256=sha(R / "tests/fixtures/native-pos-boundaries.json"),
        complete_native_entry=native,
        words=values,
        changed_raw_assessments=changes,
        policy_checks=checks,
        frontend=frontend,
        all_raw_candidates_and_indices_unchanged=True,
        all_headword_candidates_unchanged=True,
        all_cli_api_records_and_native_fields_equal=True,
        packaged_matches_expected=bool(expected),
    )
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        len(values),
        "surfaces,",
        len(values) * 6,
        "full CLI outputs,",
        len(changes),
        "changed assessments,",
        len(checks),
        "policy checks, full API/native/assets equal",
        flush=True,
    )
finally:
    if server:
        server.terminate()
        server.wait(timeout=30)
