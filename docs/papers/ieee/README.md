# IEEE English Paper Draft

This folder contains the IEEE conference-style English paper draft for the single-room spatial digital twin thesis prototype.

The current framing is aligned first for `IEEE Digital Twin 2026`, colocated with `IEEE Smart World Congress 2026`. The backup venue is `IEEE DTPI 2026`. The main contribution is sparse-sensing indoor field estimation and non-networked appliance impact learning, while the MCP interface is treated as a secondary service layer rather than the paper's headline novelty.

As checked on 2026-04-24:

- IEEE Digital Twin 2026 full papers are listed as 6 pages, with at most 2 additional paid overlength pages if accepted; the full-paper submission deadline is May 1, 2026.
- IEEE DTPI 2026 lists a submission deadline of May 15, 2026 after extension.

## Files

- `paper.tex`
  Main IEEE-style LaTeX manuscript using `IEEEtran`.
- `references.bib`
  BibTeX references used by the manuscript.
- `paper.pdf`
  Locally compiled PDF output.

## Compile

Use Overleaf or a local TeX distribution:

```bash
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex
```

This machine now has `tectonic` installed through Homebrew, so the current PDF can also be regenerated with:

```bash
tectonic --keep-logs --keep-intermediates paper.tex
```

## Before IEEE Submission

- Recheck the target IEEE conference template, page limit, blind-review rule, copyright notice, and PDF eXpress requirement immediately before submission.
- Verify every BibTeX item against the final references you actually cite.
- Remove or rewrite the acknowledgement section if the final venue uses double-blind review.
- Keep the validation wording aligned with the current evidence hierarchy: synthetic full-field results, real-bedroom sparse calibration at a held-out pillow point, public task-aligned benchmarks, and recommendation actions pending physical intervention validation.
