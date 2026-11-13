#!/usr/bin/env python3
"""Add NuMAFFT to a current website checkout without replacing other projects."""
import hashlib
import html
import json
from pathlib import Path
import re
import sys


def upsert_project(template, project, row):
    """Replace only NuMAFFT; keep all other project content byte for byte."""
    section = re.search(r'(<section id="projects"[^>]*>)(.*?)(</section>)', template, re.S)
    if section is None:
        raise ValueError('Expected a projects section')
    body = section.group(2)
    existing = r'<article class="project" aria-labelledby="project-numafft">.*?</article>'
    if re.search(existing, body, re.S):
        body = re.sub(existing, lambda _: project.strip(), body, count=1, flags=re.S)
    else:
        body = body.rstrip() + '\n\n' + project + '\n    '
    if 'id="overview-numafft"' in body:
        body = re.sub(r'<tr id="overview-numafft">.*?</tr>', lambda _: row.strip(), body, count=1, flags=re.S)
    else:
        table = re.search(r'<table aria-label="Maintained pipeline summary">.*?</tbody>', body, re.S)
        if table is None:
            raise ValueError('Expected the maintained pipeline summary table')
        addition = table.group().replace('</tbody>', row + '\n          </tbody>')
        body = body[:table.start()] + addition + body[table.end():]
    return template[:section.start(2)] + body + template[section.end(2):]


def main():
    site = Path(sys.argv[1])
    bench = Path(__file__).resolve().parent
    rows = json.loads((bench / 'summary.json').read_text())
    metadata = json.loads((bench / 'report-metadata.json').read_text())
    if (not rows or any(not r['valid_runs'] or r['identical_pairs'] != r['repetitions'] for r in rows)
            or metadata['optimized_commit'] != '6474c62da49ca3af73bbb7b05287bbbb4a2036e5'
            or metadata['environment'].get('machdep.cpu.brand_string') != 'Apple M1 Max'
            or metadata['repetitions'] != 3):
        raise ValueError('Review website prose for a different source, machine or measurement protocol')
    repo = 'https://github.com/BioCode-Commons/NuMAFFT'
    evidence = repo + '/tree/main/bench/biocode'
    report = repo + '/blob/main/BENCHMARKS.md'
    template_path = site / 'template.html'
    template = template_path.read_text()
    project = """      <article class="project" aria-labelledby="project-numafft">
        <h3 id="project-numafft"><a href="https://github.com/BioCode-Commons/NuMAFFT">NuMAFFT</a></h3>
        <p>Multiple sequence alignment based on MAFFT v7.526, with an optimized default FFT-NS-2 implementation.</p>
        <p>Apple M1 Max, four requested threads: 16S.T fell from 197.324 to 18.092 seconds, a 10.91-fold speedup. All 21 measured pairs across seven input/thread cases had byte-identical output.</p>
        <p class="benchmark-note">Local repeated measurements are complete. Historical 32-core CARC logs are reported separately; those jobs were not rerun. Broader input coverage and comprehensive human code review remain open.</p>
        <p><a href="benchmarks/numafft.html">Charts, timing tables and methods</a> · <a href="https://github.com/BioCode-Commons/NuMAFFT/blob/main/BENCHMARKS.md">Full report and raw evidence</a></p>
      </article>"""
    row = """            <tr id="overview-numafft">
              <th scope="row"><a href="#project-numafft">NuMAFFT</a></th>
              <td><a href="https://gitlab.com/sysimm/mafft">MAFFT</a> v7.526 baseline</td>
              <td><strong>Running time:</strong> 3.04×–10.91×, local 4-thread tests<br><strong>RAM:</strong> see per-run measurements; no universal reduction claimed</td>
              <td><strong>Audit:</strong> Comprehensive human audit pending.<br><strong>Output:</strong> All 21 measured pairs byte-identical across the listed local input/thread cases.</td>
            </tr>"""
    template = upsert_project(template, project, row)
    template_path.write_text(template)
    measured_rows = ''.join(f"<tr><th scope='row'>{html.escape(r['dataset'])}</th><td>{r['threads']}</td><td>{r['baseline_median_seconds']:.3f}</td><td>{r['optimized_median_seconds']:.3f}</td><td>{r['speedup_ratio_of_medians']:.2f}×</td><td>{r['identical_pairs']}/3</td></tr>" for r in sorted(rows, key=lambda r: (r['threads'], r['dataset'])))
    large = {'rnasim5k', 'rnasim10k', '16S.T', '16S.3', 'homfam_p450', 'rnasim20k', '16S.B.ALL', 'homfam_sdr', 'homfam_Acetyltransf', 'rnasim25k', 'homfam_rvp', 'rnasim50k'}
    historical_rows = []
    for line in (bench / 'evidence/carc-regenerated.md').read_text().splitlines():
        fields = [f.strip() for f in line.split('|')[1:-1]]
        if len(fields) == 10 and fields[0] in large:
            historical_rows.append('<tr>' + ''.join(f'<td>{html.escape(x)}</td>' for x in (fields[0], '32', fields[1], fields[2], fields[6], fields[8])) + '</tr>')
    style_version = hashlib.blake2s((site / 'styles.css').read_bytes(), digest_size=6).hexdigest()
    page = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NuMAFFT benchmark | BioCode Commons</title>
  <meta name="description" content="NuMAFFT runtime, thread counts, output comparisons and project status.">
  <link rel="icon" href="../favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../styles.css?v={style_version}">
