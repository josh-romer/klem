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

Known gaps include contracted 하 aspiration (피케), broad adverbial derivation
(같이, 없이, 달리), rarer endings/particle combinations, and foreign spelling
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
inserted inside a joined auxiliary chain such as 먹어들봐요. Spaced 먹어들 봐요
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
families, and Article 39 잖/찮 remain separate audit work under COV-013.

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
General -히, 하다-root derivation, ㅂ recovery (가까이), other stem classes,
and nominal -이 remain COV-013 audit work. No general dictionary of corpus
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
