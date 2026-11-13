# NuMAFFT implementation notes

NuMAFFT imports the fast-mafft v10 implementation of default FFT-NS-2, based on
MAFFT v7.526. The BioCode Commons packaging changes the project documentation and
presentation; it does not alter these alignment kernels.

## Distance calculations

6-mer distances use SIMD kernels, inverted indexes and masks. Distances calculated
from an existing multiple alignment use bit-parallel scoring. ARM and x86 select
different kernel paths; the local ARM measurements cannot be treated as AVX2 results.

## Guide trees

Candidate lists reduce repeated nearest-neighbor scans while preserving the original
selection and tie rules.

## Progressive alignment

The imported implementation combines dynamic-programming loops, defers gap insertion
and reduces row copying. A scheduler distributes independent merges and lets idle
workers help with large steps. Inputs above 20,000 sequences can use threaded
progressive passes where upstream uses a serial path.

Version 10 also changes Myers-Miller alignment, long-sequence anchor searches,
FFT processing and buffer reuse. The local benchmark measures the complete command;
it does not isolate a speedup for each individual change.

## Output compatibility

For the seven locally tested input/thread cases, all 21 measured pairs and seven
warmup pairs had byte-identical stdout. This establishes agreement with the pinned
upstream build on those inputs. It does not extend the result to untested strategies.

The imported source documents a multithread corner case when the alignment crosses
30,000 columns mid-pass. Its mode switch can depend on timing, and the optimized
implementation can produce a different alignment. Historical logs include such a
case. See [benchmarks](../BENCHMARKS.md) for the evidence and limitations.

The original source and its development history are identified in [NOTICE.md](../NOTICE.md).
