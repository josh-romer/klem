# Coverage and completion tracker

Last reviewed: 2026-09-26.

This tracks the modern written Korean rule coverage needed by the CLI, library,
and sentence explorer. Completion means that the explicitly listed scope has
implementation and regression evidence. It does not establish that every Korean
analysis is generated or that every generated candidate is linguistically valid.
Contextual sense selection and sentence parsing remain separate work.

The examples below were initially probed with the CLI and the local September
2026 Korean Basic Dictionary snapshot. Closed items describe subsequent fixes.
Open examples are audit observations, not yet
executable regression cases unless a test is linked. No overall completion
percentage is assigned: the inventory itself still needs an audit.

## Status and priorities

- **Implemented:** the stated behavior has code and regression coverage; broader
  coverage or independent linguistic review may still be pending.
- **Missing:** the intended analysis is not generated in the audited examples.
- **Partial:** some readings work, but decomposition, roles, or combinations are missing.
- **Audit needed:** coverage has not been inventoried sufficiently to declare it complete.
- **Deferred:** outside the current release scope; not silently counted as complete.

P1 and the bounded COV-010/011/012/014/015/016/017a–ad/018a–k/018m–n/019a–g/019i/020a–i/021a–b/022a–b batches are implemented.
COV-013 has an initial inventory pass; its remaining work is split into
COV-017..022 below. P3 needs further scope or representation decisions.
Priorities reflect the concrete failures found,
not measured frequency estimates across novels.

## Existing coverage to preserve

These checked items record implemented scopes, not entire grammar families.
The examples and source references are expanded in [Grammar coverage](rules.md).

- [x] **COV-001 — Predicate endings and spelling recovery.** Regular conjugation,
  consonant attachment, common 아/어 contractions, 하/푸/ㅡ recovery, and the
  implemented irregular boundaries. Preserve alternative lexical hypotheses.
  Evidence: [rule fixtures](../tests/rules.rs),
  [positive/negative constraints](../tests/candidate_correctness.rs), and the
  [candidate judgment ledger](../tests/fixtures/validity.json).
- [x] **COV-002 — Prefinals, copulas, and auxiliary grouping.** Implemented
  honorific/tense/modal ordering, copular components, nominalizations followed
  by particles, and licensed attached auxiliary chains. This does not certify
  nonstandard spacing or cover every auxiliary. Evidence:
  [grouping tests](../tests/candidate_correctness.rs),
  [ordered breakdown tests](../src/breakdown.rs), and
  [stress/output compatibility tests](../tests/stress.rs).
- [x] **COV-003 — Ordinary particle chains and selected nominal contractions.**
  Implemented chains such as 학교에서는 and 학교에서만은; the special forms
  내가, 제가, 누가, 내, 게, 건, 걸. Broader contraction work is COV-006/007.
  Evidence: [curated rules](../tests/rules.rs).
- [x] **COV-004 — Nominal plural suffix -들.** Bare plurals, particles after
  plurals, and copulas after plurals; retain unsplit lexical alternatives such
  as 아들. Reject the tested wrong particle allomorphs and recursive plural
  stripping. Evidence: `nominal_plural_precedes_particles_and_copulas_without_replacing_lexical_readings`
  in [candidate correctness](../tests/candidate_correctness.rs),
  `plural_nominal_survives_cli_dictionary_filtering` in
  [dictionary tests](../tests/dictionary.rs), `nominal-plural-*` case IDs in the
  [ledger](../tests/fixtures/validity.json), and the 지식인들을
  [browser regression](../web/tests/browser.mjs). The separate 들 particle is COV-009.
- [x] **COV-005 — Dictionary-backed display and candidate preservation.** Grouped
  dictionary filtering, ordered components, normalized-form notices, per-word
  alternatives, bounded combination display, and filtered JSON export.
  Evidence: [dictionary tests](../tests/dictionary.rs),
  [breakdown tests](../src/breakdown.rs), and
  [browser/API tests](../web/tests/browser.mjs).
  A headword match is not contextual or POS validation; see COV-009/014.

## Open coverage checklist

### P1: implemented particle/pronoun batch

- [x] **COV-006 — Contracted particles.** **Implemented for the scoped attachment families.**
  학교에선 and 선생님께선 now recover the particle chains
  학교 + 에서 + 는 and 선생님 + 께서 + 는, with an explicitly normalized display.
  Contracted ㄴ/ㄹ attachment and existing particle chains use canonical 는/를,
  separate from verb endings. Tests also cover 병원엘, 보곤, and 걷질.
  Source starting points: KRDict [ㄴ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85847)
  and [ㄹ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85760).
  Evidence: `contractions_preserve_case_chains_and_pronoun_alternatives` and
  `particle_slots_and_ending_boundaries_do_not_overstrip` in
  [particle tests](../tests/particles.rs), `particle-contracted-topic` in the
  ledger, and browser/CLI regressions.
- [x] **COV-007 — Pronoun contractions beyond the special cases.** **Implemented
  for 이/그/저 subject/topic/object paradigms and 뭘.** Both short and expanded
  pronouns are retained with the appropriate particles; outer particles compose,
  e.g. 이건요. Productive ㄴ/ㄹ recovery also covers 난/날, 넌/널, 우린/우릴.
  Whole-word readings remain available; contractions do not invent character spans.
  Source starting points: KRDict [이거](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=71128),
  [뭐](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=84991), and
  the ㄴ/ㄹ entries above. Evidence: the full three-pronoun paradigm and NFD
  tests in [particles.rs](../tests/particles.rs), `pronoun-*` ledger IDs, and
  the browser's 이건요 alternative selector. Other contractions remain COV-013 work.
- [x] **COV-008 — Polite particle 요.** **Implemented for nominal/adverbial bases,
  particle chains, and explicitly licensed ending families.** 저 + 도 + 요,
  친구 + 는 + 요, and 먹다 + 으면 + 요 now survive dictionary filtering.
  Existing 어요-family analyses remain alongside separated 어 + 요 readings.
  One outer 요 slot is supported; arbitrary stripping after adnominal or formal
  endings is not enabled. Source: [NIKL explanation and attachment examples](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=312410).
  Evidence: particle attachment/boundary tests, `particle-polite-*` ledger IDs,
  and dictionary/browser regressions.
- [x] **COV-009 — Distinguish the 들 particle from nominal -들.** **Implemented
  for nominal/adverbial bases and the listed connective/final endings.** 빨리들
  now has an adverbial + particle analysis; 먹어들 has 먹다 + 어 + 들.
  지식인들을 remains a nominal + suffix + particle analysis. The browser shows
  the correct grammar entry/label for the selected role.
  Source: KRDict [들 particle](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86264)
  versus [plural suffix -들](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74906).
  `LemmaKind::Adverbial` has dictionary compatibility with 부사. Headword-only
  filtering still retains incompatible hypotheses; POS-aware consumers can
  distinguish them. Evidence: `adverbs_and_plural_nouns_have_distinct_role_hypotheses`
  in [particles.rs](../tests/particles.rs), the dictionary role test, and the
  browser regression that opens the 들 particle entry.

