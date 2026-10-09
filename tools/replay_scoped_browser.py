"""Replay the six nested-suffix diagrams against source-bound Nix packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['cli', 'server', 'assets', 'dictionary', 'rust-source',
                 'web-source', 'chromium', 'capture', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists() and not args.capture.exists()
    sources = {}
    for source, prefix in [(args.rust_source, ''), (args.web_source, 'web/')]:
        for path in source.rglob('*'):
            if path.is_file():
                name = prefix + str(path.relative_to(source))
                assert path.read_bytes() == (ROOT / name).read_bytes(), name
                sources[name] = sha(path)
    driver = ROOT / 'web/tests/hada-remaining-scoped.mjs'
    frozen = {str(p): sha(p) for p in [args.cli, args.server, args.dictionary,
              driver, Path(__file__), *[p for p in args.assets.rglob('*') if p.is_file()]]}
    command = [str(args.server), '--port', '0', '--assets', str(args.assets),
               '--dictionary', str(args.dictionary)]
    receipt = {'state': 'running', 'command': command, 'cli': str(args.cli),
               'frozen_inputs': frozen, 'source_files': sources,
               'rust_source': str(args.rust_source), 'web_source': str(args.web_source),
               'producer': {'text': Path(__file__).read_text(), 'sha256': sha(__file__)}}

    def save():
        args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')

    save()
    server = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True)
    try:
        match = re.search(r'http://127\.0\.0\.1:\d+', server.stderr.readline())
        assert match, 'server did not report its loopback URL'
        url = match.group()
        receipt['url'] = url
        with urllib.request.urlopen(url, timeout=10) as response:
            html = response.read()
        assert html == (args.assets / 'index.html').read_bytes()
        for path in re.findall(r'(?:src|href)="(/assets/[^"?#]+\.(?:js|css))"', html.decode()):
            with urllib.request.urlopen(url + path, timeout=10) as response:
                assert response.read() == (args.assets / path.lstrip('/')).read_bytes()
        env = dict(os.environ, KLEM_ROOT=str(ROOT), KLEM_WEB_URL=url,
                   KLEM_BIN=str(args.cli), KLEM_DICTIONARY=str(args.dictionary),
                   KLEM_SCOPED_OUTPUT=str(args.capture), CHROMIUM_PATH=str(args.chromium))
        with args.output.with_suffix('.log').open('xb') as log:
            result = subprocess.run(['node', str(driver)], env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        receipt.update(state='passed' if result.returncode == 0 else 'failed',
                       exit_code=result.returncode)
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGINT)
        receipt['server_exit_code'] = server.wait(timeout=20)
        receipt['server_stopped'] = True
        receipt['inputs_unchanged'] = all(sha(p) == h for p, h in frozen.items())
        receipt['sources_unchanged'] = all(sha(ROOT / p) == h for p, h in sources.items())
        save()
    assert receipt['state'] == 'passed'
    assert receipt['inputs_unchanged'] and receipt['sources_unchanged']
    print('Passed all six source-bound installed diagrams; owned server stopped.')


if __name__ == '__main__':
    main()
