import json
from pathlib import Path
import tempfile
import unittest

import render


class ReportGuards(unittest.TestCase):
    def suite(self, root, name='case', flags='-O3'):
        directory = Path(root) / name
        directory.mkdir()
        manifest = {'inputs': [{'dataset': name}], 'threads': [4], 'repetitions': 3,
                    'baseline_commit': 'base', 'optimized_commit': 'fast',
                    'compiler': 'gcc', 'cflags': flags, 'environment': {'machine': 'arm64'}}
        (directory / 'manifest.json').write_text(json.dumps(manifest))
        (directory / 'summary.json').write_text(json.dumps([{'dataset': name, 'threads': 4, 'identical_pairs': 3}]))
        runs = [{'valid_run': True, 'paired_stdout_byte_identical': True} for _ in range(8)]
        (directory / 'runs.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in runs))
        return directory, runs

    def test_incomplete_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory, runs = self.suite(temporary)
            (directory / 'runs.jsonl').write_text(json.dumps(runs[0]) + '\n')
            with self.assertRaisesRegex(ValueError, 'expected 8 rows'):
                render.load_suites([directory])

    def test_mismatching_warmup_is_not_hidden_by_matching_measured_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory, runs = self.suite(temporary)
            runs[0]['paired_stdout_byte_identical'] = False
            (directory / 'runs.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in runs))
            with self.assertRaisesRegex(ValueError, 'warmup or measured output pair differs'):
                render.load_suites([directory])

    def test_different_build_flags_cannot_be_pooled(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, _ = self.suite(temporary, 'first')
            second, _ = self.suite(temporary, 'second', flags='-Ofast')
            with self.assertRaisesRegex(ValueError, 'different cflags'):
                render.load_suites([first, second])


if __name__ == '__main__':
    unittest.main()
