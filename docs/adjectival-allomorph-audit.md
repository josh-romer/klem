# Adjectival-question canonical allomorph audit

`COV-017bu` corrects the canonical analysis of adjective questions. For example,
`아프냐고` currently emits both `아프다 + 냐고` and `아프다 + 으냐고`.
The second path is unsupported by the attachment note for the distinct
`-으냐고` entry. `기냐고` has the same problem with underlying `길다`.
The sentence and its general `-냐고` reading must survive the correction.

The parser now applies this boundary across all 18 families. The original source
preflight remains immutable, while explicit overlays correct the central and
dictionary-policy judgments. The checklist item remains open for broader stream,
corpus and packaged validation; these authored judgments are not an independently
reviewed Korean precision benchmark.

## Sources and boundaries

The [immutable source freeze](adjectival-allomorph-source-preflight.json.gz)
preserves complete native entries, all example groups, sense notes and
translations. It includes every native homonym for these 18 canonical families
and their distinct general `냐` counterparts:

| Canonical component | KRDict entries |
| ------------------- | -------------- |
| 으냐                | 76235          |
| 으냐고              | 79258, 87444   |
| 으냐는              | 86032          |
| 으냐며              | 86921          |
| 으냐면서            | 86119          |
| 으냐니              | 87425, 92543   |
| 으냔                | 85664          |
| 으냔다              | 85925          |
| 으냬                | 89683          |
| 으냐지만            | 85643          |
| 으냐니까            | 80820          |
| 으냐느니            | 88987          |
| 으냐면              | 80180          |
| 으냐던데            | 86361          |
| 으냐는구나          | 88947          |
| 으냐는군            | 89638          |
| 으냐더군            | 89661          |
| 으냐더군요          | 89826          |

