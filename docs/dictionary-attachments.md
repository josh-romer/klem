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
| `bare_literary_declarative` | Bare lexical predicates with 나이다 | Known adjectives conflict, with 있다/없다/계시다 exceptions. 머나이다 retains the verb 멀다 while its adjective homonym conflicts; listed intervening prefinals keep their own licenses. |
| `bare_literary_question` | Bare lexical predicates with 나이까 | The corresponding NIKL verbal/existential class; compatible verb homonyms and unknown provider classes survive. Intervening prefinals retain their separate licenses. |
| `volitional_promise_verb` | Bare lexical predicates with canonical 음세 | Keeps valid verb homonyms such as 크다 while identifying the adjective entry conflict; generic prefinal combinations remain unknown. |
| `bare_background_verb` | Bare lexical predicates with canonical 는바 | Identifies adjective-entry conflicts; keeps verb homonyms, 있다/없다/계시다 and adjectives ending in 있다/없다. Listed prefinals and other ending owners do not inherit this bare constraint. |
| `bare_neuni_verb` | Bare lexical adjective entries with 느니/느니만/느니만큼 | Identifies ordinary adjective conflicts per entry, preserving verb homonyms and listed existential classes. Compound existential adjectives remain unknown for 느니만. |
| `bare_niman_adjective` | Bare lexical verb entries with 니만 | Identifies the verb-entry conflict for the reviewed comparative expression; standalone auxiliary roles and prefinal variants remain unknown. |

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

The [restricted humble and 나이다 review](jaop-evaluation.json) adds ten
dictionary-policy cases (seven required, three forbidden). Bare 나이다 licenses
verbs and the explicitly listed existential/honorific heads. Intervening
honorific, past or polite prefinals allow the source-attested adjective and
copula examples. These checks do not choose a contextual sense or resolve
negative-auxiliary inheritance. The preserved [draft correction](jaop-draft-corrections.json)
records why the negative ㄹ-stem case uses adjective-only 힘들다 rather than
the ambiguous 멀다. Separate per-entry checks keep the verbal 멀다 alternative.

The [나이까 review](naikka-evaluation.json) adds eleven policy cases (eight
required, three forbidden), retaining the same explicitly listed bare
existential/honorific heads and supported prefinals. The question conflict has
its own serialized rule, preserving the existing declarative rule identity.
Per-entry tests keep verbal 멀다 alongside its conflicting adjective homonym
and verify that an unrecognized provider POS remains unknown.

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

## Written ㅂ inflection compatibility (COV-021f)

The per-entry spelling checks include ㅂ. Written `활용` 니 forms establish
regular retention or irregular recovery; written 운/온 forms additionally
support adnominal-only entries such as 꽃답다 and 참답다. Surrounding whitespace
is ignored when comparing a form, while evidence preserves its original string.
The [443-entry inventory](../tests/fixtures/bieup-sources.json) has 56 regular,
377 irregular and 10 unknown dispositions. Pronunciation strings never classify
an entry. 곱다 and 굽다 have genuine regular/irregular homonyms, assessed
separately before deciding whether to retain a complete reading.

`EntryMatch` adds optional `bieup: ConjugationEvidence`, and `SpellingClass` adds
`BieupRegular` and `BieupIrregular`. Old JSON remains readable with missing fields
unknown; Rust struct literals and exhaustive matches need the additions. SQLite
is unchanged. The same cache budget includes the written-form evidence.
Auxiliaries and nominalizations retain their owning requirements. The productive
-답다 suffix already enforces its fixed irregular class in the raw derivation;
its inflection is not a lexical constraint on the preceding nominal lemma.

The finite raw spelling rules also recover 곱디고와, 듣자와 and 받자오니 from
their primary entries. 곱디곱다 uses 와 before 아/어 but 우 before (으) endings;
듣잡다 and 받잡다 use 오 in both positions. This does not license arbitrary
compounds or historical inflection patterns. General 돕다/곱다 versus other ㅂ
vowel choices remain in the existing raw rules.

