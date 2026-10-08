"""Capture the actual production server, SolidJS browser, and served asset bytes."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--rust', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    parser.add_argument('--assets', type=Path, default=ROOT/'web/dist')
    parser.add_argument('--chromium', type=Path, required=True)
    args = parser.parse_args()
    prefix = args.output_prefix.resolve()
    output = Path(str(prefix)+'-browser-runtime.json')
    log = Path(str(prefix)+'-server.log')
    assert not output.exists() and not log.exists()
    cli = args.cli.resolve()
    server = Path(str(prefix)+'-server')
    assert not server.exists()
    shutil.copyfile(args.server, server)
    server.chmod(0o755)
    browser = ROOT/'web/tests/literary-question-go.mjs'
    database = ROOT/'data/dictionaries/krdict/krdict.db'
    rust = json.loads(args.rust.read_text())
    assert rust['state'] == 'passed' and rust['exit_code'] == 0
    assert rust['inputs_unchanged'] is True
    snapshot = rust['snapshot']['files']
    assert len(snapshot) == 922
    assert all(sha(ROOT/name) == record['sha256'] for name, record in snapshot.items())
    package = json.loads((ROOT/'docs/ostensible-reason-package-nix.json').read_text())
    frontend = {name.removeprefix('web/'): sha(ROOT/name)
                for name in package['snapshot']['files'] if name.startswith('web/')}
    assert len(frontend) == 18
    assets = {str(path.relative_to(args.assets)): sha(path)
              for path in args.assets.rglob('*') if path.is_file()}
    paths = [cli, server, browser, database, Path(__file__), args.rust,
             ROOT/'docs/literary-question-go-prototype-source-replay.json.gz',
             ROOT/'docs/literary-question-go-boundary-matched-owner-preparation.json.gz']
    frozen = {str(path): sha(path) for path in paths}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    command = [str(server), '--assets', str(args.assets), '--port', str(port),
               '--dictionary', str(database)]
    report = {'schema_version': 1, 'state': 'running',
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_snapshot': snapshot, 'frontend_snapshot': frontend,
              'asset_snapshot': assets, 'command': command, 'url': url,
              'cli': str(cli), 'rust_receipt': str(args.rust),
              'frozen_inputs': frozen,
              'producer': {'text': Path(__file__).read_text(), 'sha256': sha(__file__)},
              'scope': 'Actual production source, server/CLI and SolidJS browser. '
                       'All39 original structures,23 authored boundaries and16 conditional '
                       'Native/mode cases; broader precision/context/register remains unjudged.'}
    output.write_text(json.dumps(report, indent=2)+'\n')
    try:
        with log.open('xb') as stream:
            job = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            report['server_pid'] = job.pid
            try:
                deadline = time.monotonic()+30
                while True:
                    assert job.poll() is None
                    try:
                        with urllib.request.urlopen(url, timeout=2) as response:
                            html = response.read()
                        break
                    except OSError:
                        assert time.monotonic() < deadline
                        time.sleep(.1)
                assert hashlib.sha256(html).hexdigest() == assets['index.html']
                checks = []
                for name in re.findall(r'(?:src|href)="(/assets/[^"?#]+\.(?:js|css))"', html.decode()):
                    with urllib.request.urlopen(url+name, timeout=10) as response:
                        raw = response.read()
                    digest = hashlib.sha256(raw).hexdigest()
                    assert digest == assets[name.lstrip('/')]
                    checks.append({'path': name, 'sha256': digest})
                assert len(checks) == 2
                report['asset_checks'] = checks
                env = dict(os.environ, KLEM_ROOT=str(ROOT), KLEM_PROTOTYPE=str(ROOT),
                           KLEM_FRONTEND=str(ROOT/'web'), KLEM_WEB_URL=url,
                           KLEM_BIN=str(cli), KLEM_CAPTURE_PREFIX=str(prefix),
                           CHROMIUM_PATH=str(args.chromium))
                command = ['node', str(browser)]
                report['browser_command'] = command
                subprocess.run(command, cwd=ROOT, env=env, check=True)
                report['browser_sha256'] = sha(Path(str(prefix)+'-browser.json'))
            finally:
                if job.poll() is None:
                    job.send_signal(signal.SIGINT)
                report['server_exit_code'] = job.wait(timeout=20)
                report['server_stopped'] = True
        assert report['server_exit_code'] in [-signal.SIGINT, 130]
        assert all(sha(path) == digest for path, digest in frozen.items())
        assert all(sha(ROOT/name) == record['sha256'] for name, record in snapshot.items())
        assert all(sha(ROOT/'web'/name) == digest for name, digest in frontend.items())
        assert all(sha(args.assets/name) == digest for name, digest in assets.items())
        report.update(state='passed', exit_code=0, inputs_unchanged=True)
    except Exception as error:
        report.update(state='failed', exit_code=1, error=repr(error))
        raise
    finally:
        report.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      server_log_sha256=sha(log))
        output.write_text(json.dumps(report, indent=2)+'\n')
    print('Production browser, source, Native, filter and served-asset checks passed; server stopped.')


if __name__ == '__main__':
    main()
