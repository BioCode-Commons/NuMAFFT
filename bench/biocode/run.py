#!/usr/bin/env python3
"""Paired MAFFT benchmark; Python standard library, Linux and macOS.

Each invocation runs serially. Every measurement gets a fresh worker process so
RUSAGE_CHILDREN's high-water mark cannot leak in from an earlier measurement.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import filecmp
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fasta(path):
    records, name, sequence = [], None, []
    with open(path) as stream:
        for line in stream:
            line = line.strip()
            if line.startswith('>'):
                if name is not None:
                    records.append((name, ''.join(sequence).upper()))
                name, sequence = line[1:], []
            elif line:
                if name is None:
                    raise ValueError('Sequence before FASTA header')
                sequence.append(line)
    if name is not None:
        records.append((name, ''.join(sequence).upper()))
    if not records:
        raise ValueError('Empty FASTA')
    return records


def validate_output(source, output):
    try:
        aligned = fasta(output)
        lengths = {len(seq) for _, seq in aligned}
        preserved = Counter((name, seq.replace('-', '')) for name, seq in aligned) == source
        return {'sequence_count': len(aligned), 'alignment_columns': next(iter(lengths)) if len(lengths) == 1 else None,
                'rectangular': len(lengths) == 1, 'ungapped_sequences_preserved': preserved}
    except (ValueError, UnicodeError) as error:
        return {'validation_error': str(error), 'rectangular': False, 'ungapped_sequences_preserved': False}


def worker(job):
    env = {key: value for key, value in os.environ.items() if not key.startswith('MAFFT_')}
    env['LC_ALL'] = 'C'
    with tempfile.TemporaryDirectory(prefix='mafft-benchmark-') as temporary:
        env['TMPDIR'] = temporary
        with open(job['output'], 'wb') as output, open(job['stderr'], 'wb') as stderr:
            started = datetime.now(timezone.utc).isoformat()
            before = time.perf_counter()
            process = subprocess.Popen(job['command'], stdout=output, stderr=stderr, env=env, start_new_session=True)
            timed_out = threading.Event()
            def kill_on_timeout():
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        timed_out.set()
                    except ProcessLookupError:
                        pass
            timer = threading.Timer(job['timeout'], kill_on_timeout)
            timer.start()
            try:
                process.wait()
            finally:
                timer.cancel()
            wall = time.perf_counter() - before
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'started_at_utc': started, 'wall_seconds': wall, 'cpu_seconds': usage.ru_utime + usage.ru_stime,
            'peak_child_rss_bytes': usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
            'returncode': process.returncode, 'timed_out': timed_out.is_set()}


def platform_details():
    details = {'platform': platform.platform(), 'machine': platform.machine(), 'logical_cpus': os.cpu_count(),
               'python': sys.version, 'load_average_at_start': os.getloadavg(),
               'exclusive_host': False, 'cpu_affinity': 'not pinned', 'cache_policy': 'warm; no OS cache flush'}
    if sys.platform == 'darwin':
        for key in ('machdep.cpu.brand_string', 'hw.memsize', 'hw.perflevel0.physicalcpu', 'hw.perflevel1.physicalcpu'):
            result = subprocess.run(['sysctl', '-n', key], capture_output=True, text=True)
            details[key] = result.stdout.strip()
    return details


def git_revision(path):
    return subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--optimized', type=Path, required=True)
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--optimized-source', type=Path, required=True)
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--cflags', required=True)
    parser.add_argument('--threads', nargs='+', type=int, default=[1, 4])
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('inputs', nargs='+', type=Path)
    args = parser.parse_args()
    if args.repetitions < 1 or any(n < 1 for n in args.threads):
        parser.error('Repetitions and threads must be positive')
    args.out.mkdir(parents=True, exist_ok=False)
    binaries = {'baseline': args.baseline.resolve(), 'optimized': args.optimized.resolve()}
    data = []
    names = set()
    sources = {}
    for path in args.inputs:
        path = path.resolve()
        if path.stem in names:
            parser.error('Input file stems must be unique')
        names.add(path.stem)
        parsed = fasta(path)
        sources[path.stem] = Counter((name, seq.replace('-', '')) for name, seq in parsed)
        lengths = [len(seq) for _, seq in parsed]
        data.append({'dataset': path.stem, 'path': str(path), 'sha256': sha256(path), 'sequences': len(parsed),
                     'min_length': min(lengths), 'max_length': max(lengths), 'mean_length': statistics.mean(lengths)})
    manifest = {'schema_version': 1, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'environment': platform_details(), 'compiler': args.compiler, 'cflags': args.cflags,
                'baseline_commit': git_revision(args.baseline_source), 'optimized_commit': git_revision(args.optimized_source),
                'baseline_remote': 'https://gitlab.com/sysimm/mafft', 'optimized_remote': 'https://github.com/yih0nk/fast-mafft',
                'strategy': 'default FFT-NS-2', 'threads': args.threads, 'repetitions': args.repetitions,
                'warmups_per_variant_per_case': 1, 'order': 'AB, BA, AB, ...; warmup AB',
                'timeout_seconds': args.timeout, 'binaries': {key: str(value) for key, value in binaries.items()},
                'launcher_sha256': {key: sha256(path) for key, path in binaries.items()},
                'disttbfast_sha256': {key: sha256(path.parent.parent / 'libexec/mafft/disttbfast') for key, path in binaries.items()},
                'installed_file_sha256': {key: {p.name: sha256(p) for p in sorted((path.parent.parent / 'libexec/mafft').iterdir()) if p.is_file()} for key, path in binaries.items()},
                'rss_definition': 'Per-invocation RUSAGE_CHILDREN maximum: largest child high-water RSS, not simultaneous process-tree sum. Darwin bytes; Linux KiB converted to bytes.',
                'inputs': data}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    all_rows = []
    failed = False
    different = False
    for entry in data:
        for threads in args.threads:
            for repetition in range(args.repetitions + 1):
                warmup = repetition == 0
                variants = ['optimized', 'baseline'] if repetition and repetition % 2 == 0 else ['baseline', 'optimized']
                pair = {}
                for position, variant in enumerate(variants):
                    stem = f"{entry['dataset']}.t{threads}.r{repetition}.{variant}"
                    output = args.out / (stem + '.fasta')
                    command = [str(binaries[variant]), '--thread', str(threads), entry['path']]
                    job = {'command': command, 'output': str(output), 'stderr': str(args.out / (stem + '.stderr.log')), 'timeout': args.timeout}
                    completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--_worker', json.dumps(job)], capture_output=True, text=True, check=True)
                    row = {'dataset': entry['dataset'], 'threads': threads, 'repetition': repetition, 'warmup': warmup,
                           'variant': variant, 'position_in_pair': position, 'command': command, 'output_file': output.name,
                           **json.loads(completed.stdout), 'stdout_sha256': sha256(output),
                           **validate_output(sources[entry['dataset']], output)}
                    pair[variant] = row
                    print(f"{stem}: {row['wall_seconds']:.3f}s rc={row['returncode']}", flush=True)
                identical = filecmp.cmp(args.out / pair['baseline']['output_file'], args.out / pair['optimized']['output_file'], shallow=False)
                different = different or not identical
                for row in pair.values():
                    row['paired_stdout_byte_identical'] = identical
                    row['valid_run'] = row['returncode'] == 0 and row['rectangular'] and row['ungapped_sequences_preserved'] and not row['timed_out']
                    failed = failed or not row['valid_run']
                    with (args.out / 'runs.jsonl').open('a') as stream:
                        stream.write(json.dumps(row) + '\n')
                    all_rows.append(row)
    summary = []
    for entry in data:
        for threads in args.threads:
            rows = [r for r in all_rows if r['dataset'] == entry['dataset'] and r['threads'] == threads and not r['warmup']]
            baseline = [r for r in rows if r['variant'] == 'baseline']
            optimized = [r for r in rows if r['variant'] == 'optimized']
            valid = all(r['valid_run'] for r in rows)
            b = statistics.median(r['wall_seconds'] for r in baseline)
            o = statistics.median(r['wall_seconds'] for r in optimized)
            summary.append({'dataset': entry['dataset'], 'threads': threads, 'repetitions': args.repetitions,
                            'valid_runs': valid, 'baseline_median_seconds': b, 'optimized_median_seconds': o,
                            'speedup_ratio_of_medians': b / o if valid else None,
                            'paired_speedups': [baseline[i]['wall_seconds'] / optimized[i]['wall_seconds'] for i in range(len(baseline))] if valid else [],
                            'identical_pairs': sum(r['paired_stdout_byte_identical'] for r in baseline),
                            'baseline_wall_range': [min(r['wall_seconds'] for r in baseline), max(r['wall_seconds'] for r in baseline)],
                            'optimized_wall_range': [min(r['wall_seconds'] for r in optimized), max(r['wall_seconds'] for r in optimized)],
                            'baseline_max_child_rss_bytes': max(r['peak_child_rss_bytes'] for r in baseline),
                            'optimized_max_child_rss_bytes': max(r['peak_child_rss_bytes'] for r in optimized)})
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 1 if failed else (2 if different else 0)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--_worker':
        print(json.dumps(worker(json.loads(sys.argv[2]))))
    else:
        raise SystemExit(main())
