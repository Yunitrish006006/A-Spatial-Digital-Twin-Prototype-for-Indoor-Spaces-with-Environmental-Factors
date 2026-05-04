# Repository Working Rules

This repository contains one research project expressed in multiple synchronized artifacts. Any AI assistant editing this repository must treat the following outputs as one coupled deliverable, not as independent documents.

## Current Submission Target

As of 2026-05-01, the active submission target for the English IEEE-style manuscript is IoTaIS 2026, the 2026 IEEE International Conference on Internet of Things and Intelligence Systems.

- Active target: IoTaIS 2026.
- Submission system: EDAS, `https://edas.info/N34817`.
- Full paper deadline: June 15, 2026.
- Current format target: IEEE A4 conference paper, 6-7 pages for full papers.
- Former targets no longer active: IEEE Digital Twin 2026 and IEEE DTPI 2026.

Future edits to the IEEE manuscript should optimize for IoTaIS 2026's Internet of Things and intelligence systems scope. Frame the work around sparse IoT sensing, indoor spatial intelligence, non-networked appliance impact learning, and decision-support services. Keep the MCP interface as a secondary service layer rather than the paper's headline novelty.

This venue note records the current submission strategy only. It does not relax the synchronization rules below, and it does not imply that the IEEE manuscript is already submission-ready.

## Room Design Data Requirement

Any new room design, room scenario, or room-specific 3D dataset must follow `docs/requirements/room_design_format_requirements_zh.md`.

At minimum, the design must provide:

- A complete room dimension block with `width_m`, `length_m`, and `height_m`.
- A consistent 3D coordinate system using meters and the origin at the floor southwest corner.
- Sensor, zone, device, and furniture coordinates in `{x, y, z}` format.
- Bounding boxes for zones and furniture using `min_corner` and `max_corner`.
- Validation that every point and bounding box stays inside the room dimensions.

Use `docs/templates/room_design_template.json` for new designs and `docs/templates/room_design_standard_room_example.json` as the current reference room.

## Mandatory Synchronization Scope

Whenever the thesis topic, method, experiment setup, metrics, architecture, figures, chapter structure, or conclusions change, the assistant must update all of the following together:

- Chinese thesis source: `docs/thesis/thesis_draft_zh.md`
- Chinese thesis build source: `scripts/build_thesis_docx.py`
- Chinese thesis outputs:
  - `docs/papers/thesis/thesis_draft_zh.docx`
  - `docs/papers/thesis/thesis_draft_zh.pdf`
  - `outputs/papers/thesis_draft_zh.docx`
  - `outputs/papers/thesis_draft_zh.pdf`
- English IEEE paper source:
  - `docs/papers/ieee/paper.tex`
  - `docs/papers/ieee/references.bib`
- English IEEE output:
  - `docs/papers/ieee/paper.pdf`
- Presentation source:
  - `scripts/build_thesis_pptx.py`
  - `docs/thesis/presentation_outline_zh.md`
  - `docs/thesis/presentation_outline_zh_30min.md`
- Presentation outputs:
  - `outputs/papers/thesis_presentation_zh.pptx`
  - `outputs/papers/thesis_presentation_zh_30min.pptx`

If a change affects figures used by the thesis or slides, also update:

- `docs/thesis/system_architecture_diagrams_zh.md`
- `outputs/figures/architecture/*`
- `docs/papers/thesis/assets/*`

## Progress Consistency Rule

Chinese thesis, English paper, IEEE paper content, and presentation must remain at the same project progress level.

This means:

- If a new method is added to one artifact, it must appear in the others where relevant.
- If an old claim is removed or weakened in one artifact, it must be removed or weakened in the others.
- Metrics, scenario counts, benchmark results, and conclusions must not disagree across artifacts.
- Figure captions and slide wording must match the current thesis narrative.
- Placeholder text, outdated names, and deprecated architecture descriptions must be removed from every synchronized artifact, not just one.

## Source-of-Truth Rules

- The Chinese thesis source and `scripts/build_thesis_docx.py` must stay logically aligned.
- `paper.tex` is the source of truth for the IEEE manuscript.
- `scripts/build_thesis_pptx.py` is the source of truth for the presentation.
- Generated outputs must be rebuilt after source changes.
- Do not update only generated files while leaving source files stale.

## Definition of Done

A thesis-related edit is not complete unless all applicable items below are satisfied:

1. The affected Chinese thesis source is updated.
2. The affected English/IEEE source is updated.
3. The presentation source and outlines are updated.
4. Any affected architecture or result figures are rebuilt.
5. The generated `docx`, `pdf`, and `pptx` outputs are rebuilt.
6. No old metrics, names, captions, or claims remain in synchronized artifacts.

## Required Rebuild Commands

After synchronized edits, run the relevant commands:

```bash
python3 scripts/build_architecture_diagrams.py
python3 scripts/build_thesis_docx.py
python3 scripts/build_thesis_pdf.py
python3 scripts/build_thesis_pptx.py
cd docs/papers/ieee && tectonic --keep-logs --keep-intermediates paper.tex
```

If code or service behavior changed, also run:

```bash
python3 -m unittest discover -s tests
```

## Explicit Prohibitions

Do not do any of the following:

- Update only the Chinese thesis and leave the English paper behind.
- Update only the IEEE paper and leave the slides behind.
- Change benchmark numbers in one artifact without propagating them everywhere else.
- Leave placeholders such as fake emails, draft notes, or “should be revised” text in published outputs.
- Keep repository-structure details in thesis figures when the figure is supposed to describe research architecture.

## Short Instruction for Future AI Tools

If you are an AI assistant making thesis-related edits in this repository, assume that:

- Chinese thesis
- English/IEEE paper
- presentation

must always stay synchronized in scope, claims, metrics, and progress.

If you cannot update all of them in the same round, you must explicitly state that the work is incomplete.