</head>
<body>
  <aside class="sidebar">
    <div class="site-name">BioCode Commons</div>
    <nav aria-label="Contents"><a class="toc-heading" href="../index.html#projects">All projects</a><a href="#local">Local results</a><a href="#carc">32-core CARC results</a><a href="#status">Implementation status</a><a href="#reproduce">Reproduce</a><a href="#references">References</a></nav>
  </aside>
  <header class="mobile-header"><div class="site-name">BioCode Commons</div><a href="../index.html#projects">All projects</a></header>
  <main class="benchmark-page">
    <h1>NuMAFFT</h1>
    <p>BioCode Commons' multiple sequence alignment project, based on MAFFT v7.526 with an optimized default FFT-NS-2 implementation.</p>
    <section id="local" aria-labelledby="local-title">
      <h2 id="local-title">Local runtime and output comparisons</h2>
      <p>Apple M1 Max, native arm64, GCC 16.1.0, 11 November 2026. Both versions use <code>-O3 -ffp-contract=off -std=c99</code>. Each table entry is the median of three measured runs after an excluded warmup. Speedup is original median divided by optimized median.</p>
      <figure class="numafft-benchmark-figure">
        <img src="assets/numafft-local-4threads.svg" width="2540" height="1215" alt="Five four-thread tests on Apple M1 Max: original MAFFT versus NuMAFFT median wall time, and speedup from 3.04 to 10.91 times.">
        <figcaption>Four requested threads, three measured repetitions per case after excluded warmup. All 15 measured pairs were byte-identical. <a href="assets/numafft-local-4threads.pdf">Download PDF</a> · <a href="assets/numafft-local-4threads.png">PNG</a></figcaption>
      </figure>
      <div class="benchmark-table-wrap" tabindex="0" role="region" aria-label="Local timing table; scroll horizontally on small screens">
        <table class="benchmark-table"><caption>Requested threads and wall time in seconds; the workstation had no exclusive core allocation.</caption>
          <thead><tr><th scope="col">Dataset</th><th scope="col">Threads</th><th scope="col">Original MAFFT, s</th><th scope="col">NuMAFFT, s</th><th scope="col">Speedup</th><th scope="col">Identical pairs</th></tr></thead><tbody>{measured_rows}</tbody>
        </table>
      </div>
      <p>All 21 measured pairs and seven warmup pairs had byte-identical stdout. Each output preserved the input headers and ungapped sequences and formed a rectangular alignment. RNASim is simulated RNA, prot2k is simulated protein, HomFam is biological protein-family data, and 16S.T is biological rRNA.</p>
      <p>Runs executed one at a time in alternating order. macOS chose worker placement; OS caches were not flushed, and background activity and thermals were uncontrolled. The <a href="{report}">full benchmark report</a> gives the inputs, hashes, commands, time ranges, CPU measurements and memory definition.</p>
    </section>
    <section id="carc" aria-labelledby="carc-title">
      <h2 id="carc-title">Historical 32-core CARC measurements</h2>
      <p>The imported implementation's original logs record 10.10 to 43.85 times mean paired speedup on 12 large datasets. Each job allocated 32 CPU cores and 64 GB memory on AMD EPYC 7513. Builds used GCC 13.3.0 with <code>-O3 -march=native -flto</code>, and both variants ran with <code>--thread 32</code>.</p>
      <div class="benchmark-table-wrap" tabindex="0" role="region" aria-label="Historical CARC timing table; scroll horizontally on small screens">
        <table class="benchmark-table"><caption>Three paired repetitions per dataset. The mean paired speedup uses a different statistic from the local table above.</caption>
          <thead><tr><th scope="col">Dataset</th><th scope="col">Allocated cores</th><th scope="col">Original mean, s</th><th scope="col">Optimized mean, s</th><th scope="col">Mean paired speedup</th><th scope="col">Output hashes</th></tr></thead><tbody>{''.join(historical_rows)}</tbody>
        </table>
      </div>
      <p>All 36 timed pairs for these 12 datasets had matching output hashes. The table was regenerated from retained logs; those CARC jobs were not rerun for this local evaluation. <a href="{evidence.replace('/tree/', '/blob/')}/evidence/carc-regenerated.md">Regenerated table</a> · <a href="{repo}/tree/main/carc/logs">Original logs</a></p>
    </section>
    <section id="status" aria-labelledby="status-title">
      <h2 id="status-title">Implementation status and limits</h2>
      <p>The optimized source is imported without alignment-code changes. It accelerates distance calculations, guide trees, progressive alignment and output processing. SIMD and bit-parallel kernels, candidate lists, fewer row copies and parallel scheduling reduce repeated work. <a href="{repo}/blob/main/docs/IMPLEMENTATION.md">Implementation notes</a></p>
      <p>A separate historical SARS-CoV-2 test with 2,000 genomes showed a 205-fold timing speedup, but only two of three timed output pairs matched. That number is excluded from the equivalent-output speedup range. The source documents timing-dependent multithread behavior when an alignment crosses 30,000 columns mid-pass.</p>
      <p>Local paired validation is complete for the listed cases. Broader input and strategy coverage, controlled Linux repetitions and comprehensive human code review remain open. Output agreement checks do not measure biological accuracy against a trusted reference alignment.</p>
    </section>
    <section id="reproduce" aria-labelledby="reproduce-title">
      <h2 id="reproduce-title">Reproduce and inspect</h2>
      <p>The executable remains <code>mafft</code>. The command tested here is <code>mafft --thread N input.fa</code> with no strategy override.</p>
      <p><a href="{repo}/blob/main/README.md">Build and usage</a> · <a href="{report}">Benchmark methods</a> · <a href="{evidence.replace('/tree/', '/blob/')}/measurements.csv">Per-run measurements</a> · <a href="{evidence}/results">Logs and stdout archives</a></p>
    </section>
    <section id="references" aria-labelledby="references-title">
      <h2 id="references-title">Acknowledgments and references</h2>
      <p>MAFFT was developed by Kazutaka Katoh and collaborators. The imported optimization is Yihan Hong's fast-mafft v10, source revision <code>6474c62da49ca3af73bbb7b05287bbbb4a2036e5</code>, based on upstream v7.526 revision <code>ee9799916df6a5d5103d46d54933f8eb6d28e244</code>.</p>
      <p><a href="https://mafft.cbrc.jp/alignment/software/">MAFFT and citations</a> · <a href="https://github.com/yih0nk/fast-mafft">Optimization source</a> · <a href="{repo}/blob/main/NOTICE.md">Attribution and license notices</a></p>
    </section>
  </main>
</body>
</html>
'''
    (site / 'benchmarks').mkdir(exist_ok=True)
    (site / 'benchmarks/numafft.html').write_text(page)
    print('Built NuMAFFT page and appended its project entry; run website build.py next.')


if __name__ == '__main__':
    main()