Batch limits and sources: [P1 rule scope](rules.md#particle-and-pronoun-expansion-p1).
Further ending licenses and other pronoun contractions remain in COV-013.
COV-019a covers one internal particle in joined auxiliary chains. Independent linguistic
review remains open under the completion review below.

### P2: additional morphology

- [x] **COV-010 — Productive suffix decomposition.** **Implemented for bounded
  -님, -적, and -답다 hypotheses.** 선생님께 additionally exposes 선생 + 님 + 께;
  과학적이다 exposes 과학 + 적 + 이다 + 다. 학생답다 and 학생다워요 now retain
  dictionary-filtered paths through 학생. Whole-word alternatives remain and
  the browser initially prefers a compact dictionary-compatible reading.
  `MorphemeKind::Suffix` uses canonical 답다 before its inflection; the display
  shows 답 and links the -답다 entry. The known suffix uses ㅂ-irregular vowel
  attachment. Nominal paths allow one 님, 적, or 들, or 님 + 들; these can
  precede particles/copulas. 답다 may follow an unsplit base or 님/들/님 + 들,
  before licensed inflection and existing auxiliaries. No recursive derivation,
  님 stem alternation, or semantic noun-class validation is claimed. Further
  combinations and adjective ending licenses remain COV-013 audit work.
  Sources: KRDict [-답다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=92145),
  [-님](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88852),
  [-적](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88966).
  Evidence: [suffix path and boundary tests](../tests/derivation.rs),
  `derivational_suffixes_survive_dictionary_filtering_and_keep_lexical_readings`
  in [dictionary tests](../tests/dictionary.rs), eight `suffix-*` ledger cases,
  and browser selection/entry regressions. Scope: [suffix rules](rules.md#bounded-suffix-decomposition-cov-010).
- [x] **COV-011 — Further 하다 contractions.** **Implemented for the listed
  Article 40 ending families and simple coda classes.** 생각지/생각건대 recover
  생각하다; 피케 and 비유컨대 recover 피하다 and 비유하다. Separate deletion and
  aspiration rules preserve canonical endings and their auxiliary connections.
  The scoped inventory is 게/게요, 지/지요/지만/지만요, 다/다고/다는/다니/다면,
  도록, 고자, 건대. Paired negative cases reject the swapped coda classes and
  prevent a restored 하 from being reinterpreted as a nominal before a zero copula.
  Evidence: [Article 40 examples and boundary tests](../tests/hada.rs),
  `shortened_hada_matches_full_lemmas_in_cli_and_pos_filtering` in
  [dictionary tests](../tests/dictionary.rs), nine `hada-*` judgment cases,
  and browser normalization/grammar-entry checks. Source:
  [NIKL's Article 40 explanation](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=325451).
  COV-021a adds 잖/찮 contractions. Complex codas and other ending families remain COV-013
  audit work. See [the implemented scope](rules.md#shortened-hada-cov-011).
- [x] **COV-012 — Adverbial derivation.** **Implemented for bounded -이 families.**
  Adjective bases ending in 같/없, the stems 굳/길/깊/높/많, and the historical
  달리/빨리 mappings gain optional suffix analyses. 같이 → 같다 + 이,
  없이 → 없다 + 이, and 달리 → 다르다 + 이 now recover the recorded corpus gold.
  Whole-word readings remain preferred in the browser; the deeper path has a
  suffix, not a fabricated ending. Particles 도/만/는/요/들 compose through the
  existing chain order (including 만은). Noun/case and arbitrary -이/히 stripping
  are not enabled. Evidence: [adverb tests](../tests/adverbs.rs),
  [three complete annotated KAIST sentences](../tests/fixtures/kaist-adverbs.conllu),
  `annotated_adverb_derivations_recover_previously_missed_gold_cases` in
  [corpus tests](../tests/corpus.rs), eight `adverb-*` ledger cases, and
  dictionary/browser tests for preservation and the correct -이 homonym.
  Sources and exclusions: [adverb derivation scope](rules.md#adverbial-derivation-cov-012).
  Remaining -이/-히 families, nominal/adverbial homonyms, and attachment classes
  are COV-013 inventory work. This does not certify all adverbial derivation.
- [ ] **COV-013 — Ending, particle-chain, and auxiliary inventory audit.**
  **Partial: initial inventory, development-miss clustering, and persistent
  entry review queue implemented.** The [715-entry queue](inventory-review-queue.json)
  preserves homonyms, source attachment notes, and links to existing evidence.
  The [manual review ledger](inventory-reviews.json) records 196 scoped
  dispositions from COV-016/017m–n/017p–z/017aa–ad/018e–k/018m–n/019d–g/019i/020d–h; 518 entries have no disposition in this
  ledger yet, including entries with implemented behavior elsewhere. One additional
  entry (마다, COV-018l) records an observed gap with unresolved acceptability. Neither
  catalog links nor test citations automatically certify coverage. Source and
  evidence drift checks run offline and in `nix flake check`. See the
  [review workflow](inventory-audit.md#persistent-entry-review-queue).
  See [the reproducible audit](inventory-audit.md) and its
  [compact report](inventory-audit.json): 715 dictionary grammar entries are
  inventoried for triage, without treating literal table mentions as coverage.
  COV-016 fixes the reviewed -듯/-듯이 family; 19 additional development cases
  match, leaving 378 KAIST and 242 GSD development misses. COV-017..022 split
  the remaining morphology work. Every-entry linguistic review is still open.
  Compare the implemented tables with dictionary grammar
  entries and cluster saved corpus misses by rule family. Previously recorded
  examples include 보듯이, 있습니다만, 어디까지나, and 번져나갔다; re-probe them
  before promoting a miss to a required test. Distinguish true missing rules
  from annotation errors and differing lexical segmentation. Split this item
  into individually scoped entries as families are reviewed. Corpus gold does
  not enumerate every valid alternative.
  Include the remaining P1 extensions: pronoun contractions outside the finite
  이/그/저 and 뭘 paradigms, additional particle/ending combinations, and particles
  inside joined auxiliary chains. Spaced input is already analyzed token by token.
  Audit further suffix combinations/adjective ending licenses. COV-020a adds
  direct nominalization + copula without an intervening particle, including
  학생다움이다, alongside the existing 학생다움만이다 particle path.
  For 하다 shortening, audit complex coda pronunciation, remaining ending/particle
  combinations, and Article 39 잖/찮 forms separately; COV-011 covers Article 40.
  Audit remaining adverbial -이/-히 bases, spelling recoveries (e.g. 가까이),
  and nominal -이 separately. COV-012 does not infer unrestricted -이 removal or
  a productive 르 → ㄹ리 rule from the historical 달리/빨리 pairs.

### Work split from COV-013

- [x] **COV-016 — Comparative -듯/-듯이 endings.** **Implemented for literal
  predicate attachment.** 보듯이 → 보다 + 듯이; 살듯 preserves ㄹ. Existing
  honorific/past/modal markers, copulas, and auxiliary chains compose before
  these endings. They do not themselves license an auxiliary connector.
  No bound-noun 듯 segmentation, additional particle attachment, or shortened
  하다 variants are included. Sources: KRDict
  [-듯](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80280) and
  [-듯이](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80282).
  Evidence: [path/boundary tests](../tests/comparative_endings.rs), six
  `comparative-*` ledger cases, two full [KAIST sentences](../tests/fixtures/kaist-comparative.conllu),
  dictionary/CLI parity and browser grammar-entry checks. All 30 existing
  fingerprints remain unchanged; no frozen corpus baseline was regenerated.
- [ ] **COV-017 — Further ending families.** **Partial: COV-017a–ad implemented.**
  Remaining: other quoted contractions and unreviewed inventory
  entries. Re-probe each path and check verb/adjective attachment, prefinals,
  and whole-word alternatives. Corpus signatures identify candidates for review,
  not a blanket license to add every dictionary spelling as a literal suffix.
- [x] **COV-017a — Present conditional -ㄴ다면/-는다면.** Implemented with
  canonical ending 는다면. 한다면/산다면 use attached ㄴ, while 먹는다면 uses
  the non-ㄹ consonant boundary. Honorific 시 is permitted; this present path
  rejects recovered past/modal/retrospective markers. Existing plain 다면 paths
  such as 먹었다면 remain. Vowel-only ㅂ/ㅎ/ㄷ recovery is not applied at the
  present ending. Existing auxiliaries can precede it, but it is not itself an
  auxiliary connector. Evidence: [boundary/group tests](../tests/conditional_endings.rs),
  eight `conditional-*` ledger cases, three offline annotated cases,
  dictionary/CLI parity and browser normalization/homonym checks.
  Sources: KRDict [-ㄴ다면](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=66956)
  and [-는다면](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=68738).
  The rule-only engine does not distinguish lexical verb/adjective classes;
  the quoted-expression homonyms and additional outer particles are not added.
  See [rule scope](rules.md#present-conditionals-cov-017a) and
  [the recorded development comparison](conditional-evaluation.json).
- [x] **COV-017b — Shortened adnominal expressions (으)려는 and 자는.**
  **Implemented as bundled grammatical components.** 먹으려는 recovers 먹다,
  살려는 preserves ㄹ, 들으려는/도우려는 recover their irregular stems, and
  바꿔보자는 retains the 바꾸다 + 보다 auxiliary group. Canonical endings are
  으려는 and 자는; no implicit 하다 lemma is inserted. Intention expressions
  permit honorific 시; the proposal expression is bounded to bare stems in
  this batch. Other prefinals, outer particles, lexical verb/adjective class
  validation, and a fully expanded quotation analysis remain for review.
  Sources: KRDict [-으려는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86717),
  [-려는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86688),
  [-자는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=83896).
  These are tagged 문법‧표현 / 품사 없음. Browser lookup admits the two canonical
  expression IDs through an explicit exception; unrelated unclassified entries
  remain excluded. Evidence: [path and boundary tests](../tests/adnominal_expressions.rs),
  eight `adnominal-*` ledger cases, three complete KAIST sentence fixtures,
  dictionary/CLI parity, and browser/source-lookup regressions.
  See [rule scope](rules.md#shortened-adnominal-expressions-cov-017b) and
  [the development comparison](adnominal-evaluation.json).
- [x] **COV-017c — Literal -다가.** Implemented separately from existing
  vowel-boundary -어다가. 먹다가, 갔다가, 불렀다가, and 먹으셨다가 recover
  their stems and ordered prefinals. Copulas, existing auxiliaries, and known
  -답다 derivation compose with it. Honorific/past markers are supported;
  recovered 겠/더 paths are excluded. 가다가 retains both 다가/어다가 readings.
  Sources: KRDict [-다가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85740)
  and [-어다가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86099).
  Evidence: [path/boundary tests](../tests/daga.rs), eight `daga-*` ledger cases,
  three positive offline corpus cases plus the preserved quoted-subject
  annotation for 살겠다가, dictionary/CLI parity and browser alternative/link
  checks. See [scope](rules.md#literal-daga-cov-017c) and
  [the development comparison](daga-evaluation.json). Further outer particles,
  joined auxiliary uses of 다가, and short-form 다 sense selection remain open.
- [x] **COV-017d — Bundled quoted questions -냐는/-느냐는.** Literal
  attachment supports 아니냐는, 했느냐는, ㄹ deletion in 사느냐는, and
  honorific/past/modal prefinals in order. Existing auxiliary chains compose;
  bare copulas use 냐는, while copula + past + 느냐는 remains available.
  Both expressions retain one `Ending` component without an inferred 하다.
  Sources: KRDict [-냐는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86030)
  and [-느냐는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86031).
  Evidence: [path/boundary tests](../tests/quoted_questions.rs), eight
  `quoted-question-*` ledger cases, two complete KAIST sentence fixtures,
  dictionary/CLI parity, and browser component/source-link checks. See
  [scope](rules.md#quoted-questions-cov-017d) and
  [the development comparison](quoted-question-evaluation.json).
  Adjective allomorphy and retrospective quotation are covered by COV-017e.
  Lexical verb/adjective validation and additional outer particles remain open.
- [x] **COV-017e — Adjective quoted-question boundaries and retrospective 더.**
  좋으냐는, 기냐는, 추우냐는, and 파라냐는 recover canonical 으냐는
  through the existing 으 boundary, including ㄹ/ㅂ/ㅎ recovery. Bare adjective
  suffix -답다 uses its known ㅂ-irregular boundary. Literal 냐는 remains
  separate; honorific/past/modal markers still use 냐는/느냐는, and retrospective
  더 now composes with 냐는, including copulas and auxiliaries. No implicit
  하다 is inserted. Evidence: expanded [quoted-question tests](../tests/quoted_questions.rs),
  eight `quoted-adjective-*`/`quoted-retrospective` ledger cases, attributed
  dictionary fixtures, CLI parity, and browser canonical-form/link tests.
  [Scope and sources](rules.md#adjective-and-retrospective-questions-cov-017e)
  explain the representation and lexical-class limit. No new development
  gold matches are attributed to this family; its examples are source-backed
  constructions, not independently annotated corpus cases.
- [x] **COV-017f — Confirmation expressions -잖아/-잖아요.** Bundled
  confirmation/correction readings remain separate from the negative contraction
  in COV-021a. 먹잖아요 preserves 먹다 + 잖아요 as well as 먹다 + 지 + 않다 +
  어요; the app labels and links the confirmation expression. Honorific, past,
  and modal prefinals compose; retrospective 더 is excluded for the bundled
  expression. Copulas and existing auxiliary groups retain their components.
  Sources: KRDict [86756](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86756)
  and [86757](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86757).
  Evidence: [negative/confirmation tests](../tests/negative_contractions.rs),
  three confirmation-related ledger cases, dictionary/CLI parity and browser
  source-link checks. No new development gold match is attributed to these
  expressions; source-backed synthetic cases cover them.
- [x] **COV-017g — Correct propositive -(으)ㅂ시다.** The label audit exposed
  a legacy 습시다 spelling. Canonical 읍시다 now covers 먹읍시다 and attached
  갑시다/삽시다, with the vowel-boundary recoveries 들읍시다, 부읍시다,
  and 도웁시다. Existing auxiliary groups and lexical alternatives remain.
  The change does not classify unknown lexical stems or establish sentence-mood
  compatibility; further lexical/prefinal restrictions remain COV-017/019 work.
  Evidence: [boundary/group tests](../tests/propositive_endings.rs), eleven
  `propositive-*` ledger cases, complete KAIST MH2_0159-s160, dictionary/CLI
  parity, and browser normalization/source-link checks. Sources and candidate
  changes are recorded in [the audit](grammar-label-evaluation.json).
- [x] **COV-017h — Intention/expectation and concessive endings.**
  Canonical 으리라고, 을지라도, and 자면 recover 되리라고, 할지라도,
  and 들자면. Vowel/ㄹ and consonant allomorphs preserve the existing irregular
  alternatives; literal 자면 does not restore vowel-triggered irregulars.
  Prefinal licenses are family-specific. Known auxiliary adjectives, -답다
  derivatives, and copulas reject verb-only 자면, including after honorific 시;
  restrictions apply to the relevant predicate, not an entire auxiliary chain.
  Copulas and adjective derivatives retain 으리라고/을지라도. The new endings
  do not themselves license an auxiliary connector. Bundled expressions have
  sourced browser labels without an inferred reporting verb. Unknown lexical
  verb/adjective classes and contextual intention/quotation senses remain open.
  Evidence: [boundary and composition tests](../tests/intention_endings.rs),
  fifteen `intention-*` ledger cases, eleven full annotated source sentences,
  dictionary/CLI parity, and six browser/source-link regressions. See
  [scope and sources](rules.md#intention-expectation-and-concession-cov-017h)
  and [development comparison](intention-ending-evaluation.json).
- [x] **COV-017i — Concessive -(으)나마 ending.** Canonical 으나마 is
  separate from the nominal/adverbial (이)나마 particle. 작으나마, 약소하나마,
  and 먹지못하나마 retain their predicate/auxiliary groups; 조금이나마 retains
  both particle and copular-ending readings. Existing vowel-boundary irregulars,
  ㄹ deletion, honorific/past/modal markers, and known -답다 spelling apply;
  retrospective 더 and new auxiliary links are not licensed. These are
  source-backed synthetic cases, not additional corpus gains. Evidence and
  sources are shared with COV-018c below. Broader omitted-copula and outer-particle
  licenses remain COV-018/020.
- [x] **COV-017j — Short quoted facts and commands -란/-(으)란.**
  학생이란 preserves 학생 + 이다 + 란 alongside the separate particle reading.
  Explicit and vowel-final omitted copulas, 아니다, honorific copulas and
  retrospective forms such as 먹었더란 are supported. 먹으란/먹어보란 use
  canonical 으란 with their own allomorph and prefinal licenses. Conjectural
  (으)리 is a scoped prefinal before 란, including 작으리란 and 먹었으리란;
  existing -(으)리라/-(으)리라고 remain bundled. Explicit standalone 이란 gains
  a Copula-kind reading without joining tokens or inserting a nominal component.
  The source's 행복하란 example prevents a blanket adjective-command ban;
  further lexical/mood restrictions and -답다 command licenses remain open.
  Evidence: [path and boundary tests](../tests/quoted_definitions.rs), shared
  twenty-one `definition-*` ledger cases, dictionary/CLI role checks and eight
  browser/source-link cases. [Scope and sources](rules.md#definition-particles-and-short-quotations-cov-018d017j),
  [evaluation](quoted-definition-evaluation.json).
- [x] **COV-017k — Intention/necessity -아/어/여야겠-.** The canonical
  `어야겠` component occupies a prefinal position before a final ending.
  Existing vowel recovery covers 해야겠다, 와야겠다, 들어야겠다 and 도와야겠다;
  copulas, honorific/past markers, -답다, and existing auxiliary groups compose.
  No implicit 하다 lemma is inserted. The new progressive-order check preserves
  먹고 있어야겠다 while rejecting 먹어야겠고 있다. Broader ending/prefinal and
  auxiliary restrictions remain COV-017/019 work. Evidence: [path/boundary tests](../tests/obligation.rs),
  twelve `obligation-*` ledger cases, five complete annotated sentences,
  dictionary/CLI parity, and nine browser reading/source-link checks.
  The [evaluation](obligation-evaluation.json) records three new grouped matches
  and two GSD implicit-하다 representation differences; no prior recoveries or
  current output fingerprints are lost. See [scope and sources](rules.md#intention-and-necessity-bundle-cov-017k).
- [x] **COV-017l — Factual 라-family and command prefinal licenses.**
  먹었더라 retains bundled 더라 and factual 더 + 라; conjectural 으리 also
  composes with the reviewed 라/라서/라고/라면 family. Incompatible recovered
  past/modal/retrospective paths are removed from the reviewed command, quoted
  command, and formal request/proposal endings, preserving honorific paths and
  lexical alternatives. The separate 더라는 bundle preserves 못하더라는's corpus
  gold without an invalid 더 + 으라는 analysis. Copular factual readings and
  declarative/question 세요 remain; exclamatory 어라 and homonymous 자 require
  further audit beyond the restrictions documented here.
  Evidence: [path/boundary tests](../tests/prefinal_licenses.rs), seventeen
  `prefinal-license-*` ledger cases, one complete KAIST test sentence,
  dictionary/CLI parity, and browser/source-link checks. The
  [evaluation](prefinal-license-evaluation.json) records every candidate change
  for 63 surfaces and the reviewed 먹었었겠더라 fingerprint: twenty invalid
  command paths become ten factual paths, preserving bundled 더라. No frozen
  corpus baseline is changed. See [scope and sources](rules.md#factual-라-family-and-command-prefinal-licenses-cov-017l).
- [x] **COV-017m — Polite informative and reported endings.** 답니다,
  present-verb ㄴ/는답니다, copular/factual 랩니다 and reported-command
  (으)랍니다 now retain distinct canonical paths. Literal/attached/vowel
  boundaries, honorific/past/modal/retrospective licenses, known adjective
  auxiliary/suffix restrictions and copula roles are checked. No implicit 하다
  is inserted; informative/reported senses remain dictionary alternatives.
  Evidence: [boundary and composition tests](../tests/reporting_endings.rs),
  fourteen `reporting-*` ledger cases, four complete annotated sentences,
  dictionary/CLI parity, and browser alternatives with nine primary-source
  entries. The [evaluation](reporting-evaluation.json) records four development
  recoveries with no lost groups/component sets or changed stress fingerprints.
  Arbitrary lexical head verb/adjective classes remain unknown; other quoted
  contractions remain open. See [scope](rules.md#polite-informative-and-reported-endings-cov-017m).
- [x] **COV-017n — Causal -기에/-길래.** Literal predicate, explicit copula,
  known adjective suffix and auxiliary paths retain the ending as one component.
  The existing 기 + 에 nominalization reading remains separately selectable.
  Source-listed honorific/past attachment is supported for both; 기에 additionally
  permits modal 겠, including the existing 어야겠 bundle. Retrospective 더 and
  vowel-only irregular recovery at ㄱ are excluded. Evidence:
  [boundary/composition tests](../tests/causal_endings.rs), twelve `causal-*`
  ledger cases, two complete GSD sentences, dictionary/CLI parity, and browser
  source links with nominalization alternatives. See [scope](rules.md#causal-endings-cov-017n)
  and [evaluation](causal-evaluation.json). Omitted-copula and shortened 하다
  allomorphs, further outer particles, and contextual interpretation remain open.
- [x] **COV-017o — Quoted alternatives and enumerations.** Ten source-listed
  expressions map to eight canonical bundles: 는다거나/다거나/라거나/으라거나/
  자거나 and 는다든가/다든가/라든가. Attached ㄴ/non-ㄹ consonant, command
  vowel boundaries, copulas, prefinals and known auxiliary/suffix classes have
  distinct licenses. Factual 라든가 retains 시/더/으리 attachment. No implicit
  하다 is inserted. Evidence: [boundary/composition tests](../tests/quoted_alternatives.rs),
  twenty-two `quoted-alt-*` ledger cases, three complete annotated development
  sentences, dictionary/CLI parity, and browser source links. The
  [comparison](quoted-alternatives-evaluation.json) records each candidate change
  and the source dispositions. These entries are 문법‧표현, outside COV-013's
  715-entry POS inventory. Other quotation contractions, expanded quotation
  analysis, particle alternatives and quoted-clause copulas remain open. See
  [scope](rules.md#quoted-alternatives-cov-017o).
- [x] **COV-017p — Literal choice ending -든가.** Bare predicates and the
  source-listed honorific/past markers are supported, including copulas,
  auxiliaries and 답다. Literal ㄷ attachment preserves ㄹ and excludes
  vowel-boundary irregular recovery. Recovered 겠/더/어야겠 are not licensed.
  The ending remains distinct from particle 든가 and bundled quoted alternatives.
  Evidence: [ending/boundary tests](../tests/enumerative_particles.rs), eight
  `choice-ending-*` ledger cases, dictionary/CLI and browser homonym checks,
  and [evaluation](enumerative-particle-evaluation.json). Further outer particles
  and contextual choice remain open. Source: KRDict
  [-든가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82342).
- [x] **COV-017q — Sequential 고서 and emphatic 어서야.** Literal 고서
  preserves consonant stems and honorific 시, rejects recovered past/modal/
  retrospective stacks, and distinguishes verb/아니다 attachment from known
  adjective or represented-copula paths. Vowel-boundary 어서야 preserves
  아/어/여 allomorphs, irregulars, 하 contractions and a separate 어서 + 야
  reading. Evidence: [boundary/composition tests](../tests/seo_connectives.rs),
  source-cited `seo-connectives-*` judgments, dictionary/CLI parity and browser
  alternatives/source links. [The comparison](seo-connective-evaluation.json)
  records gains shared with COV-018i; broader 어서야 prefinal constraints and
  lexical class/sense selection remain open. See [scope](rules.md#seo-connectives-and-particles-cov-017q018i).
- [x] **COV-017r — Retrospective following-ending licenses.** Recovered 더
  is rejected before 33 reviewed ordinary or retrospective-bundled endings,
  including 다, 지, 어/어요, formal endings, 고 and doubled 더라/던데.
  The same condition applies to lexical predicates, explicit/omitted copulas,
  derived adjectives, auxiliary chains and outer particles. Licensed 라/니/냐/
  구나 families and literal bundles remain. Evidence: [132-path matrix and
  composition tests](../tests/retrospective_licenses.rs), 81 source-cited ledger
  cases, four complete unchanged annotated sentences, dictionary/CLI/browser
  checks and [comparison](retrospective-license-evaluation.json). The report
  accounts for every removed candidate across 184 surfaces and preserves all
  30 stress fingerprints. COV-017s below extends this review to 나 and nominalizing 기,
  including the separately represented 더 + 나 + 요 alternative.
  This closes the 더 + 다 gap recorded by COV-020g. See
  [scope](rules.md#retrospective-following-ending-licenses-cov-017r).
- [x] **COV-017s — Retrospective nominalization and connective boundaries.**
  Recovered 더 is rejected before 33 further reviewed endings, including
  나/으나, 기 and its bundles, 음, 게/도록/듯, 으면/으며/으면서/으므로,
  어서 and related AEO connectives, 고자/건대/소/오. Nominal particles,
  later copulas and auxiliaries cannot bypass the boundary. Licensed prefinal
  stacks, lexical stems and bundled/component alternatives remain. Evidence:
  [132-path matrix and composition tests](../tests/retrospective_connectives.rs),
  107 source-cited ledger cases, four complete unchanged annotated sentences,
  dictionary/CLI/browser checks and [comparison](retrospective-connective-evaluation.json).
  Every removal across 211 surfaces contains the reviewed boundary; all 30
  stress fingerprints and development gold/component recovery remain unchanged.
  Three short 며/면서/므로 sources are added to their existing canonical labels.
  Spaced 기로 하다 remains a nominalized clause followed by a lexical main verb;
  it does not establish a joined auxiliary connector. Other retrospective
  followers and attachment restrictions remain open. See
  [scope](rules.md#retrospective-nominalization-and-connectives-cov-017s).
- [x] **COV-017t — Retrospective adnominal and question alternatives.**
  Preserve 더 + 은/은데/은가/은지-family component analyses; NIKL documents
  alternative segmentation, so ordinary adnominal notes do not justify a
  blanket retrospective ban. Add dictionary bundles 던가/던지, with their
  licensed prefinals, copulas, particles and the 던가 + 보다/싶다 auxiliary
  construction. Reject 더 before 17 reviewed present/prospective endings,
  and prevent doubled 더 before the new bundles. Eleven dictionary source
  entries attribute the bundles and short ㄴ/ㄹ-family allomorphs.
  Evidence: [68-path matrix, preserved alternatives and composition](../tests/retrospective_adnominals.rs),
  144 source-cited ledger cases, four complete unchanged annotated sentences,
  dictionary/CLI/browser checks and [comparison](retrospective-adnominal-evaluation.json).
  Across 157 surfaces, every added bundled path has a split counterpart and
  every removal contains a reviewed incompatible boundary. All 30 stress
  fingerprints and development gold/component recovery are preserved.
  Other followers, omitted-copula adnominals and lexical/contextual restrictions
  remain open. See [scope](rules.md#retrospective-adnominal-and-question-alternatives-cov-017t).
- [x] **COV-017u — 놓아 → 놔 contraction.** Article 35 supplement 1
  restores 놓다 in 놔/놔라/놨다, including compound-final 놓다, double past,
  existing particles and auxiliary chains. Both verb and adjective/copular left
  contexts of auxiliary 놓다 remain. This lexical exception does not generalize
  ㅎ deletion (좋아 does not become 좌), treat phonetic 노아 as the written form,
  or restore 놓 before a non-아/어 boundary. Lexical 놔두다 and split 놓다 + 두다
  remain distinct; internal headword normalization is not added.
  Evidence: [boundary/full-form tests](../tests/noh_contraction.rs), 64 `noh-*`
  ledger cases, two complete KAIST sentences, dictionary/CLI parity and browser
  normalization/source checks. The [comparison](noh-contraction-evaluation.json)
  reviews 119 surfaces and 192 additions, with no lost candidates or changed
  existing provenance. 놨었지요 newly matches development gold; all 30 stress
  fingerprints remain unchanged. Broader auxiliary restrictions remain COV-019.

- [x] **COV-017v — Informative/reported 다네 and 다는데 families.**
  Ten canonical forms preserve present ㄴ/는 allomorphs, plain adjective/prefinal
  attachment, copular/factual 라 forms and separate (으)라 command readings.
  더라네/더라는데 bundles coexist with split retrospective components;
  source-listed polite 요 and concessive 도 paths retain the same restrictions.
  No implicit reporting 하다 or contextual sense is selected. Known auxiliary
  roles and -답다 derivation constrain attachment; unknown lexical classes and
  broader honorific judgments remain unverified.
  The shorter 라는데 entry has a narrower note than 더라는데/라는데요/라는데도;
  the latter entries support the retrospective/conjectural family paths. The
  [review](report-ne-evaluation.json) records this compositional interpretation.
  Evidence: [path/boundary tests](../tests/report_ne_endings.rs), 187 `report-ne-*`
  ledger cases, five complete annotated sentences, dictionary/CLI parity and
  browser homonym/source/normalization checks. The comparison accounts for 954
  additions on 186 surfaces with no lost candidates or changed prior provenance;
  all 30 stress fingerprints remain unchanged. Five development groups newly
  match, including 대부분이라는데, 풍속이었다네 and 판매한다네요.
  Further quoted families, outer particles, sense choice and independent Korean
  review remain open. See [scope and sources](rules.md#informative-and-reported-ne-families-cov-017v).

- [x] **COV-017w — Literal 되 and licensed 으되.** Canonical 으되
  preserves literal 되 after ordinary stems/honorific 시 and full 으되 after
  bare 있다/없다 (including compounds) or past/modal markers. It does not apply
  general 으-boundary irregular recovery: 살되/듣되/돕되 preserve their stems.
  Existing copulas, auxiliaries, -답다 and polite 요 compose. 치렀으되 and 그리되
  newly match their annotated development groups.
  Evidence: [boundary/composition tests](../tests/doe_endings.rs), 54 `doe-*`
  ledger cases, two complete annotated sentences, dictionary/CLI parity and
  browser allomorph/source checks. The [comparison](doe-evaluation.json) accounts
  for 132 additions on 67 surfaces without losing prior candidates or changing
  provenance; all 30 stress fingerprints remain unchanged.
  **Still unjudged:** short existential 있되/없되 and their compounds; the broad
  되 and specific 으되 notes do not settle their exclusivity in this review.
  Named followups `doe-short-existential` and `doe-further-composition` also keep
  omitted copulas and additional particles visible. This closes only the stated
  positive and boundary scope, not those unresolved judgments. See
  [scope and sources](rules.md#literal-doe-and-licensed-eudoe-cov-017w).

- [x] **COV-017x — Quoted/confirmatory -며/-면서 families.** Eighteen
  canonical components cover statements, commands, proposals, questions and
  retrospective reports, including ㄴ/는다며 and 다면서. Copular/factual 라
  stays distinct from command 으라; bundled 더라 alternatives coexist with
  더 + 라 components. Present forms retain attached-ㄴ boundaries and honorific
  licenses. Commands/proposals, question allomorphs, known adjective/auxiliary
  classes and copulas have separate checks. Auxiliary 있다/계시다 and inherited
  negatives preserve source-attested stative plain-다 readings in these new
  families. Polite 요 and longer -면서 + 도 compose; broader particles remain
  unjudged. No implicit reporting 하다 or contextual sense is selected.
  There are 157 required and 78 forbidden judgments, six complete unchanged
  annotated sentences, dictionary/CLI parity and browser source regressions.
  Six development gains leave 106 KAIST and 151 GSD misses, with no losses.
  Generic 더 + 냐며/냐면서 hypotheses remain unjudged: missing examples or
  an omitted prefinal in a short dictionary note is not a categorical ban.
  Evidence: [tests](../tests/report_myeo_endings.rs), stable `report-myeo-*`
  ledger cases, `report_myeo_endings_preserve_dictionary_and_cli_parity`,
  [rules](rules.md#quoted-and-confirmatory-myeo-families-cov-017x) and
  [source/candidate review](report-myeo-evaluation.json).

- [x] **COV-017y — Shared present-declarative prefinal and class licenses.**
  Eleven canonical ㄴ/는다 families now share their verb and prefinal constraints.
  Older 는다/는다고/는다는 reject recovered past/modal/retrospective markers;
  honorific 시 remains. Known adjective/copula roles, including 답다 and inherited
  negatives, cannot gain present declaratives through honorifics. Later verbal
  auxiliaries reset the class. Plain-다 counterparts, unknown lexical heads and
  nondeclarative 는데/는지 remain distinct. Nine missing full/attached source
  homonyms are now mapped in the browser. Evidence: [role/NFD/unknown-head
  tests](../tests/present_licenses.rs), 338 stable `present-license-*` ledger cases,
  dictionary/CLI parity and browser source selections, plus [source/candidate
  review](present-license-evaluation.json). The 343-surface comparison removes
  306 unsupported paths with no added candidates, lost corpus gold or changed
  stress fingerprints. This also resolves COV-019h's generic past/modal + present
  declarative gap; existential honorific/question/adnominal review stays open.

- [x] **COV-017z — Surprise and quoted -니 families.** Nine canonical
  components cover 다니/는다니/라니/으라니/더라니/자니/냐니/느냐니/으냐니.
  Present attached-ㄴ and consonant-는 boundaries, factual versus command 라,
  question allomorphs and prefinal/known-class licenses remain distinct. Bare
  verbal 다니 surprise is preserved (하다니 and 한다니 are both possible).
  Bundled 더라니 coexists with split 더 + 라니; source-listed polite surprise
  readings compose with 요 without licensing every homonymous sense. No implicit
  reporting verb is inserted. There are 109 required and 54 forbidden judgments,
  three complete unchanged corpus sentences, dictionary/CLI parity and browser
  source selections. Development misses fall to 104 KAIST and 150 GSD with no
  lost gold groups or changed stress fingerprints. All eight new components
  have labels; 24 added source IDs preserve full/short and expression homonyms.
  Evidence: [role/NFD tests](../tests/report_ni_endings.rs), stable `report-ni-*`
  ledger cases, `report_ni_preserves_dictionary_roles_and_cli_parity`,
  [rules](rules.md#surprise-and-quoted-ni-families-cov-017z) and
  [source/candidate review](report-ni-evaluation.json). Generic 더 + 냐니 and
  further existential paradigms remain unjudged. Broader quoted contractions
  such as 된단 and 노력했단 are now covered by COV-017ab; other families remain open.

- [x] **COV-017aa — Lexical attachment classes in dictionary-backed readings.**
  Added a finite, source-backed per-reading policy and opt-in `--dict-compatible`
  CLI/library/browser filtering. It excludes lexical-role conflicts, adjective
  present declaratives (가는다니 → 가늘다 + 는다니), verbal bare adjectival
  questions (길으냐니 → 긷다 + 으냐니), and the distinct command hypothesis
  아니다 + 으라니 while preserving factual 아니라니. Valid homonyms and unknown
  provider classes remain. Separately written auxiliaries such as 싶었다 are
  unknown without their preceding word, not automatically conflicting. Wish
  uses 행복하란/행복하자 remain; this is not a blanket adjective-command ban.
  The [separate dictionary-policy ledger](../tests/fixtures/dictionary-attachments.json)
  has 63 exact cases (39 required, 24 forbidden); all are present before filtering
  and after headword-only filtering. The raw rule API and `--dict-only` candidate
  groups remain unchanged across 2,389 regression surfaces. Per-entry evidence,
  component ownership, Unicode/cache behavior, CLI/library parity and browser
  choices/glosses/export are covered. See [policy and limits](dictionary-attachments.md)
  and [review/measurements](dictionary-attachment-evaluation.json).
  Further lexical/sense restrictions remain COV-017/019; the novel audit exposes
  missing adverbial-role alternatives under COV-018n. Dictionary matching or
  passing this finite policy still does not certify grammatical correctness.

- [x] **COV-017ab — Short quoted modifiers and change/conditional endings.**
  Eight components cover 단/는단/잔/냔/느냔/으냔/다간/다가는. Preserve both
  quoted and change/conditional 단 homonyms; the latter admits bare verbs,
  including auxiliary verbs. Present full/attached boundaries, proposals,
  question allomorphs and known-class/prefinal conditions remain distinct.
  The source-illustrated 누구냔 recovers an omitted copula without permitting
  consonant-final 학생냔 as 학생 + 이다. Existing 란/으란 paths remain.
  The noun suffix -단 is excluded from ending lookups. No implicit reporting
  verb is inserted. There are 92 required / 50 forbidden judgments, two complete
  annotated sentences, dictionary/CLI parity and browser source checks. 된단
  and 노력했단 newly match; misses fall to 102 KAIST / 150 GSD with no lost
  gold groups or changed stress fingerprints. The 151-surface comparison adds
  599 candidates without removing or changing existing ones. Evidence:
  [tests](../tests/short_clauses.rs), `short-clause-*` ledger cases,
  `short_clauses_preserve_dictionary_roles_and_cli_parity`,
  [rules](rules.md#short-quoted-modifiers-and-changeconditionals-cov-017ab) and
  [source/candidate review](short-clause-evaluation.json). Further outer particles,
  copula omission, 하다 shortening, existential questions and lexical-class
  choices remain explicitly tracked followups under COV-018/020/021/019h/017aa.

- [x] **COV-017ac — Shared adjectival question-family attachment.**
  The six canonical 으냐/으냐는/으냐며/으냐면서/으냐니/으냔 forms now
  share bare-adjective licensing. Plain 으냐 and 으냐는 no longer bypass
  the known auxiliary-verb restriction; recovered prefinals cannot precede the
  adjectival family. General 냐 and verbal 느냐 paths remain distinct, including
  계시냐, 싶었냐 and 싶으시느냐. Negative auxiliaries inherit only represented
  classes; unknown lexical heads remain available without a dictionary.
  Evidence: [169 ledger cases](../tests/fixtures/validity.json) (120 required / 49
  forbidden), [Unicode/dictionary/CLI tests](../tests/adjectival_question.rs),
  one complete GSD sentence, browser source/selection checks, and
  [source/candidate review](adjectival-question-evaluation.json). Twenty-one
  ending/expression entries are reviewed; three grammar-POS entries receive
  new scoped inventory dispositions. Thirty-six scoped hypotheses are removed
  across 187 focused/stress/observation surfaces, without additions or provenance
  changes. The only changed development token loses a distinct auxiliary
  으냐는 hypothesis; its gold lemma and general 냐는 remain. Stress hashes
  and all development recovery outcomes are unchanged. Broader existential
  paradigms, honorific 있다 and past adnominals remain open under COV-019h.

- [x] **COV-017ad — Uncertain possibility and shortened intention questions.**
  -(으)ㄹ는지 and -(으)려는가/지 now expose canonical 을는지, 으려는가
  and 으려는지. Boundary and irregular recovery retain ㄹ; possibility admits
  honorific/past markers, while the intention expressions admit only honorific
  시. The latter reject represented adjective auxiliaries, inherited known
  adjective/copula negatives, direct copulas and 답다 derivation. Unknown lexical
  heads remain; dictionary filtering does not certify every lexical attachment.
  Existing ordered nominal/question particles compose, including 나올는지는
  and 있을는지요. No implicit 하다 or contextual sense is selected.
  Evidence: [92 stable judgments](../tests/fixtures/validity.json) (55 required /
  37 forbidden), [Unicode/dictionary/CLI tests](../tests/uncertainty.rs),
  the complete unchanged KAIST MH2_0159-s309 sentence, six dictionary grammar
  sources, browser source/selection checks and [review](uncertainty-evaluation.json).
  같을는지 recovers 같다, leaving 101 KAIST and 150 GSD development misses;
  no prior gold recovery is lost. All thirty stress fingerprints are unchanged.
  Nonstandard 을런지 spelling repair, broader intention-family/class licenses,
  contextual particle distribution and independent Korean review remain open.

- [ ] **COV-018 — Further particle attachments and pronoun contractions.**
  **Partial: COV-018a–k and COV-018m–n implement post-ending, outer choice, emphatic,
  concessive, definition, enumerative, destination and recipient particles,
  including nominal (이)라고 alternatives, the noun-attached 치고 family and
  source-attested case marking after range particles, and comparison/extent particles.**
  Remaining: pronouns outside the existing finite paradigms. Preserve homonym-specific
  dictionary labels and review additional ending/particle licenses.
  Include quoted clauses marked as nominals: KAIST MH2_0169-s444/3 살겠다가
  is annotated 살 + 겠 + 다 + 가 (subject particle), not a -다가 example.
- [x] **COV-018a — Post-ending particles.** Connective 는/도 and scoped
  restrictive 만 now compose, including 먹고는, 하면서도, and 통해서만.
  Final-ending 만/마는 supports 있습니다만, 먹는다마는, copulas and auxiliary
  groups. The browser distinguishes concessive 만 (86555) from nominal or
  restrictive 만 (86554); full 마는 (86552) is never stripped from bare nominals.
  Evidence: [particle paths/boundaries](../tests/particles.rs), eight
  `post-ending-*` ledger cases, five offline corpus tokens, dictionary/CLI and
  browser homonym tests. One compatibility snapshot gains four reviewed
  unverified lexical hypotheses; all previous analyses remain. See
  [scope](rules.md#post-ending-particles-cov-018a) and
  [development comparison](post-ending-evaluation.json).
- [x] **COV-018b — Outer choice/emphasis and nominal quotative particles.**
  Case/restrictive chains admit (이)나, (이)라도, (이)든지, and (이)야 with
  the allomorph selected by the immediately preceding surface. 어디까지나 and
  이제부터라도 recover their bases. Duplicate choice families are rejected;
  nominal, adverbial, nominalized, and reviewed post-ending readings coexist.
  Nominal (이)라고 is a `Particle`, distinct from copular `Ending` 라고;
  학생이라고 retains both alternatives. Labels link to particle entries and
  retain homonyms. Evidence: [path/boundary tests](../tests/particles.rs), twelve
  `chain-*` ledger cases, four annotated offline tokens, dictionary/CLI parity,
  browser/source-link tests, and [development comparison](particle-chain-evaluation.json).
  All 30 current compatibility fingerprints remain unchanged. See
  [scope and sources](rules.md#outer-choice-and-quotative-particles-cov-018b).
  Quoted clauses followed by subject particles and cross-token quotation
  structure are not implemented by these nominal paths.
- [x] **COV-018c — Emphatic/concessive particles and locative 서.**
  (이)야말로, (이)나마, 은/는커녕 and bare 커녕 compose with the existing
  nominal/suffix/particle order. Contracted ㄴ커녕 normalizes to 는커녕, as
  in 먹긴커녕 → 먹다 + 기 + 는커녕. Nominalizations, auxiliary groups, and
  adverbial phrases retain distinct roles; bare 커녕 has nominal attachment
  only. 나마 additionally accepts the source-listed adverbial 게 ending.
  Locative 서 now follows consonants too, including 서울서/시장서, and carries
  no foreign-base pronunciation assumption. This does not broaden the separate
  count-emphasis 서 homonym's lexical scope. No new auxiliary connector is added.
  Evidence: [boundary/role tests](../tests/emphatic_particles.rs), nineteen
  `emphatic-*` judgments, dictionary/CLI parity, twelve browser/source-link
  cases, and [evaluation](emphatic-particle-evaluation.json). Thirteen newly
  recovered corpus tokens have explicit tests. A fourteenth numerical gain,
  확약서 → 확약, stays a segmentation-review case, not a required linguistic
  judgment. See [scope and sources](rules.md#emphatic-and-concessive-particles-cov-018c017i).
- [x] **COV-018d — Definition/topic particles 란/이란.** Nominal allomorphs
  preserve 문화란 → 문화 and 학생이란 → 학생, with nominalization and suffix
  composition. They do not accept adverbial/case-marked bases; 학생 + 이 + 란
  is not substituted for the bundled particle or copula + ending. Unknown foreign
  bases retain explicit pronunciation conditions. Together with COV-017j this
  recovers 26 annotated groups, protected by complete source sentences and a
  stable-ID index. The same [evaluation](quoted-definition-evaluation.json)
  records eight remaining 라는 cases: three annotation/representation differences
  preserve existing copula + ending analyses; quoted-clause and omitted-copula
  fragments remain COV-018/020 review. No unsupported 라는 particle is added
  solely to match corpus segmentation. Evidence is shared with COV-017j above.
- [x] **COV-018e — Enumerative (이)라든가/(이)라든지 and choice (이)든가.**
  Six particle forms preserve nominal, reviewed adverbial/case-phrase and
  nominalization paths, alongside existing copular/ending alternatives.
  든가 separately follows final 다/는다/라 allomorphs; 먹는다든가 retains both
  the bundle and 는다 + 든가. Nominal suffixes, polite 요, NFD and conditional
  foreign-base pronunciation compose. Full 이라든가/이라든지 have nominal-only
  attachment; the short forms do not strip subject/object case phrases.
  The viewer uses explicitly mapped related entries when the pinned dictionary
  lacks a separate 라든가 or 이든가 particle entry. Evidence:
  [path/role/boundary tests](../tests/enumerative_particles.rs), twenty
  `enum-*`/`choice-particle-*` ledger cases, dictionary/CLI parity and browser
  source links. Three further ledger judgments exclude known adjective/copula
  classes before present 는다 even after 시, preventing the composed particle
  reading from bypassing the same restriction. [Scope and sources](rules.md#enumerative-particles-and-choice-ending-cov-018e017p)
  and [evaluation](enumerative-particle-evaluation.json) retain unjudged candidates.
  Further particle stacks and quoted-clause attachment remain open.
- [x] **COV-018f — Emphatic destination/recipient particles.** 에다/에다가,
  에게다/에게다가, 한테다/한테다가, (으)로다가 and 보고/더러 preserve
  nominal paths and existing predicate readings. Separate emphatic 다/다가
  attaches after eight reviewed case forms or seven deictic location/direction
  words, retaining bundled and component alternatives. Nominalizations, suffixes,
  outer particles, NFD and conditional foreign pronunciation compose. Arbitrary
  nouns, adverbs, predicate endings and subject/object case phrases do not license
  emphatic 다/다가. Recipient suitability and contextual senses remain explicit
  limitations. Evidence: [path/boundary tests](../tests/destination_particles.rs),
  twenty-four `destination-*` ledger cases, three complete development sentences,
  dictionary/CLI parity and browser homonym/source-link checks. [Evaluation](destination-particle-evaluation.json)
  records two KAIST and one GSD recovery, with all thirty stress fingerprints
  unchanged. [Scope and sources](rules.md#destination-recipient-and-emphatic-adverbial-particles-cov-018f)
  leave other adverbial bases and further particle stacks open; COV-018g adds
  enumerative 다/이다 separately.
- [x] **COV-018g — Enumerative 다/이다 particles.** Vowel-final 다 and
  consonant-final 이다 attach to nominals, bounded suffixes and nominalizations,
  preserving copular and emphatic alternatives. Prior case phrases and predicate
  endings do not license enumeration. Foreign-base pronunciation conditions and
  existing outer 들/요 slots remain explicit hypotheses. Identical paths such
  as 저기 + 다 merge provenance and display “Enumeration / emphasis”; separate
  copula paths retain their roles. Evidence: [boundary/composition tests](../tests/enumerative_da.rs),
  sixteen `enumerative-da-*` judgments, an unchanged annotated copula sentence,
  dictionary/CLI parity and browser source/alternative checks.
  [Evaluation](enumerative-da-evaluation.json) records every candidate change,
  unchanged development recall and three individually reviewed stress changes,
  retaining prior candidates and hashes. Contextual enumeration, lexical
  suitability and broader particle combinations remain open. See
  [scope and sources](rules.md#enumerative-daida-particles-cov-018g).
- [x] **COV-018h — 은 after consonant-final connectives.** The connective
  attachment inventory now accepts both topic/emphatic allomorphs 은/는 with
  their existing consonant/vowel boundary checks. 먹지만은 and 의사지만은
  retain bundled 지만 + 은 alongside existing component alternatives.
  Wrong allomorphs and arbitrary adnominal/formal endings remain excluded.
  Source: KRDict [은 86111](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86111),
  sense 3. Evidence: `closed_connectives_accept_eun_without_losing_neun_boundary_checks`
  in [tests](../tests/omitted_connectives.rs), six `omitted-connectives-topic-*`
  judgments, dictionary/CLI parity and browser source checks. This corrects
  the existing allomorph omission; it does not expand the connective inventory
  or auxiliary-internal particle slots.
- [x] **COV-018i — Reviewed particles after 서 connectives.** Connective
  고서 admits the existing 은/는, 도, 만, 요 slots and emphatic 야; 어서
  also admits 야. 부터 follows 어서/고/으면서, while comparative 보다
  follows 어서, with existing outer particles. Examples include 돌리고서는,
  되어서야, 나오면서부터 and 통해서보다는. Together with COV-017q,
  nine complete unchanged KAIST development sentences become exact grouped
  matches; no prior gold or candidates are lost. Evidence: [tests](../tests/seo_connectives.rs),
  twenty-nine ledger cases across both items, attributed dictionary fixtures,
  CLI/browser checks and [evaluation](seo-connective-evaluation.json).
  Other ending/particle families, especially broader 부터/보다 attachment,
  remain for review. No unrestricted clause nominalization is introduced.
- [x] **COV-018j — Noun-attached 치고 family.** 치고, 치고는 and 치고서
  retain separate source-backed bundles, plural bases and reviewed topic/polite
  composition. 학생치고는 preserves both 치고는 and 치고 + 는; 사람치고서는
  preserves 치고서 + 는. Existing 치다/고치다/놓치다 predicate readings remain.
  Bare predicate endings and intervening case particles do not license noun
  attachment. The GSD 아파트치고 group now recovers 아파트. Evidence:
  [boundary/ambiguity tests](../tests/chigo_particles.rs), 63 stable ledger
  cases, one complete unchanged annotated sentence, dictionary/CLI parity,
  source-linked browser alternatives and [comparison](chigo-evaluation.json).
  The required raw 교수님 plural paths have an explicit dictionary headword gap;
  the existing 교수 + 님 + 들 alternatives survive dictionary-only filtering.
  Further outer particles, repeated topics, nominalized-base semantics and
  contracted 치곤 remain unjudged in the report; COV-018 remains open.

- [x] **COV-018k — Case marking after range particles.** Source examples
  support 까지 + 가/를/에/로 and 부터 + 가 across the ordinary particle
  ordering stages. 역사까지를, 여기까지가, 페이지까지로, 정착되기까지에는
  and 제목부터가 now recover their bases. Existing nominalizations,
  honorific/plural suffixes, topic/polite particles and attached ㄹ compose;
  case allomorphs still follow the immediately preceding sound. Evidence:
  [boundary tests](../tests/range_case_particles.rs), 47 stable ledger cases,
  dictionary/CLI parity, source-linked browser alternatives and
  [candidate/source comparison](range-case-evaluation.json). One unchanged
  annotated sentence preserves the KAIST 역사까지를 gain; another records the
  separate unjudged COV-018l observation. All prior analyses remain; two existing
  contracted paths gain provenance only. Other case chains remain open.
- [ ] **COV-018l — Resolve 마다 + 에 distribution.** The complete KAIST
  `MH2_0159-s285/15` observation 편마다에도 is retained in
  [the fixture](../tests/fixtures/kaist-range-case.conllu). Its expected
  편 + 마다 + 에 + 도 path is not generated. KRDict 마다 specifies noun
  attachment but does not settle following case marking. The primary paper's
  abstract links distribution to semantic restrictions; the full distribution
  evidence and Korean review are still needed. This observed gap is neither
  a required nor forbidden candidate judgment. See the named followup and
  bibliography in [the review](range-case-evaluation.json).

- [x] **COV-018m — Comparison and extent particles.** Noun-attached 토록
  and 마냥, noun/particle 만치, and explicit 어서 + 만치/만큼 now compose
  with existing suffixes and reviewed outer particles. 필생토록 recovers 필생;
  있어서만치는 and 있어서만큼은 preserve the connective and particle roles.
  Lexical 그토록 and standalone 마냥 remain selectable, and shortened
  하다 + 도록 paths remain. Grammar lookup excludes the bound-noun 만치 and
  adverb 마냥 homonyms from particle labels. Evidence:
  [role/boundary tests](../tests/extent_particles.rs), 63 stable ledger cases,
  two complete unchanged corpus sentences, dictionary/CLI parity and browser
  alternatives/source checks. [The comparison](extent-evaluation.json) accounts
  for all additions and retains explicit followups for further connectors,
  case/particle chains and nominalized-base semantics. Adnominal + bound-noun
  joining is a separate representation; its valid homonym is not forbidden by
  an exact particle-role judgment. COV-018 remains open.

- [x] **COV-018n — Adverbial bases before ordinary focus particles.** Added
  dictionary-free Adverbial alternatives before 도/은/는/만/까지/부터, including
  아직도, 퍽도, 너무도, 자세히는 and 아직까지. New paths check the whole
  particle chain; arbitrary noun-case marking is not inherited. Source-listed
  derived adverbs also accept reviewed range particles. Nominal and unchanged
  candidates remain, including genuine 오늘/지금 homonyms. The optional dictionary
  conflict filter distinguishes 학교 + 도 as nominal and 아직 + 도 as adverbial.
  Evidence: [55 ledger cases](../tests/fixtures/validity.json) (38 required / 17
  forbidden), [role/dictionary/CLI tests](../tests/adverb_focus.rs), 28 attributed
  lexical entries and five complete KAIST/GSD sentences covering six explicitly
  annotated adverb-particle tokens. Browser choices, glosses and exports agree
  with the CLI. [The review](adverb-focus-evaluation.json) records 54 additions
  across 82 surfaces with no removals/provenance changes; three stress hashes
  have four reviewed new hypotheses with old hashes preserved. Corpus lemma
  recall is unchanged; the novel gains complete filtered readings for 86 tokens
  across 18 types without losing any previous filtered readings. The inherited
  adverbial + particle + copula hypotheses remain unjudged under COV-020;
  additional particle subclasses and contextual sense selection remain open.

- [ ] **COV-019 — Auxiliary inventory and internal particles.** **Partial:
  COV-019a implements the structural connector catalog and bounded internal
  particles; COV-019b adds negative contrast particles and short prohibitives.**
  COV-019c checks known auxiliary adjective inflections and removes unsupported
  어 + 없다. COV-019d checks the known left class before expressive 어 하다.
  Remaining: other left verb/adjective and lexical-subset restrictions,
  further ending/prefinal constraints, and additional particle combinations.
  Distinguish independent compounds and
  contextual auxiliary senses; dictionary presence does not resolve these.
  The negative 말다 mood audit in COV-019b rules out a blanket command-only
  filter; questions and indirect wishes can also be valid. Sentence-mood and
  sense selection require context beyond this token-level candidate generator.
  COV-019e adds internal 는 before 싶다 (학생이고는싶다).
  COV-019f rejects known adjective/copula roles before 어/고 있다/계시다.
  Other lexical subsets and attachment constraints still need review.
- [x] **COV-019a — Auxiliary connectors and one internal particle.** The
  [source inventory](auxiliary-inventory.json) preserves attachment notes for all
  54 KRDict auxiliary entries. Added paths include 나다/나가다, 계시다,
  adnominal 만하다/듯하다, nominal 음 + 직하다, and connector-specific
  uses of 하다/보다/들다. 가지다/갖다 and 달다 have restricted following
  forms; 으면 + 하다/싶다 requires recovered past. One reviewed particle
  slot supports 먹어들봐요, 먹고야말았다, 먹기나했다, and contracted
  먹곤했다, retaining bundled and whole-word alternatives. These are tolerant
  joined-input analyses, not spelling recommendations or cross-token parsing.
  Evidence: [path/boundary tests](../tests/auxiliary_inventory.rs), twelve
  `aux-inventory-*` ledger cases, five annotated offline tokens,
  dictionary/CLI parity, browser component/link tests, and
  [development comparison](auxiliary-evaluation.json). Packed iterative search
  and the 1,024-syllable memory test pass. One snapshot gains two unknown-stem
  hypotheses; all prior analyses remain. See [scope](rules.md#auxiliary-connectors-and-internal-particles-cov-019a).
- [x] **COV-019b — Negative auxiliary particles and short prohibitives.**
  마/마라/마요 recover 말다 with canonical 어/어라/어요; the full forms
  remain. Shortening is limited to prohibitive inflection, not arbitrary ㄹ
  stems, past tense, connective endings, or completive 고 말다. Joined input
  supports 지 + 는 (also contracted 진) before 않다/못하다/말다/아니하다,
  including 먹어보진마요. Existing 도/만 paths and lexical readings remain.
  NIKL's mood guidance preserves questions and indirect wishes rather than
  restricting every 말다 path to an imperative ending. Evidence: expanded
  [auxiliary tests](../tests/auxiliary_inventory.rs), fourteen `negative-aux-*`
  ledger cases, full GSD dev-s312, dictionary/CLI parity, and browser alternatives
  with -어라/는 source links. All current snapshots remain unchanged.
  See [scope and sources](rules.md#negative-auxiliary-particles-and-short-prohibitives-cov-019b)
  and [development comparison](negative-auxiliary-evaluation.json).
- [x] **COV-019c — Known auxiliary adjective inflections and legacy link audit.**
  The [class audit](auxiliary-class-audit.json) records all 54 source entries:
  34 verb-only, eight adjective-only, and six dual-class headwords. Bare
  adjective auxiliaries reject the reviewed verbal present/adnominal/question
  endings. Connector-specific 보다/못하다 uses and known classes inherited
  through 않다/아니하다/못하다 are checked, including particles, contractions,
  copulas, and an explicit 답다 suffix. Unknown lexical heads stay unclassified;
  prefinal and homonym alternatives remain. The unsupported 어 + 없다 auxiliary
  path is removed without changing lexical 없다 or 없이. Evidence: matrix and
  composition tests in [auxiliary tests](../tests/auxiliary_inventory.rs), fourteen
  `aux-class-*` ledger cases, four complete GSD sentences, dictionary/CLI parity,
  and browser/API checks. The [evaluation](auxiliary-class-evaluation.json)
  records each removed candidate in the targeted cases; all current fingerprints
  and corpus recoveries remain. See [scope](rules.md#auxiliary-adjective-inflections-and-legacy-links-cov-019c).
- [x] **COV-019d — Known left classes before expressive -어 하다.**
  Known auxiliary verbs and represented copulas no longer feed expressive 어 하다.
  Classes propagate through negatives, including contracted 잖 and internal
  particles; the immediately preceding class is checked after causative 게 하다.
  Adjective auxiliary and explicit 답다 paths remain, as do unclassified lexical
  hypotheses and other copula/하다 connectors. Evidence:
  [class/composition tests](../tests/auxiliary_left_class.rs), twelve `left-hada-*`
  ledger cases, dictionary/CLI parity, the retained expressive source sense,
  and browser regressions. [The comparison](auxiliary-left-hada-evaluation.json)
  lists each removed candidate and verifies unchanged corpus recovery and stress
  fingerprints. This is not a blanket left-class filter for all auxiliaries;
  lexical-subset and contextual sense restrictions remain open. See
  [scope and sources](rules.md#expressive-hada-left-class-cov-019d).
- [x] **COV-019e — Contrastive 고는/곤 before 싶다.** One internal 는 now
  connects 고 to 싶다, including 먹고는싶다, 먹곤싶다, 학생이고는싶다
  and 의사곤싶다. Prefinals, negative/expressive chains, nominalization and
  existing dictionary alternatives remain. Known adjective-ending and nominal
  boundary restrictions still apply. KRDict's 좀 entry supplies the direct
  spaced example 놀고는 싶지만; joined tests exercise tolerant input only.
  Evidence: [path/composition tests](../tests/desire_topic.rs), thirteen
  `desire-topic-*` ledger cases, dictionary/CLI parity, browser particle-source
  checks and [the comparison](desire-topic-evaluation.json). Other internal
  particles and auxiliary left-class licenses remain open. COV-019f resolves
  the known-adjective 어 있다 case discovered here. See
  [scope](rules.md#contrastive-desire-links-cov-019e).
- [x] **COV-019f — Known left classes before continuative 있다/계시다.**
  Both 어 and 고 links reject known adjective auxiliaries, inherited negative
  adjective classes, explicit 답다 derivation and represented copulas. Existing
  verb paths, class changes through expressive/causative 하다 and unclassified
  lexical heads remain. Specific dictionary expression notes establish verb
  attachment; the broader connector inventory is not a license for every pairing.
  Evidence: [44-combination matrix and composition tests](../tests/continuative_class.rs),
  twenty `continuative-class-*` ledger cases, dictionary/CLI parity and browser
  regressions. [The comparison](continuative-class-evaluation.json) reviews all
  removals across 83 surfaces and the two changed stress fingerprints, with no
  lost corpus gold. Transitivity, verb subsets, other prefinal/particle conditions
  and independent review remain open. See [scope](rules.md#continuative-left-classes-cov-019f).
- [x] **COV-019g — Stative auxiliary inflection across older report families.**
  Auxiliary 있다/계시다 now retain plain-다 readings before 다네/다는데 and
  다거나/다든가, including inherited negative readings. A later dynamic auxiliary
  resets that possibility. Bare auxiliary 있다 no longer takes the reviewed
  declarative 는다 families; lexical 있다, 계신다 and 있지 않는다 remain distinct.
  Present adnominal 는, background 는데, question 느냐 and prefinal-bearing
  reports retain their existing behavior. Evidence: [role and normalization
  tests](../tests/stative_reports.rs), 166 stable `stative-report-*` ledger cases,
  dictionary/CLI parity and browser selections, plus [source/candidate
  review](stative-report-evaluation.json). The review distinguishes direct
  attestations from morphological inferences, accounts for 96 additions and
  50 removals, and preserves all corpus gold and stress fingerprints. This does
  not settle all existential paradigms; COV-019h retains that work.
- [ ] **COV-019h — Further existential auxiliary paradigms.** **Partial:
  COV-017y applies shared present-declarative restrictions to auxiliary chains,
  including 먹고있었는다고 and modal equivalents; COV-017ac unifies the
  six bare-adjective question forms and preserves general 냐/verbal 느냐.**
  Remaining: honorific 있다
  paradigms, existential question allomorphs and past adnominals. Probe observations
  such as 먹고있으신다네 and 앉아있은 remain explicitly unjudged in
  [the latest source review](present-license-evaluation.json). Official consultation
  material does not provide a categorical auxiliary-wide judgment for every
  honorific or past-adnominal reading. Keep lexical 있다 and auxiliary 있다/계시다
  senses distinct. COV-019i resolves the missing internal-particle path
  먹고는있다네 without settling these existential paradigms.

- [x] **COV-019i — Contrastive particles before continuative auxiliaries.**
  Added 고 + 는 and 어 + 는 before 있다/계시다, including existing 곤
  expansion: 먹고는있다네, 먹곤있다, 살아는있을까, 앉아는계신다.
  Six direct dictionary examples support the spaced constructions; joined
  input and honorific/contracted composition are explicitly distinguished from
  source attestations. Existing immediate-left class, boundary, reporting and
  prefinal checks remain, with unknown lexical heads and whole-word alternatives
  preserved. Evidence: [52 ledger cases](../tests/fixtures/validity.json)
  (33 required / 19 forbidden), [Unicode/component/dictionary/CLI tests](../tests/continuative_topic.rs),
  browser component/source checks, and [candidate/source review](continuative-topic-evaluation.json).
  Across 82 focused/stress surfaces, 106 hypotheses are added with no prior
  analyses or provenance removed. All thirty stress fingerprints remain intact.
  More internal particles, lexical subsets, contextual suitability and COV-019h
  existential paradigms remain open; this is not cross-token parsing.

- [ ] **COV-020 — Derived nominal/copula composition and attachment classes.**
  **Partial: COV-020a adds direct nominalization + copula; COV-020b adds
  quoted copula fragments; COV-020c adds reviewed omitted-copula endings and
  finite 거/것 nominal alternatives; COV-020d adds enumerative -요 and
  COV-020e adds reviewed consonant-initial ending families; COV-020f adds
  honorific omission and short 세요; COV-020g adds modal/retrospective omission;
  COV-020h adds attached question endings; COV-020i adds nominal approximation -쯤.**
  Remaining: additional suffix order and adjective ending licenses, other
  omitted-copula endings/prefinals, and particle-marked nominal bases. Quoted or
  connective clauses before copulas need a separate source/representation audit;
  nominalization does not authorize arbitrary ending + copula attachment.
- [x] **COV-020a — Direct nominalization + copula.** 기/음 nominalizations
  compose with explicit copulas, vowel-final omission, and existing polite
  copula allomorphs. 학생다움이다 exposes 학생 + 답다 + 음 + 이다 + 다;
  먹기다 and 먹기예요 preserve 먹다 + 기 + 이다. Existing prefinals, suffix
  order, auxiliary groups, outer particles, and nested nominalizations compose
  without a fixed nesting cutoff. Consonant-final bases still require 이 and
  known -답다 still requires its ㅂ-irregular boundary. Whole-word readings remain.
  Evidence: [composition/boundary tests](../tests/nominal_copulas.rs), eight
  `nominal-copula-*` ledger cases, one complete annotated KAIST sentence,
  dictionary/CLI parity and browser selector/source-link tests. All current
  snapshots and frozen corpus recoveries remain; the new 떠먹이기다 group is
  recorded in [the evaluation](nominal-copula-evaluation.json). See
  [scope and sources](rules.md#direct-nominalization-and-copulas-cov-020a).
- [x] **COV-020b — Quoted copula fragments.** Standalone 이라는 gains a
  Copula-role analysis; standalone 라는 additionally recovers omitted 이다
  with explicit provenance requiring preceding quoted material. Tokenization,
  original byte offsets, and lexical alternatives remain. The browser displays
  the condition with the selected breakdown and exports it with the analysis.
  Evidence: [fragment/streaming tests](../tests/copula_fragments.rs), two complete
  [KAIST sentences](../tests/fixtures/kaist-copula-fragments.conllu), three
  `quoted-copula-*` ledger cases, dictionary/CLI parity, and browser/export checks.
  [Evaluation](copula-fragment-evaluation.json) records two additional grouped
  recoveries, with no losses or changed current fingerprints. This does not
  parse preceding quoted material or license arbitrary ending + copula
  attachment inside a token. Other fragment endings and particle combinations
  remain COV-020 review. See [scope and source](rules.md#quoted-copula-fragments-cov-020b).
- [x] **COV-020c — Omitted copulas and colloquial nominal alternatives.**
  지/지요/죠, 면, attached ㄴ데, and attached ㅂ니다/ㅂ니까 now recover 이다
  after vowel-final nominals, including 겁니다, 건데, 거죠, and 의삽니다.
  Recovery preserves the ending consonants and does not apply verb irregulars
  to nouns. Exactly 거/이거/그거/저거 also expose 것/이것/그것/저것 before
  copulas, retaining short and whole-word alternatives. Existing nominalizations,
  auxiliaries, and outer particles compose; unknown-script pronunciation
  conditions remain explicit. Evidence: [boundary/composition tests](../tests/omitted_copulas.rs),
  fourteen `omitted-copula-*` ledger cases, nine complete annotated sentences,
  dictionary/CLI parity, and browser alternative/source-link checks.
  [Evaluation](omitted-copula-evaluation.json) records nine new development
  recoveries with no losses, and one reviewed additive noun/copula hypothesis
  in each of three stress fingerprints. Every prior candidate and hash is
  preserved. Other omission families and broader colloquial paradigms remain
  open. See [scope and sources](rules.md#omitted-copulas-and-colloquial-nominal-alternatives-cov-020c).
- [x] **COV-020d — Enumerative copular -요.** 연장이요, 자화상이요,
  아비요 and 아니요 gain connective-ending paths distinct from polite particle
  요. Bare 이다/아니다, vowel-final omission, nominal suffixes/particles,
  nominalizations and explicit 이요 fragments compose. General predicates and
  recovered prefinals do not gain this ending. Evidence: [role/boundary tests](../tests/copula_yo.rs),
  eight `copula-yo-*` judgments, five complete annotated sentences,
  dictionary/CLI parity and browser role-specific source links. The
  [evaluation](copula-yo-evaluation.json) separates five connective recoveries
  from two incidental sentence-final gold-group matches. Two stress snapshots
  gain reviewed unknown-nominal hypotheses; every prior candidate and hash is
  retained. Other copula families and contextual reading selection remain open.
  See [scope and sources](rules.md#enumerative-copular-yo-cov-020d).
- [x] **COV-020e — Omitted copula before further consonant-initial endings.**
  니/니까, 고, 지만, 거든 and 네, including existing 지만요/거든요/네요
  bundles, restore 이다 after vowel-final nominals. Canonical 니/으니 alternatives,
  explicit copulas, nominalizations, colloquial 거 forms and existing particle/
  auxiliary connectors remain. Consonant-final nominals do not lose their coda
  or receive predicate irregulars. Conditional foreign pronunciation is explicit.
  Evidence: [boundary/composition tests](../tests/omitted_connectives.rs),
  thirty `omitted-connectives-*` judgments shared with COV-018h, nine complete
  annotated sentences, dictionary/CLI parity and browser normalized source checks.
  [Evaluation](omitted-connective-evaluation.json) records six KAIST and three
  GSD grouped gains; the latter include an incidental place-name annotation
  match, not a linguistic improvement. Four stress changes retain every previous
  candidate and hash, with unknown nominal/auxiliary hypotheses explicitly
  unjudged. COV-020f separately adds honorific omission; other prefinals,
  further endings and copula/auxiliary eligibility remain open. See [scope and sources](rules.md#further-omitted-copulas-and-connective-eun-cov-020e018h).
- [x] **COV-020f — Honorific copula omission and short 세요.** 선수셨다
  restores 선수 + 이다 + 시 + 었 + 다; 의사시니까 and 의사세요 retain
  represented copulas. Restoration occurs before the existing prefinal stack,
  preserving contracted/uncontracted past, double past, modal/retrospective order,
  ending restrictions, nominalizations and licensed particle/auxiliary links.
  Consonant-final nouns cannot borrow predicate irregulars; restored 이 cannot
  become an invented lexical predicate, including through an outer copula.
  Evidence: [boundary/parity tests](../tests/honorific_copulas.rs), twenty-six
  `honorific-copula-*` judgments, three unchanged annotated verb sentences,
  dictionary/CLI parity and browser normalized/source checks. The
  [comparison](honorific-copula-evaluation.json) records all additions and
  unchanged development recall. One stress fingerprint gains two unjudged nominal
  hypotheses; every prior candidate and hash remains. The short 세요 component
  stays bundled; generic 시어-to-세 recovery, other prefinal omissions, contextual
  honorific suitability and broader auxiliary restrictions remain open. See
  [scope and sources](rules.md#honorific-copula-omission-cov-020f).
- [x] **COV-020g — Modal and retrospective copula omission.** Recover 이
  before 겠/더 after vowel-final nominals, preserving represented copula roles,
  normal prefinal order and explicit forms. Reviewed literal bundles 더라,
  더라고, 더군/더군요, 더니, 더라도 and 던데/던데요 retain alternatives to
  decomposed prefinals. 마찬가지겠지만, 최고더군요 and 어디더라 gain exact
  annotated groups in three complete unchanged development sentences. Evidence:
  [boundary/composition tests](../tests/prefinal_copulas.rs), thirty-five
  `prefinal-copula-*` ledger cases, attributed dictionary/CLI/browser checks and
  [comparison](prefinal-copula-evaluation.json). Bare 던/더라는 omission,
  wider prefinal-ending licenses and contextual senses remain open. The report
  records the then-existing 더 + 다 attachment problem; COV-017r now rejects
  that path across lexical and represented-copula classes. See [scope](rules.md#modal-and-retrospective-copula-omission-cov-020g).

- [x] **COV-020h — Omitted copula in attached questions.** 뭔지/뭔가
  recover 뭐 + 이다 + 은지/은가; 뭘까 recovers 뭐 + 이다 + 을까.
  Six forms cover 은지/은가/은가요/을까/을까요/을지 after vowel-final
  nominals, including 누구/어디/언제/얼마/무어 and ordinary nominal bases.
  Existing 거/것 alternatives, full spellings, nominalizations, particles and
  licensed auxiliary composition remain. Attached ㄴ/ㄹ is required; nominal
  consonants are not repaired through verb irregulars, and the recovered 이
  cannot fabricate a lexical verb. Evidence: [48-pair full-form matrix and
  composition tests](../tests/question_copulas.rs), 95 cited ledger cases,
  dictionary/CLI/browser checks and [comparison](question-copula-evaluation.json).
  Four complete annotated sentences capture two GSD gains (뭔지/뭔가) and
  preserve two explicit KAIST copulas. The comparison accounts for all 132
  additions across 105 surfaces with no removals or changed provenance.
  One stress fingerprint adds an unverified nominal hypothesis; its prior
  history is retained and dictionary filtering is checked. The other 29 are
  unchanged. This does not expand 뭐/무어 into all longer lexical counterparts;
  that remains part of COV-018's pronoun audit. See
  [scope](rules.md#omitted-copula-in-attached-questions-cov-020h).
- [x] **COV-020i — Nominal approximation -쯤.** 번쯤 exposes 번 + 쯤;
  particles and copulas compose in 내일쯤에, 번쯤은요 and 중간쯤이었다.
  Existing 님/들/님 + 들 suffix paths can precede 쯤, including 교수님들쯤은.
  Whole 그쯤/이쯤/저쯤 lexical readings survive dictionary filtering. The known
  ㅁ boundary selects outer allomorphs even after numeric/foreign spelled bases.
  The browser labels the suffix “About / approximately” and links entry 88691.
  Thirty required and nine forbidden judgments cover the stated scope. The
  complete KAIST sentence preserves 번쯤 → 번 gold, while retaining the source
  jxc tag rather than relabeling it as proof of the dictionary's suffix role.
  No recursive 쯤 splitting, predicate nominalization/inner-particle peeling,
  semantic noun-class validation or 쯤 + 답다 derivation is claimed. Existing
  적 hypotheses before 쯤 remain unjudged; other approximation suffixes -경/-여
  need their own semantic/homonym review. These followups remain COV-020 work.
  Evidence: [rules](rules.md#nominal-approximation-suffix-cov-020i),
  [tests](../tests/approximation.rs), stable `approximation-*` ledger cases,
  `approximation_suffix_preserves_dictionary_and_cli_parity`, browser source
  selections, and [source/candidate review](approximation-evaluation.json).

- [ ] **COV-021 — Remaining 하다 shortening.** **Partial: Article 39 잖/찮
  forms are covered by COV-021a; COV-021b adds shortened 기 nominalizations.** Remaining: Article 40 complex coda pronunciation
  and ending/particle families. Do not extend stop/sonorant rules without
  pronunciation evidence.
- [x] **COV-021a — Article 39 negative contractions.** 잖 recovers 지 + 않다;
  찮 restores 하지 + 않다. The left predicate uses existing spelling and
  prefinal recovery; the negative auxiliary retains its own inflection.
  Examples include 적잖은, 만만찮았다, and 먹고싶잖다. Original lexical
  readings remain, including 적잖다, 만만찮다, and 괜찮다. Recovery does not
  establish lexical membership or semantic equivalence to a lexicalized word.
  Evidence: [path/boundary tests](../tests/negative_contractions.rs), eight
  contraction/lexical ledger cases, the complete KAIST MH2_0159-s86 sentence,
  dictionary/CLI parity and browser reading selectors. All current fingerprints
  remain unchanged. See [scope and sources](rules.md#negative-contractions-and-confirmation-cov-021a017f)
  and [development comparison](negative-contraction-evaluation.json).
- [x] **COV-021b — Shortened 하다 before 기 nominalizations.** 강구키 and
  조성키로 recover 강구하다 and 조성하다. Stop-final 생각기에 recovers
  생각하다 through deletion rather than aspiration. The eight existing 기
  bundles retain full-form parity, ordinary nominal particles/copulas, and
  licensed auxiliary connectors, including 돌변키도했다. Wrong coda classes,
  unknown-script bases and standalone 키 do not gain this restoration.
  Evidence: [boundary/composition tests](../tests/hada.rs), eight `hada-ki-*`
  ledger cases, two complete annotated sentences, dictionary/CLI parity, and
  browser normalization/alternative/source-link checks. The
  [evaluation](hada-ki-evaluation.json) records two supported development
  recoveries and a separate incidental match to GSD's erroneous predicate
  annotation of the place name 이시가키와. No prior candidates, gold groups,
  component recoveries or stress fingerprints are lost. See
  [scope and sources](rules.md#shortened-hada-nominalizations-cov-021b).
- [ ] **COV-022 — Remaining adverbial and nominal derivations.** Review -이/-히
  lexical classes and nominal -이 independently. **Partial: COV-022a adds
  source-listed predicate adverbs, including 가까이; COV-022b adds finite adverb
  and repeated nominal bases plus shortened 익히/특히.** Remaining: other lexical
  classes, opaque roots (including 천천히/분연히), subdivision of nonlexical
  repeated bases, suffix/auxiliary interactions, and nominal -이. Keep lexical readings and causative/noun homonyms; historical
  달리/빨리 do not license a general 르 inflection rule.
- [x] **COV-022a — Source-listed predicate adverbs.** Six explicit ㅂ-stem
  recoveries include 가까이 → 가깝다 and 가벼이 → 가볍다. 헛되이 and 적잖이
  preserve their adjective stems. A [recorded inventory](adverb-inventory.json)
  licenses 57 이/히 roots and related 하다 lookup lemmas, without claiming
  that 하 is present in the surface derivation: 조용히 displays 조용 + 히 and
  links 조용하다. Whole lexical adverbs remain preferred/selectable; particle
  licenses stay separate from noun case marking and causative/passive suffixes.
  Evidence: expanded [adverb tests](../tests/adverbs.rs), eight
  `adverb-expansion-*` ledger cases, four complete KAIST sentences,
  dictionary/CLI parity, browser root/suffix/source-link tests, and
  [development comparison](adverb-expansion-evaluation.json). All current
  snapshots remain unchanged. See [scope](rules.md#additional-predicate-adverbs-cov-022a).

- [x] **COV-022b — Adverb/repeated nominal roots and shortened adverbs.**
  A [33-form inventory](adverb-root-inventory.json) adds eight adverb bases,
  twenty-one repeated nominal bases, shortened 익히/특히, and their full forms.
  The new paths retain base roles and adverbial suffixes, preserve whole lexical
  readings and homonymous particle paths, and compose with the existing
  adverb-compatible particles. Repeated bases remain single components; fourteen
  base/role dictionary gaps are explicit. The source-backed shortening uses
  익숙하다/특별하다 for lookup rather than inventing 익하다/특하다.
  Evidence: [role/boundary tests](../tests/adverb_roots.rs), twelve
  `adverb-root-*` ledger cases, four complete corpus sentences preserving lexical
  gold, dictionary/CLI parity, and browser suffix/source-link checks. Optional
  role constraints now distinguish homonymous paths in the ledger and retain
  unjudged alternatives. [Evaluation](adverb-root-evaluation.json) records all
  additions for 55 surfaces, unchanged development recall, and all thirty
  unchanged stress fingerprints. See [scope](rules.md#adverb-and-repeated-nominal-bases-shortened-adverbs-cov-022b).

### P3: dictionary and representation boundaries

- [x] **COV-014 — Names, unknown words, numbers, and foreign letters.**
  **Implemented within the existing unbroken-word tokenization scope.** ABC는
  and 3은 preserve their spelled bases with explicit pronunciation conditions
  in rule provenance. Particle allomorphs distinguish vowel, consonant,
  non-ㄹ consonant, and vowel-or-ㄹ assumptions. Omitted/contracted copulas
  also report their vowel condition, separately from later auxiliary contractions.
  A Hangul boundary stays known, including suffixes and units in ABC들로 and
  2026년은. Original-word candidates, unknown-name spellings, source offsets,
  and dictionary-only semantics remain: a rule cannot create a dictionary entry.
  The browser displays pronunciation conditions and exports them with each
  candidate. Tests cover Unicode/NFD, chain violations, source-backed judgments,
  39 new annotated groups, dictionary/CLI parity, and browser alternatives.
  [Scope and sources](rules.md#foreign-nominals-and-pronunciation-conditions-cov-014),
  [tests](../tests/foreign_nominals.rs), and [evaluation](foreign-nominal-evaluation.json).
  Punctuation-bearing names, decimals, and formatted numbers remain split at
  punctuation under the existing [release boundary](../README.md#boundaries-and-licensing);
  this is now covered by exact streaming/offset tests, not presented as recovered
  whole-name/number segmentation. Transliteration, choosing a numeral reading,
  and named-entity recognition are not inferred by these conditional hypotheses.
  Broader copula attachment constraints remain COV-020.
- [x] **COV-015 — Grammar-label and presentation coverage.** **Implemented
  for all 315 currently emitted canonical grammar forms.** The initial catalog
  adds 140 missing labels with source IDs, headwords, and grammatical kinds.
  Reviewed expression entries and bundled/component mappings resolve without
  a general unclassified-POS fallback. Hover notes distinguish bundles,
  contractions, and joined representations of spaced dictionary expressions.
  Table-inventory tests detect new unlabeled forms; offline source tests validate
  all mappings and reject wrong kinds/IDs/headwords/POS for exceptions. Browser
  regressions cover ten representative labels, source panes, normalized order,
  and unchanged CLI candidates. Labels describe common functions, not contextual
  senses; independent linguistic review remains in the completion review.
  Evidence: [label data](../web/src/grammar-labels.json),
  [inventory test](../src/grammar.rs), [source tests](../src/bin/klem-web/grammar_labels.rs),
  [audit](grammar-label-evaluation.json),
  [source notice](../web/public/Grammar-labels-LICENSE.txt), and
  [web API/display contract](web.md).

## Definition of done for each open item

Copy this checklist into the implementation notes for an item. A fix to one
example does not close a broader family unless the family scope is narrowed
explicitly and remaining cases get their own IDs.

- [ ] State the supported forms, attachment conditions, and remaining exclusions;
  identify primary-source evidence. Record unresolved linguistic judgments.
- [ ] Add stable case/judgment IDs to the
  [candidate ledger](../tests/fixtures/validity.json) where supported, plus tests
  for exact lemma groups, morpheme order/kinds, and rule provenance as relevant.
- [ ] Cover positive paths, boundary violations, ambiguity preservation, and
  interactions with neighboring rules. Forbidden judgments target a specific
  analysis; they must not reject all readings of an ambiguous surface.
- [ ] Verify dictionary-backed behavior using attributed offline fixtures.
  Confirm that headword presence, POS compatibility, and sense choice remain
  distinguishable. Preserve the unfiltered exhaustive candidate API.
- [ ] Verify CLI/library parity and ordered display/export. For a new grammar
  kind or label, include a browser regression and inspect contraction handling.
- [ ] Pass existing candidate, dictionary, and stress regressions. Compare all
  available frozen corpus cases without overwriting the baseline being checked.
  Review changed output fingerprints individually; never regenerate them just
  to make a failure pass.
- [ ] Run the relevant [verification commands](#verification), update this item's
  status with test names/case IDs, and document any remaining review work.

## Completion review

- [ ] Close or explicitly defer each open item with a reason and bounded scope.
- [ ] Finish COV-013's inventory audit; make newly discovered gaps visible here.
- [ ] Review remaining corpus misses and the candidate ledger's unjudged queue.
  Independent Korean-language review is still pending; test success is not a
  linguistic precision estimate.
- [ ] Check representative passages separately from repeatedly used regression
  corpora, including dictionary misses and reader-visible breakdown quality.
- [ ] Publish the supported scope and unresolved limits, alongside recall,
  candidate ambiguity, dictionary coverage, and performance evidence. Do not
  describe the tool as complete for all Korean.

Historical/dialectal coverage, spelling correction, whitespace repair, arbitrary
compound segmentation, exhaustive derivational morphology, contextual ranking,
sentence parsing, and EPUB extraction remain **deferred** under the
[current release boundaries](../README.md#boundaries-and-licensing).
COV-010/012 track bounded extensions, not a commitment to exhaustive derivation.

## Verification

Run checks appropriate to the change; a documentation-only tracker edit does not
require rebuilding the application. Existing offline fixtures require no data
downloads. Full corpus checks require the already downloaded data/baselines;
browser checks require Chromium. See [evaluation](evaluation.md) and
[web setup](web.md#tests) for prerequisites and details.

```sh
python3 -m unittest discover -s tools -p 'test_review_inventory.py'
python3 tools/review_inventory.py --verify
cargo test --locked --offline --features web
cargo clippy --locked --offline --all-targets --features web -- -D warnings
cargo fmt --all -- --check
cargo test --locked --offline --features web --test corpus pinned_full_corpus_regressions -- --ignored
cargo build --locked --offline --features web
npm run build --prefix web
CHROMIUM_PATH=/path/to/chromium npm test --prefix web
nix flake check
nix build .#web
```

To reproduce an individual dictionary-filtered miss:

```sh
cargo run --locked --offline -- word 저도요
cargo run --locked --offline -- word 저도요 --dictionary data/dictionaries/krdict/krdict.db --dict-only
```

Record the input, intended path, actual path(s), dictionary fingerprint, source,
and relevant tracker ID. An empty filtered result can reflect missing grammar
or missing vocabulary; a nonempty result can still omit the intended analysis.
