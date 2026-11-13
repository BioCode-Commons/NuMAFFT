# NuMAFFT versus MAFFT v7.526: detailed measurements

Independent local replication of default FFT-NS-2. These are measured results on an Apple M1 Max, not a claim about every alignment strategy or machine.

## Measured results

Wall times are medians of 3 measured runs after one excluded warmup for each variant and case. Speedup is baseline median / optimized median. The ranges below show the measured wall-time spread, not confidence intervals.

| Dataset | Requested threads | MAFFT median, s (min–max) | NuMAFFT median, s (min–max) | Speedup | Identical output pairs | Max child RSS, baseline / optimized, MiB |
|---|---:|---:|---:|---:|---:|---:|
| rnasim579 | 4 | 10.100 (10.093–10.737) | 2.382 (2.373–2.382) | 4.24× | 3/3 | 542.3 / 423.2 |
| rnasim2k | 4 | 43.292 (43.099–43.322) | 8.562 (8.531–8.591) | 5.06× | 3/3 | 1172.5 / 660.2 |
| prot2k | 4 | 4.478 (4.475–4.603) | 1.474 (1.468–1.482) | 3.04× | 3/3 | 298.5 / 198.0 |
| homfam_sdr_sub3k | 4 | 4.659 (4.651–4.826) | 1.203 (1.188–1.213) | 3.87× | 3/3 | 311.4 / 99.0 |
| 16S.T | 4 | 197.324 (196.594–208.189) | 18.092 (17.803–18.344) | 10.91× | 3/3 | 4671.8 / 2554.4 |
| rnasim579 | 1 | 29.329 (29.248–29.988) | 8.678 (8.639–8.681) | 3.38× | 3/3 | 179.0 / 119.1 |
| prot2k | 1 | 13.534 (13.515–13.549) | 4.734 (4.721–4.746) | 2.86× | 3/3 | 165.3 / 99.9 |

All 21 measured pairs and 7 warmup pairs had byte-identical stdout. Every output was a rectangular alignment with the input headers and ungapped sequences preserved. This checks agreement with this upstream build; it does not establish biological accuracy against a reference alignment.

## Versions and measurement conditions

- Upstream: [MAFFT v7.526](https://gitlab.com/sysimm/mafft/-/tree/ee9799916df6a5d5103d46d54933f8eb6d28e244), commit `ee9799916df6a5d5103d46d54933f8eb6d28e244`.
- Optimized: [fast-mafft v10](https://github.com/yih0nk/fast-mafft/tree/6474c62da49ca3af73bbb7b05287bbbb4a2036e5), commit `6474c62da49ca3af73bbb7b05287bbbb4a2036e5`.
- Compiler: Homebrew GCC 16.1.0; both builds use `-O3 -ffp-contract=off -std=c99`. C99 is explicitly included because GCC 16's default C dialect rejects a legacy declaration in the baseline's implicit build rules. No algorithm changes were made for this build.
- OS: `macOS-26.5.2-arm64-arm-64bit-Mach-O`. CPU: Apple M1 Max, 8 performance + 2 efficiency cores, 32 GiB RAM.
- Command: `bin/mafft --thread N input.fa` with no strategy overrides. Wall time includes launcher, alignment, and stdout writing. CPU time is recorded separately in the CSV.
- Runs execute one at a time. Measured order alternates baseline/fast, fast/baseline, baseline/fast. Each case has one excluded warmup per variant. OS file caches are not flushed.
- Shared interactive host; no exclusive allocation or CPU affinity. Performance and efficiency cores are scheduled by macOS. Background activity and thermal state were not controlled; see per-suite start load averages in the manifests.
- `MAFFT_*` environment overrides are removed. Each invocation uses a fresh temporary directory and a fresh measurement worker. Installed file hashes, input SHA-256 values, commands, timestamps and individual runs are retained.
- Memory is the maximum child-process high-water RSS per invocation, not the sum of simultaneously running processes. macOS reports bytes; Linux KiB are converted to bytes. Table values are MiB.
- Timings from single-thread and four-thread cases are compared only within the same thread count. ARM defaults do not enable the same progressive-DP vector kernels as x86 AVX2.

## Data

| Dataset | Sequences | Ungapped length, min / mean / max | SHA-256 |
|---|---:|---:|---|
| rnasim579 | 579 | 1543 / 1566.6 / 1593 | `3642da08cbb2eca93afcf10dcf9fc9dbd2ac6816f4b46bc817246075b6a57de3` |
| rnasim2k | 2,000 | 1527 / 1554.6 / 1586 | `3d77d379c3a80ae21da548711bde8f35cfad53362ebb5709e40db3e2fed4ade6` |
| prot2k | 2,000 | 369 / 405.8 / 446 | `12ba22a61ba810372d7cdf1f8018e15e417d466b57bff4923bec540e94db027c` |
| homfam_sdr_sub3k | 3,000 | 26 / 163.3 / 215 | `29f48a4cbdcccf42ca7fa5fb09a9be595f709e1de8a7f341b5a6c479562e1114` |
| 16S.T | 7,350 | 506 / 1492.1 / 4066 | `65d566908cfd460ecc2bcfd097e5c5564a0600216a6dd9a991b9d5da01299668` |

RNASim is simulated RNA, not empirical biological data. `prot2k` is generated protein data. HomFam is a biological protein-family dataset; 16S is biological rRNA data. See [data provenance and licenses](../DATA.md) and the checked release checksums. Inputs come from the pinned source repository's `data-v1` release.

## Existing CARC evidence and limits

The imported implementation's [CARC measurements](../../BENCHMARKS.md#historical-carc-measurements) record 10.10 to 43.85 times arithmetic-mean paired speedups on 12 large datasets with 32 allocated CPUs on AMD EPYC 7513, GCC 13.3.0 and `-O3 -march=native -flto`. The logs and regeneration script are retained. Those historical results use a different statistic and environment; they are not pooled with this local replication.

A reported 205.29× result for SARS-CoV-2 2,000 sequences had only 2/3 byte-identical output pairs. It must not be advertised as an unconditional equivalent-output speedup. The source documents timing-dependent multithread behavior when an alignment crosses 30,000 columns mid-pass. This replication does not rerun that corner case or the entire CARC/BAliBASE suite. Use single-thread validation when exact reproducibility is required, and validate your own inputs.

Faster execution does not imply lower memory use or better alignment quality. Other MAFFT strategies, GPU performance, and machines not listed here are outside this comparison.

## Evidence and reproduction

See [README.md](README.md) for build/run commands. [measurements.csv](measurements.csv) contains warmup and measured rows; [summary.json](summary.json) is the machine-readable table. Each result directory retains `manifest.json`, `runs.jsonl`, stderr logs, and an archive of stdout alignments. Input SHA-256 and stdout SHA-256 allow comparisons without redistributing large files in Git.
