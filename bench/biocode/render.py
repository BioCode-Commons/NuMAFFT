#!/usr/bin/env python3
"""Render the report from completed benchmark directories, without rerunning MAFFT."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def load_suites(directories):
    suites = []
    for directory in directories:
        manifest = json.loads((directory / 'manifest.json').read_text())
        summary = json.loads((directory / 'summary.json').read_text())
        runs = [json.loads(line) for line in (directory / 'runs.jsonl').read_text().splitlines()]
        if any(not row['valid_run'] for row in runs):
            raise ValueError(f'{directory}: failed or invalid run; inspect logs before reporting')
        expected = len(manifest['inputs']) * len(manifest['threads']) * (manifest['repetitions'] + 1) * 2
        if len(runs) != expected:
            raise ValueError(f'{directory}: expected {expected} rows, got {len(runs)}')
        if any(row['identical_pairs'] != manifest['repetitions'] for row in summary):
            raise ValueError(f'{directory}: output differences; report them explicitly before publishing speedups')
        if any(not row['paired_stdout_byte_identical'] for row in runs):
            raise ValueError(f'{directory}: a warmup or measured output pair differs')
        suites.append((directory, manifest, summary, runs))
    pinned = ('baseline_commit', 'optimized_commit', 'compiler', 'cflags', 'repetitions', 'environment')
    for key in pinned[:-1]:
        if len({str(suite[1][key]) for suite in suites}) != 1:
            raise ValueError(f'Cannot combine suites with different {key}')
    for key in ('platform', 'machine', 'machdep.cpu.brand_string', 'hw.memsize'):
        if len({str(suite[1]['environment'].get(key)) for suite in suites}) != 1:
            raise ValueError(f'Cannot combine suites on different {key}')
    cases = [(row['dataset'], row['threads']) for suite in suites for row in suite[2]]
    if len(cases) != len(set(cases)):
        raise ValueError('Duplicate dataset/thread cases would give a misleading combined table')
    return suites


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('results', nargs='+', type=Path)
    args = parser.parse_args()
    suites = load_suites(args.results)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = suites[0][1]
    metadata = {key: manifest[key] for key in ('baseline_commit', 'optimized_commit', 'compiler', 'cflags', 'repetitions', 'environment')}
    metadata['suite_started_at_utc'] = [suite[1]['started_at_utc'] for suite in suites]
    metadata['source_file_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted(Path(__file__).resolve().parent.iterdir())
                                      if p.suffix in ('.py', '.sh')}
    (args.out / 'report-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    summary = [row for suite in suites for row in suite[2]]
    runs = [row for suite in suites for row in suite[3]]
    fields = ('dataset', 'threads', 'repetition', 'warmup', 'variant', 'position_in_pair', 'started_at_utc',
              'wall_seconds', 'cpu_seconds', 'peak_child_rss_bytes', 'returncode', 'timed_out',
              'stdout_sha256', 'paired_stdout_byte_identical', 'sequence_count', 'alignment_columns',
              'rectangular', 'ungapped_sequences_preserved', 'valid_run', 'output_file')
    with (args.out / 'measurements.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(runs)
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['# NuMAFFT versus MAFFT v7.526: detailed measurements', '',
             'Independent local replication of default FFT-NS-2. These are measured results on an Apple M1 Max, not a claim about every alignment strategy or machine.', '',
             '## Measured results', '',
             f"Wall times are medians of {manifest['repetitions']} measured runs after one excluded warmup for each variant and case. Speedup is baseline median / optimized median. The ranges below show the measured wall-time spread, not confidence intervals.", '',
             '| Dataset | Requested threads | MAFFT median, s (min–max) | NuMAFFT median, s (min–max) | Speedup | Identical output pairs | Max child RSS, baseline / optimized, MiB |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for row in summary:
        bmin, bmax = row['baseline_wall_range']
        omin, omax = row['optimized_wall_range']
        lines.append(f"| {row['dataset']} | {row['threads']} | {row['baseline_median_seconds']:.3f} ({bmin:.3f}–{bmax:.3f}) | {row['optimized_median_seconds']:.3f} ({omin:.3f}–{omax:.3f}) | {row['speedup_ratio_of_medians']:.2f}× | {row['identical_pairs']}/{row['repetitions']} | {row['baseline_max_child_rss_bytes'] / 1048576:.1f} / {row['optimized_max_child_rss_bytes'] / 1048576:.1f} |")
    measured = [row for row in runs if not row['warmup']]
    lines += ['', f"All {len(measured)//2} measured pairs and {len(runs)//2-len(measured)//2} warmup pairs had byte-identical stdout. Every output was a rectangular alignment with the input headers and ungapped sequences preserved. This checks agreement with this upstream build; it does not establish biological accuracy against a reference alignment.", '',
              '## Versions and measurement conditions', '',
              f"- Upstream: [MAFFT v7.526](https://gitlab.com/sysimm/mafft/-/tree/{manifest['baseline_commit']}), commit `{manifest['baseline_commit']}`.",
              f"- Optimized: [fast-mafft v10](https://github.com/yih0nk/fast-mafft/tree/{manifest['optimized_commit']}), commit `{manifest['optimized_commit']}`.",
              f"- Compiler: {manifest['compiler']}; both builds use `{manifest['cflags']}`. C99 is explicitly included because GCC 16's default C dialect rejects a legacy declaration in the baseline's implicit build rules. No algorithm changes were made for this build.",
              f"- OS: `{manifest['environment']['platform']}`. CPU: Apple M1 Max, 8 performance + 2 efficiency cores, 32 GiB RAM.",
              '- Command: `bin/mafft --thread N input.fa` with no strategy overrides. Wall time includes launcher, alignment, and stdout writing. CPU time is recorded separately in the CSV.',
              '- Runs execute one at a time. Measured order alternates baseline/fast, fast/baseline, baseline/fast. Each case has one excluded warmup per variant. OS file caches are not flushed.',
              '- Shared interactive host; no exclusive allocation or CPU affinity. Performance and efficiency cores are scheduled by macOS. Background activity and thermal state were not controlled; see per-suite start load averages in the manifests.',
              '- `MAFFT_*` environment overrides are removed. Each invocation uses a fresh temporary directory and a fresh measurement worker. Installed file hashes, input SHA-256 values, commands, timestamps and individual runs are retained.',
              '- Memory is the maximum child-process high-water RSS per invocation, not the sum of simultaneously running processes. macOS reports bytes; Linux KiB are converted to bytes. Table values are MiB.',
              '- Timings from single-thread and four-thread cases are compared only within the same thread count. ARM defaults do not enable the same progressive-DP vector kernels as x86 AVX2.', '',
              '## Data', '', '| Dataset | Sequences | Ungapped length, min / mean / max | SHA-256 |', '|---|---:|---:|---|']
    seen = set()
    for _, man, _, _ in suites:
        for item in man['inputs']:
            if item['dataset'] not in seen:
                seen.add(item['dataset'])
                lines.append(f"| {item['dataset']} | {item['sequences']:,} | {item['min_length']} / {item['mean_length']:.1f} / {item['max_length']} | `{item['sha256']}` |")
    lines += ['', 'RNASim is simulated RNA, not empirical biological data. `prot2k` is generated protein data. HomFam is a biological protein-family dataset; 16S is biological rRNA data. See [data provenance and licenses](../DATA.md) and the checked release checksums. Inputs come from the pinned source repository\'s `data-v1` release.', '',
              '## Existing CARC evidence and limits', '',
              'The imported implementation\'s [CARC measurements](../../BENCHMARKS.md#historical-carc-measurements) record 10.10 to 43.85 times arithmetic-mean paired speedups on 12 large datasets with 32 allocated CPUs on AMD EPYC 7513, GCC 13.3.0 and `-O3 -march=native -flto`. The logs and regeneration script are retained. Those historical results use a different statistic and environment; they are not pooled with this local replication.', '',
              'A reported 205.29× result for SARS-CoV-2 2,000 sequences had only 2/3 byte-identical output pairs. It must not be advertised as an unconditional equivalent-output speedup. The source documents timing-dependent multithread behavior when an alignment crosses 30,000 columns mid-pass. This replication does not rerun that corner case or the entire CARC/BAliBASE suite. Use single-thread validation when exact reproducibility is required, and validate your own inputs.', '',
              'Faster execution does not imply lower memory use or better alignment quality. Other MAFFT strategies, GPU performance, and machines not listed here are outside this comparison.', '',
              '## Evidence and reproduction', '',
              'See [README.md](README.md) for build/run commands. [measurements.csv](measurements.csv) contains warmup and measured rows; [summary.json](summary.json) is the machine-readable table. Each result directory retains `manifest.json`, `runs.jsonl`, stderr logs, and an archive of stdout alignments. Input SHA-256 and stdout SHA-256 allow comparisons without redistributing large files in Git.', '']
    (args.out / 'REPORT.md').write_text('\n'.join(lines))
    print(f'Rendered {len(summary)} cases and {len(runs)} individual runs to {args.out}')


if __name__ == '__main__':
    main()
