"""Checks for the benchmark's measurement and correctness guards."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import run


class BenchmarkChecks(unittest.TestCase):
    def test_alignment_validation_rejects_lost_or_changed_sequences(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'out.fa'
            source = run.Counter([('a', 'ACG'), ('b', 'AG')])
            output.write_text('>a\nacg\n>b\na-g\n')
            self.assertTrue(run.validate_output(source, output)['ungapped_sequences_preserved'])
            output.write_text('>a\nACG\n>b\nACT\n')
            self.assertFalse(run.validate_output(source, output)['ungapped_sequences_preserved'])
            output.write_text('>a\nACG\n>b\nAG\n')
            self.assertFalse(run.validate_output(source, output)['rectangular'])

    def test_duplicate_headers_do_not_hide_lost_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'out.fa'
            output.write_text('>same\nAC\n>same\nAC\n')
            source = run.Counter([('same', 'AC'), ('same', 'AG')])
            self.assertFalse(run.validate_output(source, output)['ungapped_sequences_preserved'])

    def test_worker_records_failure_and_timeout_separately(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = {'output': str(Path(temporary) / 'out'), 'stderr': str(Path(temporary) / 'err'), 'timeout': 5}
            failed = subprocess.run([sys.executable, run.__file__, '--_worker', json.dumps({**base, 'command': [sys.executable, '-c', 'raise SystemExit(7)']})], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(failed.stdout)['returncode'], 7)
            self.assertFalse(json.loads(failed.stdout)['timed_out'])
            expired = subprocess.run([sys.executable, run.__file__, '--_worker', json.dumps({**base, 'timeout': 0.1, 'command': [sys.executable, '-c', 'import time; time.sleep(60)']})], capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(expired.stdout)['timed_out'])
            self.assertLess(json.loads(expired.stdout)['wall_seconds'], 5)


if __name__ == '__main__':
    unittest.main()