The dictionary notes describe attachment to adjectives with a final consonant
other than ㄹ. Entry 76235 also says `주로`; that qualifier is preserved.
[NIKL's description of the question endings](https://m.korean.go.kr/nkview/nknews/200107/36_7.html)
explicitly distinguishes non-ㄹ closed stems from open and ㄹ stems.
[Its later answer](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=310957)
also permits the general colloquial `-냐` after predicates and copulas.

Surface shape alone cannot decide the boundary.
[NIKL analyzes `어떠냐`](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=5987&mn_id=217&pageIndex=1)
as underlying `어떻다` plus `-으냐` with ㅎ irregular conjugation.
The supplemented proposed matrix therefore preserves ㅂ, ㅎ and ㅅ irregular closed stems,
as well as ordinary closed stems, closed auxiliaries and adjective-forming
suffixes. It separately tracks open stems, ㄹ stems, copulas, open auxiliary
owners and prefinal boundaries.

## Original observations

The broad native scan includes every Hangul word containing `냐`, `냔` or `냬`
in dictionary example text. This intentionally includes general questions,
irregular spellings, conflicting native uses and unrelated lexical matches.
Each occurrence retains its whole example group, entry, sense, text index,
character span and UTF-8 byte span. These are observations, not gold analyses.

The freeze scans all six local KAIST/GSD train, development and test files.
Matched rows retain all ten original CoNLL-U fields and their complete sentence.
Train observations are distinct from the four held-out dev/test evaluation
streams; a later comparison must preserve each existing gold/component match.

The pinned CLI is the package from commit `886e027`. Every distinct observed or
proposed word is frozen in all-candidate, dictionary-headword and dictionary-
compatible modes, with complete ordered analyses, dictionary assessments,
text offsets and spacing records. The English LMF adapter retains all examples
and notes for every imported native owner. The compressed source retains all
translation languages; the LMF adapter retains English for offline Rust tests.

The entire original central validity ledger is archived. The 26 flagged
required judgments retain their original ID, components, source URL and reason.
In particular, the original `기냔다` selector cites entry 85921, whereas the
canonical `-으냔다` owner is 85925. Correcting that citation must be explicit.
The flags are a review queue: an open nominal before suffix `답다`, for example,
is not evidence that the actual adjective owner is open.

The original authored draft also incorrectly proposed regular `아이답으냐`
surfaces as required derived paths. The
[append-only derived supplement](../tests/fixtures/adjectival-allomorph-derived-supplement.json)
archives all 18 original proposals, explicitly changes them to forbidden and
adds all 18 `아이다우냐`-family recoveries. It preserves the complete native
suffix entry 92145 and its English LMF adapter, plus all three pinned CLI
streams for the added words. [NIKL's explanation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=90&pageIndex=1&qna_seq=329643)
confirms ㅂ irregular conjugation of adjectives formed with `-답다`.
The original source freeze and original matrix have not been rewritten.

The [frozen evaluation](adjectival-allomorph-preflight-evaluation.json) contains
396 effective structural proposals: all 216 required paths already exist,
while the original parser emitted 53 of 180 forbidden paths. It tracks the precise
analysis and dictionary reading for every matching path in each filter.
These are candidate-boundary judgments; native observations and contextual
choices remain unjudged. The full source freeze contains 1,703 native
occurrences, 1,399 words, 289 annotated tokens and 1,700 complete native owners.

## Implemented correction

The [central corrections](../tests/fixtures/adjectival-allomorph-corrections.json)
retain all 26 original cases and publish explicit replacements with their ordered
owner, coda and canonical source. The `기냔다` citation is explicitly changed
from 85921 to 85925. All 396 supplemented matrix cases are in the central ledger.

The [policy preflight](adjectival-allomorph-policy-preflight.json.gz) also archives
the entire original dictionary-attachment ledger and all three pinned pre-change
CLI views of eight additional incorrect required policy paths. Its
[policy corrections](../tests/fixtures/adjectival-allomorph-policy-corrections.json)
reject those aliases explicitly. A ninth, already-forbidden `기다리냐느니` policy
path is now rejected during generation. Every other dictionary conflict must
still be generated before the optional filter is applied.

The [314-word checkpoint](adjectival-allomorph-checkpoint.json.gz) tracks 703
individual raw removals, 93 in the headword-filtered view and 69 in the compatible
view. Its 5,138 retained candidate occurrences keep their original order,
dictionary readings and referenced native lemma fields. Each removal has a
stable ID, original candidate and reading, canonical sources and original spans.
The checkpoint binds the exact
[ordered-owner verifier](../tools/adjectival_allomorph.rs) and
[regression tests](../tests/adjectival_allomorphs.rs) by hash. This is the selected
matrix/old-ledger/derived cohort; broader streams and spacing are outside its scope.

The tests cover NFC/NFD, caches 0/1/4096, three CLI filters, all 216 required and
180 forbidden matrix paths, and every prior cohort path and assessment. Older
fixture files remain unchanged. Their replay tests apply explicit owner or case
overlays. Caller-constructed invalid copula analyses still exercise the existing
dictionary API's class checks, alongside assertions that the parser rejects them.
Independent POS-profile and homonym tests now use the valid verbal `느냐`
boundary to prove the reviewed adjective/native verb distinction; they no longer
depend on an invalid open-stem `으냐` alias.

The [complete stream comparison](adjectival-allomorph-observations.json.gz)
replays all 1,128,312 records in eight candidate/novel modes and all three frozen
1,399-word diagnostic streams against the pinned pre-change CLI. It tracks 3,806
distinct removals and 29,691 retained candidate occurrences in changed records.
Each removal keeps its original reading, context, stable ID, source entries and
Rust-derived ordered owner. All other candidate, assessment and native fields
are preserved. Spacing option identities and order remain unchanged; 33
diagnostic spacing records lose only unsupported aliases within their segments.
The report retains 282 complete native entries, including five
[additional sources](../tests/fixtures/adjectival-allomorph-additional-native.json).
[Full-stream regressions](../tests/adjectival_allomorph_streams.rs) replay every
tracked removal across 1,642 distinct words.

The [four complete held-out reports](adjectival-allomorph-corpora.json.gz) retain
all 66,570 original ordered gold rows, including misses, and all recovered
component sets. Only mean candidate counts decrease. The complete original and
replacement JSONL is archived, rather than preserving summary totals alone.
The [offline verifier](../tools/adjectival_allomorph_corpora.py) checks every row
and binds each original report to the previous corpus audit.

The [packaged HTTP checks](adjectival-allomorph-packaged-runtime.json) compare
all 2,050 cohort words with the CLI in NFC/NFD, check all 860 encoded candidate
judgments, verify every API component order against Rust, and reproduce all
1,706 complete native entry responses. The
[browser run](adjectival-allomorph-packaged-browser.json) checks 60 exports in
both encodings and all three filters, plus nine selected diagrams and their
dictionary source links. Mobile layout was inspected without horizontal overflow.
The local preview runs the tested package. The full x86_64-linux Nix check
passes 861 Rust tests with zero failures and one downloaded-corpus test ignored.
The final fixture build's CLI/web binaries are byte-identical to the runtime
package. COV-017bu's bounded canonical-allomorph audit is complete; native final
ending 79258 has its own scoped disposition in the inventory ledger.

## Work remaining

- Broader spelling, contextual selection, prefinal/outer-attachment combinations
  and independent review remain separate open checklist work.

## Reproduction

The source files are created once and are not regenerated after a parser change:

```sh
python3 tools/adjectival_allomorph_audit.py \
  --cli-before /path/to/pinned/886e027/klem \
  --dictionary data/dictionaries/krdict/krdict.db
```

The committed preflight is verifiable without the downloaded export:

```sh
python3 tools/adjectival_allomorph_audit.py --verify
python3 tools/adjectival_allomorph_corpora.py --verify
python3 tools/adjectival_allomorph_compare.py --verify
python3 tools/adjectival_allomorph_runtime.py --verify
python3 tools/adjectival_allomorph_browser.py --verify
```

Add `--dictionary` to reproduce the full native/corpus scan and raw-export hashes.
Add both `--dictionary` and `--cli-before` to reproduce all three frozen CLI
streams exactly. The preflight verifier does not certify parser completion.
The flake's `inventory-review` check runs this offline verifier.
