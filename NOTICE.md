# Source and attribution notices

NuMAFFT is the BioCode Commons packaging of the optimized MAFFT implementation
distributed as fast-mafft v10.

| Component | Origin |
| :--- | :--- |
| MAFFT base | MAFFT v7.526, Kazutaka Katoh and collaborators; upstream commit `ee9799916df6a5d5103d46d54933f8eb6d28e244` |
| Imported optimization | fast-mafft v10, Yihan Hong; source commit `6474c62da49ca3af73bbb7b05287bbbb4a2036e5` |
| BioCode Commons materials | NuMAFFT documentation, local benchmark packaging and website presentation |

The import and project rename preserve the source history and do not change the
alignment code. Retain the copyright notices, license conditions and disclaimers
in [LICENSE](LICENSE) and `fast-mafft-src/license`. Unchanged extension components
keep the notices in `fast-mafft-src/license.extensions`.

Local output archives include their own data notices in
`bench/biocode/THIRD_PARTY_NOTICES.md`. Data provenance is recorded in `bench/DATA.md`.

The original repositories remain at:

- https://gitlab.com/sysimm/mafft
- https://github.com/yih0nk/fast-mafft
