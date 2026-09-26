# Grammar coverage

Use the [coverage completion checklist](coverage-checklist.md) to track open
families, priorities, regression requirements, and release completion criteria.

The runtime grammar is authored in Rust, with no learned weights or corpus answer
lookup table. `src/grammar.rs` holds endings and spelling transformations;
`src/engine.rs` composes them. A reverse suffix trie indexes terminal rules.

| Family | Covered examples |
| --- | --- |
| Regular predicates | 먹고, 먹지만, 먹는데, 먹기, 가는, 간다 |
| Comparative endings | 보듯, 보듯이, 살듯, 보셨듯이 |
| Present conditional | 한다면, 산다면, 먹는다면, 먹으신다면 |
| Shortened adnominal expressions | 먹으려는, 살려는, 도우려는, 먹자는, 바꿔보자는 |
| Change/continuation connective | 먹다가, 갔다가, 불렀다가, 먹으셨다가; distinct 먹어다가 |
| Consonant attachment | 갑니다, 삽니다, 먹습니다, 간, 갈, 감, 삶 |
| 아/어 contractions | 먹어, 잡아, 봐, 줘, 돼, 마셔 |
| 하 / 푸 / ㅡ | 해, 하여, 퍼, 아파, 써, 커 |
| ㄷ / ㅅ / ㅂ | 들어, 들으면, 지어, 지으면, 추워, 추운, 도와 |
| ㅎ / 르 / 러 | 빨개, 빨간, 그래, 그러면, 몰라, 불러, 이르러 |
| ㄹ deletion | 사는, 삽니다, 사세요, 사니까, 사느냐 |
| Prefinal order | honorific → past (up to twice) → 겠 → 더 → terminal |
| Ending allomorphs | 먹으리라 / 가리라; interrogative 먹니 / connective 먹으니 |
| Copulas | 학생입니다, 학생이었다, 의사였다, 의사예요, 학생이에요 |
| Particle chains | 학교에서는, 학교에서만은, 사람만으로도, 길로 |
| Nominal plural suffix | 지식인들, 지식인들을, 친구들은, 지식인들이다 |
| Nominalized/embedded predicates | 먹기를, 먹음은, 있는가를, 것임을 |
| Attached auxiliaries | 먹어봤어요, 먹고있다, 하지않았다, 먹어보고있다, 먹어야한다 |
| Contracted nominals/pronouns | 내가, 제가, 누가, 내, 게, 건, 걸 |
| Contracted particles | 학교에선, 집엔, 병원엘, 보곤, 걷질 |
| Demonstrative contractions | 이게/그게/저게, 이건/그건/저건, 이걸/그걸/저걸, 뭘 |
| Outer particles | 저도요, 친구는요, 빨리요, 빨리들, 먹어들 |

Prefinal traversal decreases grammatical stage or consumes a past-marker slot.
Particle traversal consumes input with finite ordering rules. Auxiliary analysis
stores shared links between shorter input prefixes, reuses equal suffix recoveries,
and expands final paths iteratively. It does not cache copies of entire chains.
There is no arbitrary search-depth, beam-width,
or candidate-count cutoff. Distinct analyses are materialized, so termination
does not imply constant cost.

Lexical membership in an irregular class remains a hypothesis. For example,
`들어` admits `들다` and `듣다`. Some generated stems may not exist in dictionaries.
Rules enforce spelling boundaries and the implemented morphotactics, not lexical
existence. Corpus segmentation may also disagree with preserved vocabulary units.
Joined auxiliary input is analyzed morphologically, including some nonstandard
spacing; this does not certify that writing the components together is correct.

Known gaps include further 하다 shortening, additional adverbial derivation
outside the COV-012 families, rarer endings/particle combinations, and foreign spelling
whose pronunciation determines particle allomorphs. Evaluation reports retain
measured misses and separately count unsupported annotations.

Nominal plural [-들](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74906)
is a `suffix` morpheme, separate from a lemma or particle. One plural slot is
recognized before particles or a copula, and bare plurals are supported. The
unsplit alternative remains available (e.g. 아들 is also a lexical noun).
Particle allomorphs are checked against the plural surface, so 지식인들을
recovers 지식인 + 들 + 을 but 지식인들를 does not recover that path.
The separate 들 particle after nominals, adverbs, and licensed endings is
implemented as described below. General derivational suffix analysis remains open.

## Particle and pronoun expansion (P1)

The contracted particles [ㄴ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85847)
and [ㄹ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85760)
are recovered by removing the final attached consonant from an open-syllable
base. Output uses canonical 는 and 를. Case/topic chain rules still apply;
emphatic ㄹ additionally permits an inner adverbial particle, as in 병원엘.
Connective-ending attachment is explicitly licensed: e.g. 보곤 → 보다 + 고 + 는
and 걷질 → 걷다 + 지 + 를. This is normalized morphology, not source spans.

The 이/그/저 demonstrative paradigm has short and expanded alternatives:
이건 → 이거 + 는 / 이것 + 은, 이걸 → 이거 + 를 / 이것 + 을, and
이게 → 이거 + 가 / 이것 + 이. 뭘 has 뭐 + 를 / 무엇 + 을.
Whole-word candidates remain available, including the older bare 거/것
representations. These contractions compose with outer particles, e.g. 이건요.
Sources include KRDict [이거](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=71128),
[뭐](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=84991), and
the ㄴ/ㄹ examples. Other pronoun contractions are not implied by this finite paradigm.

[Polite 요](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86116)
and [distributive 들](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86264)
occupy separate outer slots: ordinary particles → 들 → 요. They attach to nominal
or adverbial hypotheses and to explicitly listed connective/final endings.
Examples: 저 + 도 + 요, 빨리 + 들, 먹다 + 어 + 들. Nominal -들 still uses
`MorphemeKind::Suffix`; distributive 들 uses `Particle`. Existing fused endings
remain alternatives, so 먹어요 also has 먹다 + 어 + 요 alongside 먹다 + 어요.

`LemmaKind::Adverbial` maps to dictionary POS 부사. An incompatible nominal
hypothesis can still survive the existing headword-only filter; consumers can
inspect POS compatibility or use the library's POS-aware annotation predicate.
The browser prefers a dictionary-compatible reading, then fewer morphemes for
a compact initial display. This is not contextual ranking or a change to export.

Scope limits: one slot for each outer particle; explicit supported ending
families rather than arbitrary stripping after every ending; no particles
inserted inside a joined auxiliary chain in this P1 batch; COV-019a now supports
먹어들봐요. Spaced 먹어들 봐요
is analyzed token by token. Further chains/ending licenses belong to COV-013.
Predicate dictionary membership and correct usage in a sentence remain hypotheses.

Evidence: [particle boundary tests](../tests/particles.rs),
[dictionary/CLI role tests](../tests/dictionary.rs), the `particle-*` and
`pronoun-*` [judgment cases](../tests/fixtures/validity.json), and
[browser regressions](../web/tests/browser.mjs). Independent linguistic review
of the candidate ledger is still pending.

