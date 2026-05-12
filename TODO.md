# TODO — Future MD → PPTX paths

Scratchpad for optional work. Not a roadmap commitment.

## Context

The canonical slide source is Markdown (typically [`slides.md`](slides.md)): slides are separated by a line that contains only `---` (see [README.md](README.md)). The shipped pipeline turns that into a standalone HTML deck via [`converter/md2html.py`](converter/md2html.py), with fidelity tied to **browser rendering**—MathJax, highlight.js, optional Graphviz blocks, Font Awesome, and custom CSS. Any **PPTX-oriented** tool is a different rendering engine; expect tradeoffs, not a pixel-perfect match.

## Vision: deck-lovers as a thin wrapper

A possible future mode: same `slides.md` (or `output/slides.md` after optional LaTeX extraction), run an **external** exporter, emit `slides.pptx`, and **skip** the HTML projector + FastAPI server when the goal is only a static file (e.g. import into Google Slides). In that mode, **live likes, QR companion, mirror WebSocket**, and related UI do not apply.

## Option A — Marp CLI

- Package: `@marp-team/marp-cli` (e.g. `marp slides.md --pptx -o slides.pptx`).
- Slide breaks: aligns well with `---`-style slide Markdown and Marp themes/CSS.
- **Strengths:** Purpose-built for MD decks; reasonable path for “authoring stays Markdown.”
- **Weaknesses:** LaTeX math in PPTX is typically weaker than in Marp’s HTML output; complex custom markup may need Marp-specific frontmatter or a fork of the source.

## Option B — Pandoc

- Example: `pandoc slides.md -o slides.pptx`; styling via `--reference-doc=my-template.pptx`.
- **Strengths:** Ubiquitous CLI; reference doc for branding.
- **Caveats:** PPTX slide boundaries are often driven by **heading levels / slide level**, not necessarily the same rules as a `---`-only deck-lovers file—may require reshaping Markdown or Lua filters. Code and math are not guaranteed to match HTML/MathJax quality.

## Option C — PptxGenJS or python-pptx

- **Nature:** Programmatic construction of OOXML (slides, text, images, tables).
- **Image-per-slide:** Matches the philosophy of the current client PDF path (rasterize each slide, pack into a file)—good **visual parity** with the HTML deck if captures come from the same DOM; slides are mostly **pictures**, not editable body text.
- **Cost:** Custom glue code and ongoing maintenance unless kept minimal.

## Limitations checklist (vs. current deck-lovers HTML)

- **LaTeX / MathJax:** PPTX usually gets plain text, simplified math, or images; full TeX fidelity needs a prerender or raster pipeline.
- **Graphviz (`dot` fenced blocks):** Not native in PPTX; requires prerender to images or dropping the feature in export.
- **Font Awesome, custom CSS, slide chrome:** May not transfer; layouts differ from HTML.
- **PDF paths:** Server-side PDF ([`converter/export_pdf.mjs`](converter/export_pdf.mjs)) and client raster PDF are **orthogonal** to PPTX; a PPTX exporter would be a separate step or container.

## Non-goals / open questions

- Single canonical `slides.md` vs. a Marp-tuned or Pandoc-tuned copy when syntax diverges.
- Whether to adopt Marp frontmatter globally or keep deck-lovers-flavored MD only.
- Docker / `deploy.sh` / CI: optional profile for Marp or Pandoc binaries vs. host-only tooling.

## See also

- [README.md](README.md) — current conversion pipeline, deploy, and slide format.
- [ARCHITECTURE.md](ARCHITECTURE.md) — component map and internals.
