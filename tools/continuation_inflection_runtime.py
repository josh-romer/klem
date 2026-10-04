"""Verify full-native continuation cohorts through CLI streams and local API."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def post(base, endpoint, body):
    req = urllib.request.Request(
        base + "/api/" + endpoint,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def identity(pid):
    path = Path("/proc") / str(pid)
    return {
        "uid": path.stat().st_uid,
        "start": path.joinpath("stat").read_text().rsplit(")", 1)[1].split()[19],
        "exe": str(path.joinpath("exe").resolve()),
        "cwd": str(path.joinpath("cwd").resolve()),
        "args": path.joinpath("cmdline").read_bytes().split(b"\0")[:-1],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", type=Path, required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--url")
    a = p.parse_args()
    assert not a.output.exists()
    source = json.loads(
        (ROOT / "tests/fixtures/continuation-inflection-sources.json").read_text()
    )
    extra = json.loads(
        (ROOT / "tests/fixtures/continuation-inflection-additional.json").read_text()
    )
    frozen = dict(source["before_words"])
    frozen.update(extra["before_words"])
    db = ROOT / "data/dictionaries/krdict/krdict.db"
    assert sha(db) == source["dictionary_sha256"]
    cli = a.cli.resolve()
    server = a.server.resolve()
    owned = None
    try:
        if a.url:
            base = a.url
        else:
            owned = subprocess.Popen(
                [
                    str(server),
                    "--port",
                    "0",
                    "--assets",
                    str(a.assets.resolve()),
                    "--dictionary",
                    str(db),
                ],
                stderr=subprocess.PIPE,
                text=True,
            )
            stamp = identity(owned.pid)
            assert (
                stamp["uid"] == os.getuid()
                and stamp["exe"] == str(server)
                and stamp["cwd"] == str(ROOT)
            )
            line = owned.stderr.readline().strip()
            assert "http://127.0.0.1:" in line, line
            base = "http://" + line.split("http://", 1)[1].split()[0]
        words = {}
        for i, (surface, modes) in enumerate(frozen.items()):
            actual = {}
            for mode, flags in [
                ("all", []),
                ("headword", ["--dict-only"]),
                ("compatible", ["--dict-compatible"]),
            ]:
                actual[mode] = json.loads(
                    subprocess.check_output(
                        [str(cli), "word", surface, "--dictionary", str(db), *flags]
                    )
                )
                if mode != "compatible":
                    assert {
                        k: v for k, v in actual[mode].items() if k != "dictionary"
                    } == {k: v for k, v in modes[mode].items() if k != "dictionary"}, (
                        surface
                    )
            api = post(base, "analyze", {"text": surface, "suggest_spacing": False})
            records = [
                json.loads(x)
                for x in subprocess.check_output(
                    [str(cli), "text", "--dictionary", str(db)], input=surface.encode()
                ).splitlines()
            ]
            assert api["records"] == records
            assert len(api["breakdowns"]) == 1 and len(api["breakdowns"][0]) == len(
                actual["all"]["analyses"]
            )
            for path, components in zip(
                actual["all"]["analyses"], api["breakdowns"][0], strict=True
            ):
                assert len(components) == len(path["lemmas"]) + len(path["morphemes"])
            words[surface] = dict(actual, api=api)
            if (i + 1) % 50 == 0:
                print(i + 1, "source word API responses verified", flush=True)
        streams = []
        for nfd in [False, True]:
            surfaces = [unicodedata.normalize("NFD", s) if nfd else s for s in frozen]
            text = " ".join(surfaces)
            for cache in [0, 1, 4096]:
                for mode, flags in [
                    ("all", []),
                    ("headword", ["--dict-only"]),
                    ("compatible", ["--dict-compatible"]),
                ]:
                    data = subprocess.check_output(
                        [
                            str(cli),
                            "text",
                            "--dictionary",
                            str(db),
                            "--cache-bytes",
                            str(cache),
                            *flags,
                        ],
                        input=text.encode(),
                    )
                    all_records = [json.loads(x) for x in data.splitlines()]
                    assert "".join(r["surface"] for r in all_records) == text
                    records = [r for r in all_records if r["kind"] == "word"]
                    assert len(records) == len(surfaces)
                    for s, r in zip(surfaces, records, strict=True):
                        assert (
                            r["surface"] == s
                            and text.encode()[
                                r["span"]["start"] : r["span"]["end"]
                            ].decode()
                            == s
                        )
                        expected = words[unicodedata.normalize("NFC", s)][mode]
                        assert (
                            r["analysis"]
                            == {k: v for k, v in expected.items() if k != "dictionary"}
                            and r["dictionary"] == expected["dictionary"]
                        )
                    streams.append(
                        {
                            "normalization": "NFD" if nfd else "NFC",
                            "cache_bytes": cache,
                            "mode": mode,
                            "records": len(records),
                            "jsonl_sha256": hashlib.sha256(data).hexdigest(),
                        }
                    )
                    print("stream", nfd, cache, mode, "verified", flush=True)
        native = dict(source["complete_native_entries"])
        native.update(extra["complete_native_entries"])
        for ident, entry in native.items():
            assert post(base, "entry", {"id": ident})["entry"] == entry, ident
        report = {
            "schema_version": 1,
            "checklist": "COV-019ae",
            "cli": str(cli),
            "cli_sha256": sha(cli),
            "server": str(server),
            "server_sha256": sha(server),
            "dictionary_sha256": sha(db),
            "words": words,
            "streams": streams,
            "complete_native_api_entries": len(native),
            "all_ordered_paths_and_utf8_spans_verified": True,
            "contextual_verdict": "unjudged",
        }
        a.output.write_bytes(
            gzip.compress(
                json.dumps(report, ensure_ascii=False, indent=2).encode(), mtime=0
            )
        )
        print(
            len(words),
            "words;",
            len(streams),
            "streams;",
            len(native),
            "complete native API entries verified",
            flush=True,
        )
    finally:
        if owned is not None and owned.poll() is None:
            assert identity(owned.pid) == stamp, "Owned server identity changed"
            owned.terminate()
            owned.wait(timeout=10)


if __name__ == "__main__":
    main()
