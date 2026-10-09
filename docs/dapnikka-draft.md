# Rhetorical and reported questions: -답니까 / -랍니까

Status: implemented on `coverage/reported-questions`; integrated package,
performance, contextual and independent review remain open.

Four ending identities (78782, 78786, 78797, 78803) and six separate reported
expression identities (86563, 86566, 86628, 86630, 80909, 85833) retain complete
original Native entries. Expression -랍니까 has separate factual and command
senses; the importer never merges these with the same-spelled endings.

Canonical paths include present-verbal -는답니까 (including attached ㄴ),
plain -답니까 for adjectives or its own immediate honorific/past/modal/어야겠
markers, factual/copular -랍니까, and command -으랍니까 with its own
allomorph and immediate honorific boundary. Source-listed retrospective -더-
and conjectural -으리- boundaries retain separate morphemes. Commands reject
adjective/copula owners and past forms; present forms reject past/modal markers.
Dictionary homonyms keep original POS and separate attachment assessments.

New paths carry `ending.question_dapnikka`. Explicit copulas preserve
nominal + 이다, including 모양이랍니까; 가랍니까 has a separate command reading.
Viewer labels cite exact ending/expression owners. A nine-entry Native label
fixture preserves all source fields used by the entry dialogs.

[Source preparation](dapnikka-source-preparation.json.gz) retains all 46
complete original groups, authored lemma proposals and earlier CLI records.
These are structural judgments, not annotated gold.
[Native closure](dapnikka-native-closure.json.gz) retains 90 complete entries
covering source owners, proposed/control headwords and all homonyms.
[The 62-case fixture](../tests/fixtures/dapnikka-validity.json) contains 55
required and seven forbidden paths. A separate
[novel case](../tests/fixtures/dapnikka-novel-validity.json) requires
말랍니까 → 말다 + 으랍니까, retaining the complete original sentence, older
ordered paths and all four Native homonyms. The shared ledger has 35,142
cases, 30,999 required and 4,159 forbidden judgments; earlier 35,079 cases and
source records remain exact.

[Runtime evidence](dapnikka-runtime.json.gz) verifies all 46 proposals in
twelve NFC/NFD × cache × dictionary-filter streams, every earlier path and
assessment, and exact import of all 90 entries.
[Browser evidence](dapnikka-browser.json.gz) retains 330 selected diagrams,
six exact CLI exports and all 90 dictionary-entry endpoints.

[Eight complete large-text streams](dapnikka-broad-retry1.json.gz) preserve
1,128,312 frames and previous candidates/order/assessments/display/spacing.
Five captures of one novel form add a command path; no spacing option is added.
Original full context and four complete Native owners remain retained and
contextually unjudged. [Complete cohort replay](dapnikka-cohorts.json.gz)
preserves 32,096 corpus and 21,406 historical surfaces without additions.
[Annotated adapter replay](dapnikka-corpora.json.gz) preserves 66,570 gold
rows and earlier outcomes, with no summary metric changes.

Portable source/cohort/broad controls pass 9/5/7 tests and are wired into the
flake. They reject lost source groups, substituted identities, changed case
requirements, missing/rehashed cohort records, lost older paths, rewritten
novel context, changed prior stream hashes and lost Native owners. Focused
Rust, browser, TypeScript/Vite and focused Clippy checks pass. The historical
ledger audit passes 38 controls, including exact earlier ledger snapshots and
coordinated fixture/ledger mutation rejection. Clippy passes with warnings denied across all integrated Rust targets. Twelve integrated tests for the
new source/boundary/novel cases and complete expanded shared ledger pass.
[Full prototype Rust](dapnikka-full-tests-retry1.json.gz) passes 1,102 tests,
with one ignored test across 238 batches including doctest. The expanded shared
ledger is separately validated; full committed integrated replay remains pending. The initial integrated ledger run rejected the
novel's repository-path source string; the corrected fixture cites the pinned
original Wikisource URL and its exact bytes remain bound by the historical audit.

The [preceding main four-check gate](declarative-dao-combined-retry3-nix.json.gz)
passed with frozen source/HEAD/index. It covers the declarative-DAO baseline;
new name/title/self-question and this ending family require their own subsequent
package and installed validation.

Remaining: full integrated Rust and Nix, installed source/browser/export,
broad/cohort/adapter binding, quiet novel timing, main integration, wider
lexical/marker/auxiliary/particle distributions and independent contextual
review. Structural compatibility does not select the novel's intended 말다 sense.
