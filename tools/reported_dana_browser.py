"""Verify integrated authored and corpus diagrams, exports and complete dictionary entries."""

import argparse
import base64
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    import gzip

    p = ROOT / name
    return json.loads(
        gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
    )


def sha(name):
    return hashlib.sha256(Path(name).read_bytes()).hexdigest()


def semantic(response):
    return {key: value for key, value in response.items() if key != "elapsed_ms"}


def capture(web, cli, assets, prefix, chromium):
    prefix = str(Path(prefix).resolve())
    log = Path(prefix + "-preview.log")
    receipt = Path(prefix + "-browser-result.json")
    assert not log.exists() and not receipt.exists()
    args = [
        str(Path(web).resolve()),
        "--assets",
        str(Path(assets).resolve()),
        "--port",
        "0",
        "--dictionary",
        str(ROOT / "data/dictionaries/krdict/krdict.db"),
    ]
    result = {"schema_version": 1, "state": "running", "command": args}
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    with log.open("xb") as stream:
        server = subprocess.Popen(
            args,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
    record = None
    try:
        deadline = time.monotonic() + 20
        while True:
            assert server.poll() is None
            match = re.search(r"http://127\.0\.0\.1:\d+", log.read_text())
            if match:
                break
            assert time.monotonic() < deadline
            time.sleep(0.1)
        url = match[0]
        proc = Path("/proc") / str(server.pid)
        record = {
            "pid": server.pid,
            "uid": os.getuid(),
            "start_ticks": int(
                (proc / "stat").read_text().rsplit(")", 1)[1].split()[19]
            ),
            "exe": str((proc / "exe").resolve()),
            "exe_sha256": sha(proc / "exe"),
            "cwd": str((proc / "cwd").resolve()),
            "args": args,
            "url": url,
        }
        with urllib.request.urlopen(url + "/api/status", timeout=10) as response:
            record["status"] = json.load(response)
        Path(prefix + "-preview.json").write_text(json.dumps(record, indent=2) + "\n")
        env = os.environ.copy()
        env.update(
            KLEM_WEB_URL=url,
            KLEM_BIN=str(Path(cli).resolve()),
            KLEM_CAPTURE_PREFIX=prefix,
            CHROMIUM_PATH=chromium,
        )
        command = ["node", str(ROOT / "web/tests/reported-dana.mjs")]
        browser = subprocess.run(command, cwd=ROOT, env=env)
        result["browser_command"] = command
        result["exit_code"] = browser.returncode
        browser.check_returncode()
        current = json.loads(Path(prefix + "-browser.json").read_text())
        assert len(current["diagrams"]) == 220 and len(current["native"]) == 208
        assert len(current["records"]) == 6 and current["errors"] == []
        prior = read("docs/reported-deoni-main-browser.json.gz")["browser"]
        by_case = {(d["case_id"], d["encoding"]): d for d in current["diagrams"]}
        assert len(prior["diagrams"]) == 148
        for previous in prior["diagrams"]:
            assert by_case[previous["case_id"], previous["encoding"]] == previous
        result["prior_diagrams_verified"] = 148
        screenshots = {}
        for viewport in ["desktop", "mobile"]:
            path = Path(prefix + "-" + viewport + ".png")
            raw = path.read_bytes()
            assert raw.startswith(b"\x89PNG\r\n\x1a\n")
            screenshots[viewport] = {
                "sha256": sha(path),
                "base64": base64.b64encode(raw).decode(),
            }
        result.update(
            state="passed",
            prototype=True,
            browser=current,
            screenshots=screenshots,
            cli_sha256=sha(cli),
            web_sha256=sha(web),
            preview=record,
            native_source_sha256=sha(
                ROOT / "docs/reported-dana-browser-native.json.gz"
            ),
            browser_producer_sha256=sha(ROOT / "web/tests/reported-dana.mjs"),
            producer={"text": Path(__file__).read_text(), "sha256": sha(__file__)},
        )
    except BaseException as error:
        result.update(state="failed", error=repr(error))
        raise
    finally:
        if server.poll() is None:
            if record:
                proc = Path("/proc") / str(server.pid)
                assert str((proc / "exe").resolve()) == record["exe"]
                assert (
                    int((proc / "stat").read_text().rsplit(")", 1)[1].split()[19])
                    == record["start_ticks"]
                )
                assert [
                    s.decode()
                    for s in (proc / "cmdline").read_bytes().split(b"\0")
                    if s
                ] == args
            server.send_signal(signal.SIGINT)
        server.wait(timeout=10)
        result["owned_preview_stopped"] = True
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        "Prototype browser verifies220 diagrams,6 exports,208 complete Native endpoints; owned preview stopped.",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--chromium", required=True)
    args = parser.parse_args()
    capture(args.web, args.cli, args.assets, args.prefix, args.chromium)
