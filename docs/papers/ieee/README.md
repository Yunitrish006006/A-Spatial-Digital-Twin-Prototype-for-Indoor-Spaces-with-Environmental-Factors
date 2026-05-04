# IEEE English Paper Draft

This folder contains the IEEE conference-style English paper draft for the single-room spatial digital twin thesis prototype.

As of 2026-05-01, the active submission target is `IoTaIS 2026`, the 2026 IEEE International Conference on Internet of Things and Intelligence Systems. The manuscript should be reframed from a digital-twin-first venue toward an IoT and intelligence-systems venue: sparse IoT sensing, indoor spatial intelligence, non-networked appliance impact learning, and decision-support services. The MCP interface remains a secondary service layer rather than the paper's headline novelty.

Current IoTaIS 2026 planning notes checked on 2026-05-01:

- Paper submission: `https://edas.info/N34817`.
- Full paper submission deadline: June 15, 2026.
- Full papers are listed as 6-7 pages using the IEEE paper template on A4 size pages; the camera-ready maximum is 7 pages without additional page charges, with 1 extra page allowed for a fee if accepted.
- Submissions are subject to blind review; author lists should be finalized before submission because IoTaIS notes that author-list changes are prohibited once a paper has been submitted for review.

Historical planning notes:

- IEEE Digital Twin 2026 full papers are listed as 6 pages, with at most 2 additional paid overlength pages if accepted; the full-paper submission deadline is May 1, 2026.
- IEEE DTPI 2026 lists a submission deadline of May 15, 2026 after extension.
- Recheck all deadline, page-limit, blind-review, copyright, and PDF eXpress requirements before any renewed submission.

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
