"""Audit installed spacing evidence without treating finite coverage as completion."""

import gzip
import hashlib
import json
import math
import re
from pathlib import Path

from predicate_auxiliary_spacing_runtime import verify as runtime_verify
from predicate_auxiliary_spacing_sources import inspect as source_inspect
from predicate_auxiliary_spacing_adapter_audit import inspect as adapter_inspect

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    path = ROOT / "docs" / ("predicate-auxiliary-spacing-" + name)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if name.endswith(".gz") else raw)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect():
    package = read("package-nix.json")
    assert package["state"] == "passed" and package["exit_code"] == 0
    assert package["snapshot_unchanged"]
    assert sha(package["producer"]["text"].encode()) == package["producer"]["sha256"]
    log = gzip.decompress((ROOT / "docs/predicate-auxiliary-spacing-package-nix.log.gz").read_bytes())
    assert sha(log) == package["log_sha256"]
    batches = re.findall(rb"klem> test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;", log)
    assert len(batches) == 230
    assert tuple(sum(int(row[i]) for row in batches) for i in range(3)) == (1069, 0, 1)
    sources = source_inspect(ROOT / "docs/predicate-auxiliary-spacing-historical-sources.json.gz")
    assert len(sources) == 969
    paths = {}
    for name in ["klem", "web-assets", "corpus-adapter"]:
        matches = [p for p in package["outputs"] if p.endswith("-" + name + "-0.1.0")]
        assert len(matches) == 1
        paths[name] = matches[0]
    assert len(package["outputs"]) == 3
    cli = read("packaged-cli.json")
    assert cli["state"] == "passed" and cli["exit_code"] == 0 and cli["inputs_unchanged"]
    assert cli["cli"] == paths["klem"] + "/bin/klem"
    assert cli["snapshot_files"] == package["snapshot"]["files"]
    assert cli["package_sha256"] == sha((ROOT / "docs/predicate-auxiliary-spacing-package-nix.json").read_bytes())
    assert cli["producer"]["text"] == (ROOT / "tools/capture_predicate_auxiliary_spacing_cli.py").read_text()
    assert sha(cli["producer"]["text"].encode()) == cli["producer"]["sha256"]
    broad = read("main-broad.json.gz")
    assert len(cli["broad"]) == len(broad["comparisons"]) == 8
    for actual, expected in zip(cli["broad"], broad["comparisons"], strict=True):
        command = expected["commands"][1].copy()
        command[0] = cli["cli"]
        assert actual == {"mode": expected["mode"], "source": expected["source"], "source_sha256": expected["source_sha256"], "command": command, "records": expected["records"], "output_sha256": expected["after_jsonl_sha256"], "exit_code": 0, "exact_captured_output": True}
    assert sum(r["records"] for r in cli["broad"]) == 1128312
    assert len(cli["finite_runs"]) == 12
    for family, name in [("source", "main-source-replay"), ("boundary", "main-boundary-preflight")]:
        previous = json.loads(gzip.decompress((ROOT / "docs" / ("additive-ppundeoreo-" + name + ".json.gz")).read_bytes()))
        actual_runs = [r for r in cli["finite_runs"] if r["family"] == family]
        assert len(actual_runs) == 6
        for actual, old in zip(actual_runs, previous["runs"], strict=True):
            command = old["command"].copy()
            command[0] = cli["cli"]
            assert actual["command"] == command and actual["exit_code"] == 0
            assert actual["output_sha256"] == sha(old["jsonl"].encode())
            assert (actual["encoding"], actual["mode"], actual["records"], actual["input_sha256"]) == (old["encoding"], old["mode"], old["records"], old["input_sha256"])
    assert sorted(r["surfaces"] for r in cli["words"]) == [21406, 32096]
    cohorts = json.loads(gzip.decompress((ROOT / "docs/additive-ppundeoreo-main-corpus-history.json.gz").read_bytes()))["cohorts"]
    assert cli["words"] == [{"family": r["family"], "surfaces": len(r["after_words"]), "word_sha256": r["after_word_sha256"], "exact_captured_output": True} for r in cohorts]
    adapter = read("packaged-adapter.json.gz")
    assert adapter["adapter"] == paths["corpus-adapter"] + "/bin/klem-corpus-adapter"
    assert adapter["snapshot_files"] == package["snapshot"]["files"]
    original = json.loads(gzip.decompress((ROOT / "docs/literary-question-geona-prototype-corpora.json.gz").read_bytes()))
    adapter_inspect(adapter, original)
    main = read("main-portable-runtime.json.gz")
    installed = read("packaged-portable-runtime.json.gz")
    for report in [main, installed]:
        result = runtime_verify(report, ROOT)
        assert result["observations"] == 540 and not result["coverage_complete"]
    assert installed["frozen_inputs"][cli["cli"]] == cli["cli_sha256"]
    for key in ["runs", "requirements", "observations", "unmet_requirements", "independent_replay", "native"]:
        assert installed[key] == main[key], key
    browser, main_browser = read("packaged-browser.json.gz"), read("main-browser.json.gz")
    web = read("packaged-browser-runtime.json.gz")
    assert web["state"] == "passed" and web["exit_code"] == 0 and web["inputs_unchanged"]
    assert web["server_stopped"] and web["server_exit_code"] in [-2, 130]
    assert web["command"][0] == paths["klem"] + "/bin/klem-web"
    assert web["assets"] == read("main-frontend-build.json.gz")["assets"]
    assert web["snapshot_files"] == package["snapshot"]["files"]
    assert web["browser_sha256"] == sha(json.dumps(browser, ensure_ascii=False, indent=2).encode() + b"\n")
    for key in ["exports", "diagrams", "native", "errors"]:
        assert browser[key] == main_browser[key], key
    assert len(browser["diagrams"]) == 156 and len(browser["exports"]) == 6 and len(browser["native"]) == 105
    for key in ["single", "scene"]:
        for value in [browser[key]["elapsed_ms"], main_browser[key]["elapsed_ms"]]:
            assert isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
        assert {k: v for k, v in browser[key].items() if k != "elapsed_ms"} == {k: v for k, v in main_browser[key].items() if k != "elapsed_ms"}
    launcher = read("launcher.json.gz")
    assert launcher["state"] == "actual-current-flake-web-launcher-built"
    assert launcher["help_exit_code"] == 0
    assert launcher["package_sha256"] == cli["package_sha256"]
    assert sha(launcher["launcher_text"].encode()) == launcher["launcher_sha256"]
    assert [line for line in launcher["launcher_text"].splitlines() if line.startswith("exec ")] == [f'exec {paths["klem"]}/bin/klem-web --assets {paths["web-assets"]}/share/klem-web "$@"']
    launched = read("packaged-launcher-browser-runtime.json.gz")
    assert launched["state"] == "passed" and launched["exit_code"] == 0 and launched["inputs_unchanged"]
    assert launched["server_stopped"] and launched["server_exit_code"] in [-2, 130]
    assert launched["snapshot_files"] == package["snapshot"]["files"]
    assert launched["command"] == [launcher["launcher"], "--port", launched["url"].rsplit(":", 1)[1], "--dictionary", "/home/josh/projects/klem/data/dictionaries/krdict/krdict.db"]
    assert launched["frozen_inputs"][launcher["launcher"]] == launcher["launcher_sha256"]
    launched_browser = read("packaged-launcher-browser.json.gz")
    assert launched["browser_sha256"] == sha(json.dumps(launched_browser, ensure_ascii=False, indent=2).encode() + b"\n")
    for key in ["exports", "diagrams", "native", "errors"]:
        assert launched_browser[key] == browser[key], key
    return {"source_inputs": 969, "release_tests": 1069, "broad_frames": 1128312, "original_annotated_rows": 66570, "finite_runtime_observations": 540, "browser_diagrams": 156, "native_endpoints": 105, "coverage_complete": False, "unmet_requirements": installed["unmet_requirements"]}


if __name__ == "__main__":
    print(json.dumps(inspect()))
