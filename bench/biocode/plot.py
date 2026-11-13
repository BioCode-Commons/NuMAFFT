#!/usr/bin/env python3
"""Recreate the published four-thread chart from frozen summary.json.

Requires matplotlib. Run from any working directory; outputs go to figures/.
"""
import json
from pathlib import Path

bench = Path(__file__).resolve().parent
summary = json.loads((bench / 'summary.json').read_text())
output = bench / 'figures'
output.mkdir(exist_ok=True)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none'})
rows = sorted([r for r in summary if r['threads'] == 4], key=lambda r: r['speedup_ratio_of_medians'], reverse=True)
fig, axes = plt.subplots(1, 2, figsize=(14, 6.7), gridspec_kw={'width_ratios': [1.55, 1]}, layout='constrained')
baseline_color, optimized_color = '#94a3b8', '#087f8c'
ys = list(range(len(rows)))
ax = axes[0]
ax.barh([y-.18 for y in ys], [r['baseline_median_seconds'] for r in rows], height=.30, color=baseline_color, label='Original MAFFT v7.526')
ax.barh([y+.18 for y in ys], [r['optimized_median_seconds'] for r in rows], height=.30, color=optimized_color, label='NuMAFFT')
for y, row in enumerate(rows):
    for offset, key in [(-.18, 'baseline_median_seconds'), (.18, 'optimized_median_seconds')]:
        value = row[key]
        ax.text(value + 2, y + offset, f'{value:.2f} s', va='center', fontsize=10)
ax.set_yticks(ys, [r['dataset'] for r in rows])
ax.set_xlim(0, 235)
ax.set_xlabel('Wall time (seconds; lower is faster)')
ax.set_title('Measured runtime', loc='left', fontweight='medium', pad=18)
ax.invert_yaxis()
ax.legend(loc='lower right', frameon=False)
ax = axes[1]
ax.barh(ys, [r['speedup_ratio_of_medians'] for r in rows], height=.48, color=optimized_color)
for y, row in enumerate(rows):
    ax.text(row['speedup_ratio_of_medians']+.16, y, f"{row['speedup_ratio_of_medians']:.2f}×", va='center', fontweight='medium')
ax.set_yticks(ys, [r['dataset'] for r in rows])
ax.set_xlim(0, 12.5)
ax.set_xlabel('Speedup (original median / optimized median)')
ax.set_title('Same input, same requested threads', loc='left', fontweight='medium', pad=18)
ax.invert_yaxis()
for ax in axes:
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.xaxis.grid(True, alpha=.15)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
fig.suptitle('NuMAFFT vs MAFFT: local paired replication', x=.015, ha='left', fontsize=20, fontweight='medium')
fig.set_layout_engine('constrained', rect=(0, .11, 1, .89))
fig.text(.015, .02, 'Apple M1 Max · 4 requested threads · FFT-NS-2 · 3 timed repetitions per case after excluded warmup\nAll 15 measured pairs byte-identical · Native GCC 16.1.0, matched flags · 11 Nov 2026 · Shared host, no CPU affinity', ha='left', fontsize=10, color='#475569')
for extension in ['svg', 'png', 'pdf']:
    fig.savefig(output / ('numafft-local-4threads.' + extension), dpi=180, bbox_inches='tight', facecolor='white')
plt.close(fig)
