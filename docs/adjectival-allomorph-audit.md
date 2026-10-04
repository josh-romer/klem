# Adjectival-question canonical allomorph audit

`COV-017bu` corrects the canonical analysis of adjective questions. For example,
`아프냐고` currently emits both `아프다 + 냐고` and `아프다 + 으냐고`.
The second path is unsupported by the attachment note for the distinct
`-으냐고` entry. `기냐고` has the same problem with underlying `길다`.
The sentence and its general `-냐고` reading must survive the correction.

This is a source preflight. The parser and existing judgments have not yet been
changed. The checklist item remains open; these authored proposals are not an
independently reviewed Korean precision benchmark.

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
while 53 of 180 forbidden paths are currently emitted. It tracks the precise
analysis and dictionary reading for every matching path in each filter.
These are candidate-boundary judgments; native observations and contextual
choices remain unjudged. The full source freeze contains 1,703 native
occurrences, 1,399 words, 289 annotated tokens and 1,700 complete native owners.

## Work remaining

- Check each flagged path's ordered owner and publish explicit original-to-
  replacement judgments, including the erroneous citation.
- Apply the canonical boundary to the audited families while preserving the
  general `냐` analyses and irregular closed-stem recovery. Keep source-specific
  lexical/POS exceptions separate from the coda boundary.
- Exercise the matrix with NFC/NFD, cache settings, all three CLI filters and
  the native dictionary adapter. Track each intentional path removal; preserve
  every unrelated prior path and assessment.
- Replay the eight candidate/novel streams and four held-out corpus evaluations.
  Any loss must have an individual source-backed explanation; do not update a
  baseline merely to make a check pass.
- Update frozen-fixture replay tests through explicit correction overlays,
  then validate the packaged CLI, browser and Nix checks before closing this
  bounded item. Broader spelling, contextual selection and independent review
  remain separate open checklist work.

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
```

Add `--dictionary` to reproduce the full native/corpus scan and raw-export hashes.
Add both `--dictionary` and `--cli-before` to reproduce all three frozen CLI
streams exactly. The preflight verifier does not certify parser completion.
The flake's `inventory-review` check runs this offline verifier.
