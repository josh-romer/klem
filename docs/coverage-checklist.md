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

P1 and the bounded COV-010/011/012/016/017a/017b/017c batches are implemented.
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
Further ending licenses, other pronoun contractions, and particles inside joined
auxiliary chains (e.g. 먹어들봐요) remain in COV-013. Independent linguistic
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
  Complex codas, other ending families, and 잖/찮 contractions remain COV-013
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
  **Partial: initial inventory and development-miss clustering complete.**
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
  Audit further suffix combinations/adjective ending licenses, and direct
  nominalization + copula without an intervening particle (e.g. 학생다움이다).
  The tested 학생다움만이다 path already composes through the particle rule.
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
- [ ] **COV-017 — Further ending families.** **Partial: COV-017a/b/c implemented.**
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
- [ ] **COV-018 — Further particle attachments and pronoun contractions.**
  Review post-ending 만 (있습니다만), 는/도 after connective endings, chains
  such as 어디까지나/이제부터라도, quotation-particle 라고 versus copula analyses,
  and pronouns outside the existing finite paradigms. Preserve homonym-specific
  dictionary labels; the current nominal 만 label cannot describe every use.
  Include quoted clauses marked as nominals: KAIST MH2_0169-s444/3 살겠다가
  is annotated 살 + 겠 + 다 + 가 (subject particle), not a -다가 example.
- [ ] **COV-019 — Auxiliary inventory and internal particles.** Review
  나가다/나다, 계시다, adnominal auxiliaries such as 만하다/듯하다, and the other
  unreviewed auxiliary entries with connector-specific constraints. Include
  particles inside joined chains (먹어들봐요). Distinguish independent compounds
  and lexical readings; preserve the packed acyclic search and stress bounds.
- [ ] **COV-020 — Derived nominal/copula composition and attachment classes.**
  Review direct nominalization + copula (학생다움이다), additional suffix order,
  and adjective ending licenses. 학생다움만이다 already composes; this does not
  establish the direct path or arbitrary recursive derivation.
- [ ] **COV-021 — Remaining 하다 shortening.** Review Article 39 잖/찮 forms,
  Article 40 complex coda pronunciation, and remaining ending/particle families
  separately. Do not extend stop/sonorant rules without pronunciation evidence.
- [ ] **COV-022 — Remaining adverbial and nominal derivations.** Review -이/-히
  lexical classes, 가까이-type recovery, and nominal -이 independently. Keep
  lexical adverb readings and causative/noun homonyms; historical 달리/빨리 do
  not license a general 르 inflection rule.

### P3: dictionary and representation boundaries

- [ ] **COV-014 — Names, unknown words, numbers, and foreign letters.**
  **Partial.** ABC는 and 3은 do not recover their intended particle attachment
  in the audit. Separate pronunciation uncertainty, tokenizer boundaries, and
  absent dictionary headwords: fixing a rule cannot create a missing dictionary
  entry. Define pronunciation inputs or explicit alternative hypotheses before
  relaxing consonant/vowel conditions. Keep unknown tokens visible and report
  uncertainty. Any new filter mode or fallback must preserve the documented
  semantics of `--dict-only`. See [release boundaries](../README.md#boundaries-and-licensing)
  and [dictionary integration](dictionary.md).
- [ ] **COV-015 — Grammar-label and presentation coverage.** **Partial.**
  Common grammar labels exist; unmapped forms fall back to generic role labels.
  Inventory missing labels, attach source IDs, and test kind-sensitive lookup
  and ordering whenever a morphology family is added. Continue separating
  normalized expansion, independent word combinations, and dictionary senses.
  Evidence: [label data](../web/src/breakdown.ts),
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
