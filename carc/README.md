# Historical CARC benchmark evidence

This directory retains the imported implementation's original job scripts, raw logs and summarizer. The scripts use the precursor source layout and data release. They are retained for audit and reproduction of those jobs.

Read the current [NuMAFFT benchmark report](../BENCHMARKS.md) for the local comparison, hardware, timings, output checks and known limits. The CARC job logs were regenerated into a table; those HPC jobs were not rerun in the local replication.

Regenerate the historical tables with:

```sh
python3 carc/summarize.py carc/logs/v10final-*.log
```

The original source revision and attribution are in [NOTICE.md](../NOTICE.md).