Background: [Korean UD conventions](https://universaldependencies.org/ko/index.html),
[Lovit's rule-based lemmatization explanation](https://lovit.github.io/nlp/2018/06/07/lemmatizer/),
and [conjugation boundaries](https://lovit.github.io/nlp/2019/01/22/trained_kor_lemmatizer/).
This implementation does not import their code, dictionaries, or extracted rules.

## Bounded suffix decomposition (COV-010)

Derivations are additional grouped analyses. The engine retains whole-word
lemmas and never requires a dictionary to generate a suffix hypothesis.
KRDict documents [-님](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88852),
[-적](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88966), and
[-답다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=92145)
as suffixes with restricted nominal attachment. The implementation hypothesizes
a nominal base; it does not verify semantic classes such as titles/personified
objects for 님, or suitability for 적/답다. Even a dictionary/POS match does not
establish that a derivation makes sense in context.

- Nominal decomposition supports one 님, 적, or 들, plus the ordered 님 + 들
  sequence. These paths compose with particles and copulas. For example,
  선생님들을 has 선생 + 님 + 들 + 을 alongside 선생님 + 들 + 을.
  과학적이다 adds 과학 + 적 + 이다 + 다 while preserving 과학적 + 이다 + 다.
- Predicate-forming 답다 follows an unsplit nominal hypothesis or the 님, 들,
  or 님 + 들 paths. Its canonical `MorphemeKind::Suffix` form is **답다**,
  followed by its own prefinals/ending; it is not a second lexical lemma.
  `Analysis::breakdown()` interleaves this inflection before any auxiliary or
  outer particle/copula. 학생답게됐다 yields 학생 + 답다 + 게 + 되다 + 었 + 다.
- The known suffix requires ㅂ-irregular recovery before the supported vowel
  boundaries. Tests cover 다워요, 다웠어요, 다우면, 다운, 다우셨다, and 다움을,
  plus consonant attachments 답다/답습니다/답겠어요. The offline fixture retains
  [정답다's source conjugations](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=75947)
  (정다운, 정다워, 정다우니, 정답습니다). Regularized 답아요/답으면/답은 do not
  receive the suffix path; unverified whole-predicate hypotheses are preserved.
  Attachment licenses are explicit in `dap_suffix_allowed`; this is not a full
  adjective syntax validator. Existing prefinal/auxiliary constraints still apply.
- Dictionary-only filtering continues checking every **lexical lemma**, not
  grammatical suffixes or their semantics. The browser displays the stem 답,
  opens **-답다**, and retains the canonical form in JSON. It initially prefers
  a compact compatible reading; deeper decomposition is available in the selector.

No arbitrary suffix recursion, 적 + 들/답다 decomposition, 님-related stem
alternations (e.g. 아드님 → 아들 + 님), or phrase-level attachment is introduced.
Bare 적 derivation is a nominal-base hypothesis and makes no contextual choice
between the resulting nominal/adnominal uses. Direct nominalization + copula
without a particle (학생다움이다) remains an inventory gap; 학생다움만이다
works through the existing nominalization/particle path. Follow-ups are COV-013.

Evidence: [derivation regressions](../tests/derivation.rs), the `suffix-*`
[candidate judgments](../tests/fixtures/validity.json), attributed source-form
and CLI filtering checks in [dictionary tests](../tests/dictionary.rs), and
selector/grammar-entry [browser regressions](../web/tests/browser.mjs).

## Shortened 하다 (COV-011)

The rule engine now reverses the two Article 40 spelling processes documented
in [NIKL's explanation](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=325451).
They are suffix-boundary recoveries, not global replacements of 케/치/타.
The literal, unshortened forms remain available.

- `deletion.ha` restores 하 after a simple coda with stop realization [ㄱ/ㄷ/ㅂ].
  The implemented spelling classes are ㄱ/ㄲ/ㅋ, ㄷ/ㅅ/ㅆ/ㅈ/ㅊ/ㅌ, and ㅂ/ㅍ.
  Tests include 생각지, 생각건대, 생각다, 깨끗지, 넉넉지, 익숙지, and 섭섭지.
- `contraction.ha_aspiration` restores 하 after an open syllable or ㄴ/ㄹ/ㅁ/ㅇ
  coda, reversing the following aspirated ㄱ/ㄷ/ㅈ. Examples include 간편케,
  연구토록, 다정타, 분발토록, 무심치, 결근코자, 비유컨대, and 피케.
  Wrong-class paths such as 생각컨대 → 생각하다 and 익숙치 → 익숙하다 are
  forbidden. NIKL separately documents the
  [익숙지 correction](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=9288&mn_id=62&pageIndex=2).

The explicit ending inventory is 게/게요, 지/지요/지만/지만요,
다/다고/다는/다니/다면, 도록, 고자, and 건대. The ordinary 건대 ending was also
added; its KRDict entry is [78410](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=78410).
The 게/지 connectors compose with the existing auxiliary grammar, e.g.
생각지않았다 → 생각하다 + 지 + 않다 + 었 + 다. Existing particle licenses apply;
this batch does not extend them to every new ending. Components remain normalized:
the browser shows 생각하 + 건대 and the JSON retains 생각하다 plus ending 건대.

Restored 하 stays part of a predicate. It cannot be reused as a nominal before
an omitted copula. No bare 케/치/타 rewrites to 하다 without a base, and foreign
letters/numbers do not supply a guessed coda class. Complex codas, further ending
families remain separate audit work under COV-013. COV-021a below adds Article 39
잖/찮 recovery.

Dictionary-free recovery can add unknown lexical hypotheses such as 걷하다
beside 걷다 for 걷지. This is consistent with the exhaustive candidate API;
headword/POS filtering remains separate from grammatical boundary validation.
Evidence: [positive/negative and composition regressions](../tests/hada.rs),
nine `hada-*` [judgment cases](../tests/fixtures/validity.json), and
[dictionary/CLI tests](../tests/dictionary.rs). Independent linguistic review
remains pending.

## Adverbial derivation (COV-012)

This bounded extension adds optional predicate-base + `Suffix("이")` analyses
without replacing lexical adverbs. KRDict's
[adverb-forming -이](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88927)
has restricted attachment, distinct from its noun-forming and ending homonyms.
NIKL's [spelling discussion](https://www.korean.go.kr/nkview/nknews/199911/16_11.htm)
documents several stem-preserving -이 forms. The implemented classes are:

- Stems ending in 같/없, preserving the complete base: 같이 → 같다 + 이,
  똑같이 → 똑같다 + 이, 없이 → 없다 + 이, 끝없이 → 끝없다 + 이.
  Unknown compound bases remain hypotheses subject to dictionary filtering.
- The independently listed stems 굳, 길, 깊, 높, 많 followed by 이.
  Nominal homonyms such as 높이 retain their whole-word readings; nominal
  suffix decomposition is not inferred from the adverbial path.
- Explicit 달리 → 다르다 + 이 and 빨리 → 빠르다 + 이 mappings. NIKL treats
  these as [historically established forms](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=304692),
  not modern 르 inflection. `derivation.adverbial.lexical` marks that distinction.

All paths carry `suffix.adverbial.i`. The base uses the existing `Predicate`
lemma kind; dictionary POS compatibility therefore checks predicate membership,
not a contextual adjective sense. `Analysis::breakdown()` consumes the suffix
directly after the predicate base, with no ending or prefinal. It displays
같 + 이 / 없 + 이 / 다르 + 이 while preserving canonical lemma forms in JSON.
The browser labels the suffix and opens KRDict 88927, retaining the original
whole-word reading as its compact initial choice.

Derived paths can precede 도/만/는/요/들 and ordered combinations such as 만은
or 도요; normal particle allomorph and slot rules still apply. They do not license
subject/object marking, prefinals, arbitrary suffix recursion, or a joined
auxiliary connector. For instance 높이를 retains 높이 + 를, without inventing an
adverbial 높다 + 이 + 를 path. Other nominal interpretations remain available.
The source-listed -히, 하다-root and ㅂ-recovery extension is COV-022a below.
Other lexical/root classes and nominal -이 remain COV-013 audit work. No dictionary of corpus
answers is loaded by the engine.

Evidence: [path/boundary tests](../tests/adverbs.rs), eight `adverb-*`
[candidate judgments](../tests/fixtures/validity.json), and three unmodified
KAIST development sentences in [the annotated fixture](../tests/fixtures/kaist-adverbs.conllu).
Their target IDs are M2TA_069-s19/2 (같이), M2TA_089-s68/8 (없이), and
MH2_0069-s41/7 (달리). The corpus adapter checks these recovered base lemmas;
the project's suffix-kind judgments remain separately authored and pending
independent review. Dictionary/CLI/browser regressions check preservation and
the -이 homonym lookup.

## Candidate correctness audit

`tests/candidate_correctness.rs` specifies required and forbidden recoveries
independently of the reverse engine. Cases are manually authored spelling
constraints, not generated forward/inverse round trips or dictionary blacklists.

* Stem-final ㄹ must drop at the relevant ㄴ/ㅂ/ㅅ and -오 boundaries. The suite
  checks 살다, 알다, 만들다, and 놀다 across endings and tests retained ㄹ at
  non-triggering boundaries. For example, 사니까 recovers 살다, while 살니까
  cannot recover that lemma. Attached consonants and ㄷ irregulars have separate
  boundary checks. This follows the National Institute of Korean Language's
  [orthography Article 18](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001&regltn_no=222)
  and [explanation of ㄹ deletion](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=319173).
* Copular 이 remains part of the recovered stem. 학생이라고 retains the group
  학생 + 이다 and cannot generate 학생다 by stripping 이라고. Zero copulas
  after vowels and the negative copula 아니다 remain available. In particular,
  라서 is restricted to copular contexts; it cannot recover 가다 from 가라서.
  NIKL documents this restriction in its
  [discussion of 이라서 and 아니라서](https://www.korean.go.kr/nkview/nklife/1996_4/6_10.html).
  The separate imperative (으)라 family still licenses 먹으라고 and 가라고.
* Ambiguous 들어 → 들다/듣다 and 사는 → 사다/살다, and unchanged hypotheses,
  remain available. A forbidden recovery does not imply that an entire input
  token has no valid nominal or other interpretation.

The second audit adds these constraints and preservation checks:

* The ㅂ rule distinguishes 도와/고와 from 도워/고워 for 돕다/곱다 before
  아/어-family endings and past markers. Both stems still use 우 before (으)
  endings, as in 도우면 and 고우니. Regular 도우다/고우다 hypotheses remain
  available for 도워/고워. See NIKL's
  [ㅂ-irregular explanation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=261&pageIndex=1&qna_seq=316687).
* 리라 cannot bypass (으) boundary selection: 먹으리라 is accepted for 먹다,
  while 먹리라 is rejected for that lemma. Tests preserve 가리라, 살리라,
  and irregular recovery through 들으리라, and check past/modal combinations.
  The Korean Basic Dictionary specifies the
  [리라 attachment conditions](https://krdict.korean.go.kr/jpn/dicSearch/SearchView?ParaWordNo=79280&nation=jpn).
* Interrogative 니 and connective (으)니 are separate morpheme paths. Both 먹니
  and 먹으니 recover 먹다; 그렇니 and 그러니 recover 그렇다 through different
  endings. Tests check the paths, not just the flattened lemma list. NIKL
  [explicitly distinguishes these endings](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=313616).
* In joined obligation input such as 먹어야한다, 어야 is the connector and 하다
  is the auxiliary; 야하다 must not become an auxiliary component. Past forms,
  하 contractions, and nested auxiliaries are checked. The dictionary describes
  [auxiliary 하다](https://krdict.korean.go.kr/eng/dicSearch/SearchView?ParaWordNo=62888&nation=eng).
  NIKL requires [spacing between 어야 and 하다](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6204);
  recognizing joined input is tolerance, not a spacing recommendation.
* Additional paired cases cover ㄷ/ㅅ/ㅎ/르/ㅡ boundaries and preserve regular
  alternatives. They check, for example, 들으면 versus 들면 for 듣다 and 몰라
  versus 몰러 for 모르다. These follow the spelling transformations in
  [orthography Article 18](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001&regltn_no=222).

The audit covers these cases and boundary families only. Broader ending selection,
irregular-class membership, lexical validity, and contextual interpretation
still need independent evidence. Corpus regression snapshots protect previously
recovered gold groups separately from these negative correctness tests.

## Comparative endings (COV-016)

KRDict [-듯 (80280)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80280)
and [-듯이 (80282)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80282)
license direct attachment to predicates/이다 and honorific, past, and modal
markers. Each is a literal consonant-boundary `Ending`, with existing `ending`
and `boundary.regular` provenance. Thus 보듯이 is 보 + 듯이, not a noun 듯 plus
suffix 이. Stem-final ㄹ remains; vowel-boundary ㄷ/ㅂ/르 recovery is not applied.
Existing auxiliary chains may end in these forms (먹어보듯이); the comparative
ending itself is not an auxiliary connector (no 먹다 + 듯이 + 보다 path).

The offline tests cover open/closed/ㄹ stems, adjectives, copulas, prefinal order,
existing auxiliaries, Unicode normalization, lexical alternatives, component
projection, and targeted negative boundaries. Dictionary/CLI filtering retains
보다, and the browser labels both endings “As / like” and opens their distinct
source entries. The spaced bound noun 듯, outer particles, additional attachment
classes, and shortened 하다 spellings need separate review. The general predicate
kind does not independently distinguish verb/adjective dictionary senses.

The [inventory audit](inventory-audit.md) explains the source comparison and
remaining work; merely finding a suffix spelling is not proof of coverage.

## Present conditionals (COV-017a)

KRDict [-ㄴ다면 (66956)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=66956)
licenses vowel/ㄹ-final verb stems and honorific 시, while
[-는다면 (68738)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=68738)
licenses other consonant-final verb stems. Both use canonical `Ending` 는다면:
한다면 → 하다 + 는다면, 산다면 → 살다 + 는다면, 먹는다면 → 먹다 + 는다면.
The vowel-stem alternative 사다 remains for 산다면. Existing attached-coda or
consonant-boundary provenance explains the difference in spelling.

The attached ㄴ boundary restores an open or ㄹ stem; it does not perform the
vowel-only ㅂ/ㅎ recoveries used by adjective adnominal endings. Prefinal recovery
for this present family permits 시 only. Past/modal/retrospective markers are
not recovered into a 는다면 path; existing 먹었다면/먹겠다면 paths retain plain
다면. Unknown lexical stems that happen to look inflected remain hypotheses.
Honorific recovery retains its own vowel boundary, so 들으신다면 and 도우신다면
still recover 듣다 and 돕다 before 시. An earlier predicate in an auxiliary chain
can independently carry past (먹었어야한다면).

The library uses its existing generic predicate role. It does not certify that
a generated lexical stem is a verb rather than an adjective, nor does headword
filtering decide that class. Known derived -답다 remains governed by its existing
ending whitelist. Additional outer particles, this ending as an auxiliary
connector, and the separately listed quoted-expression homonyms (68881/68841)
are outside this batch. The browser displays the canonical 는다면 component,
marks expanded spellings, and opens the ending entry 68738. The attributed
fixture includes both quoted-expression homonyms to test kind-sensitive lookup.

## Shortened adnominal expressions (COV-017b)

KRDict [-으려는 (86717)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86717)
and [-려는 (86688)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86688)
record shortened (으)려고 하는 expressions of intention or impending action.
Closed non-ㄹ stems use 으려는; vowel/ㄹ stems and honorific 시 use 려는. Existing
으-boundary recovery handles 들으려는 → 듣다, 도우려는 → 돕다, and 지으려는 → 짓다.
The output bundles the expression into canonical `Ending` 으려는.

[-자는 (83896)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=83896)
records shortened 자고 하는, quoting a proposal while modifying a following
noun. The scoped literal boundary preserves ㄹ/ㄷ/ㅂ, as in 놀자는, 듣자는,
and 돕자는. Its canonical `Ending` is 자는. Bare stems are supported; honorific
or other prefinal readings of this proposal expression remain unreviewed and
are not recovered into this new path. Intention permits 시 only. Unknown lexical
stems that resemble inflected forms remain hypotheses.

Both add `ending.adnominal_expression` provenance. Each is one grammatical
component, with no implicit 하다 lemma. Existing auxiliary groups can end in
these expressions, e.g. 바꿔보자는 → 바꾸다 + 어 + 보다 + 자는. The expressions
are not auxiliary connectors and do not enable outer-particle attachment.
Whole-word alternatives and 자는 → 자다 + 는 remain. The generic predicate
role does not independently validate the lexical verb/adjective class.

The dictionary classifies these entries as 문법‧표현 / 품사 없음. `Ending`
therefore includes scoped bundled terminal expressions as well as ordinary
endings. The browser uses the canonical entry IDs 86717/83896 through a narrow
headword/ID/POS/kind exception. Labels are “Intending / about to” and “Quoted
suggestion”; selecting one opens the full expression definition. These three
expression entries sit outside COV-013's initial POS-based table inventory.

## Literal daga (COV-017c)

KRDict [-다가 (85740)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85740)
permits predicates/이다, honorific 시, and past markers. A literal consonant
boundary preserves the stem in 먹다가, 살다가, 듣다가, and 돕다가. Existing
prefinal recovery supplies 갔다가, 불렀다가, and 먹으셨다가, including the
engine's bounded repeated-past sequence. Recovered modal 겠 or retrospective
더 is excluded from this new path. Unknown stems that resemble inflected forms
remain unverified lexical hypotheses.

Canonical `Ending` 다가 uses ordinary `ending` and boundary provenance. It can
terminate existing auxiliary chains and copulas, and is licensed after the
known adjective suffix -답다 (학생답다가/학생다웠다가). It is not an auxiliary
connector itself. Additional outer particles and shortened -다 sense handling
remain outside this batch.

The existing [-어다가 (86099)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86099)
retains its separate vowel boundary and canonical form. 가다가 may expose both
가 + 다가 and 가 + 어다가; 먹어다가 keeps 먹다 + 어다가. The UI labels 다가
“While / then” and 어다가 “Then / using the result”, with separate source links.
These hints do not select a contextual sense.

The saved KAIST 살겠다가 case is a quoted clause followed by subject particle
가. Its annotation is 살+겠+다+가 / pvg+ep+ef+jcs. It must not be counted as
new -다가 coverage; the source excerpt and targeted forbidden judgment preserve
this distinction while leaving future quoted-clause recovery possible.

## Quoted questions (COV-017d)

KRDict [-냐는 (86030)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86030)
and [-느냐는 (86031)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86031)
describe shortened 냐고 하는 / 느냐고 하는 expressions modifying a following
noun. Each remains a single canonical `Ending`, with
`ending.adnominal_expression` provenance and no inferred 하다 lemma.
Literal attachment keeps ㄷ/ㅂ stems intact (듣냐는/돕느냐는), and the existing
ㄴ boundary drops ㄹ (사느냐는 → 살다). 사다 remains an alternative.

Both entries list 시/었/겠 attachments. Existing prefinal recovery preserves
their ordering in 먹으셨겠냐는; auxiliary paths include 먹어봤느냐는 →
먹다 + 어 + 보다 + 었 + 느냐는. Bare copulas take 냐는, while prefinals
permit 학생이었느냐는. Known adjective suffix -답다 permits bare 냐는 but
not bare 느냐는; prefinal 겠 permits 학생답겠느냐는. These are bounded
structural constraints. The generic predicate role does not independently
validate lexical verbs versus adjectives, including the 있다/없다 classes
specified by the 느냐는 entry. Dictionary headword matching is not that check.

The separate adjective allomorph and retrospective quotation were subsequently
added by COV-017e below.
No additional outer particles or auxiliary connectors are licensed.
Expression entries have 문법‧표현 / 품사 없음 metadata; the browser admits
only the exact canonical headword/ID pairs for `Ending` components. Both receive
the “Quoted question” label. Other unclassified entries remain excluded.

## Adjective and retrospective questions (COV-017e)

[-으냐는 (86032)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86032)
adds canonical `Ending` 으냐는 for the adjective allomorph. Full 으 follows
non-ㄹ closed stems (좋으냐는); its short 냐는 spelling permits ㄹ deletion
(기냐는 → 길다), ㅂ → 우 (추우냐는 → 춥다), and ㅎ deletion
(파라냐는 → 파랗다). These are compositional recoveries from the question
boundary and quoted expression, supported by NIKL's
[ㅂ explanation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=313964)
and [ㅎ/allomorph distinction](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=309166).
This differs from literal 냐는, which does not trigger those vowel recoveries.
Unknown lexical stems remain hypotheses; the generic predicate role still
does not prove adjective membership or irregular class membership.

The 으냐는 path is for bare stems; existing prefinal paths use 냐는/느냐는.
Known -답다 requires its irregular spelling (학생다우냐는), and copulas do
not acquire an adjective 으냐는 path. Retrospective 더 now precedes literal
냐는: 먹더냐는 → 먹다 + 더 + 냐는; 살더냐는 preserves ㄹ before 더.
The decomposition follows the engine's existing 더 + 냐 representation and
NIKL's [listed 더 boundary](https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=316861),
composed with the shortened quotation. It does not assert that KRDict's whole
ending -더냐 is a separate lexical lemma. Earlier prefinals, copulas, and
auxiliaries retain their ordering. No retrospective 느냐는 path is added.

## Post-ending particles (COV-018a)

KRDict [는 (85851)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85851)
and [도 (86258)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86258)
license connective attachment, including 어/게/지/고. Both now use the
existing reviewed connective inventory in `before_particle`: e.g. 먹고는,
하지도, 하면서도, and quoted adverbial 것이라고도. Topic 는 retains its
vowel boundary; bare adnominal 는 and formal final 습니다 do not license 도.
Nominalized endings continue to accept their existing ordinary particles.

Restrictive [만 (86554)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86554)
is supported after 어/어서/어야/게/고, including 통해서만 and 먹어야만.
Concessive [만 (86555)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86555)
and [마는 (86552)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86552)
follow 다/는다/습니다/냐/느냐/으냐/자/지/더니. They receive
`particle.concessive` provenance. Full 마는 is restricted to these endings,
not bare nouns or nominalizing 음. Existing prefinals, copulas, auxiliary groups,
and permitted outer particles compose before or after the new attachment.
Bundled 먹지만 → 먹다 + 지만 remains alongside 지 + 만.

The UI uses the selected analysis and adjacent ending to choose the concessive
만 label/source. Nominal/restrictive 만 keeps its existing entry. This structural
hint does not rank senses or resolve contextual ambiguity. Further particle
chains and additional attachment families remain tracked separately;
COV-019a below adds bounded particles inside auxiliary chains.

## Outer choice and quotative particles (COV-018b)

The inner coordination slots for (이)나/(이)든지/(이)야 remain; an additional
outer choice slot follows case and restrictive particles. (이)라도 occupies
the outer slot. The immediate surface boundary chooses the full or short form:
학교에서라도, 학생만이라도, 어디까지나, 학교에서든지, and 학교에서야.
ㄹ counts as a consonant here (길이라도), unlike instrumental 로. Repeating
the same choice family through the two slots is not licensed. Polite 요 and
the existing distributive slot may follow. Whole-word alternatives remain.

Sources: KRDict [이나 (89214)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89214),
[나 (89218)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89218),
[이라도 (78504)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=78504),
[라도 (78508)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=78508),
[이든지 (86139)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86139),
[든지 (70334)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70334),
[이야 (70340)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70340),
and [야 (70339)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70339).
Nominal and adverbial bases are alternatives; existing adverb derivations also
compose (달리라도 → 다르다 + 이 + 라도). Nominalized predicates retain
ordinary particle attachment (넣기라도). Short 나/라도/야 permit the reviewed
어/게/지/고 endings. 나/든지 additionally permit final 다/는다/라/으라/어라.
This is not a general license for all endings or arbitrary particle repetition.

Nominal quotation/emphasis receives separate literal `Particle` forms 이라고
(closed boundary) and 라고 (open boundary), allowing outer 도/는/요 and the
existing ㄴ contraction in 학교라곤. Source entries distinguish quotation
([70075](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70075),
[70074](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70074))
from nominal emphasis/qualification
([86353](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86353),
[86366](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86366)).
The existing 학생 + 이다 + 라고 copular path remains alongside 학생 + 이라고.
The browser's “Quotation / emphasis” hint does not select a contextual sense.
It looks up the particle key rather than the hyphenated ending key; all source
homonyms remain in the dictionary data. Cross-token quoted sentences and the
separate 살겠다가 quoted-subject annotation remain outside this nominal rule.

## Auxiliary connectors and internal particles (COV-019a)

The [auxiliary source inventory](auxiliary-inventory.json) records all 54 entries
marked 보조 동사 or 보조 형용사 in the pinned KRDict export, including notes
from every sense. This is a structural attachment catalog, not a lexical-class
or contextual sense validator. Each entry includes its primary-source URL.
The runtime keeps a finite connector/stem table; it does not read the inventory.

| Canonical connector | Auxiliary families added or expanded |
| --- | --- |
| 어 | 나다/나가다, 계시다, 가지다/갖다, 달다, 마지않다/마지아니하다, 먹다, 버릇하다, 빠지다, 쌓다, 재끼다, 젖히다, 죽다, 치우다, 터지다, 하다 |
| 고 | 계시다, 나다, 들다, 보다, 자빠지다, 하다 |
| 지 | 아니하다, alongside 않다/못하다/말다 |
| 게 | 생기다, alongside 되다/하다 |
| 은/는 | 듯하다/듯싶다, 양하다, 척하다, 체하다 |
| 을 | 듯하다/듯싶다, 만하다, 법하다, 뻔하다, 성싶다 |
| 음 | 직하다 |
| 으려/으려고 | 들다, 하다 |
| 기로/자고 | 들다 |
| 다/다가 | 보다, 못하다; 다 also connects 싶다 |
| 는가/은가/나/을까 | 보다, 싶다 hypotheses |
| 었 + 으면 | 하다, 싶다 |
| 기도/기는/기만/고자 | 하다 |

Existing 어/고/지/게/어야 connections remain. Boundaries use the existing
spelling recovery and ordered prefinal machinery. 가지다/갖다 require following
고; 달다 permits following 으라/으라고/으라는/으라면/오; 보다 after 다/다가
requires 으니/으면. These constraints reject 먹어가졌다 and 먹어달았다 for
those auxiliary readings. They do not claim every tail or lexical restriction
in the source is enforced. In particular, negative 말다 mood selection,
verb/adjective classes, source-specific subsets such as 빠지다, and the legacy
어 + 없다 path still need review under COV-019.

One internal particle slot can occur before an auxiliary. 도/만/들 use the
existing ending licenses and auxiliary connector check; 기 + 도/만 connects
하다. 고/기 + 는, 기 + 나/야 connect 하다, while 고 + 야 connects 말다.
Contracted 곤 recovers 고 + 는. Thus 먹어들봐요 has 먹다 + 어 + 들 + 보다 +
어요, 먹고야말았다 has 먹다 + 고 + 야 + 말다 + 었 + 다, and 먹곤했다
has 먹다 + 고 + 는 + 하다 + 었 + 다. The rule adds
`auxiliary.internal_particle` provenance and preserves each particle's kind.
Bundled 기도/기는/기만 and unsplit lexical candidates remain alternatives.
Repeated internal particles are not recursively stripped. The same bounded
slot can occur at different links of a longer chain; no chain-length cap is added.

Joined input is tolerated for analysis. The normal orthographic rules can
require a space before the auxiliary, particularly with intervening particles;
see [NIKL's Article 47 discussion](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=305086).
This feature does not repair whitespace, combine separately tokenized predicates,
or split particles inside bound-noun expressions such as 듯도 하다.

Two older negative tests were overbroad: KRDict licenses 고 + 보다 (62171,
sense 3) and 고 + 하다 (62888, sense 7). The tests now use unsupported 게 + 보다
and 지 + 하다 instead, with positive regressions for the source-listed pairs.
Exact lemma/morpheme order, NFD normalization, particle provenance, and boundary
violations are checked in [auxiliary tests](../tests/auxiliary_inventory.rs).
Dictionary/CLI and browser tests preserve the same groups and role-specific
labels. The packed iterative auxiliary search remains; stress tests retain the
1,024-syllable memory bound and unlimited candidate enumeration.

## Direct nominalization and copulas (COV-020a)

The nominalizing endings [기 (72222)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=72222)
and [음 (78528)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=78528)
make predicates function as nominals. They now compose directly with
[copular 이다 (86232)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86232),
using the existing -ㅁ/-음 spelling recovery. This adds a missing composition
boundary; it does not reinterpret every ending as a nominalizer or implement the
homonymous noun-forming suffixes -기/-음.

Explicit copulas, existing vowel-final 이 omission, and polite 이에요/예요 and
이야/야 forms share the nominalized-base expansion. 학생다움이다 exposes
학생 + 답다 + 음 + 이다 + 다; 먹기다 and 먹기예요 retain 먹다 + 기 + 이다.
Consonant-final 먹음 requires 이, so 먹음다 and 먹음예요 do not gain those
paths. Known -답다 uses its existing ㅂ-irregular boundary; 학생답음이다 does
not gain a 학생 + 답다 decomposition. No additional suffix ordering is enabled.
Whole-word nominal and predicate hypotheses remain, even when not dictionary
headwords. Nominalizing-ending provenance is `nominalization`; the copula retains
its existing `copula`, `copula.zero`, or `copula.polite` provenance.

Prefinals and auxiliaries retain their positions on each side of the boundary:
먹었음이었다 → 먹다 + 었 + 음 + 이다 + 었 + 다 and
먹어보기였다 → 먹다 + 어 + 보다 + 기 + 이다 + 었 + 다.
Nominalizations of copulas can themselves precede copulas; each recursive
composition consumes input. A regression retains a 64-level structural path
without a nesting cutoff; it is a termination/representation test, not a claim
that such a sentence is natural. Existing particles after a copula and the
separate particle-before-explicit-copula paths remain. The new direct path does
not admit arbitrary connective/adnominal endings, quoted clauses, or new omitted
copula contexts.

[Path and boundary tests](../tests/nominal_copulas.rs) cover normalization,
whole-word alternatives, suffixes, nesting, and ordered breakdown. The annotated
KAIST token MH2_0169-s271/6 (떠먹이기다) supplies independent grouped-lemma
evidence; synthetic source-backed tests cover the derived forms. The corpus
adapter does not judge the correctness of all grammatical components or alternatives.

## Negative contractions and confirmation (COV-021a/017f)

[NIKL's Article 39/40 explanation](https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=84&pageIndex=1&qna_seq=335814)
distinguishes contracted 지 않 → 잖 and 하지 않 → 찮 from the separate
Article 40 shortening of 하. The rule adds optional expanded analyses:
적잖은 → 적다 + 지 + 않다 + 은 and 만만찮았다 → 만만하다 + 지 + 않다 +
었 + 다. It does not correct the spellings 쟎/챦. The left predicate uses
existing 지 attachment and prefinal recovery, so Article 40 deletion can also
compose in 넉넉잖다 → 넉넉하다 + 지 + 않다 + 다. Incorrect 하 deletion after
ㄴ does not create 만만하다 from 만만잖다. Conversely, 찮 restoration uses
the existing aspiration boundary: open syllables and ㄴ/ㄹ/ㅁ/ㅇ permit it,
while stop-final 거북찮다 does not restore 거북하다. This follows
[NIKL’s explicit 거북잖다/생각잖다 explanation](https://www.korean.go.kr/nkview/nklife/1994_1/4_10.html).
Complex coda classes remain part of the COV-021 audit.

The expansion is represented as a predicate followed by an auxiliary, with
`contraction.negative` provenance. Both sides retain their own prefinals and
endings. Auxiliary search preserves contracted components in intermediate tails,
so 먹고싶잖다 retains 먹다 + 싶다 + 않다, while 먹잖고있다 retains 먹다 +
않다 + 있다. Existing known -답다 decomposition and direct nominalization/copula
composition also apply, e.g. 학생답잖다 and 적잖음이다. Each expansion removes
a contracted 잖/찮 boundary; there is no global text substitution or candidate cap.

Original lexical analyses remain. [적잖다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=84451),
[만만찮다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=50338),
and [괜찮다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=60097)
are dictionary entries in their own right. A mechanically restored stem may be
unknown, and an expanded negative need not have the same meaning as a lexicalized
word. Dictionary presence does not settle that semantic question. Tests preserve
both compact and expanded dictionary-compatible readings rather than replacing
lexical words with their historical constituents.

The separate expressions [-잖아 (86756)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86756)
and [-잖아요 (86757)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86757)
confirm or correct something for the listener. They remain one `Ending`
component with `ending.confirmation` provenance, without an inferred 않다.
Thus 먹잖아요 has both a bundled confirmation reading and an expanded negative
reading. The source-listed honorific/past/modal prefinals are supported;
retrospective 더 is excluded for the bundled expression. Copulas and preceding
auxiliaries compose, including 학생이잖아요 and 먹어봤잖아요. No contextual
selection, additional outer-particle licenses, or new auxiliary connector is
claimed for these expressions. Browser lookup admits only these two reviewed
품사 없음 expression IDs, alongside the existing expression exceptions.

[Regression tests](../tests/negative_contractions.rs) check full/short path parity,
NFD normalization, lexical alternatives, component ordering, and negative
boundaries. KAIST MH2_0159-s86/12 supplies independent 적다 + 않다 gold for
적잖은. Corpus recall does not judge every expanded candidate; the remaining
적잖이 miss concerns adverb derivation and stays under COV-022.

## Additional predicate adverbs (COV-022a)

The [adverb inventory](adverb-inventory.json) records the source-listed forms,
related predicate IDs, and dictionary coverage. Sources are KRDict's
[-히 (88504)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88504),
[-이 (88927)](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88927),
[NIKL's spelling discussion](https://m.korean.go.kr/nkview/nknews/199911/16_11.htm),
and the linked lexical entries. The runtime uses explicit root/suffix pairs,
not a heuristic that any consonant or final syllable selects a spelling.

Six listed ㅂ forms recover adjective stems: 가까이/가벼이/고이/새로이/외로이/
즐거이 → 가깝다/가볍다/곱다/새롭다/외롭다/즐겁다 + suffix 이.
`derivation.adverbial.bieup` distinguishes this derivation from ordinary vowel
ending recovery. 헛되이 → 헛되다 and 적잖이 → 적잖다 preserve their stems.
The latter retains the lexical adjective; it does not recursively split an
implicit negative auxiliary inside the adverb.

The 57 root/suffix pairs support related 하다 adjective lookup, e.g.
깨끗이 → 깨끗하다 + 이 and 조용히 → 조용하다 + 히. This is lemma-oriented
normalization: [NIKL identifies 조용 as the root to which 히 attaches](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=261&pageIndex=1&qna_seq=317650).
There is no literal 하 segment in 조용히. `derivation.adverbial.hada` records
the relationship; the browser displays 조용 + 히 while linking the related
adjective. The JSON keeps the lookup lemma and the suffix. Other consumers
should use provenance when presenting the root rather than blindly concatenating
lemma stems and suffixes. No root lemma kind or implicit 하다 suffix is added.

All new paths retain `suffix.adverbial.i` or `suffix.adverbial.hi`; suffix 히
is distinct from the causative/passive homonyms. Derivation consumes no prefinal
or inflectional ending and does not license an auxiliary. The existing reviewed
particle chains compose; 조용히도요 is supported, but 조용히를 does not gain an
adverbial 조용하다 path. 가까이 has a nominal homonym: 가까이를 retains that
whole-word noun reading without treating the adverbial 가깝다 + 이 as a noun.
Spelling regressions reject the targeted 가깝이/가까히, 조용이 and 깨끗히 paths.

This finite list is not an exhaustive lexical inventory. KRDict lacks some rare
related predicates listed in the NIKL discussion, including 열심하다; rule
recovery does not create a dictionary entry. Adverb/noun roots (곰곰, 더욱,
가만, reduplicated nouns), other adjective classes, shortened 익히/특히, and
nominal -이 remain open under COV-022. Dictionary POS compatibility checks the
existing broad predicate role, not adjective sense or semantic equivalence.

## Negative auxiliary particles and short prohibitives (COV-019b)

`irregular.mal` recovers exactly 마 → 말다 + 어, 마라 → 말다 + 어라,
and 마요 → 말다 + 어요. NIKL accepts both these short imperatives and
말아/말아라/말아요 ([2019 guidance](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6717),
[Article 18 explanation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=73&pageIndex=1&qna_seq=320385)).
The existing full forms remain. Standalone words receive a predicate hypothesis;
joined negative constructions put 말다 in the auxiliary role. Lexical 마 remains
an independent reading. The source guidance does not license arbitrary ㄹ loss,
short past forms, or shortening before connective 어서/어야. In auxiliary chains,
short 마 requires a preceding 지; it cannot replace completive 고 말다 or
act as connective 어 before another auxiliary. The browser shows the normalized
말 stem and ending, and -어라 links to KRDict 80682 (command/exclamation).
[NIKL explicitly excludes 마라요](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6475);
existing particle licenses already prevent 어라 + 요.

The one internal-particle slot now permits 지 + 는 before each existing negative
auxiliary: 않다, 못하다, 말다 and 아니하다. It also expands contracted 진
into 지 + 는, preserving `particle.contraction.n` and
`auxiliary.internal_particle`. Sources: KRDict [는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85851)
and [ㄴ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85847),
which explicitly allow attachment after 지, and
[NIKL's 애쓰지는 마라 example](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=44&pageIndex=1&qna_seq=334700).
These compose with existing earlier auxiliaries, e.g. 먹어보진마요, and preserve
internal 도/만. The particle remains after its ending in ordered breakdowns;
it does not authorize a new connector such as 지 + 보다 or repeated 는 slots.
Joined-input recovery is tolerant analysis, not a recommendation to omit spaces.

The KRDict auxiliary entry's command/proposal note is not a safe token-level
ending whitelist. [NIKL's question discussion](https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=98&pageIndex=1&qna_seq=326614)
recognizes 가지 말까요 and 하지 말아요 as questions, while noting a lexical
sense distinction not fully captured by the dictionary entry.
[Its indirect-wish guidance](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=8079&mn_id=27&pageIndex=1)
also permits 말았으면 in an appropriate context. Regression cases preserve
먹지말까요, 먹지말았으면, quoted 말라고 and embedded 말아야한다. No blanket
past-tense or nonimperative ban is applied. This is preservation of possible
lemma groups, not contextual certification of the auxiliary sense or sentence
mood. Lexical verb/adjective restrictions and remaining auxiliary links are
still COV-019 work.

## Auxiliary adjective inflections and legacy links (COV-019c)

The [class audit](auxiliary-class-audit.json) groups all 54 KRDict auxiliary
entries into 48 headwords: 34 verb-only, eight adjective-only, and six with both
classes. The eight unambiguous auxiliary adjectives are 듯싶다, 듯하다, 만하다,
법하다, 뻔하다, 성싶다, 싶다, and 직하다. This classification applies to their
auxiliary use in a grouped analysis, not every possible lexical homonym.

Bare adjective auxiliaries reject canonical 는다/는다고/는다는/는다면 and
는/는데/는데요/는데도/는데다가/는지/는가/는가요/느냐/느냐는. The audit
records the dictionary attachment notes for these families and their allomorphs.
For example, 먹고싶는다 and 먹을만하는 lose their targeted auxiliary readings;
먹고싶다 and 먹을만한 remain. Prefinals have separate licenses, so this pass
does not restrict endings after recovered 시/었/겠/더. In particular,
먹고싶었는데 and 먹고싶었느냐는 remain. No command-only whitelist is inferred:
어라 also has an exclamatory adjective use.

| Auxiliary use | Class evidence used |
| --- | --- |
| The eight adjective-only headwords | Adjective |
| The 34 verb-only headwords | Verb; resets a preceding adjective class |
| 보다 after 어/다가 | Verb |
| 보다 after 는가/은가/나/을까 | Adjective |
| 보다 after 고/다 | Ambiguous; preserve both classes |
| 못하다 after 다/다가 | Adjective |
| 않다/아니하다/못하다 after 지 | Inherit a known preceding class |
| 하다 after 어/게/어야/으려/으려고/고자/으면 | Verb |
| Other 하다 links and 양하다 | Ambiguous |

The single forward scan of each grouped analysis consumes nominal suffixes,
each predicate's prefinals and ending, then its particles. A plain nominal does
not consume the next copula's ending. An explicit 답다 suffix supplies adjective
evidence even though its lemma is nominal; ordinary lexical heads supply no
class without a dictionary. The scan allocates no extra component vectors.

[NIKL's negative-adjective example](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=312012)
requires 살고 싶지 않은 rather than the corresponding 는 reading. This supports
class inheritance through negative auxiliaries: 먹고싶지는않은 and 먹고싶잖은
remain, while their targeted 는 paths are excluded. By contrast, 먹어보지않는
and 먹고싶어하는 remain verbal. Class changes and inherited classes are checked
through multiple auxiliary links without imposing a chain-length cutoff.

The converse rule, excluding 은가 from every source-tagged verb, is not applied.
Honorific 계신가 is attested in [KRDict's examples](https://krdict.korean.go.kr/eng/dicSearch/SearchView?ParaWordNo=85753),
and existential negatives need separate treatment; tests preserve 먹고계신가 and
먹고있지않은가. Unknown or ambiguous classes are not silently treated as verbs
or adjectives. This batch does not resolve arbitrary lexical heads, left lexical
subsets such as the limited verbs before auxiliary 먹다, additional prefinal
constraints, or contextual sense selection.

The old 어 + 없다 table entry had no support in the modern auxiliary inventory.
KRDict [없다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89917)
is a lexical adjective; its noun/수 constructions do not license an 어 auxiliary.
That link is removed, including particle and later-auxiliary extensions. Lexical
없다 inflections and 없이 remain. Whole-word and other lexical hypotheses are
preserved; removal targets the unsupported grouped auxiliary reading. Existing
게 + 되다 is retained, but this inventory does not assign it an auxiliary class
by elimination because KRDict labels 되다 as a lexical verb.

## Propositive spelling and boundaries (COV-017g)

The grammar-label inventory exposed the legacy `습시다` rule. The canonical
ending is now `읍시다`: 먹읍시다 → 먹다 + 읍시다, 갑시다 → 가다 + 읍시다,
and 삽시다 retains both 사다 and 살다 hypotheses. Unlike 습니다/습니까, this
family uses vowel-boundary recovery: 들읍시다 → 듣다, 부읍시다 → 붓다, and
도웁시다 → 돕다. The attached ㅂ boundary drops ㄹ. The regular and irregular
lexical-class alternatives remain hypotheses, as elsewhere in the rule engine.
The test rejects the specific 먹다 path in 먹습시다, not the original token or
all conceivable unknown-word analyses. 먹어봅시다 and 먹지맙시다 retain their
auxiliary groups; prefinal and lexical-class restrictions need further review.

Sources: KRDict [-읍시다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=68880)
and [-ㅂ시다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=68883);
the example 도웁시다 in [-는다니까](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=81937).
The complete KAIST MH2_0159-s160 fixture preserves 봅시다 → 보다; that lexical
recovery already worked before this correction, so it is not counted as a gain.
See [tests](../tests/propositive_endings.rs) and [the audit](grammar-label-evaluation.json).

## Foreign nominals and pronunciation conditions (COV-014)

Particle attachment is determined by the preceding pronunciation, not the last
Latin letter or digit. [NIKL's examples](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=330830)
include A는/M은 and 1은/2는. The engine does not choose among letter names,
transliterations, numeral systems, or contextual readings. Instead, a spelled
base ending in a non-Hangul letter or number can support a **conditional**
nominal analysis. Four stable rule IDs state the necessary final-sound condition:

| Rule ID | Assumption |
| --- | --- |
| `pronunciation.assumed_vowel` | A final vowel, e.g. the split ABC + 는 |
| `pronunciation.assumed_consonant` | A final consonant, e.g. 3 + 은 |
| `pronunciation.assumed_non_rieul_consonant` | A consonant other than ㄹ, e.g. 3 + 으로 |
| `pronunciation.assumed_vowel_or_rieul` | A vowel or ㄹ, e.g. 1 + 로 |

The [로 source entry](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85761)
records its ㄹ exception. A condition is not an asserted pronunciation or a
recommendation to use every allomorph with every spelling. Conditional candidates
are visible even when their base has no dictionary entry. The unchanged word
also remains. All dictionary matching continues to use the spelled NFC lemma;
there is no inferred Hangul transliteration, number-name lemma, or fabricated
headword. `--dict-only` therefore still removes analyses with unmatched bases.

Only the new non-Hangul boundary is relaxed. Outer particles use the preceding
Hangul surface normally: ABC로만은 carries the condition for ABC + 로, while
ABC에는 and ABC들로 need none. Particle order and duplicate restrictions remain.
Hangul names and units, such as 김민수는 and 2026년은, keep ordinary coda checks.
The implementation accepts Unicode letters/numbers and their attached combining
marks, preserves NFC/NFD behavior, and does not turn punctuation or emoji into
new phonological bases. Compatibility jamo retain their original spelling;
no letter-name transliteration or jamo normalization is added.

Omitted copulas use the vowel condition: ABC다, ABC라면, ABC예요, and ABC야.
Existing contracted 이 + 어 → 여 readings, such as ABC였다 and ABC여요, now
also report that condition. Explicit ABC이다/ABC이에요/ABC이었다 do not require
an inferred final vowel. The initial copula contraction is tracked separately
from contractions in later auxiliaries, so ABC이었나봐요 does not acquire an
assumption from 봐. Sources: [NIKL's 이에요/예요 guidance](https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=326208)
and its [standard-language teaching material](https://m.korean.go.kr/common/download.do%3Bfront%3D12C549533B186950B1B76A529FAB4D33?c_file_name=94f3dbab-ed26-469f-b3d8-743c88e37a32_0.pdf&file_path=etcData&o_file_name=%EB%B0%94%EB%A5%B8+%EA%B5%AD%EC%96%B4+%EC%83%9D%ED%99%9C-%EA%B5%90%EC%82%AC%EC%A7%81%EB%AC%B4%EC%97%B0%EC%88%98%EA%B5%90%EC%9E%AC.pdf).
This is not a complete audit of copula ending/attachment restrictions (COV-020).

Tokenization remains lossless and splits at punctuation/symbols. Thus text
`3.14는` becomes `3`, `.`, `14는`, and `O'Neil은` becomes `O`, `'`, `Neil은`.
No whole decimal/name recovery across those boundaries is claimed. Raw `word`
input is not silently retokenized; new pronunciation hypotheses do not cross
punctuation inside its base. Whole-word candidates remain available to consumers
that supply their own tokenization or dictionary.

Evidence: [foreign boundary tests](../tests/foreign_nominals.rs),
[streaming/token boundary tests](../tests/text.rs), twelve `foreign-*` ledger
cases, dictionary/CLI filtering tests, ten browser cases, and 39 newly recovered
annotated development tokens. [The evaluation](foreign-nominal-evaluation.json)
keeps lexical recovery distinct from pronunciation validation; corpus spellings
such as Bilbe are retained literally, not silently corrected.

## Intention, expectation, and concession (COV-017h)

Three additional ending families retain one canonical `Ending` component:

| Canonical form | Surface boundary | Meaning and source |
| --- | --- | --- |
| 으리라고 | -으리라고 after a non-ㄹ consonant; -리라고 after a vowel or ㄹ | Reported intention/expectation: KRDict [85920](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85920), [85922](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85922) |
| 을지라도 | -을지라도 after a non-ㄹ consonant; attached -ㄹ지라도 otherwise | Concession: KRDict [77049](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=77049), [77051](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=77051) |
| 자면 | Literal attachment to a verb stem | Intention: KRDict [80338](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80338); shortened proposal quotation: [80339](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80339) |

The source attachment notes, senses, and examples are retained in the attributed
`krdict-grammar-labels.json` offline fixture. The vowel-boundary families use
existing ㄷ/ㅅ/ㅂ/ㅎ recovery; 자면 preserves stem consonants. Thus 들자면
recovers 들다, whereas 들으리라고 can recover 듣다. 살지라도 retains both
살다 and 사다. Original-word and unknown lexical alternatives remain.

으리라고 permits the existing honorific, past, and modal sequence, including
먹으셨겠으리라고; retrospective 더 is not licensed. 을지라도 permits honorific
and past markers, not 겠/더. 자면 permits a verb's honorific path but excludes
past/modal/retrospective markers. The honorific extension follows the engine's
verb-preserving 시 composition; the dictionary's -자면 notes state verb
attachment without separately enumerating prefinals. This distinction remains
visible for independent linguistic review rather than treating a corpus match
as a judgment of every tense or mood combination.

Known auxiliary adjectives and the explicit -답다 suffix cannot take 자면,
including after 시. Neither can a nominal copula. These restrictions apply to
the predicate carrying that ending: 먹고싶어하자면 retains 싶다 + 어 + 하다,
and 학생이고싶어하자면 retains its earlier copula. Unknown lexical heads remain
unclassified, so a dictionary match alone does not certify verb compatibility.
The conjectural 으리라고 and concessive 을지라도 support adjectives/copulas;
-답다 still requires its ㅂ-irregular spelling at a vowel boundary.

Existing auxiliary chains may precede these endings; none of the three is a new
auxiliary connector. A following reporting predicate is not inserted implicitly.
The -으리라고 intention and expectation senses and the two -자면 homonyms share
a bundled representation; the browser exposes both sources and a context note.
This adds neither contextual sense selection nor cross-token quotation parsing.
Additional outer particles and shortened quotation families remain COV-017/018.

## Emphatic and concessive particles (COV-018c/017i)

| Component | Source and attachment |
| --- | --- |
| 야말로 / 이야말로 | KRDict [86102](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86102) / [86103](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86103): emphasis after an open/consonant nominal or adverbial phrase |
| 나마 / 이나마 | [70309](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70309) / [70312](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70312): accepting limited conditions, with the same open/consonant distinction |
| 는커녕 / 은커녕 | [70316](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70316) / [70317](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70317): emphatic negation after an open/consonant nominal or adverbial phrase |
| ㄴ커녕 → 는커녕 | [70315](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70315): contraction after an open boundary; one normalized particle component |
| 커녕 | [86168](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86168): the independent bare particle follows a noun |
| 서 | [86712](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86712): locative/source, shortened 에서, after nouns including consonant-final 시장/부산 |
| -으나마 / -나마 | [80164](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80164) / [80167](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80167): separate predicate ending, canonical 으나마 |

The new particles use the existing outer slot after nominalization, adverbial case, and
restrictive particles, before polite 요 or distributive 들. The immediately
preceding surface chooses the allomorph: 안에서나마, 학교로나마, 학생만이나마.
ㄹ is a consonant for these particle pairs, unlike instrumental 로. New stacked
outer-focus combinations are not licensed by placing several forms in this slot.
More permissive particle ordering remains an explicit COV-018 review task.
Subject/object-marked phrases are not adverbial bases for these new particles:
조금 + 이 + 나마 is rejected, while 조금 + 이나마 and 조금 + 이다 + 으나마
remain. Bare 커녕 does not recurse through case particles; the separate
은/는커녕 forms cover the source-listed longer nominal particles.

Nominal/suffix paths compose, including 학생들은커녕 and 학생답기는커녕;
auxiliary nominalizations include 먹어보기는커녕. Source-listed adverb derivations
retain their deeper readings in 조용히나마 and 빨리는커녕. Bare 커녕 does not
inherit the longer particles' adverbial license. 나마 after adverbial 게 is
explicitly supported by the source's 막연하게나마 example; other post-ending
families are not inferred from the broad word “adverbial.”

Contracted 먹긴커녕 and 화핸커녕 normalize to 먹다 + 기 + 는커녕 and 화해 +
는커녕. The new `particle.contraction.nkeonyeong` provenance explains the
contraction. The display uses canonical components without invented character
spans; the label catalog links both full and contracted source entries. Topic 는
and 커녕 are not separately asserted for the bundled particle. Original-word and
unknown-base hypotheses remain available.

The old 서 rule incorrectly applied the count-emphasis homonym's open-boundary
condition to the locative homonym. Correcting the latter admits 서울서 and
시장서 and removes the unnecessary vowel assumption from ABC서. It does not
assert that the count-emphasis reading (source 86557, e.g. 둘이서) applies to
arbitrary consonant-final nouns. Dictionary glosses/labels summarize available
entries without selecting the contextual homonym. A surface ending in 서 may
instead be lexical: GSD's 확약서 in a sentence about submitting a written pledge
is a segmentation-review case. Its annotated 확약 + 서 now matches numerically,
but that is not evidence that the particle reading is intended there.

The homonymous predicate ending -으나마/-나마 has separate `Ending` components
and source lookups. Existing (으) boundary recovery handles ㄷ/ㅅ/ㅂ/ㅎ and ㄹ
deletion; honorific 시, past 었 and modal 겠 are licensed, not retrospective 더.
The known -답다 derivation requires its ㅂ-irregular boundary. 조금이나마 retains
both 조금 + 이나마 and 조금 + 이다 + 으나마, the latter explicitly illustrated
by source 80167. No new auxiliary connector or contextual sense decision is
introduced. Omitted copulas beyond the existing engine paths and further outer
particles remain COV-018/020 work.

## Definition particles and short quotations (COV-018d/017j)

| Representation | Attachment and sources |
| --- | --- |
| 란 / 이란 (`Particle`) | Definition/topic after an open/consonant nominal: KRDict [85858](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85858), [85859](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85859) |
| 란 (`Ending`) | Shortened quoted fact after copulas, honorific copulas, retrospective 더, or conjectural (으)리: [86297](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86297) |
| 으란 (`Ending`) | Shortened quoted command, full -으란 after a non-ㄹ consonant and -란 otherwise: [89676](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89676), command sense of [86297](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86297) |
| 으리 (`Prefinal`, scoped before 란) | Conjecture/intention with full 으리 or short 리: [86606](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86606), [52612](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=52612) |

학교란 and 학생이란 retain both nominal definition particles and copular
quotations, with different lemma groups and grammatical kinds. The particle path
supports nominalizations and existing nominal suffixes, e.g. 먹기란 and
학생들이란, but not a subject-marked 학생 + 이 + 란 or an adverbial case chain.
ㄹ counts as a consonant for the particle pair; foreign bases state the necessary
pronunciation condition. The copular path preserves explicit 이 after consonants,
permits its existing vowel-final omission, and admits 아니다 and honorific 시.
Bare past/modal markers before 란 are not licensed by this copular path.

The factual expression additionally follows retrospective 더, including earlier
honorific/past/modal markers already supported by the engine. Conjectural 으리
is recognized only before 란 in this batch, with honorific/past/modal before it,
not retrospective 더. This recovers the source's 작으리란 and the composed
먹었으리란 without adding a freely attachable prefinal to every ending.
Existing 으리라 and 으리라고 remain bundled endings. The new provenance
`prefinal.conjectural_quotation` explains this bounded representation.
Known -답다 derivatives retain the ㅂ boundary, including 학생다우리란.

The quoted command 으란 permits bare or honorific stems, not recovered
past/modal/retrospective markers. Vowel-boundary irregulars apply and ㄹ is
preserved, as in 들으란, 도우란, and 살란. It does not replace the copular
fact expression. Source 86297 calls the command attachment verbal but also
explicitly gives 행복하란; the implementation therefore does not impose a
blanket lexical-adjective rejection on state-directed wishes/commands. Broader
mood/lexical constraints and the existing -답다 command exclusions remain
COV-019/020 work. No new auxiliary connector or implicit reporting 하다 is added.

Explicit standalone 이란 gains an 이다 lemma with `Copula` role and
`copula.fragment` provenance. The source corpus has such a token after a quoted
nominal phrase. This retains the original word and lexical hypotheses and does
not join tokens or invent a missing nominal. Bare 라는, with an omitted 이,
remains a separate representation question under COV-020.

The full 라는 form already has copula + ending analyses. NIKL explains
[철수라는 as omitted copular 이](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=90&pageIndex=1&qna_seq=327939)
and [이라는/라는 as a shortened quotation](https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=98&qna_seq=329041).
Three KAIST entries instead annotate 근대라는, 사회주의라는, and 민주주의라는
as noun + particle, with no copula in the gold group. The engine keeps its sourced
copular analysis; these remain measured misses and documented representation
differences. The evaluation separately records quotation after ending-bearing
clauses and omitted-copula fragments, rather than licensing arbitrary suffix
removal to match the corpus.

### Quoted copula fragments (COV-020b)

Standalone `이라는` has an explicit `이다 + 라는` Copula-role candidate, alongside
its previous predicate/lexical hypotheses. Standalone `라는` now has the same
canonical components with `copula.omitted_fragment` provenance. This candidate
requires preceding quoted material; word analysis cannot establish that context.
The browser shows the condition for the selected reading and includes it in
filtered JSON export. Its normalized `이 + 라는` display does not claim that 이
has a source span. No nominal component or reporting verb is invented.

Source: [NIKL, quotation punctuation and 라는](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=90&pageIndex=1&qna_seq=327939)
explains that 라는 after a closing quote omits 이 from 이라는. The bundled
ending retains its existing [KRDict label/source](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82217).
Explicit `이란` remains covered by COV-018d/017j.

The omitted-fragment rule is scoped to the complete token 라는. It does not
relax consonant-final omission inside 학생라는, remove other terminal endings,
license following particles, or recover unbroken quoted clauses such as
대안인가라는. Those forms require their own attachment/representation review.
Tokenization remains unchanged: punctuation stays separate, offsets reference
the original input, and streaming/cache results equal independent word results.

Two complete KAIST development sentences protect MH2_0209-s39/4 and
MH2_0209-s122/4. Both annotate the lemma 이; their `OrigLemma=이+란` differs
from this program's canonical 라는 component. The measured gain concerns the
lemma group, not a claim that the morpheme segmentation matches the corpus.

### Intention and necessity bundle (COV-017k)

The dictionary expressions [-아야겠-](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86238),
[-어야겠-](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86239),
and [-여야겠-](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86240)
share canonical `어야겠`. They appear before a final ending, so the API uses
`MorphemeKind::Prefinal` for this bundled expression; this does not assert that
KRDict classifies it as a single prefinal ending. No implicit 하다 is inserted.
The viewer labels it “Intention / necessity” and links all three source entries.
The hint explains its bundled and normalized representation.

Recovery uses the existing 아/어 boundary, including vowel harmony, 하다 and
irregular alternatives: 해야겠다, 하여야겠다, 살아야겠다, 와야겠다,
들어야겠다, 도와야겠다, 몰라야겠다, 써야겠다 and 그래야겠다. Adjectives
and copulas are licensed by the source, including 넓어야겠군요 and
학생이어야겠다. Known -답다 still requires its ㅂ-irregular form in
학생다워야겠다. Honorific/past markers can precede the bundle; no recovered
겠/더 precedes it through this route. Retrospective 더 can follow, consistent
with the source's 해야겠더라 example. Composition beyond the source examples,
including past and honorific combinations, remains agent-authored judgment
pending independent linguistic review.

Existing auxiliaries can precede the bundle, such as 먹어봐야겠다 and
먹고 있어야겠다 (represented as joined input in the word API). The new
necessity path is rejected before progressive 고 있다/계시다: necessity applies
to the whole progressive predicate, not to an action subsequently made
progressive. The attachment judgment uses the documented progressive functions
of [있다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=62595)
and [계시다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=61346).
Only the immediately preceding predicate is checked. Other inherited ending
and auxiliary licenses remain part of the COV-017/019 audit, including modal
combinations; this batch does not certify every generated combination.

The five complete corpus sentences include three newly matched groups and two
GSD annotations that supply implicit 하다 in 와야겠다 and 세척해야겠지요.
The latter remain measured misses with their original annotations. Literal
와야하겠다 still produces 오다 + 하다; the expression-only spelling retains
its bundled form. See [individual comparisons](obligation-evaluation.json).

### Factual 라-family and command prefinal licenses (COV-017l)

Factual 라/라서/라고/라면 now have component paths after recovered 시 and 더,
and a scoped conjectural 으리 path. 라는 permits 시; its separate quoted-experience
relative 더라는 is a bundled contraction of 더라고 하는. Thus 먹었더라 retains
both 먹다 + 었 + 더라 and 먹다 + 었 + 더 + 라, while 못하더라는 has 못하다 +
더라는. No unspelled 하다 lemma is inserted. Existing 으리라/으리라고 bundles,
으리 + 란, copulas, nominalizations, -답다, and auxiliary groups remain available.

The reviewed command/quoted-command forms 으라/으라고/으라는/으라면/으란 and
formal 으세요/으십시오/읍시다 permit recovered 시, but exclude recovered past,
modal, and retrospective markers. Copula-role paths exclude the reviewed command
and proposal endings. This leaves lexical predicate hypotheses intact: the engine
does not know whether an arbitrary headword is a verb or adjective. 으세요 also
has declarative/question senses, so 학생이세요 remains. 어라 has adjective
exclamation senses: only its incompatible 더 boundary is excluded in this batch.
자 has non-propositive homonyms, so 먹어보았자 is preserved. Further licenses for
these homonyms remain an explicit audit, not an inferred blanket mood filter.

Sources: KRDict [-라](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=79275),
[-라서](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80211),
[-라고](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=73964),
[-라면](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=68832),
[-라는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82217),
[-더라는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86347),
[-으라](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80715),
[-으세요](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86609),
[-어라](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80682),
and NIKL on [더 + 라](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=261&qna_seq=322161),
[alternative segmentation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=309235),
and [copula inflection](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=305261).
The [evaluation](prefinal-license-evaluation.json) lists the full source inventory
and every changed candidate for 63 audited surfaces. Composition judgments remain
agent-authored pending independent Korean-language review.

### Omitted copulas and colloquial nominal alternatives (COV-020c)

The reviewed omitted-이 boundaries now support 지/지요/죠, 면, attached ㄴ데,
and attached ㅂ니다/ㅂ니까 after a vowel-final nominal. 겁니다 has 거 + 이다 +
습니다; 건데 has 거 + 이다 + 은데; 학교죠 has 학교 + 이다 + 죠. Canonical
ending forms remain unchanged. Recovery requires the surface ending consonant
where applicable, and does not conjugate the nominal through verb irregulars.
The reconstructed 이 is a copula, not part of a fabricated lexical predicate.
For pure non-Hangul bases such as ABC죠, the separate-suffix path explicitly
requires a vowel-final pronunciation. No transliteration is chosen.

Before a copula, exactly 거/이거/그거/저거 also gain the alternatives
것/이것/그것/저것. These additions compose with existing explicit and polite
copulas: 거예요 keeps both 거 and 것. They do not rewrite arbitrary 거-final
words or recursively expand derivations. Whole-word homonyms such as 거지
remain. Existing nominalizations, auxiliaries, and outer particles compose:
먹긴데, 거지않다, 겁니다만, and 거면요 have ordered component paths.

Sources: NIKL explicitly explains [겁니다 and 거입니다](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=5935&mn_id=62&pageIndex=210)
and [건데 and 것인데](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=306752).
The [writing-teacher guide](https://www.korean.go.kr/common/download.do?c_file_name=cc9a75c9-14ac-4d4f-ab04-1f5e4fa08558_1.pdf&file_path=reportData&o_file_name=%EC%B4%88%EA%B8%89%20%ED%95%9C%EA%B5%AD%EC%96%B4%28%EC%93%B0%EA%B8%B0%29%20%EA%B5%90%EC%9B%90%EC%9A%A9%20%EC%A7%80%EC%B9%A8%EC%84%9C%20%EA%B0%9C%EB%B0%9C%20%EB%B3%B4%EA%B3%A0%EC%84%9C_2.pdf)
also illustrates 의삽니다 and distinguishes conversational omission from usual
formal writing. KRDict documents the copular attachment of
[-죠](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85771),
[-면](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80259),
[-ㄴ데](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85132),
[-ㅂ니다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=79397),
and [-ㅂ니까](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=79401).

The [evaluation](omitted-copula-evaluation.json) records nine additional annotated
groups and every changed candidate for 41 audited surfaces. Other omitted-copula
endings and prefinals, particle-marked nominal bases, broader colloquial noun
paradigms, and contextual sense selection remain open. Composition judgments
beyond explicit source examples await independent Korean-language review.

### Adverb and repeated nominal bases; shortened adverbs (COV-022b)

The [finite source inventory](adverb-root-inventory.json) adds eight adverb bases
(곰곰, 더욱, 일찍, 오뚝, 히죽, 생긋, 가만, 단연) and twenty-one repeated
nominal bases before their listed adverb-forming 이/히. Thus 더욱이 has 더욱 +
이 with an Adverbial lemma; 낱낱이 has 낱낱 + 이 with a Nominal lemma and Suffix
component. The same spelling also retains any subject-particle reading. Repeated
bases remain one component, without recursively splitting them or claiming that
every repeated string is a lexical noun. The inventory explicitly records absent
base entries and homonyms whose dictionary POS is incompatible with that path.

NIKL describes 익히 and 특히 as shortened 익숙히 and 특별히. These gain
normalized lookup paths through 익숙하다 and 특별하다; their displayed roots are
익숙 and 특별, followed by 히. The full forms are also supported. This does not
invent 익하다/특하다, delete arbitrary syllables, or equate every contextual sense.
The whole lexical adverb remains the initial dictionary-compatible browser reading.

Adverb-compatible outer particles compose across the new base classes, including
더욱이도, 곰곰이만은, 가만히들, 낱낱이도, and 익히도. A nominal *base* does
not license subject/object/location case on the resulting derived adverb. Existing
whole-word noun and particle hypotheses remain separate. Dictionary filtering
uses actual entries: 틈틈 lacks a standalone entry, while 점점 has an adverb entry
but no nominal entry in the pinned snapshot. Neither gap is repaired by inventing
an entry or changing POS compatibility.

Sources: NIKL's [spelling families](https://www.korean.go.kr/nkview/nknews/199911/16_11.htm)
and [익히/특히 explanation](https://korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=8296&mn_id=62&pageIndex=5),
and KRDict [-이](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88927)
and [-히](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88504).
[Evaluation](adverb-root-evaluation.json) records all additions for 55 surfaces.
Opaque roots such as 천천히/분연히, other lexical classes, nominal -이,
subdivision of nonlexical repeated bases, and derivation across suffix/auxiliary
boundaries remain open. The corpus fixtures preserve whole-word lexical adverb
annotations; optional decompositions are source-backed judgments, not new corpus gold.

## Shortened 하다 nominalizations (COV-021b)

Article 40 recovery now includes 기 and the existing bundles 기로, 기가, 기는,
기도, 기만, 기를, 기보다. Vowel/sonorant bases retain aspiration (강구키,
조성키로); stop-final bases delete 하 (생각기). Existing nominal particle,
copula and auxiliary attachment paths compose with the restored stem. Bundled
and separated alternatives remain available; no new connector is licensed.

NIKL explicitly documents [생각하기에 → 생각기에](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6606&mn_id=62&pageIndex=1)
and [돌변하기도 → 돌변키도](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=320083).
The other variants follow the same [Article 40 spelling boundary](https://www.korean.go.kr/kornorms/m/m_regltn.do)
and existing nominalization composition. Tests compare all eight bundles with
full forms across vowel, sonorant and stop codas, including NFD, ordered
breakdowns, wrong-class rejections and joined auxiliaries.

This does not license contraction without a preceding base, guess non-Hangul
pronunciation, handle complex codas, or repair spellings such as 등록케. It can
emit unknown lexical hypotheses: the extra measured GSD match for 이시가키와
is an annotation anomaly, separately documented in the
[evaluation](hada-ki-evaluation.json), not a validated predicate. The original
word and nominal 이시가키 + 와 remain available. Independent linguistic review
and broader Article 40 coverage remain open.

## Polite informative and reported endings (COV-017m)

The source distinguishes informative endings from homonymous shortened reports.
The engine represents both with one grammatical component; it does not insert
an implicit 하다 or choose the contextual sense. Canonical 는답니다 covers
attached ㄴ답니다 after open/ㄹ stems and literal 는답니다 after other codas.
Only honorific 시 can precede this present-verb path. Plain 답니다 permits
honorific, past and modal markers, while retrospective 더 takes 랩니다.

Sources: KRDict [ㄴ답니다 ending](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=81377),
[는답니다 ending](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=81389),
[답니다 ending](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=81393),
and the corresponding [ㄴ답니다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86633),
[는답니다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86635),
[답니다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86636) report expressions.
Their attachment notes were inspected in the pinned official September 2026
export and retained in the attributed offline grammar fixture.

[Informative 랩니다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=76427)
follows the copula/아니다 or the listed honorific, retrospective and conjectural
markers. Existing vowel-final omitted-copula recovery also composes. The
[report expression](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86638)
additionally has a command sense, whose consonant counterpart is
[으랍니다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=81412).
The latter uses canonical 으랍니다 with the existing (으) boundary and honorific
only. Thus 먹으시랍니다 preserves both factual and command paths; 먹었더랍니다
has the factual path without a retrospective command reading.

Known adjective auxiliaries and -답다 derivation reject the new command path;
bare copulas use 랩니다 rather than 답니다/는답니다. Unknown lexical head classes
are not inferred, so unrestricted dictionary-free hypotheses still require
review. The endings themselves do not license following auxiliaries, nominal
case particles or an extra polite 요. Existing lexical alternatives, including
답니다 → 달다 + 습니다, remain. The [evaluation](reporting-evaluation.json)
records the tested scope and remaining limits.

## Enumerative copular -요 (COV-020d)

KRDict [-요, 86117](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86117)
is a connective for listing or contrasting facts, attached to bare 이다/아니다.
[NIKL's spelling explanation, Article 15](https://korean.go.kr/kornorms/m/m_regltn.do)
distinguishes this from terminal -오 and explicitly illustrates vowel-final
omission of 이. Thus 연장이요 exposes 연장 + 이다 + 요, 아비요 additionally
exposes 아비 + 이다 + 요, and 아니요 exposes 아니다 + 요. The ordinary
[polite particle 요](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86116)
remains a separate reading with a different dictionary source and grammar kind.

The rule does not attach to arbitrary predicates or recover honorific, past,
modal or retrospective markers before connective 요. Known copula roles are
required: a lexical predicate merely ending in 이다 is insufficient. Existing
nominal suffixes, particles and nominalizations can precede the copula. An
explicit 이요 fragment retains Copula role without joining a preceding token;
standalone omitted 요 is not introduced. Non-Hangul vowel assumptions use the
existing explicit pronunciation provenance. The ending does not itself license
auxiliaries or further case/polite particles.

The unfiltered API may add unknown nominal hypotheses before omitted copulas;
dictionary filtering still requires actual entries. [The evaluation](copula-yo-evaluation.json)
records each reviewed addition, including two compatibility snapshots. Gold
lemma groups do not establish contextual correctness: two newly matched KAIST
cases use sentence-final 요, distinct from the connective this rule supports.
No spelling repair or contextual parsing is inferred.

## Causal endings (COV-017n)

KRDict [-기에](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=84811)
and [-길래](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=73011)
are causal connectives. NIKL also explains the
[standard status and spoken use of -길래](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=5571).
The pinned source notes license verbs, adjectives and 이다; both list honorific
시 and past 었, while 기에 also lists modal 겠. The rule retains the existing
어야겠 bundle before 기에 and the existing repeated-past recovery. Retrospective
더 is not added to either attachment inventory; 길래 does not gain recovered
modal paths from 기에. These boundaries describe the reviewed standard forms,
not a judgment of every colloquial or quoted usage.

Both endings attach literally: 살길래 retains ㄹ, 듣길래 retains ㄷ, and
돕기에 retains ㅂ. Recovery before a preceding vowel-initial prefinal still
works, as in 들으셨길래. Existing auxiliaries, explicit copulas, and known
답다 derivation compose, including 먹고싶기에 and 학생답길래. Neither ending
becomes an auxiliary connector or a nominalizer.

The causal analysis 먹다 + 기에 is distinct from the existing nominalization
먹다 + 기 + 에. Both remain in the API and browser, with their original grammar
roles and source links. The causal path carries `ending.causal` provenance.
The two complete GSD development sentences protect 추천하길래 and 뽑길래;
[the comparison](causal-evaluation.json) records every change in the audited
surfaces and the unchanged historical baselines. Corpus lemma recall alone
cannot distinguish the two 기에 decompositions.

Omitted copulas before these endings, additional outer particles, and shortened
하다 allomorphs remain COV-020/018/021 review work. Existing nominalization
shortening such as 생각하다 + 기 + 에 is preserved. The tool does not infer
causal relations between clauses, choose a contextual sense, or certify the
lexical membership of arbitrary recovered stems.

## Expressive 하다 left class (COV-019d)

KRDict [하다, auxiliary verb sense 9](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=62888)
selects an adjective before expressive -어 하다. NIKL's
[궁금해하다 explanation](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=8010)
confirms that construction. This differs from causative 게 하다, necessity 어야
하다, nominalizing 기도 하다 and other 하다 senses. The offline auxiliary
fixture now retains sense 9 as well as its existing causative sense 1.

The ordered analysis already knows some predicate classes: auxiliary uses such
as trial 어 보다 are verbs; 싶다 and several other auxiliaries are adjectives;
explicit 답다 supplies an adjective; represented 이다 is a copula. Expressive
어 하다 now excludes a known verb or copula immediately on its left. Negative
않다/아니하다/못하다 inherit a known class, and internal particles or contracted
잖 do not change it. The check handles nominalized predicate + copula as well.
In 학생답게해해요, the immediately preceding 게 하다 is a verb even though the
chain starts with an adjective suffix.

먹고싶어한다 and 학생다워해요 retain their adjective paths. Following auxiliaries
still compose: 먹고싶어해본다 keeps 먹다 + 싶다 + 하다 + 보다. Unknown lexical
heads remain unclassified, so a hypothesis such as 먹다 + 어 + 하다 in 먹어하다
is still emitted for later lexical/sense review. Dictionary headword filtering
alone does not establish the required adjective sense. Other copula connectors,
including the existing 학생이고싶다 alternative, remain.

This source-specific restriction is not generalized to every auxiliary: the
54-entry source inventory includes homonyms, multiple left classes and notes
that say 'mainly', as well as lexical-subset and contextual conditions. Its
remaining restrictions stay under COV-019. The [comparison](auxiliary-left-hada-evaluation.json)
records every removal in the audited cases. Existing annotated corpus groups
remain unchanged; those corpora do not independently certify these newly
forbidden paths or all retained alternatives. Independent linguistic review
remains pending.

## Quoted alternatives (COV-017o)

Ten KRDict grammar-expression entries are represented as eight canonical
`Ending` bundles. They are marked 문법‧표현 / 품사 없음 by the source, not ordinary
어미 entries. The viewer admits their exact reviewed IDs/headwords/POS through
its existing explicit catalog mapping; unrelated unclassified entries remain
excluded. The source dispositions and every candidate change are recorded in
[the comparison](quoted-alternatives-evaluation.json).

| Reading | Canonical forms | Source entries |
| --- | --- | --- |
| Present verb alternatives | 는다거나, 는다든가 | [ㄴ다거나](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86055), [는다거나](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86053), [ㄴ다든가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82118), [는다든가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82119) |
| Adjective / past / modal statements | 다거나, 다든가 | [다거나](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86056), [다든가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82121) |
| Copular / factual alternatives | 라거나, 라든가 | [라거나](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86057), [라든가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82122) |
| Reported commands | 으라거나 | [으라거나](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86332), [라거나 sense 3](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86057) |
| Reported proposals | 자거나 | [자거나](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=83892) |

Present verbs use attached ㄴ after open/ㄹ stems and 는 after other consonants.
They permit honorific 시; recovered past/modal/retrospective markers instead
need another form. Literal 다거나/다든가 retain adjective and past/modal
paths, including honorific composition and the existing 어야겠 bundle, but not
retrospective 더. Known bare auxiliary verbs take the present form; known
adjective auxiliaries and explicit 답다 suffixes do not gain present verbal
attachment. Arbitrary lexical heads remain unclassified.

Copular 라거나/라든가 use explicit 이다/아니다 and existing vowel-final copula
omission. 라든가 additionally has source-listed factual 시/더/으리 paths.
Command 으라거나 has a vowel boundary (들으라거나, 도우라거나) and allows
honorific 시, while proposal 자거나 is a bare-stem path. These command/proposal
paths do not attach to a represented copula or known auxiliary adjective.
Present ㄴ has no vowel-only ㅂ/ㅎ recovery: 도운다거나 does not restore 돕다.
Neither bundle licenses a following auxiliary or nominal case particle.

The expressions do not insert an implicit 하다 lemma or expand into a quoted
clause. All lexical and previously generated alternatives remain. For example,
학생이라거나 has the copular 라거나 path, distinct from the command canonical
으라거나. Nominal particle 이라든가 and further quotation variants need their
own attachment and representation review. The remaining corpus 위해서라거나
case is a connective-clause + copula question under COV-020, not evidence that
an arbitrary ending may become a copular nominal.

The four recovered development tokens are 경시한다든가, 해방시킨다거나,
된다거나 and 세련되었다든가. The pinned full dictionary lacks the generated
headword 해방시키다, so that gold recovery is available unfiltered but excluded
by dictionary-only filtering. The rule does not manufacture a dictionary entry
or silently replace the corpus's causative lemma with 해방하다.

## Enumerative particles and choice ending (COV-018e/017p)

The following particle paths are separate from copular and ending analyses:

| Surface forms | Attachment in this batch | Dictionary source |
| --- | --- | --- |
| 이라든가 | Consonant-final nominal | [85861](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85861) |
| 라든가 | Vowel-final nominal/adverbial related form | 85861 and the NIKL related-form inventory below |
| 이라든지 | Consonant-final nominal | [86046](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86046) |
| 라든지 | Vowel-final nominal/adverbial | [86518](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86518) |
| 든가 | Vowel-final nominal/adverbial or final 다/는다/라 allomorphs | [70330](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70330) |
| 이든가 | Consonant-final nominal/adverbial related form | 70330 and NIKL section 3.1.12 below |

The [2017 NIKL curriculum, printed p. 463 (PDF p. 481)](https://korean.go.kr/common/download.do?c_file_name=f8313ff7-b33b-43b6-a01e-a8af43eb6a1d.pdf&file_path=reportData&o_file_name=2017%EB%85%84+%EA%B5%AD%EC%A0%9C+%ED%86%B5%EC%9A%A9+%ED%95%9C%EA%B5%AD%EC%96%B4+%ED%91%9C%EC%A4%80+%EA%B5%90%EC%9C%A1%EA%B3%BC%EC%A0%95+%EC%A0%81%EC%9A%A9+%EC%97%B0%EA%B5%AC(4%EB%8B%A8%EA%B3%84).pdf)
lists all four 라든가/라든지 particle variants together. The
[NIKL grammar-expression development study, stage 3, section 3.1.12, printed p. 76 (PDF p. 90)](https://www.korean.go.kr/common/download.do?c_file_name=5a2db2bc-a7ad-49f4-84a4-34b20ad33ffc_0.pdf&file_path=reportData&o_file_name=%ED%95%9C%EA%B5%AD%EC%96%B4%EA%B5%90%EC%9C%A1+%EB%AC%B8%EB%B2%95%ED%91%9C%ED%98%84+%EB%82%B4%EC%9A%A9%EA%B0%9C%EB%B0%9C+%EC%97%B0%EA%B5%AC_3%EB%8B%A8%EA%B3%84.pdf)
distinguishes 이든가 after consonants from 든가 after vowels. The pinned KRDict
snapshot lacks standalone particle entries for 라든가 and 이든가. Their catalog
mappings explicitly link the related particle entries, preserving the source
headwords and explaining the relationship instead of inventing dictionary IDs.
The vowel-form 라든가 adverbial scope follows the related 라든지 form; this
source-based extension remains subject to independent linguistic review.

Examples include 학생 + 이라든가, 학교 + 라든가, 밥 + 이라든지,
학교 + 에서 + 라든지, and 학교 + 에서 + 든가. Nominalizations and bounded
nominal suffixes compose: 먹다 + 음 + 이라든지 and 학생 + 들 + 이라든가.
The full 이라든가/이라든지 paths do not consume preceding particles; the short
forms allow adverbial case phrases but reject subject/object case splitting.
Further stacked particles require review. The implemented outer enumeration
slot permits polite 요; it does not enable arbitrary recursive enumeration.
든가 shares 든지's existing inner/outer choice slots and repeated-family guard,
with a separate exclusion of subject/object case phrases. 학생 + 이 + 든가
is not substituted for 학생 + 이든가 or 학생 + 이다 + 든가. The older
든지 family is unchanged and its other attachment paths remain for audit.
Unknown foreign bases retain the same explicit pronunciation conditions as other
particle allomorphs. Lexical and adverb-derived alternatives remain available.

After a final ending, 든가 exposes a second representation of some quoted forms:
먹는다든가 can be 먹다 + 는다든가 or 먹다 + 는다 + 든가.
학생이라든가 additionally retains 학생 + 이다 + 라든가 and
학생 + 이다 + 라 + 든가. These are possible representations, not contextual
sense choices. A bare adnominal or unlicensed connective does not become a
quoted nominal just because a particle can be removed from its spelling.

The separate literal ending [-든가, 82342](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82342)
accepts bare verbs/adjectives and source-listed 시/었 prefinals. 먹든가 and
먹으셨든가 recover 먹다; literal ㄷ preserves ㄹ in 살든가 and does not trigger
vowel-boundary irregular recovery. Recovered 겠/더/어야겠 are excluded.
Explicit copulas, existing auxiliary groups and known 답다 derivation compose;
학교이든가 thus retains a copula + ending reading even though 학교 + 이든가
is the wrong particle allomorph. Omitted copulas, further ending-particle links,
conversational spelling variants and sense selection remain separate review work.

Composition also exposed a pre-existing known-class gap before present 는다:
honorific 시 must not turn a represented copula or adjective into a verb. The
[verb-only attachment note, 85037](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85037)
is now enforced for known auxiliary adjectives, copulas and 답다 with or
without 시. Tests exclude 학생이신다, 먹고싶으신다, 학생다우신다 and their
composed 든가 forms while preserving 먹으신다든가 and 먹어보신다든가.
Other present-ending families and unknown lexical head classes remain open.

## Destination, recipient and emphatic adverbial particles (COV-018f)

Twelve source-listed particle forms have distinct paths and dictionary labels:

| Forms | Source entries | Attachment |
| --- | --- | --- |
| 에다 / 에다가 | [73013](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=73013), [73014](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=73014) | Nominals; location or addition |
| 에게다 / 에게다가 | [80293](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80293), [86573](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86573) | Recipient nominals |
| 한테다 / 한테다가 | [83879](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=83879), [83880](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=83880) | Recipient nominals |
| 로다가 / 으로다가 | [86550](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86550), [86577](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86577) | Vowel/ㄹ versus other consonants; direction, means and other source-listed senses |
| 보고 / 더러 | [70051](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70051), [70037](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=70037) | Recipient/addressee nominals |
| 다 / 다가 | [41693](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=41693), [41695](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=41695) | Reviewed location/direction/means/recipient adverbials and case phrases |

강에다 retains both 강 + 에다 and 강 + 에 + 다. 학교에다가, 친구에게다가,
친구한테다 and 손으로다가 similarly preserve bundle/component alternatives.
Nominal suffixes and nominalizations compose, including 학생 + 들 + 한테다가,
선생 + 님 + 에게다, and 먹다 + 음 + 으로다가. Existing outer particle slots
support 강에다는, 학교로다가도 and 학교에다가요. `(으)로다가` uses the
same explicit pronunciation conditions as `(으)로` for an unknown foreign base;
Hangul boundaries, including ㄹ, remain directly checked.

For separate emphatic 다/다가, this batch licenses preceding 에/에서/서/에게/
한테/께/로/으로. It also licenses the location readings of 여기/거기/저기/어디
and the direction readings of 이리/그리/저리. The seven corresponding dictionary
entries and their sense definitions are preserved in the evaluation report.
Nominal pronouns and directional adverbs retain different lemma roles. This
finite lexical scope is not an unrestricted adverb rule: 빨리다가 and arbitrary
nominal/ending + 다가 are not inferred. A bare nominalization needs an
intervening case marker, as in 먹기 + 에 + 다가. Subject/object marking and
recursive emphatic stacking do not satisfy this reviewed attachment path.
Other adverbial bases and particle combinations remain for review.

Recipient particles retain `particle.recipient` provenance. The source notes
require an appropriate referent: 보고 lists people/animals, 더러 and 한테다가
list people, and related forms include animate or personified uses. The engine
does not infer that semantic eligibility from spelling or dictionary presence.
It preserves a conditional recipient hypothesis without removing a lexical or
predicate alternative such as 돌보다 + 고 in 돌보고. Display glosses do not
choose among a headword's senses; deictic and manner homonyms remain distinct
source meanings even when they share a spelling or POS.

Emphatic particle 다/다가 is separate from predicate -다/-다가/-어다가.
Enumeration particle 다 (85738) is implemented separately in COV-018g below;
the emphatic reading links 41693. Tests that exclude an emphatic interpretation do
not declare every use of nominal + 다 invalid. Quoted-clause subject 가, including
the saved 살겠다가 annotation, also remains COV-018/020 work. No final-ending
+ case rule is inferred solely to match that segmentation.


## Enumerative 다/이다 particles (COV-018g)

KRDict [다 85738](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85738)
and [이다 86118](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86118)
are enumerative particles, both homonym 3. They enumerate nominal items on an
equal footing. 다 requires a vowel-final noun; 이다 requires a consonant-final
noun, including ㄹ. The source examples include 구두다 / 옷이다 and 노래다 /
춤이다. These have particle paths separate from the copula 이다 and ending -다.

The rule accepts nominal bases, existing bounded nominal suffixes and 기/음
nominalizations. It preserves lexical alternatives and existing outer 들/요
slots without inferring that a sentence actually contains a list or an appropriate
distributive/polite use. It does not recursively strip case/focus particles before
this enumerative particle, or treat arbitrary final/connective endings as nouns.
Unknown-script bases preserve the existing vowel/consonant pronunciation conditions.
Nominal lexical identity is a hypothesis; dictionary presence does not select the
contextual reading. Thus formal predicate surfaces can gain unknown nominal
hypotheses in the raw API, as individually recorded in the comparison.

`particle.enumerative_da` distinguishes this recovery from emphatic 다. Exact
lemma/morpheme paths merge provenance, so 저기 + 다 can retain both rules in
one analysis. The browser labels that merged path “Enumeration / emphasis” and
lists both source entries; purely enumerative and emphatic paths use their own
labels and preferred dictionary entries. Represented copulas prefer source 86232,
since KRDict tags both copular and enumerative 이다 as 조사. The label checks the immediate component
base as well as analysis-wide provenance. Copular alternatives remain independently
selectable. The existing deterministic compactness ordering can initially select
an enumerative path; this is not sentence-level disambiguation.

[Tests](../tests/enumerative_da.rs), sixteen candidate judgments, dictionary/CLI
parity and browser checks cover allomorphs, nominal composition, merged provenance,
source homonyms, Unicode and preserved alternatives. The complete GSD training
sentence train-s1156 preserves its original copular annotation for 옷이다; it is
not relabeled as enumeration. The [comparison](enumerative-da-evaluation.json)
records unchanged development recovery, additions and provenance changes, and
three stress fingerprint changes with prior hashes preserved. It makes no new
held-out recall or precision claim. Further particle combinations, contextual
sense selection and independent Korean-language review remain open.


## Further omitted copulas and connective 은 (COV-020e/018h)

The reviewed vowel-final nominal omission paths now include 니/니까, 고, 지만,
거든 and 네, plus the existing polite bundles 지만요, 거든요 and 네요.
노동자니까 recovers 노동자 + 이다 + 으니까; 최고네요 recovers 최고 + 이다 +
네요. Literal 니 and canonical 으니 paths remain separate components where the
existing ending inventory distinguishes them. Explicit copulas remain available.

[NIKL's copula guidance](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=309714)
permits omission of copular 이 after vowel-final nominals. Its
[vowel-boundary explanation](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=321172)
distinguishes this from contraction before 에요/었 and notes the limits of
adnominal/nominalizing omission. Each ending's copula attachment is retained from
KRDict in the [source review](omitted-connective-evaluation.json): 80139, 80144,
76426, 76420, 85823, 78583, 85022, 78638, 66501, 77333 and expression entries
66503/85934. Catalog mappings add the short -니까/-니 sources to their canonical
full forms. Source homonyms are not a prediction of sentence mood or meaning.

Recovery inserts the represented copula without applying predicate irregulars
to the nominal. It rejects consonant-final omission, including ㄹ, and preserves
conditional vowel pronunciation for non-Hangul bases. Nominalizations, finite
거/것 alternatives, and existing particle-marked copula bases compose. No new
base class or auxiliary connector is introduced; 고 uses the existing connector
inventory, retaining its unresolved left-class/sense restrictions.

The same review exposed a missing allomorph in post-ending particle attachment.
KRDict [은 86111](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86111)
(sense 3) licenses consonant-final connectives. The existing connective inventory
now accepts 은 as well as 는, with the original allomorph boundary checks.
먹지만은 has 먹다 + 지만 + 은; 의사지만은 has 의사 + 이다 + 지만 + 은.
Existing 지 + 만 + 은 alternatives remain. This adds no arbitrary final or
adnominal attachment and does not widen internal auxiliary particle slots.

The comparison records six KAIST and three GSD development grouped recoveries.
The Terni place-name case is an incidental match to an apparent annotation error;
its original gold and whole-word reading remain. 어디서고 composes through an
existing particle-marked base; competing readings and broader base constraints
remain unjudged. The pinned dictionary lacks 엘리트주의, so its recovered raw
path does not survive dictionary-only filtering.

Four stress snapshots gain unknown nominal/copula hypotheses, recorded separately
with every prior candidate/hash retained. In particular, represented copula +
progressive 고 있다/계시다 needs further left-class review under COV-019; this
batch does not certify those generated paths. COV-019e below closes the internal
는 gap before 싶다 (학생이고는싶다 / 의사고는싶다), alongside existing 도.
Other omitted ending and prefinal families remain COV-020 work. NIKL's valid
honorific omission example 선수셨다 is not entered as a forbidden regression
merely because that recovery was not included in COV-020e. COV-020f below
implements that honorific omission. Independent Korean review remains pending.


## Honorific copula omission (COV-020f)

[NIKL explicitly permits 선수셨다](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=309714)
as a shortened 선수이셨다 after a vowel-final nominal. The engine now recovers
that omitted copula at the honorific 시 boundary, before the existing prefinal
stack. Thus 선수셨다 has 선수 + 이다 + 시 + 었 + 다, and 의사시니까 has
의사 + 이다 + 시 + 으니까. The uncontracted 시었 spelling, double past,
modal/retrospective order, and the existing ending licenses remain available.

Restored 이 is tagged for copula-only expansion. That flag survives final ending
recovery, nominalization and later auxiliary composition, preventing a fabricated
의사이다 predicate in 의사셨다 or 의사셨기다. The boundary checks the original
nominal and does not apply verb irregulars: 학생셨다 cannot recover 학생 + 이다,
and 사셨다 does not license 살 + 이다 through ㄹ deletion. Existing 살다/돕다
verb paths remain. Non-Hangul bases retain the explicit vowel-pronunciation
condition, independently of later 시어 contractions. Explicit ABC이셨다 needs
no such assumption.

KRDict [-시- 80330](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80330)
licenses copula attachment; [-으시- 80329](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80329)
retains the full lexical-predicate allomorph. The catalog now records both.
The separate bundled [-세요 86558](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86558)
also licenses a copula; 의사세요 gains 의사 + 이다 + 으세요, with the short
source mapped alongside [-으세요 86609](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86609).
This does not introduce generic 시어-to-세 recovery. The existing 시 + 어요
path remains available for 셔요. Bare-bundle restrictions and known copula ending
restrictions still reject the reviewed past/세요 and honorific/verbal-present
combinations. Honorific referent suitability and sentence mood remain contextual.

Nominalizations, an outer copula, negative auxiliaries and other already licensed
connectors compose. This is structural coverage, not evidence that every nominal
referent can appropriately be honored. Broader auxiliary left-class constraints
remain COV-019 work. Other copula prefinal omissions remain COV-020 work.

[The comparison](honorific-copula-evaluation.json) records 72 additions over
66 audited surfaces, no removed candidates/provenance, and unchanged development
recovery. One stress fingerprint gains two unknown nominal 들으 + copula
hypotheses while retaining existing verb readings; prior hashes are preserved.
Three complete annotated sentences protect 마셨다, 주셨습니다 and 주셨어요
as lexical verb cases. These are preservation regressions, not new corpus gold
recoveries or a precision estimate. Independent Korean-language review remains
pending.


## Contrastive desire links (COV-019e)

A single contrastive 는 after 고 can precede auxiliary 싶다. The existing
곤 contraction expands to 고 + 는, preserving the particle role and normal
auxiliary grouping: 먹곤싶다 → 먹다 + 고 + 는 + 싶다 + 다. The same link
composes with represented copulas (학생이고는싶다), vowel-final omitted
copulas (의사곤싶다), existing trial auxiliaries, right-side prefinals,
negatives and expressive 하다. Normal nominal boundaries and the known
adjective class of 싶다 still constrain these paths.

The pinned KRDict [좀](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=75798)
entry, sense 4, directly exemplifies 놀고는 싶지만. The
[는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85851) and
[ㄴ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85847)
entries license full/contracted particles after 고;
[싶다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=62657)
records the desire construction. The auxiliary-connecting sense of
[-고](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=78583)
includes represented copulas. The attributed [evaluation](desire-topic-evaluation.json)
preserves source notes and the direct example.

These joined forms are tolerant token analyses; standard source spacing remains
unchanged. There is no cross-token grouping or contextual sense decision.
Nominalization composition is a structural test, not a judgment that every
referent is natural in a desire construction. Other particle slots remain for
review. Existing 어 있다 candidates after known adjective auxiliaries, such as
먹고는싶어있는다, remain explicitly unjudged pending a source/left-class audit.
