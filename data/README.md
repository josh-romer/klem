# Evaluation data

## Korean Basic Dictionary

`krdict.lock.json` pins the official September 2026 JSON archive and all 11 LMF
JSON members by SHA-256. Run `bash tools/fetch-krdict.sh` to download explicitly
into ignored `dictionaries/krdict/`; `--verify` checks local extracted JSON.
Downloads and generated SQLite databases are excluded from Cargo/Nix sources.
The importer adds a manifest with source hashes and a snapshot fingerprint.

Attribution: National Institute of Korean Language (국립국어원), Korean Basic
Dictionary (한국어기초사전). Text retains **CC BY-SA 2.0 KR** terms, separately from
the code: [source policy](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo),
[license](https://creativecommons.org/licenses/by-sa/2.0/kr/).
The database is an adaptation: selected text fields, decoded XML entities, NFC
lookup keys and derived identifiers for idiom/proverb subentries. Multimedia are
omitted and have separate source terms. Keep these notices when sharing data.
See [usage and coverage](../docs/dictionary.md).

## Annotated corpora

`corpora.lock` pins each file to a full Git revision and SHA-256 checksum. UD 2.15
is deliberately pinned instead of following a moving latest release. Ignored
`corpora/` contains full datasets, READMEs, and licenses after explicit download.

`baselines/*.jsonl` contains versioned summary reports followed by every converted
token's case ID, surface, expected lemmas, and recovery outcome. Input SHA-256
fingerprints and per-case comparisons prevent gains from hiding regressions.
See [format and review workflow](../docs/evaluation.md#individual-case-regression-tracking).
These are corpus-derived evaluation artifacts, not runtime dictionaries. They retain
CC BY-SA 4.0 attribution. Do not tune rules against held-out test reports.

* [KAIST revision 888f855](https://github.com/UniversalDependencies/UD_Korean-Kaist/tree/888f855c7bcf1e39291246744f4e98f6bda6742e): CC BY-SA 4.0; morphology converted from manual annotations; news, fiction, academic writing.
* [GSD revision 60ffc4f](https://github.com/UniversalDependencies/UD_Korean-GSD/tree/60ffc4f2f0cbf0bf816f0d44a7339512f5ce9c25): annotations CC BY-SA 4.0; automatic morphology; news/blogs. Its README separately discusses rights in source text.

Citation: Jayeol Chun, Na-Rae Han, Jena D. Hwang, Jinho D. Choi (2018),
*Building Universal Dependency Treebanks in Korean*, LREC. Credit also belongs to
KAIST contributors including Key-Sun Choi, and GSD contributors Ryan McDonald,
Joakim Nivre, Daniel Zeman, and colleagues. For GSD also cite McDonald et al.
(2013), *Universal Dependency Annotation for Multilingual Parsing*, ACL.
Downloaded READMEs retain full upstream notices and contributor lists.

[License terms](https://creativecommons.org/licenses/by-sa/4.0/legalcode).
[Offline excerpt provenance](../tests/fixtures/README.md).

## Novel benchmark input

`novel.lock.json` pins all seven Wikisource sections of 이광수's *무정*, covering
chapters 1–126, to revision IDs and raw-content SHA-256 hashes. The final extracted
text has its own hash. `bash tools/fetch-novel.sh` downloads it explicitly into
ignored `books/mujeong.txt`; `--verify` checks the final text without networking.
No build or test downloads the novel, and book text is excluded from packaging.

Source and attribution: [무정, Korean Wikisource](https://ko.wikisource.org/wiki/무정),
이광수 and the Wikisource transcription contributors. Each section's revision
history is accessible at `https://ko.wikisource.org/w/index.php?oldid=REVISION`
using the IDs in the lock file. The source marks the original work as public
domain; the site's transcription/contribution terms are
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Preserve these notices and revision links when redistributing the transcription.

Extraction removes the pinned sections' metadata templates and surrounding
whitespace, joins them in chapter order with one newline, and keeps the prose's
spelling and internal spacing. The extractor rejects unexpected remaining wiki
markup and verifies the final checksum. It is specific to these revisions, not
a general Wikisource or EPUB importer. This historical prose is a performance
workload, not annotated gold or a representative sample of contemporary novels.
