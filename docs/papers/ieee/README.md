# IEEE English Paper Draft

This folder contains an IEEE conference-style English paper draft for the single-room spatial digital twin thesis prototype.

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

- Replace placeholder author names, affiliations, and emails.
- Check the target IEEE conference template, page limit, blind-review rule, copyright notice, and PDF eXpress requirement.
- Verify every BibTeX item against the final references you actually cite.
- Add real figures if the target venue expects visual architecture and result plots.
- Remove or rewrite the acknowledgement section if the venue uses double-blind review.
- Confirm that results are acceptable for the target venue; current results are simulation-based, not physical deployment data.
