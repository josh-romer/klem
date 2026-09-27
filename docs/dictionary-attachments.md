# Dictionary-backed attachment checks (COV-017aa / COV-017ag / COV-017ai / COV-019m / COV-017al)

`--dict-compatible` keeps headword-matching analyses unless the dictionary supplies
only conflicting lexical evidence for at least one component. It is an explicit,
finite conflict policy, not a grammaticality score. Unknown classes remain.
`--dict-only` still checks headword presence regardless of POS. Neither option
changes the rule engine or its cached, unfiltered analyses.

The browser offers **Exclude known grammar conflicts** under **Dictionary matches
only**. Reading choices, counts, combinations and JSON export use the same policy.
The browser prefers a homonym supported by that particular reading for its short
gloss; all dictionary entries and their senses remain available for inspection.
This does not select a sense from sentence context.

## Evidence and decisions

The [source review](dictionary-attachment-evaluation.json) retains the pinned
KRDict entries, all notes/senses and source hashes. The independent
[dictionary-policy ledger](../tests/fixtures/dictionary-attachments.json) has
stable case/judgment IDs and exact lemma/morpheme roles. Its required/forbidden
verdicts apply **after this filter**. They are separate from the unfiltered rule
ledger because an unknown-class rule hypothesis must still be generated.

| Check | Scope | Example |
|---|---|---|
| `lexical_role` | Existing broad POS-to-role mapping | 가늘다 as a nominal base before omitted 이다 conflicts with its adjective-only entry. |
| `present_declarative_verb` | Lexical predicates with the shared canonical present-declarative family, including honorific 시 | 가는다니 → 가늘다 + 는다니 conflicts; 먹는다니 remains. |
| `bare_adjectival_question` | Bare lexical predicates with 으냐/으냐고/으냐는/으냐며/으냐면서/으냐니/으냔 | 길으냐니 → 긷다 + 으냐니 conflicts; 좋으냐니 remains. |
| `intention_verb` | Eleven reviewed verbal intention forms, shared with the engine | 좋으려다가 conflicts; 크려는 retains verbal 크다. |
| `result_transfer_verb` | Canonical 어다/어다가 | 좋아다 conflicts; 모셔다 retains lexical 모시다. |
| `habitual_condition_verb` | Canonical 을라치면, directly or through 지-negatives | Known adjective entries conflict; attested 있다 and verbal 늦다 remain. Different auxiliaries reset the dependency. |
| `bare_copular_ending` | Seventeen exact factual 라-family endings at a bare lexical predicate boundary | 누이다 + 라고 conflicts; 누이다 + 으라고 and 누이 + 이다 + 라고 remain. |
| `negative_copula_command` | Lexical 아니다 with canonical command 으라니 | 아니라니 retains 아니다 + factual 라니, excluding its distinct command hypothesis. |
| `auxiliary_class` | A represented auxiliary's known class, shared with the engine | 오려나봐 supports inference 보다 (보조 형용사), excluding the trial auxiliary-verb homonym from this reading's hint. |
| `literary_assertion_class` | Bare lexical predicates with 으니라/느니라 | 읽으니라 conflicts with its verb-only entry; 크니라 and 크느니라 retain their respective adjective/verb homonyms. |

The present family is shared with the engine: 는다/는다고/는다는/는다면/는답니다/
는다거나/는다든가/는다네/는다는데/는다며/는다면서/는다니/는단. Attached ㄴ
spellings have these canonical forms. An outer particle does not change the
attachment class, and honorific 시 does not turn an adjective into a verb.
The [는다니 source](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86182)
and [으냐니 source](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=87425)
state their different lexical attachment classes.

