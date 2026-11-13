# NuMAFFT benchmark tools and evidence

This directory keeps NuMAFFT benchmark tools and raw measurements. The imported optimized
implementation is fast-mafft v10, based on upstream MAFFT v7.526.
The scope is **default FFT-NS-2**, not every strategy available in MAFFT.

Read [REPORT.md](REPORT.md) for measured results and limits. [measurements.csv](measurements.csv)
has every warmup and measured run. [summary.json](summary.json) contains the summary table.
The original author's 32-thread CARC results remain in [BENCHMARKS.md](../../BENCHMARKS.md#historical-carc-measurements) and
[carc/logs](../../carc/logs); those are separate evidence, not this machine's measurements.

## Build both versions

Requirements: Git, make, a C compiler, Python 3.11 or later, and a POSIX system (Linux or macOS).
The tested compiler is Homebrew GCC 16.1.0 on arm64 macOS.

```sh
CC=/opt/homebrew/bin/gcc-16 sh bench/biocode/build.sh /absolute/path/to/new-build-directory
```

The script fetches the full repositories and checks out these exact revisions:

| Variant | Source | Commit |
|---|---|---|
| Baseline | https://gitlab.com/sysimm/mafft | `ee9799916df6a5d5103d46d54933f8eb6d28e244` (v7.526) |
| Optimized | https://github.com/yih0nk/fast-mafft | `6474c62da49ca3af73bbb7b05287bbbb4a2036e5` (v10) |

Both builds use `-O3 -ffp-contract=off -std=c99` and the same compiler. C99 also covers the
Makefile's implicit compilation rules, avoiding GCC 16's incompatible default C dialect.
No alignment source was patched for this replication. The same installation prefix is passed
when building and installing each variant; otherwise MAFFT's generated launcher may run
binaries from a different installation.

The publication repository retains the original history, authors and BSD license; bundled
extensions retain their own licenses. The optimized code and benchmark inputs are unchanged.

## Fetch data

```sh
bash bench/get_data.sh
```

This downloads the original repository's `data-v1` release and checks the recorded MD5 values.
The runner separately records SHA-256 for every input used. See [DATA.md](../DATA.md) for data
provenance and licenses. RNASim is simulated RNA; `prot2k` is simulated protein; HomFam and 16S
are biological datasets. The benchmark does not redistribute BAliBASE.

## Run the replication

From the repository root, replace `/absolute/path/to/new-build-directory` below with your build:

```sh
python3 bench/biocode/run.py \
  --baseline /absolute/path/to/new-build-directory/baseline/bin/mafft \
  --optimized /absolute/path/to/new-build-directory/optimized/bin/mafft \
  --baseline-source /absolute/path/to/new-build-directory/upstream-source \
  --optimized-source /absolute/path/to/new-build-directory/optimized-source \
  --compiler 'Homebrew GCC 16.1.0' \
  --cflags='-O3 -ffp-contract=off -std=c99' \
  --threads 4 --repetitions 3 --timeout 600 \
  --out bench/biocode/results/your-machine-4threads \
  bench/data/rnasim579.fa bench/data/rnasim2k.fa bench/data/prot2k.fa \
  bench/data/large/homfam_sdr_sub3k.fa bench/data/large/16S.T.fa
```

Repeat with `--threads 1`, a new output directory, and `rnasim579.fa` and `prot2k.fa` only to
reproduce the smaller single-thread suite. Run suites sequentially, not concurrently.
Each output directory must be new so earlier evidence cannot be overwritten silently.

The runner excludes one warmup per variant and input/thread case, then alternates order AB, BA,
AB for three measured pairs. It records wall time, CPU time, peak child RSS, exit status, full
stdout SHA-256, byte comparison, alignment dimensions and ungapped-sequence preservation.
Every invocation uses a fresh worker for memory measurement. A timeout kills that invocation's
process group. Exit code 1 means a failed or invalid run; 2 means a stdout difference was found.
Inspect such cases before quoting a speedup. Workstation scheduling and caches remain uncontrolled.

Render combined results (without rerunning MAFFT):

```sh
python3 bench/biocode/render.py --out bench/biocode \
  bench/biocode/results/your-machine-4threads \
  bench/biocode/results/your-machine-1thread
python3 -m unittest discover -s bench/biocode -p 'test_*.py' -v
```

The renderer refuses mixed builds, duplicate cases, invalid runs and output differences.
It does not hide failures or summarize only the successful subset.

## Evidence layout

Each recorded suite contains:

- `manifest.json`: hardware, OS, compiler/flags, commits, installed-file hashes, input hashes,
  thread counts, repetition count, command policy and initial host load.
- `runs.jsonl`: one row per invocation, including excluded warmups and exact commands.
- `summary.json`: medians, min/max times, pairwise speedups, identity counts and RSS.
- `*.stderr.log`: the complete MAFFT diagnostics for each invocation.
- `stdout-alignments.tar.gz`: all FASTA stdout files, with names matching `runs.jsonl`.

The archived stdout files can be unpacked in the suite directory and checked against the hashes.
Identical contents use internal tar hardlinks to preserve every per-run filename without storing
duplicate bytes. Each archive includes [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Raw uncompressed FASTA is ignored by Git to avoid checking in duplicate large alignment files.
Build logs and a regenerated historical CARC table are retained under `evidence/`.

## Interpretation

These measurements establish runtime and agreement with the pinned upstream build on the tested
inputs. They do not measure alignment accuracy against a trusted biological reference. More speed
does not guarantee less memory. Keep hardware and thread counts alongside any speedup claim.

The source documents a timing-dependent multithread corner case when the alignment crosses
30,000 columns mid-pass. In the historical SARS-CoV-2 2,000-genome test, a reported 205× timing
speedup had only 2/3 matching output pairs. Do not present it as an unconditional
equivalent-output result. This local replication does not rerun that corner case.

## Rebuild the chart

With Matplotlib installed, run `python3 bench/biocode/plot.py` from the repository root.
It reads the frozen summary and writes SVG, PNG and PDF into `figures/`. This does not
rerun the aligner or alter any measurements. The website renderer adds only NuMAFFT
to an existing site, preserving the other project entries.
