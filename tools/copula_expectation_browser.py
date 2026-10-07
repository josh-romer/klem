"""Run and stop an owned local preview, checking complete prototype browser parity."""
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
from copula_expectation_production import ROOT, read, sha


def semantic(response):
    return {key: value for key, value in response.items() if key != 'elapsed_ms'}


def capture(web, cli, assets, prefix, chromium, entries_only=False):
    prefix = str(Path(prefix).resolve())
    log = Path(prefix + '-preview.log')
    receipt = Path(prefix + ('-entries-result.json' if entries_only else '-browser-result.json'))
    assert not log.exists() and not receipt.exists()
    args = [str(Path(web).resolve()), '--assets', str(Path(assets).resolve()), '--port', '0',
            '--dictionary', str(ROOT / 'data/dictionaries/krdict/krdict.db')]
    result = {'schema_version': 1, 'state': 'running', 'command': args}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    with log.open('xb') as stream:
        server = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=stream, stderr=subprocess.STDOUT)
    record = None
    try:
        deadline = time.monotonic() + 20
        while True:
            assert server.poll() is None
            match = re.search(r'http://127\.0\.0\.1:\d+', log.read_text())
            if match:
                break
            assert time.monotonic() < deadline
            time.sleep(.1)
        url = match[0]
        proc = Path('/proc') / str(server.pid)
        record = {'pid': server.pid, 'uid': os.getuid(),
                  'start_ticks': int((proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]),
                  'exe': str((proc / 'exe').resolve()), 'exe_sha256': sha(proc / 'exe'),
                  'cwd': str((proc / 'cwd').resolve()), 'args': args, 'url': url}
        with urllib.request.urlopen(url + '/api/status', timeout=10) as response:
            record['status'] = json.load(response)
        Path(prefix + '-preview.json').write_text(json.dumps(record, indent=2) + '\n')
        if entries_only:
            closure = read('docs/copula-expectation-native-closure.json.gz')
            entries = []
            for ident, expected in sorted(closure['complete_native_entries'].items()):
                request = urllib.request.Request(url + '/api/entry',
                    data=json.dumps({'id': ident}).encode(),
                    headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    assert response.status == 200
                    actual = json.load(response)
                assert actual['entry'] == expected, ident
                entries.append({'id': ident, 'response': actual})
            assert len(entries) == 17
            result.update(state='passed', entries=entries, preview=record,
                          web_sha256=sha(web), cli_sha256=sha(cli),
                          source_sha256=sha(ROOT / 'docs/copula-expectation-native-closure.json.gz'),
                          producer={'text': Path(__file__).read_text(), 'sha256': sha(__file__)})
            print('Verified all17 complete Native/LMF owners through the production entry API.', flush=True)
            return
        env = os.environ.copy()
        env.update(KLEM_WEB_URL=url, KLEM_BIN=str(Path(cli).resolve()),
                   KLEM_CAPTURE_PREFIX=prefix, CHROMIUM_PATH=chromium)
        command = ['node', str(ROOT / 'web/tests/copula-expectation.mjs')]
        browser = subprocess.run(command, cwd=ROOT, env=env)
        result['browser_command'] = command
        result['exit_code'] = browser.returncode
        browser.check_returncode()
        current = json.loads(Path(prefix + '-browser.json').read_text())
        expected = read('docs/copula-expectation-prototype-runtime.json.gz')['browser']
        for key in ['records', 'diagrams', 'native', 'errors']:
            assert current[key] == expected[key], key
        assert len(current['responses']) == len(expected['responses']) == 2
        for actual, old in zip(current['responses'], expected['responses'], strict=True):
            assert actual['encoding'] == old['encoding'] and actual['request'] == old['request']
            assert semantic(actual['response']) == semantic(old['response'])
        screenshots = {}
        for viewport in ['desktop', 'mobile']:
            path = Path(prefix + '-' + viewport + '.png')
            raw = path.read_bytes()
            assert raw.startswith(b'\x89PNG\r\n\x1a\n')
            screenshots[viewport] = {'sha256': sha(path), 'base64': base64.b64encode(raw).decode()}
        result.update(state='passed', prototype_parity=True, browser=current, screenshots=screenshots,
                      cli_sha256=sha(cli), web_sha256=sha(web), preview=record,
                      prototype_sha256=sha(ROOT / 'docs/copula-expectation-prototype-runtime.json.gz'),
                      browser_producer_sha256=sha(ROOT / 'web/tests/copula-expectation.mjs'),
                      producer={'text': Path(__file__).read_text(), 'sha256': sha(__file__)})
    except BaseException as error:
        result.update(state='failed', error=repr(error))
        raise
    finally:
        if server.poll() is None:
            if record:
                proc = Path('/proc') / str(server.pid)
                assert str((proc / 'exe').resolve()) == record['exe']
                assert int((proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]) == record['start_ticks']
                assert [s.decode() for s in (proc / 'cmdline').read_bytes().split(b'\0') if s] == args
            server.send_signal(signal.SIGINT)
        server.wait(timeout=10)
        result['owned_preview_stopped'] = True
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Production browser matches all 42 diagrams, six exports, nine Native endpoints and both full authored API responses.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web', required=True)
    parser.add_argument('--cli', required=True)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--chromium', required=True)
    parser.add_argument('--entries-only', action='store_true')
    args = parser.parse_args()
    capture(args.web, args.cli, args.assets, args.prefix, args.chromium, args.entries_only)