The all-form regression covers 1,674 written forms. One source mismatch remains:
KRDict 67256 lists 얃잡는 under 얕잡다. The fixture keeps that spelling and
explicitly tracks the missing headword recovery; spelling correction is outside
this rule. Ten entries without useful written evidence also remain unknown,
including shortened 뵙다 and nonstandard cross-reference heads. Unknown retention
is not a claim of grammatical correctness. Full source forms, hashes, individual
judgments and observed output changes are in [the evaluation](bieup-evaluation.json).

## Written 르/러 inflection compatibility (COV-021g)

Written `활용` 아/어 forms now distinguish four recovery classes: ㅡ deletion
(치러 → 치르다), ㄹ doubling (몰라 → 모르다), 러 addition (푸르러 → 푸르다),
and uncontracted 르어. Each entry supplies its own evidence; 이르다 and 누르다
homonyms can support different classes. The [149-entry inventory](../tests/fixtures/reu-sources.json)
contains 8 deletion, 126 doubling, 6 러 and 9 unknown profiles. No native entry
in this inventory supplies uncontracted 르어 evidence.

Only written 아/어 forms distinguish these classes. Pronunciations and 니/ㄴ
forms alone do not. Surrounding whitespace and Unicode normalization affect
comparison, while the evidence retains original source strings. Unknown entries
remain unknown, and multiple explicitly written classes may coexist in custom
dictionaries. Literal and (으) endings impose no 르-class restriction. Past and
auxiliary boundaries keep their own requirements: 치러놓으니 constrains 치르다
by ㅡ deletion and 놓다 by its separate regular ㅎ paradigm.

`EntryMatch` adds optional `reu: ReuEvidence`, with `eu_deletion`,
`rieul_doubling`, `reo` and `uncontracted` written-form lists. `SpellingClass`
adds `ReuEuDeletion`, `ReuDoubling`, `ReoAddition` and `ReuUncontracted`.
Old JSON remains readable; missing evidence stays unknown. Rust callers using
struct literals or exhaustive enum matches need these additions. The dictionary
schema is unchanged. Relevant full entries are fetched once per cached lookup;
only the scoped evidence is retained and charged to the existing cache budget.
Raw candidates and `--dict-only` keep the existing possibilities.
`--dict-compatible` excludes a path only when all its entry alternatives conflict.

