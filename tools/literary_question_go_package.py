"""Bind actual Nix outputs, release tests, CLI, adapter, browser and launcher captures."""
import json
import re
from pathlib import Path

from ostensible_reason_audit import ROOT, producer, read, sha
from ostensible_reason_runtime import without_elapsed
from literary_question_go_runtime import verify_cli
from literary_question_go_adapter_audit import inspect as verify_adapter
from literary_question_go_browser_audit import inspect as verify_browser


def inspect(package, cli, adapter, runtime, browser, launcher):
    producer(package)
    assert package['state'] == 'passed' and package['exit_code'] == 0
    assert package['snapshot_unchanged'] is True
    log_path = ROOT/'docs/literary-question-go-package-nix.log.gz'
    import gzip
    log = gzip.decompress(log_path.read_bytes())
    assert sha(log) == package['log_sha256']
    batches = re.findall(r'test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', log.decode())
    tests = {key: sum(int(row[i]) for row in batches)
             for i, key in enumerate(['passed', 'failed', 'ignored'])}
    tests['batches'] = len(batches)
    assert tests == {'passed': 1052, 'failed': 0, 'ignored': 1, 'batches': 222}
    assert len(package['snapshot']['files']) == 939
    rust = read(ROOT/'docs/literary-question-go-main-full-rust.json')
    assert rust['state'] == 'passed' and rust['tests'] == tests
    assert runtime['source_snapshot'] == rust['snapshot']['files']
    assert len(rust['snapshot']['files']) == 922
    for name, record in rust['snapshot']['files'].items():
        assert package['snapshot']['files'][name] == record
    assert len(runtime['frontend_snapshot']) == 18
    for name, digest in runtime['frontend_snapshot'].items():
        assert package['snapshot']['files']['web/'+name]['sha256'] == digest
    assert set(package['source_profiles']) == {'klem', 'web-assets', 'corpus-adapter'}
    assert package['source_profiles']['klem'] == package['source_profiles']['corpus-adapter']
    assert all(re.fullmatch(r'/nix/store/[a-z0-9]{32}-source', value)
               for value in package['source_profiles'].values())
    assert len(package['outputs']) == len(set(package['outputs'])) == 3
    main = next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    adapter_path = next(p for p in package['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))
    assets = next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0'))+'/share/klem-web'
    assert cli['cli'] == main+'/bin/klem'
    assert adapter['adapter'] == adapter_path+'/bin/klem-corpus-adapter'
    cli_summary = verify_cli(cli)
    adapter_summary = verify_adapter(adapter, read(ROOT/'docs/literary-question-go-prototype-corpora.json.gz'))
    assert runtime['cli'] == cli['cli'] and browser['cli_sha256'] == cli['cli_sha256']
    assert runtime['command'][2] == assets
    copied_server = runtime['command'][0]
    assert runtime['frozen_inputs'][copied_server] == launcher['server_sha256']
    browser_summary = verify_browser(
        runtime, browser, read(ROOT/'docs/literary-question-go-boundary-matched-owner-preparation.json.gz'),
        browser_path=ROOT/'docs/literary-question-go-packaged-browser.json')
    producer(launcher)
    assert launcher['producer']['text'] == (ROOT/'tools/capture_literary_question_go_launcher.py').read_text()
    assert launcher['state'] == 'passed' and launcher['exit_code'] == 0
    assert launcher['inputs_unchanged'] is True and launcher['server_stopped'] is True
    assert launcher['server_exit_code'] in [-2, 130] and launcher['help_exit_code'] == 0
    assert launcher['cli'] == cli['cli'] and launcher['cli_sha256'] == cli['cli_sha256']
    assert launcher['server'] == main+'/bin/klem-web' and launcher['assets'] == assets
    assert launcher['package_sha256'] == sha((ROOT/'docs/literary-question-go-package-nix.json').read_bytes())
    assert sha(launcher['launcher_text'].encode()) == launcher['launcher_sha256']
    assert [line for line in launcher['launcher_text'].splitlines() if line.startswith('exec ')] == [
        f'exec {launcher["server"]} --assets {assets} "$@"']
    assert launcher['frozen_inputs'][launcher['launcher']] == launcher['launcher_sha256']
    assert launcher['frozen_inputs'][launcher['server']] == launcher['server_sha256']
    assert launcher['index_sha256'] == runtime['asset_snapshot']['index.html']
    assert len(launcher['asset_checks']) == 2
    for check in launcher['asset_checks']:
        assert check['sha256'] == runtime['asset_snapshot'][check['path'].lstrip('/')]
    launched = read(ROOT/'docs/literary-question-go-launcher-browser.json')
    assert launcher['browser_sha256'] == sha((ROOT/'docs/literary-question-go-launcher-browser.json').read_bytes())
    assert launched['cli_sha256'] == cli['cli_sha256'] and launched['errors'] == []
    for key in ['diagrams', 'exports', 'native', 'opened', 'modeJudgments', 'conditionalExports',
                'conditionalDiagrams', 'conditionalModeJudgments']:
        assert launched[key] == browser[key]
    assert len(launcher['responses']) == 2
    for response, original in zip(launcher['responses'], browser['responses'], strict=True):
        assert response['encoding'] == original['encoding']
        assert response['request'] == original['request']
        assert without_elapsed(response['after']) == without_elapsed(original['after'])
    return {'release_tests': tests, 'compile_and_frontend_inputs': 939,
            'cli': cli_summary, 'adapter': adapter_summary, 'browser': browser_summary,
            'launcher_assets': 2, 'launcher_original_api_frames': 1070,
            'owned_servers_stopped': True}


def inputs():
    return [read(ROOT/'docs'/name) for name in [
        'literary-question-go-package-nix.json', 'literary-question-go-packaged-cli-replay.json',
        'literary-question-go-packaged-adapter.json.gz', 'literary-question-go-packaged-browser-runtime.json',
        'literary-question-go-packaged-browser.json', 'literary-question-go-launcher-web-launcher.json']]


if __name__ == '__main__':
    print(inspect(*inputs()))