The command/factual distinction is deliberately narrow. The source for
[라니](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86509)
separates factual 이다/아니다 readings from verbal commands. This supports
excluding the command analysis of 아니다, not every adjective command.
[란](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86297)
illustrates 행복하란, and
[NIKL's consultation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=261&pageIndex=1&qna_seq=318597)
explains wish uses of some adjective commands/proposals. 행복하란 and 행복하자
therefore remain. Broader command restrictions need lexical and contextual review.

The [connective extension](attachment-connectives-evaluation.json) adds the exact
forms 으려거든/으려기에/으려는데/으려다/으려다가/으려더니/으려도/
으려야/으려는/으려는가/으려는지 and 어다/어다가. KRDict notes select
verbs for these forms. It does not apply a prefix-wide 려 restriction: 으려면,
으려고 and 을는지 retain source-listed adjective uses. The check follows the
lexical head's own ending, including after honorifics and before outer particles.
In 좋아하려다가보면 and 좋아해다주었다 the restrictive ending belongs to
auxiliary 하다, so lexical 좋다 must not be rejected. The exact 122 new policy
cases include the observed irregular-derived 노래다 → 노랗다 + 어다 conflict
and preservation of the distinct noun 노래 + 이다 + 다 reading. The policy ledger
now has 185 cases (109 required / 76 forbidden). All are generated and headword
matched before the optional filter; raw and headword-only candidates are unchanged.

## Homonyms, unknowns and ownership

The [literary assertion extension](nira-evaluation.json) adds fifteen policy cases
(12 required / 3 forbidden), bringing the whole-reading policy ledger to 200
cases (121 required / 79 forbidden). The new lexical check applies only at a bare
stem boundary. Honorific 시 can precede either family; past/modal markers can
precede 느니라. Source-listed existential predicates retain their exceptional
behavior, with uncertain verbal 으니라 uses marked unknown. A token-initial
auxiliary remains unknown: 먹으니라 keeps its auxiliary homonym even though its
lexical verb entries conflict. The narrower 읽다 case has no such homonym.
Source-attested negative 니라 and uncertain inherited negative classes are not
categorically decided from the engine's structural POS. These limits remain
explicit in COV-019h and the review's unjudged observations.

The [auxiliary class review](auxiliary-dictionary-evaluation.json) and
[43-case entry ledger](../tests/fixtures/auxiliary-dictionary.json) track 86
per-entry judgments. Connector-specific 보다/하다 classes and the existing fixed
auxiliary classes now constrain their own dictionary entries. Known verb/adjective
classes propagate through 않다/아니하다/못하다; explicit 답다 derivation supplies
an adjective class. Internal particles do not replace the connector. Two 보다
slots in 먹어보나보다 independently select trial and inference homonyms.

Unknown lexical heads, ambiguous 고 + 보다/기 + 하다 and 양하다 stay unresolved.
The engine's copula class remains distinct: the reviewed negative-auxiliary notes
do not justify converting it to a dictionary adjective class. Later copulas reset
class inheritance, and general 하다 derivation does not establish a verb class.
The browser uses the supported entry for its existing dictionary hint; KRDict's
English hint can still be a romanization rather than a contextual translation.

Each entry must satisfy both the proposed lexical role and the applicable ending
check. Evidence from different homonyms is never mixed to make an otherwise
unsupported entry pass. Any compatible entry preserves the lemma slot. If none
is compatible but at least one has an unknown class, the slot is unknown. With
no entries it is also unknown; both CLI filters independently require headword
presence. A reading conflicts if any slot conflicts, is unknown if at least one
slot is unknown, and otherwise passes the finite checks.

Thus 큰다니 retains verbal 크다 while marking adjectival 크다 as conflicting;
늦으냐니 retains adjectival 늦다 while marking its verbal homonym as conflicting.
Unchanged/unclassified dictionary words remain unknown and are retained.
Unknown provider POS labels are not guessed. A token-initial predicate matching
an auxiliary entry is also unknown: 싶었다 in 먹고 싶었다 needs the preceding
word to establish its auxiliary role. Its broad `pos_compatibility` remains the
legacy role-only value; the per-reading assessment records this boundary-aware
exception. No missing preceding verb is invented. Existential/honorific 있다/없다/
계시다 question paradigms are not rejected from their verbal POS alone; they
remain COV-019h. An adjectival homonym may independently support such a reading.

Checks follow the ordered component breakdown. In 가늘어한다니, 는다니 belongs
to auxiliary 하다, not lexical 가늘다. Nominalization, later copulas and adjective
suffixes likewise do not lend their ending to another lexical head. Malformed
externally constructed analyses with no supported breakdown are unknown.

## Lexical uncertainty before expressive 하다 (COV-019o)

KRDict 62888 sense 9 describes adjective + 어 하다, but NIKL also licenses
[some verbs, including 꺼리다](https://korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=8227).
[Article 47](https://www.korean.go.kr/kornorms/m/m_regltn.do) gives the negative
phrase 내키지 않아 하다. A blanket lexical-verb conflict would lose valid paths.
Each lexical verb entry is therefore assessed as **unknown** at this boundary,
also through 지 + 않다/아니하다/못하다. A different auxiliary, derivational
suffix or copula ends that dependency. Adjective entries remain compatible with
this finite check; no homonym lends its POS to another entry.

Twenty-two additional policy cases bring the whole-reading ledger to 222 cases
(143 required / 79 forbidden). They preserve both sourced examples and unresolved
hypotheses such as 잘해서 → 자다 + 어 + 를 + 하다. This is an evidence-status
correction, not a precision gain or a new rejection rule. Filtering still retains
unknown readings. The semantic verb subset needs further source/sense review;
NIKL distinguishes lexical 즐겨 하다 from auxiliary usage. The token engine
represents joined sequences without validating their spacing.

## Recurring conditions (COV-017al)

Ten additional policy cases bring the ledger to 232 cases (148 required /
84 forbidden). The `habitual_condition_verb` conflict applies to a known lexical
adjective entry before 을라치면, except source-attested 있다. Each homonym keeps
its own assessment. The requirement follows 지 + 않다/아니하다/못하다; the
conflict belongs to the lexical entry and references the later ending index.
A different auxiliary, suffix or copula stops the dependency. 좋아질라치면
therefore remains, while 예쁘지않을라치면 has a known lexical-class conflict.
Missing or unclassified lexical evidence stays unknown. See the
[source and case review](llachimyeon-evaluation.json).

## Library and JSON

`DictionarySession::annotate` adds `readings`, aligned with `WordAnalysis.analyses`.
Each reading includes a status and lemma-slot assessments. Each entry assessment
references its dictionary ID, status and conflict reasons, with a morpheme index
for ending conflicts. An `auxiliary_class` conflict references the preceding
connector's morpheme index, owned by the preceding component. `compatible` means only that the entry passes the checks
above, not that every ending or sense is licensed.

`Annotation::assess(&Analysis)` evaluates one reading.
`Annotation::filter(&mut WordAnalysis, DictionaryFilter::Compatible)` retains
whole groups and updates both the lemma references and reading indices. It
recomputes evidence against the supplied analyses, handling reordered candidates
and older deserialized annotations without a `readings` field. Use an owned clone
or `Arc::make_mut` when filtering a cached analysis. `DictionaryFilter::Headword`
provides the existing headword-only policy through the same library API.

Annotations use the existing bounded headword-summary cache. Bulk analysis does
not load definitions or build a Cartesian product of senses. Per-reading evidence
increases JSON output size; its memory is released with each streamed token.
The web adapter loads short hints for compatible homonyms on demand within its
existing input limits.

## Remaining scope

Further lexical subsets, negative-auxiliary inheritance from dictionary lexical
homonyms (rather than known represented classes), separately segmented
으려 + 는 paths, other reporting/
adnominal/question endings, sense-specific selection, existential paradigms and
contextual command/wish judgments remain under COV-017/019. Incompatible is not a
spelling-error diagnosis, and compatible/unknown is not a correctness guarantee.
Independent Korean review and fresh-prose evaluation remain pending.

## Bare factual copular endings (COV-020n)

The exact canonical forms 라/라도/라야/라야만/라서/라고/라는/라면/
랍니다/라든가/라네/라는데/라며/라면서/라니/라거나/란 distinguish
factual copular attachment from commands. At a bare lexical predicate boundary,
known verb/adjective entries conflict with these factual forms, except the
source-listed adjective 아니다. The verb 이다 (carry on the head) conflicts;
the separate copular 이다 role retains its particle entry. Command canonical
forms such as 으라고 and 으란 remain, including the wish 행복하란.

The check follows the current component's first ending. A prefinal or derivational
suffix ends the bare boundary; a later copula owns its own ending. Thus 먹음이라고
keeps 먹다 + 음 + 이다 + 라고. Token-initial auxiliary entries and unrecognized
provider POS remain unknown; a missing dictionary entry is not evidence of a
conflict. Outer particles do not change attachment: 누이라고밖에 loses the
known verb's factual reading while retaining the command and nominal-copula paths.

This adds 105 policy judgments (63 retained / 42 excluded), bringing the policy
ledger to 341 judgments (213 retained / 128 excluded). These are filter judgments,
not independent gold grammaticality labels. The full source fixture retains every
sense, note and example for the reviewed ending homonyms. The prefinal scope is
intentionally unresolved: the pinned KRDict 라서 entry lists 시/더/으리, whereas
[NIKL's July 2025 consultation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=318485)
cites a narrower standard-dictionary note and does not supply a noncopular example
after 시. This check neither rejects nor newly licenses those prefinal paths.
See [the evaluation record](copular-class-evaluation.json) for source IDs,
output comparisons, validation, and remaining review limits.


## Action reason/purpose endings (COV-017au)

`neura_verb` rejects a known lexical adjective entry with 느라 or 느라고, including
after honorific 시. The check follows the ending's owning component: 좋아하느라
keeps 좋다 + 어 + 하다 + 느라, since 하다 owns the final ending. Verb homonyms
remain available and unknown classes are not silently rejected. KRDict 80327/80328
and NIKL consultation 313032 support this finite attachment policy. Clause-level
meaning, subject identity and negative inheritance from ambiguous lexical heads
remain unreviewed. See [evaluation](neura-evaluation.json) and [tests](../tests/neura.rs).

## Written ㅎ inflection compatibility (COV-021d)

The `lexical_spelling` conflict checks each dictionary entry's **written 활용
forms**. A stem-preserving `-으니` form supplies regular-class evidence; a
shortened `-니` form requiring ㅎ recovery supplies irregular-class evidence.
Pronunciation fields supply neither. Both classes can coexist in an entry if
both written paradigms are supplied. Missing evidence remains unknown, and
homonyms never borrow forms from each other. The pinned source inventory has
116 entries: 46 regular, 66 irregular, and four without a usable 니 paradigm.
The source POS of 땡그랗다 remains 동사; its written forms, rather than a
blanket adjective/verb guess, establish the spelling class.

[NIKL's spelling explanation](https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=98&pageIndex=1&qna_seq=334394)
distinguishes regular 좋다 and ㅎ-final verbs from irregular adjectives, and
written forms from consonant loss in pronunciation. Thus 달라고 → 닿다 and
놀라고 → 놓다 remain raw/headword-only hypotheses but conflict under
`--dict-compatible`. Conversely, regular-spelling 하얗으니 conflicts with
하얗다's irregular paradigm. Valid 닿으니, 하야니 and the separately
licensed 놓아 → 놔 contraction remain available. Literal consonant endings
such as 하얗고/하얗습니다 impose no spelling-class requirement.

`Analysis.spelling_paths` is an optional list of alternative derivations for
the same lemma/morpheme sequence. Each recovery records a `morpheme_index` and
`class` (`hieut_regular` or `hieut_irregular`); ownership follows the ordered
breakdown. Requirements inside a path coexist. Different paths are alternatives.
The engine retains these alternatives when merging otherwise identical analyses,
instead of treating the union of rule names as an ordered derivation. A path
with no spelling requirements subsumes restricted alternatives.

A reading is retained if any complete spelling path remains compatible or
unknown. Its aggregate entry/lemma assessments summarize alternatives, while
the overall status is computed on complete paths first. This prevents different
owners from borrowing incompatible derivations from each other. The conflict's
morpheme index identifies the affected prefinal or ending. In
노래져놓으니, the first adjective requires irregular recovery and the final
놓다 requires regular spelling; the latter does not inherit the former's rule.
Nested nominalizations, copulas, repeated heads and auxiliaries preserve indices.

`EntryMatch.hieut` optionally records the supporting regular/irregular written
forms. The dictionary session caches these small profiles with the headword
summaries, charging them against its existing byte budget. Complete definitions
are read only to extract profiles for relevant single-ㅎ entries and are not
retained in this cache. Old JSON without these optional fields is readable and
retained conservatively; no missing field is treated as evidence of regularity.
Rust callers constructing `Analysis` or `EntryMatch` literals initialize the new
fields with `Vec::new()` or `None`, respectively. The SQLite schema is unchanged.

[Tests](../tests/hieut_compatibility.rs) cover 326 policy judgments (175 required,
151 forbidden), all 116 source profiles, dictionary/CLI parity, Unicode, cache
bounds, competing derivations, synthetic homonyms and pronunciation-only evidence.
The [evaluation](hieut-compatibility-evaluation.json) records raw-candidate
preservation, seven unchanged training gold groups, and every novel removal.
These checks cover the reviewed ㅎ spelling class; other lexical irregular
classes and contextual sense selection remain separate work.

## Written ㄷ/ㅅ inflection compatibility (COV-021e)

The same component-owned spelling checks now cover ㄷ and ㅅ. Each entry's
written `활용` forms distinguish retained-consonant `stem + 으니` from ㄷ→ㄹ
or deleted-ㅅ forms before 으니. Pronunciations never classify an entry. The
[124-entry source inventory](../tests/fixtures/digeut-siot-sources.json) contains
65 regular, 54 irregular and five unknown entries. Full source senses, notes,
forms and examples are retained, with English equivalents.

Real homonyms remain separate: 걷으니 supports the regular 걷다 entries while
걸으니 supports the irregular entry; 묻으니 and 물으니 likewise select different
entry evidence. Both complete readings survive when any matching entry supports
them. The filter does not choose a sense in context. 믿다 at 밀으면, 듣다 at
듣으니 and 짓다 at 짓어 conflict, while raw and headword-only hypotheses remain.
Vowel endings, prefinals, auxiliaries and nominalizations retain their own
requirements, e.g. 들어놓으니 has ㄷ irregular evidence on 듣다 and ㅎ regular
evidence on 놓다. Literal consonant endings impose no such requirement.

`SpellingClass` adds `DigeutRegular`, `DigeutIrregular`, `SiotRegular` and
`SiotIrregular`. `EntryMatch` adds optional `digeut` and `siot` evidence fields
with the same regular/irregular written-form lists as `hieut`.
`ConjugationEvidence` is the shared Rust structure; `HieutEvidence` remains a
type alias. Old JSON stays readable; absent fields remain unknown. Rust struct
literals and exhaustive enum matches must account for the additions. SQLite's
schema is unchanged, and the existing dictionary-cache budget charges evidence.

껴묻다, 내딛다, 딛다, 잡숫다 and 줄짓다 lack an informative 니 paradigm.
They remain unknown. Some shortened forms have separate consonant-only notes;
this classifier does not implement those attachment restrictions. Retaining an
unknown candidate does not certify its spelling. Other irregular classes remain
in COV-021. See [the case evaluation](digeut-siot-evaluation.json) for source
hashes, individual judgments, novel removals and the remaining unjudged queue.
