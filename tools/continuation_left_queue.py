"""Freeze and verify individual class/filter changes with actual raw indices."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from continuation_left_compare import canonical, sha

ROOT=Path(__file__).resolve().parents[1]
def report():
    fixture=ROOT/'tests/fixtures/continuation-left-sources.json'
    runtime=ROOT/'docs/continuation-left-runtime.json.gz'
    source=json.loads(fixture.read_text())
    with gzip.open(runtime,'rt')as file:evidence=json.load(file)
    assert evidence['source_sha256']==sha(fixture)
    overlay=ROOT/'tests/fixtures/continuation-left-written-vowel-judgments.json'
    assert evidence['written_vowel_overlay_sha256']==sha(overlay)
    vowel_compat=ROOT/'tests/fixtures/continuation-left-vowel-compat-judgments.json'
    assert evidence['vowel_compat_overlay_sha256']==sha(vowel_compat)
    targets={'내다':'krdict:60625','나다':'krdict:62134','나가다':'krdict:26813','버리다':'krdict:62601','치우다':'krdict:74290'}
    items=[]
    for change in evidence['changed_entries']:
        word=evidence['words'][change['surface']];a=change['analysis'];index=word['all']['analyses'].index(a)
        reading=word['all']['dictionary']['readings'][index]
        slot=next(s for s in reading['lemmas']if s['lemma_index']==change['lemma_index'])
        entry=next(e for e in slot['entries']if e['id']==change['entry_id'])
        assert entry==change['after']and entry['conflicts'][-1]['rule']=='continuation_verb'
        assert entry['conflicts'][:-1]==change['before']['conflicts']
        order=word['api']['breakdowns'][0][index];connector=entry['conflicts'][-1]['morpheme_index']
        position=order.index(dict(morpheme=connector))
        right=next(c['lemma']for c in order[position+1:]if'lemma'in c)
        assert a['lemmas'][right]['kind']=='auxiliary'
        native_id=targets[a['lemmas'][right]['text']]
        assert a['morphemes'][connector]['form']in(['어','고']if native_id=='krdict:62134'else['어'])
        matches=next(m for m in word['all']['dictionary']['lemmas']if m['lemma']==a['lemmas'][right])
        native=next(e for e in matches['entries']if e['id']==native_id)
        assert native['headword']==a['lemmas'][right]['text']and native['homonym']=='2'and native['pos']=='보조 동사'
        key=canonical([change['surface'],a,change['lemma_index'],change['entry_id']])
        assert change['id']=='continuation-left-entry-'+hashlib.sha256(key.encode()).hexdigest()[:24]
        items.append(dict(change,raw_index=index,breakdown=order,source_entry=native_id,
            source_url=source['complete_native_entries'][native_id]['url'],headword_retained=a in word['headword']['analyses'],
            compatible_retained=a in word['compatible']['analyses'],contextual_verdict='unjudged'))
    assert len({i['id']for i in items})==len(items)
    for item in evidence['removed_paths']:
        word=evidence['words'][item['surface']]
        assert word['all']['analyses'][item['raw_index']]==item['analysis']
        assert word['all']['dictionary']['readings'][item['raw_index']]==item['assessment']
        assert item['analysis']not in word['compatible']['analyses']
        assert item['analysis']in word['headword']['analyses']
        assert any(c['rule']=='continuation_verb'for slot in item['assessment']['lemmas']for e in slot['entries']for c in e['conflicts'])
    return dict(schema_version=1,checklist='COV-019ad',generator_sha256=sha(Path(__file__)),fixture_sha256=sha(fixture),
        runtime_sha256=sha(runtime),written_vowel_overlay_sha256=sha(overlay),vowel_compat_overlay_sha256=sha(vowel_compat),counts=evidence['counts'],items=items,
        removed_paths=evidence['removed_paths'],checks=evidence['checks'],
        limitation='Individual entry/filter changes in the frozen source and historical-regression cohorts. The 56 new policy cases and 33 explicitly named historical policy updates do not certify contextual correctness. Every contextual reading is unjudged. Complete broader streams are compared separately.')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');args=p.parse_args()
    current=report()
    if args.verify:
        assert current==json.loads((ROOT/'docs/continuation-left-review-queue.json').read_text())
        print(len(current['items']),'individual continuation entry changes and',len(current['removed_paths']),'filtered paths verified; all contextual readings unjudged.')
    else:print(json.dumps(current,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
