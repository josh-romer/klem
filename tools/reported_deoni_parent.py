"""Offline exact prior-companion attribution for reported and emphatic endings."""
import copy

MARKERS = {
    'ending.deoniman', 'ending.reported_deoni', 'ending.reported_command_deoni',
}
FORMS = {
    '더니만': '더니', '더니마는': '더니',
    '다더니': '다던', '는다더니': '는다던',
    '다더니만': '다던', '다더니마는': '다던',
    '는다더니만': '는다던', '는다더니마는': '는다던',
    '라더니': '라던', '으라더니': '으라던',
}


def actual_parent(word, path, parents):
    """Require the whole inverse path in an actually captured old WordAnalysis."""
    inverse = copy.deepcopy(path)
    touched = []
    for morpheme in inverse['morphemes']:
        if morpheme['form'] in FORMS:
            touched.append(morpheme['form'])
            morpheme['form'] = FORMS[morpheme['form']]
    assert len(touched) == 1, (word, touched)
    canonical = touched[0]
    bare = canonical in ('더니만', '더니마는')
    inverse['rules'] = [rule for rule in inverse['rules'] if rule not in MARKERS]
    if not bare:
        inverse['rules'].append('ending.reporting_retrospective')
    inverse['rules'] = sorted(set(inverse['rules']))
    if bare:
        original, replacement = canonical, '더니'
    elif canonical in ('으라더니', '라더니'):
        original, replacement = '라더니', '라던'
    else:
        original = next(suffix for suffix in ('더니마는', '더니만', '더니')
                        if canonical.endswith(suffix))
        replacement = '던'
    proposals = set()
    start = 0
    while (at := word.find(original, start)) >= 0:
        proposals.add(word[:at] + replacement + word[at + len(original):])
        start = at + 1
    for surface in sorted(proposals):
        if surface in parents and inverse in parents[surface]['analyses']:
            return surface, inverse
    raise AssertionError((word, path, inverse, sorted(proposals)))


def frame(before, after, parents):
    """Retain token payload, old candidate order and old dictionary assessments."""
    assert {k: v for k, v in before.items() if k not in ('analysis', 'dictionary')} == {
        k: v for k, v in after.items() if k not in ('analysis', 'dictionary')}
    if before['kind'] != 'word':
        assert before == after
        return []
    old, new = before['analysis']['analyses'], after['analysis']['analyses']
    assert [path for path in new if path in old] == old, (before['surface'], 'candidate loss/order')
    assert {k: v for k, v in before['analysis'].items() if k != 'analyses'} == {
        k: v for k, v in after['analysis'].items() if k != 'analyses'}
    additions = [path for path in new if path not in old]
    for path in additions:
        assert MARKERS.intersection(path['rules']), (before['surface'], path)
        actual_parent(after['analysis']['normalized'], path, parents)
    if 'dictionary' in before:
        old_dictionary, new_dictionary = before['dictionary'], after['dictionary']
        assert {k: v for k, v in old_dictionary.items() if k not in ('readings', 'lemmas')} == {
            k: v for k, v in new_dictionary.items() if k not in ('readings', 'lemmas')}
        assert [lemma for lemma in new_dictionary['lemmas']
                if lemma in old_dictionary['lemmas']] == old_dictionary['lemmas']
        for index, path in enumerate(old):
            assert old_dictionary['readings'][index] == new_dictionary['readings'][new.index(path)]
    return additions
