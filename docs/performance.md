# Performance

## Full novel, current engine

Measured 2026-09-26 on an AMD Ryzen AI MAX+ 395, Linux x86-64, Rust 1.98.1,
release thin LTO. Input: all seven pinned Wikisource sections of 이광수's
[*무정*](https://ko.wikisource.org/wiki/무정), chapters 1–126, **786,078 UTF-8 bytes**.
This is one complete historical novel, not repeated excerpts or a modern-fiction
sample. [Provenance and extraction](../data/README.md#novel-benchmark-input) and
[raw runs/source hashes](performance-optimized.json) make the measurement reproducible.
The [earlier report](performance-novel.json) preserves measurements before the
auxiliary-chart optimization.

Five fresh processes per mode; filesystem warm, each session cache initially
empty. Times are medians; RSS is the largest process peak across the five runs.

| Workload | Cache budget | Seconds | MiB/s | Peak RSS |
| --- | ---: | ---: | ---: | ---: |
| Streaming library | 0 | 0.431 | 1.74 | 2.93 MiB |
| Streaming library | 8 MiB | 0.237 | 3.16 | 14.32 MiB |
| Library plus JSONL serialization to counting sink | 0 | 0.464 | 1.62 | 2.93 MiB |
| Library plus JSONL serialization to counting sink | 8 MiB | 0.283 | 2.65 | 14.29 MiB |
| Actual CLI, JSONL to `/dev/null` | 8 MiB | 0.31 | 2.42 | 14.25 MiB |

There were 179,112 lossless records and 359,669 analyses. The largest word token
was 45 bytes; the most ambiguous had 23 analyses. JSONL output was **72,797,041
bytes** (about 69.4 MiB), so downstream storage/output can cost much more than
reading the source text. Cached and uncached CLI output hashes matched, and
concatenating output surfaces reproduced the exact input SHA-256.

`benchmark_stream` hashes the input before timing, then streams it without loading
the whole book. Its process RSS therefore excludes a retained full-input buffer.
Serialization uses a counting sink rather than disk I/O; the separate GNU Time
measurement includes CLI startup, buffering and writes to `/dev/null`. These
measurements are workload-specific, not an accuracy evaluation or speed guarantee.

### Repeated-token regression and fix

The original implementation retained fully expanded auxiliary chains for every
prefix, then cloned them on each join. The new chart stores individual predicate
recoveries and links to shorter prefixes. Iterative traversal expands only final
paths, unions rule provenance before output, and filters impossible terminal
endings before exploring nominalized predicates.

Caching is disabled in these synthetic JSON-serialization runs. Before values
are the original individual observations; after times are medians of five fresh
processes, and after RSS is the largest peak across those five.

| One token | Before seconds | After seconds | Before peak RSS | After peak RSS | Analyses |
| --- | ---: | ---: | ---: | ---: | ---: |
| `가` repeated 64 times | 0.069 | 0.0011 | 29.6 MiB | 3.56 MiB | 129 |
| `가` repeated 256 times | 3.53 | 0.0139 | 1,594.5 MiB | 12.16 MiB | 513 |
| `가` repeated 1,024 times | Exceeded 20 seconds | 0.274 | Not measured | 142.35 MiB | 2,049 |

The last case emits 74,677,498 JSONL bytes (about 71.2 MiB). Its fully materialized
public results still contain many long lemma/morpheme sequences: the fix removes
intermediate duplication, not the cost of the requested exhaustive output. No
candidate/depth/token cutoff was added. A bounded session cache still does not
bound memory for arbitrarily long or ambiguous tokens.

The output is byte-identical to the old engine for the full novel, a stream of
32,799 distinct corpus forms, and the smaller repeated-token cases. Corpus and
candidate-validity regressions also pass. Tests pin full JSON fingerprints for
30 representative words plus the 64-syllable case, verify complete auxiliary
chains through 256 syllables, and on Linux run the 1,024-syllable CLI case under
a **256 MiB virtual-memory limit** and 30-second deadline. The old implementation
fails that memory allowance. These are test controls, not production limits.

The earlier raw report also retains smaller chains built as 먹어 + repeated 봐 + 요
(4, 8 and 16 auxiliaries); those observations predate the optimization.

### Reproduce the novel run

```sh
bash tools/fetch-novel.sh
bash tools/fetch-novel.sh --verify
cargo build --release --locked --bin klem --example benchmark_stream
for mode in library json; do
  for budget in 0 8388608; do
    for run in 1 2 3 4 5; do
      ./target/release/examples/benchmark_stream data/books/mujeong.txt "$budget" "$mode"
    done
  done
done
# Use the GNU Time executable (not the shell keyword):
/path/to/time -f 'seconds=%e peak_rss_kib=%M' \
  ./target/release/klem text data/books/mujeong.txt > /dev/null
```

The downloader needs Bash, curl, jq and sha256sum and fetches only pinned
revisions. Ordinary tests/Nix builds stay offline. To reproduce the small stress
input, write a single line of 64 copies of 가, or 먹어 followed by four copies
of 봐 and 요, and pass that file to `benchmark_stream` with `0 json`.
Run `cargo test --locked --test stress` for the regression checks. The new raw
stress runs used a 256 MiB virtual-memory limit and 10-second deadline per run.

## Earlier corpus/synthetic measurements

Measured 2026-09-25 on an AMD Ryzen AI MAX+ 395, Linux x86-64, Rust 1.98.1,
release build with thin LTO. The engine uses one thread. These are local samples,
not portable latency guarantees. Raw measurements are in [performance.json](performance.json).
These measurements predate the later correctness audits and are retained as
historical observations; use the novel results above for the current engine.

| Workload | Measurement |
| --- | ---: |
| First word lookup, including rule-index initialization | 113 µs |
| Six representative words, uncached, mean over 1,000 iterations each | 2.9–28.1 µs |
| Repeated cached word lookup (shared result retrieval only) | about 0.02 µs |
| Varied corpus text, 1,193,085 bytes, cache disabled | 0.65 s |
| Same text with 8 MiB cache budget | 0.50 s / 2.28 MiB/s |
| CLI with JSON serialization, same text, output discarded | 0.60 s |
| Peak benchmark-process RSS on Linux | 14.8 MiB |

The varied text is the KAIST development sentence text repeated five times, not
an independently sampled novel. The cache fills and evicts entries on this input.
API throughput excludes JSON serialization; the separate CLI timing includes it.
Peak RSS includes the benchmark harness, its synthetic input, and all earlier
measurements; it is not a library memory ceiling.

The harness also measures a single sentence repeated to approximately 1 MiB.
Its cached throughput is much higher because nearly every token is a cache hit;
that synthetic result should not be used to predict general book throughput.

## Reproduce

```sh
bash tools/fetch-corpora.sh
cargo build --release --locked --examples --bin klem
awk '/^# text =/ {print substr($0,10)}' \
  data/corpora/kaist/ko_kaist-ud-dev.conllu > /tmp/klem-dev-text.txt
for pass in 1 2 3 4 5; do cat /tmp/klem-dev-text.txt; done > /tmp/klem-novel-sized.txt
./target/release/examples/benchmark /tmp/klem-novel-sized.txt
time ./target/release/klem text /tmp/klem-novel-sized.txt > /dev/null
```

Omit the path to run only the microbenchmarks and synthetic text. Supply your own
plain-text book to measure its actual vocabulary distribution. RSS reporting uses
Linux `/proc/self/status`; other platforms report `null` for that field.

Memory is bounded by the configured cache's charged weight plus bookkeeping,
the current token, and all analyses for that token. Full input and output are
streamed. Because results are exhaustive within the grammar, unusually ambiguous
tokens may have expensive output; there is no silent truncation to force a bound.
