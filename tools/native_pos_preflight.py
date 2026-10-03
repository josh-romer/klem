"""Freeze COV-021q native evidence and raw candidates without replacing baselines."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli', type=Path, required=True)
args = parser.parse_args()
cli = args.cli.resolve()
output = ROOT / 'tests/fixtures/native-pos-sources.json'
if output.exists():
    parser.error('Refusing to overwrite frozen fixture: ' + str(output))


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


preflight_path = ROOT / 'docs/native-pos-source-preflight.json'
controls_path = ROOT / 'docs/native-pos-diagnostic-controls.json'
source_path = ROOT / 'tests/fixtures/source-head-sources.json'
preflight = json.load(preflight_path.open())
controls = json.load(controls_path.open())
source = json.load(source_path.open())
entry = source['complete_native_entries']['krdict:600930']
profile = json.loads(json.dumps(entry))
for sense in profile['senses']:
    sense['translations'] = []
profile_sha = hashlib.sha256(json.dumps(profile, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

# Probes cover each existing class-sensitive attachment family, tense/honorific
# boundaries, negation and later lexical owners. These are diagnostics, not
# blanket grammatical judgments or newly selected contextual readings.
surfaces = list(preflight['words'])
for tail in [
    '단다', '다지', '다지만', '다니까', '다는구나', '다더군요',
    '으니라', '느니라', '나이다', '나이까', '느냐지만', '으냐지만',
    '느냐니까', '으냐니까', '느냬', '으냬', '느냐는군', '으냐는군',
    '느냐면', '으냐면', '느냐면요', '으냐면요', '는데', '는데요',
    '는구나', '는군', '는군요', '군', '군요', '구먼', '는걸',
    '느니', '느니만', '니만', '으니만큼', '음세', 'ㄴ다',
    '러', '려', '려다가', '느라', '느라고', '고자', '더니',
    'ㄹ라치면', '읍시다', '자는구나', '자는군', '라는구나',
    '라는군요', '더구나', '더군', '시냐', '시느냐', '시으냐',
    '시느냐면', '셨느냐면', '겠느냐면', '였느냐', '였으냐',
    '였구나', '였는구나', '였는', '였는데', '겠구나', '겠는구나',
    '시구나', '시군요', '시더구나', '옵구나',
    '지않는', '지않느냐', '지않으냐', '지않구나', '지않는구나',
    '지않느냐면', '지않으냐면', '지못하는', '지못하느냐',
    '지아니하느냐', '지않아하는', '지않아대는',
    '려하는', '지않으려하는', '지않을라치면',
]:
    surfaces.append('발그스레하' + tail)
surfaces += [
    '발그스레해지는', '발그스레해지느냐', '발그스레해지구나',
    '발그스레해지었구나', '발그스레해하는', '발그스레해하느냐',
    '발그스레해하구나', '발그스레해대는', '발그스레해대느냐',
    '발그스레함이다', '발그스레함이느냐', '발그스레함이로구나',
    '발그스레하다를', '발그르세합니다', '발그스레합니다',
    '발그스레한다', '발그스레한대', '발그스레할라치면',
    '발그스레합시다', '발그스레합디다', '발그스레할지',
]
surfaces = list(dict.fromkeys(surfaces))
before = {}
for surface in surfaces:
    before[surface] = json.loads(subprocess.check_output([str(cli), 'word', surface]))
    if surface in preflight['words']:
        frozen = preflight['words'][surface]['raw']
        assert before[surface] == {k: v for k, v in frozen.items() if k != 'dictionary'}, surface

result = dict(
    schema_version=1, checklist='COV-021q', before_revision='be1b115',
    cli=str(cli), cli_sha256=sha(cli), extractor_sha256=sha(__file__),
    original_preflight=dict(path=str(preflight_path.relative_to(ROOT)), sha256=sha(preflight_path)),
    original_controls=dict(path=str(controls_path.relative_to(ROOT)), sha256=sha(controls_path)),
    source_entries=[entry], native_profile_sha256=profile_sha,
    primary=source['primary_reviews']['separate_pos_observation'],
    before_words=before,
    isolated_adjective_controls={surface: value['analyses'] for surface, value in
        controls['controls']['expert_adjective_control'].items()},
    initial_differences=controls['differing_paths'],
    scope='Native fields and old diagnostic controls retained unchanged. Additional surfaces are authored diagnostics. Only individually recorded dictionary-policy judgments become required/forbidden; unknown mood/register and raw hypotheses remain.',
    attribution='National Institute of Korean Language (국립국어원).',
    license=source['license'],
)
with output.open('x') as file:
    json.dump(result, file, ensure_ascii=False, indent=2)
    file.write('\n')
print(json.dumps(dict(path=str(output), surfaces=len(surfaces), original_controls=46, native_profile_sha256=profile_sha)))
