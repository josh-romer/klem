"""Verify nested suffix labels against each owner's immediate inflection."""
import argparse
import hashlib
import unicodedata

from hada_remaining_audit import ROOT, REPORT as DIAGNOSTICS, read, sha

REPORT = ROOT / 'docs/hada-remaining-scoped-runtime.json'
REFRESH = ROOT / 'docs/friendly-command-hada-scoped-browser.json'
PAIR_REFRESH = ROOT / 'docs/double-past-prefinal-hada-scoped-browser.json'
PAIR_PACKAGE = ROOT / 'docs/double-past-prefinal-packaged-cli.json'
CASES = {
    '먹는양하는양하다': ['Auxiliary verb formation', 'Auxiliary verb / adjective formation'],
    '먹는양하는듯하다': ['Auxiliary verb formation', 'Auxiliary adjective formation'],
    '먹는양했던양하다': ['Auxiliary verb / adjective formation', 'Auxiliary verb / adjective formation'],
}


def context_parent_text(text):
    """Invert the three exact pair-context edits; keep every suffix-label change."""
    if 'grammarContextHeadword' not in text:
        return text
    edits = [
        ('  grammarContextHeadword,', '  grammarHeadword,'),
        ('  components?: string[];\n', ''),
        ('    const key = grammarContextHeadword(a, component.morpheme, order);',
         '    const key = grammarHeadword(m);'),
    ]
    for current, previous in edits:
        assert text.count(current) == 1
        text = text.replace(current, previous, 1)
    return text


def frontend_parent_sha(text):
    """Invert only the audited command and pair-source selection changes."""
    text = context_parent_text(text)
    if 'ending.friendly_command.n' not in text:
        return hashlib.sha256(text.encode()).hexdigest()
    new_label = '''    const attachedN = m.kind === "ending" && m.form === "ㄴ";
    const friendlyCommand = attachedN && a.rules.includes("ending.friendly_command.n");
    const label = attachedN
      ? { ...grammarLabels[key],
          label: friendlyCommand ? "Friendly command (come)" : "Noun modifier",
          note: friendlyCommand
            ? "Colloquial command illustrated for an adult addressing a child or small animal. Context, lexical sense and auxiliary attachment remain open."
            : "Adnominal ending; separate from the same-spelled friendly command.",
          sources: grammarLabels[key].sources.filter((s) => s.id === (friendlyCommand ? 73877 : 78634)) }
      : remainingHada
'''
    new_fallback = '        .find((e) => e !== undefined) ?? (attachedN ? undefined : entries[0]);'
    assert text.count(new_label) == text.count(new_fallback) == 1
    parent = text.replace(new_label, '    const label = remainingHada\n', 1)
    parent = parent.replace(new_fallback, '        .find((e) => e !== undefined) ?? entries[0];', 1)
    return hashlib.sha256(parent.encode()).hexdigest()


def inspect_cases(report):
    assert report['errors'] == []
    assert len(report['checks']) == 6
    seen = set()
    for check in report['checks']:
        text, encoding = check['request']['text'], check['encoding']
        word = unicodedata.normalize('NFC', text)
        assert text == check['surface'] == unicodedata.normalize(encoding, word)
        assert encoding in ['NFC', 'NFD'] and word in CASES
        assert (word, encoding) not in seen
        seen.add((word, encoding))
        response = check['response']
        assert response['records'] == check['cli_records']
        records = response['records']
        assert ''.join(r['surface'] for r in records) == text
        index = next(i for i, r in enumerate(records) if r.get('analysis'))
        analysis = records[index]['analysis']['analyses'][check['selected']]
        assert analysis['lemmas'] == [{'text':'먹다', 'kind':'predicate'}, {'text':'양', 'kind':'nominal'}, {'text':'듯' if '듯' in word else '양', 'kind':'nominal'}]
        assert {'suffix.auxiliary.verb.hada', 'suffix.auxiliary.adjective.hada'} <= set(analysis['rules'])
        order = response['breakdowns'][index][check['selected']]
        for li in [1, 2]:
            at = order.index({'lemma':li})
            mi = order[at + 1]['morpheme']
            assert analysis['morphemes'][mi] == {'form':'하다', 'kind':'suffix'}
            if li == 1:
                following = analysis['morphemes'][mi + 1]
                assert following == ({'form':'었', 'kind':'prefinal'} if '했던' in word else {'form':'는', 'kind':'ending'})
        assert check['labels'] == CASES[word]
    assert seen == {(word, encoding) for word in CASES for encoding in ['NFC', 'NFD']}
    return len(seen)


def inspect(report):
    producer = sha(ROOT / 'web/tests/hada-remaining-scoped.mjs')
    assert report['producer_sha256'] == producer
    frontend = ROOT / 'web/src/breakdown.ts'
    text = frontend.read_bytes().decode('utf8')
    assert report['frontend_sha256'] == frontend_parent_sha(text)
    assert report['cli_sha256'] == read(DIAGNOSTICS)['cli_sha256']
    count = inspect_cases(report)
    if report['frontend_sha256'] != sha(frontend):
        # Keep the original capture, require an exact source inverse and also
        # replay every original scoped diagram using the current Nix package.
        fresh = read(REFRESH)
        assert fresh['producer_sha256'] == producer
        # Keep this historical capture tied to its actual historical source.
        assert fresh['frontend_sha256'] == hashlib.sha256(context_parent_text(text).encode()).hexdigest()
        package = read(ROOT / 'docs/friendly-command-packaged-checks.json.gz')
        assert fresh['cli_sha256'] == package['cli_sha256']
        assert inspect_cases(fresh) == count
        for before, after in zip(report['checks'], fresh['checks'], strict=True):
            for key in ['request', 'encoding', 'surface', 'selected', 'labels', 'cli_records']:
                assert before[key] == after[key], key
            for key in ['records', 'breakdowns']:
                assert before['response'][key] == after['response'][key], key
        if 'grammarContextHeadword' in text:
            # The exact inverse alone is insufficient: replay all six scoped
            # diagrams with the new actual Nix CLI and current frontend too.
            paired = read(PAIR_REFRESH)
            assert paired['producer_sha256'] == producer
            assert paired['frontend_sha256'] == sha(frontend)
            package = read(PAIR_PACKAGE)
            assert package['state'] == 'passed' and package['exit_code'] == 0
            assert package['inputs_unchanged']
            assert paired['cli_sha256'] == package['frozen_inputs'][package['package'] + '/bin/klem']
            assert inspect_cases(paired) == count
            for before, after in zip(fresh['checks'], paired['checks'], strict=True):
                for key in ['request', 'encoding', 'surface', 'selected', 'labels', 'cli_records']:
                    assert before[key] == after[key], key
                for key in ['records', 'breakdowns']:
                    assert before['response'][key] == after['response'][key], key
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.parse_args()
    print('Verified independently scoped nested suffix diagrams:', inspect(read(REPORT)))