The source audit preserves all 404 written forms. Of these, 403 recover the
listed headword after filtering. KRDict lists 서툰 under 서투르다, whereas
[NIKL's explanation](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=324385)
assigns it to 서툴다. The regression test retains this discrepancy and the
existing 서툴다 analysis. It does not infer a general 르 deletion or silently
rewrite the source. Separate shortened-headword relationships and attachment
restrictions remain under COV-021.

The class distinctions follow the written dictionary entries and NIKL's
[다다르다 explanation](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=8763)
and [Article 18 discussion](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=322819).
[Tests](../tests/reu.rs) cover every entry profile, 663 filter judgments,
composition, unknown evidence, Unicode, legacy annotations and both CLI filters.
Eight unchanged annotated training targets survive filtering. Individual cases,
unjudged alternatives and novel/corpus comparisons are in the
[evaluation](reu-evaluation.json). Independent language review remains pending.

## Restricted short-stem endings (COV-021h)

Some shortened predicates have explicit attachment restrictions. The
[inventory](short-stem-inventory.json) binds these to twelve reviewed KRDict
entries by ID, headword and POS. Seven entries allow consonant endings only:
갖다 (verb and auxiliary), 딛다, 내딛다, 잡숫다, 뵙다 and 찾아뵙다.
Five ㄹ-final entries reject the 아/어 family and past 었 while retaining
(으) allomorphs: 건들다, 까불다 in its winnowing/shaking sense, 머물다,
서둘다 and 서툴다. Thus 딛어/딛으니 conflict, but 딛고 and 딛겠어요 remain;
머물면/머문/머묾 remain alongside the full-stem forms.

The policy follows NIKL's [short-stem explanation](https://www.korean.go.kr/nkview/nklife/2003_3/2003_0316.pdf),
[갖다/딛다 discussion](https://www.korean.go.kr/nkview/nknews/200309/62_3.html),
[뵙다 entry explanation](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=5731)
and [찾아뵙다 answer](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=326748).
The [broader source list](https://www.korean.go.kr/nkview/nknews/200005/22_2.htm)
is mapped by meaning, not spelling alone: the native 굴다, 들까불다, 썰다,
일다 and 붓다 entries do not establish the corresponding shortened senses.
The “act up” 까불다 homonym remains compatible with 까불어. Source-listed
senses absent from the pinned dictionary are recorded without guessing bindings.

Only the first ending or prefinal belonging to that lemma is checked.
Normalized 시 represents -(으)시-; a later vowel ending after 겠, an auxiliary,
a derivational suffix or a copula cannot impose a restriction on the earlier
root. `AttachmentRule::ShortStemEnding` identifies the owning morpheme.
This adds no raw candidate metadata or dictionary schema fields. An unknown
external dictionary ID does not inherit the policy merely by matching a headword.
Raw candidates and `--dict-only` remain; `--dict-compatible` uses the finite
normative policy in addition to written spelling evidence.

Three KRDict written forms conflict with these normative sources: 건들어,
까불어 in its winnowing sense, and 서툴어. The original entries are preserved,
and the conflict is tested explicitly. Untyped 머물러/서둘러 forms are ambiguous:
the short stems take purpose ending 으러, while the long stems take 어. Both
analyses remain; no long/short lemma alias is introduced.

Ten earlier “unknown spelling class, retain” judgments for 딛다/내딛다/잡숫다/
뵙다/찾아뵙다 now have independent short-stem conflicts. Their prior and current
judgments are recorded in the inventory; their written regular/irregular profiles
remain unknown. An unchanged KAIST training sentence contains 내딛었다, which
this normative policy rejects while retaining its original annotation and raw
candidate. Seven other unchanged training groups survive filtering.
[Tests](../tests/short_stems.rs) and [individual-case evaluation](short-stem-evaluation.json)
record the scope and source disagreements. Independent language review remains
pending; this is not a contextual grammar or precision guarantee.

COV-017az’s `-(으)리까` permits bare lexical adjectives and copulas, separately
from the `나이까` class. Its ten policy cases preserve seven licensed readings
and exclude three known local spelling conflicts; both verbal and adjectival
`멀다` homonyms survive. Headword-only and unfiltered candidates keep the
underlying spelling hypotheses. These checks do not select a question sense.

## Intention adjective uncertainty (COV-017aw)

The [primary-source follow-up](ryeogo-license-source-audit.json) separates final
rhetorical -(으)려고 from verbal intention/change connective uses. The final
entries license adjectives, with a past license for -으려고. NIKL's full
2026-08-24 consultation acknowledges actual adjective state-making uses and
leaves their analysis open. Broad adjective POS therefore cannot decide a
represented intention construction categorically.

Before 으려고 + auxiliary 하다/들다, known adjective entries become **unknown**,
with no invented conflict. Independent verb homonyms remain compatible. The
check follows 지-negatives and explicitly adjectival 답다; represented adjective
auxiliaries are assessed under their own class. A different auxiliary or copula
resets the dependency. Known role, ending and spelling conflicts take precedence.
Both filters retain unknown readings; raw candidates are unchanged. The separate
[entry ledger](../tests/fixtures/ryeogo-license-assessments.json) covers 45 cases
and 66 judgments, including final homonyms, ownership boundaries and provider
uncertainty. This does not resolve source-conflicted full expansions or
standalone prefinal licenses. See [the evaluation](ryeogo-licenses-evaluation.json).

The [full-expansion extension](ryeogo-expansions-evaluation.json) also marks
retained copular intention entries and immediate non-honorific intention prefinal
attachments unknown. Related shortened-expression notes conflict with blanket
full-expansion exclusions. The lexical nominal keeps its role assessment; a
copular license belongs to its own entry. An earlier tense marker does not
constrain a later auxiliary's connector. Final rhetorical forms are independent.
Known class/role/spelling conflicts still take precedence. Relational -적
state-making hypotheses can now reach finite 하다/들다 without being asserted
contextually correct; both filters retain the unknown readings.

The COV-017bc comparison/reason bundles preserve unknown evidence explicitly.
Bare verbal 으니만큼 is compatible for primary-attested 알다, while other
bare verbs remain unknown under the KRDict/NIKL distribution disagreement.
Unlisted local prefinals also remain unknown. A lexical conflict for 가다 + 니만
does not settle its standalone auxiliary entry. The regression ledger uses
기다리다 (a lexical verb without this auxiliary homonym) for the whole-reading
conflict and separately checks preservation of the unknown 가다 reading.
See [the source audit](neuni-source-audit.json) and [regressions](../tests/neuni.rs).

COV-017bd extends the existing per-entry report/question/copula policies to
quoted listing bundles. Bare 다느니 identifies ordinary lexical verb conflicts;
present 는다느니 and verbal 느냐느니 independently preserve verb homonyms.
Bare adjective 으냐느니 and factual 라느니 retain their distinct class evidence.
Standalone auxiliary entries and unlisted polite prefinals remain unknown. The
source notes do not justify blanket lexical-adjective command/wish exclusion.
Use a genuinely generated 쌓이다 + 라느니 path to test the optional factual
copula conflict; bare 기다리다 + 라느니 is already excluded by the raw boundary.
The [individual report](quoted-neuni-evaluation.json) preserves these draft
corrections and exact source IDs, including expressions outside the POS queue.

COV-017be extends `bare_neuni_verb` to exact 느니보다/느니보다는. It preserves
verb/existential lexical entries and marks ordinary adjective entries conflicting
independently, including two 크다 homonyms. Only the local source-listed 시
prefinal is known; generic unlisted markers stay unknown and survive compatible
filtering. Both teaching entries retain exact 품사 없음 expression identities
outside the inventory. The [individual evaluation](neuni-comparison-evaluation.json)
keeps raw additions separate from policy judgments and unjudged alternatives.

COV-020p spacing suggestions apply the existing compatible/headword policy to
each proposed word separately. The original word annotations and filters remain
intact. Prefix roles require a nominal case phrase or explicit 음/기 nominalization,
not an arbitrary connective/particle; the final word has its own predicate and
possible auxiliary groups. Extra partitions and unknown roles stay visible as
hypotheses. [The evaluation](spacing-evaluation.json) records every affected
occurrence and explicit limits rather than certifying a sentence from dictionary
membership or creating a headword such as 결혼을하다.

COV-017bf adds `bare_geol_verb` for immediate bare 는걸 owners. The exact
81050 note licenses verbs, 있다/없다/계시다 and adjective compounds ending
있다/없다, or licensed prefinal markers. Known ordinary adjective entries
conflict only in the bare position; verbal homonyms, unknown lexical classes
and adjective/copula paths after 시/었/겠 remain. The raw hypothesis is kept
when the engine has no represented owner class; dictionary headword filtering
retains it and compatible filtering excludes the known conflict. Guess/regret
을걸 does not impose a verb-only restriction because its guess sense admits
adjectives/copulas. [Individual evidence](geol-evaluation.json) keeps dictionary
conflicts separate from raw structural exclusions and unjudged alternatives.

COV-017bg adds `bare_exclamation_verb` and `bare_exclamation_adjective` for
the immediate bare owner of source-reviewed exclamation endings. Lexical
homonyms are checked independently; 고르는군 keeps verbal 고르다 while
고르군 keeps adjectival 고르다. Separately written known auxiliary classes
retain this narrow inflectional check despite unknown sentence context.
-구려 has both adjective exclamation and verbal recommendation senses;
-더구나's conflicting note/example leaves bare verbs unknown. Lexical 있다
and stative auxiliary 있다 have separate boundary evidence. Unlisted polite
prefinals remain unknown. These optional checks preserve raw hypotheses and
headword-only filtering. [Evidence](exclamation-evaluation.json) records every
changed novel occurrence, including two excluded bare 누다+구나 readings of
누구나, whose whole-word reading remains.

COV-017bh extends `present_declarative_verb` and `bare_adjectival_report`
to the source-reviewed quoted declarative exclamations. 고른다는군 retains
the verbal 고르다 entries while 고르다는군 retains the adjective entry.
These checks apply to the immediate owner, preserving independent auxiliary,
derivational and copular components. Lexical 있다/없다/계시다 distribution
and separately written auxiliary context retain explicit unknowns. A plain
다 report after only honorific 시 on a verbal owner also remains unknown:
listing 시 in an adjective attachment note is insufficient to certify that
extension. Listed past/modal reports have separate evidence. Unlisted polite
prefinals remain unknown without a fabricated conflict. The three reviewed
polite bundles retain their separate 요 alternatives. Raw and headword-only
paths remain available; these optional checks do not select contextual senses.
See [source and individual-case evidence](quoted-exclamation-evaluation.json).

COV-017bi extends the existing bare verbal/adjectival question rules to twelve
quoted-question expression bundles. General spoken 냐 remains a distinct
candidate from adjective 으냐. Each 고르다/보다/있다 homonym keeps its own
assessment. Unknown auxiliary-adjective readings survive independently of
incompatible verbal homonyms. Nonverbal honorific-only 느냐, unlisted polite
prefinals and inferred quoted 군 + 요 paths retain Unknown; structural class
conflicts still take precedence. A negative owner with an unclassified lexical
predecessor stays Unknown instead of borrowing a preceding dictionary entry’s
POS. No new compatibility enum or provider restriction is introduced.
[Source and case evidence](question-exclamation-evaluation.json) distinguishes
raw hypotheses, optional filtering judgments and contextual validity.

COV-017bj adds eight copular/command exclamation bundles to the finite owner
policy. Bare factual 라 readings use `bare_copular_ending`; lexical 쌓이다
cannot borrow the copular sense, while its command allomorph survives. The
negative 아니다 boundary uses `negative_copula_command`, retaining factual
아니라더군 alongside the distinct command hypothesis. 고르다’s two verbal
homonyms stay compatible with command reports; its adjectival homonym stays
Unknown for a possible wish. Derived 답다 wishes, auxiliary adjective wishes,
noncopular factual prefinal extensions and unlisted polite prefinals also remain
Unknown. Listed copular 시/더/으리 remain independent of a nominal head’s POS.
Two inferred 군 + 요 paths are retained as Unknown; dictionary absence does
not supply forbidden gold for 구나 followers. No new provider restriction or
compatibility enum is introduced. See [source and case evidence](copular-command-exclamation-evaluation.json).

COV-017bk adds four quoted proposal bundles with immediate-owner boundaries.
Bare lexical verbs retain compatible entries. Ordinary/derived adjective
wishes, existential auxiliary readings and unclassified negative owners stay
Unknown; an earlier compatible homonym does not certify a later unknown class.
Unlisted local prefinals and inferred 자는군 + 요 also stay Unknown. Explicit
자 prefinal exclusions apply to this owner, while earlier prefinals in an
auxiliary chain remain independent. Native 자더군요 and split 자더군 + 요
retain distinct paths. No new provider restriction or compatibility enum is
introduced. See the [source audit](proposal-exclamation-source-audit.json).

COV-017bl adds three conditional question bundles to finite question-owner
checks. General 냐면 keeps verb/adjective homonyms compatible; verbal
느냐면 excludes ordinary bare adjective entries, and adjective 으냐면
excludes ordinary bare verb entries. Existential exceptions, standalone
auxiliary context and unknown provider classes remain distinct. Known local
adjective derivations and auxiliary owners keep an honorific-only verbal
extension Unknown. Negative and existential Eu auxiliaries also stay Unknown;
a generic verbal class does not prove every inflection is excluded. Three
inferred polite followers remain Unknown, and no universal follower license
is inserted. See the [source audit](conditional-question-source-audit.json).

COV-018aa preserves declarative quoted 군 + 요 under the existing homonym and
owner checks. Source-attested declarative followers do not override class or
spelling conflicts. Inferred experience 더라는군 + 요 remains Unknown and
survives both dictionary filters. No inference settles quoted 구나 + 요 or
contextual register; see [the audit](quote-followers-source-audit.json).

COV-017bm keeps existing formal `읍시다` proposal hypotheses with known
adjective entries or unclassified negative owners as Unknown. Verb homonyms
remain compatible; prior spelling and role conflicts still win. Both dictionary
filters retain these uncertainties. Contextual wishes and register are not
certified by a headword match; see [the review](proposal-evaluation.json).

## Opaque derivational roots (COV-022c)

The new `Root` role represents a reviewed derivational base, not a standalone
lexical POS. POS assessment is Unknown even if a provider has a homonymous
headword; lexical presence does not certify the root/suffix relationship. The
current KRDict snapshot has no 천천, 분연 or 천천하다 entries. Consequently
`--dict-only` and `--dict-compatible` remove the new unmatched root/related-
predicate paths while preserving the whole 천천히 and both 분연히 homonyms.
The raw API retains all hypotheses. The [tests](../tests/opaque_adverbs.rs) cover
missing heads, homonym identity, conservative role assessment and CLI/library
word/text parity. [Source evidence](opaque-adverb-source-audit.json) distinguishes
the root paths from the separately inferred 천천하다 lookup relationship.

COV-022d noun-forming -이 keeps predicate base lookups separate from the
whole lexical noun. POS compatibility checks the base's predicate membership;
it does not select a homonym or prove a particular derived noun sense. Both
filters preserve matched noun derivations, lexical nouns and adverb homonyms.
A following copula owns its own ending and dictionary assessment. Native
fixtures retain all headword homonyms and full senses. Identical component
strings may have distinct noun/adverb provenance and must remain distinct in
export. Browser sources select suffix 88924/88927 from that provenance.

COV-022f uses the same noun-suffix provenance for six native sense-2 forms.
The first two lookup lemmas of compound paths preserve individual nominal/
predicate POS assessments; a shared boundary places noun-forming 이 after both.
This does not select the intended sense of 길, 걸다 or 먹다, and whole nouns
remain alternatives. 미닫이 restores the source-listed 밀다 lookup stem with
explicit finite normalization. A later copula retains its own ownership. The
[review](noun-compound-source-audit.json) distinguishes explicit primary
segmentations from source-pattern inferences and keeps other compound leads open.

COV-022g nominal-base noun paths retain each base's nominal POS assessment,
whole-word alternatives and separate copula ownership. Shared base spelling
such as 동강 keeps nominal/adverb homonyms without choosing a contextual sense.
The 바둑 game headword is not proof of a historical spotted-animal meaning.
Both filters retain source-supported matched paths; a dictionary entry does not
certify the derivational relationship. See [the review](noun-base-source-audit.json).

COV-022h sound/manner noun candidates keep adverb-role compatibility separate from contextual base senses. Base homonyms remain available, and compatible POS does not certify the formation meaning. The source-listed 뺑뺑 derivational root has no pinned headword: raw results retain the suffix path, while both dictionary filters remove it and retain the matched whole noun. No replacement predicate or synthetic head is inserted.

COV-022i roots have no standalone POS assertion and all seven lack pinned base heads. Separate related-predicate candidates keep five attested 하다 lookups; the primary quiet-person 합죽거리다 lookup is absent. Both dictionary filters remove unmatched root/related paths while retaining matched whole nouns and the five known related predicates. Dictionary membership does not choose base sense or lexical history. 미치다/광 homonyms are preserved as source observations, not substituted for the complete 미치광 base.

For 까불이, the finite noun-suffix predicate lookup retains both 까불다 entries (38390 and 42138) under raw and both filters. The suffix source is 88924 sense 3 with its original class note, not a relabelled sense-1 source. The known noun 38393 also remains. Matching spelling/POS does not decide whether a verb homonym supplies the intended person meaning.

COV-022k keeps prefix 왕- entries 72520/72521 separately from standalone 왕. All five 눈 and three 점 homonyms remain; lookup/POS compatibility does not select an eye, snow, hole, dot, point or unit sense. Prefix/base composition is a finite source-pattern hypothesis. The unmatched complete 왕눈 root stays raw and disappears under both dictionary filters; the detailed prefix/base reading, point compound and independent 박이 suffix alternative remain. Prefixes are grammar components before their lemma, not additional lexical king lemmas.
