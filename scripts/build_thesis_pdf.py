from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Dict, Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
OUTPUTS = ROOT / "outputs"
PAPERS = ROOT / "docs" / "papers" / "thesis"

sys.path.insert(0, str(SCRIPT_DIR))
from build_thesis_docx import Block, build_blocks, ensure_image_asset  # noqa: E402


TEX_PATH = PAPERS / "thesis_draft_zh.tex"
PDF_PATH = PAPERS / "thesis_draft_zh.pdf"


def latex_escape(text: object) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_\allowbreak{}",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(text))


def render_title(text: str, level: int) -> str:
    size = r"\LARGE" if level == 0 else r"\Large"
    lines = [latex_escape(line) for line in text.splitlines()]
    body = r"\\[0.6em]".join(lines)
    return (
        r"\begin{center}" + "\n"
        rf"{{{size}\bfseries {body}}}" + "\n"
        r"\end{center}" + "\n"
    )


def render_heading(text: str, level: int) -> str:
    escaped = latex_escape(text)
    if level <= 1:
        return rf"\section*{{{escaped}}}" + "\n" + rf"\addcontentsline{{toc}}{{section}}{{{escaped}}}" + "\n"
    if level == 2:
        return rf"\subsection*{{{escaped}}}" + "\n"
    return rf"\subsubsection*{{{escaped}}}" + "\n"


def latex_escape_with_math(text: object) -> str:
    """Like latex_escape but preserves $...$ inline math segments unchanged."""
    parts = re.split(r'(\$[^$]+\$)', str(text))
    return "".join(part if i % 2 == 1 else latex_escape(part) for i, part in enumerate(parts))


def render_paragraph(text: str, align: str) -> str:
    escaped = latex_escape_with_math(text).replace("\n", r"\\")
    if align == "center":
        return r"\begin{center}" + escaped + r"\end{center}" + "\n"
    return escaped + "\n\n"


def render_bullets(items: Iterable[object]) -> str:
    lines = [r"\begin{itemize}"]
    lines.extend(rf"\item {latex_escape_with_math(item)}" for item in items)
    lines.append(r"\end{itemize}")
    return "\n".join(lines) + "\n"


def render_code(text: str) -> str:
    safe_text = str(text).replace("→", "->").replace("Σ", "sum").replace("φ", "phi").replace("θ", "theta").replace("≤", "<=").replace("≥", ">=")
    return "\n".join([r"\begin{lstlisting}[basicstyle=\footnotesize\ttfamily,breaklines=true,columns=flexible]", safe_text, r"\end{lstlisting}"]) + "\n"


def column_spec(column_count: int) -> str:
    if column_count <= 1:
        return r"|p{0.88\textwidth}|"
    if column_count == 2:
        return r"|p{0.24\textwidth}|p{0.62\textwidth}|"
    width = 0.78 / column_count
    return "|" + "|".join(rf"p{{{width:.3f}\textwidth}}" for _ in range(column_count)) + "|"


def render_table(headers: List[object], rows: List[List[object]]) -> str:
    spec = column_spec(len(headers))
    lines = [r"\begin{table}[htbp]", r"\centering", r"\footnotesize", rf"\begin{{tabular}}{{{spec}}}", r"\hline"]
    lines.append(" & ".join(rf"\textbf{{{latex_escape(header)}}}" for header in headers) + r" \\")
    lines.append(r"\hline")
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        lines.append(" & ".join(latex_escape(cell) for cell in padded[: len(headers)]) + r" \\")
        lines.append(r"\hline")
    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines) + "\n"


def render_math(latex: str, display: bool = True) -> str:
    if display:
        return "\\[\n" + latex + "\n\\]\n"
    return "$" + latex + "$"


def render_image(block: Block) -> str:
    asset_path = ensure_image_asset(block)
    asset_rel = asset_path.relative_to(PAPERS).as_posix()
    width_inches = float(block.get("width_inches", 5.8))
    text_width_ratio = min(0.9, max(0.45, width_inches / 7.0))
    caption = latex_escape(str(block["caption"]))
    return (
        r"\begin{figure}[htbp]" + "\n"
        r"\centering" + "\n"
        rf"\includegraphics[width={text_width_ratio:.2f}\textwidth]{{{asset_rel}}}" + "\n"
        r"\par\smallskip" + "\n"
        rf"{{\small {caption}}}" + "\n"
        r"\end{figure}" + "\n"
    )


def render_block(block: Block) -> str:
    kind = str(block["type"])
    if kind == "title":
        return render_title(str(block["text"]), int(block["level"]))
    if kind == "heading":
        return render_heading(str(block["text"]), int(block["level"]))
    if kind == "paragraph":
        return render_paragraph(str(block["text"]), str(block.get("align", "left")))
    if kind == "bullets":
        return render_bullets(block["items"])
    if kind == "code":
        return render_code(str(block["text"]))
    if kind == "table":
        return render_table(list(block["headers"]), list(block["rows"]))
    if kind == "image":
        return render_image(block)
    if kind == "math":
        return render_math(str(block["latex"]), bool(block.get("display", True)))
    if kind == "raw_latex":
        return str(block["content"]) + "\n"
    if kind == "page_break":
        return r"\clearpage" + "\n"
    raise ValueError(f"Unsupported block type: {kind}")


def render_document(blocks: List[Block]) -> str:
    body = "\n".join(render_block(b) for b in blocks)
    return rf"""\documentclass[12pt,a4paper]{{article}}
\usepackage[top=2.54cm,bottom=2.54cm,left=2.54cm,right=2.54cm]{{geometry}}
\usepackage{{fontspec}}
\usepackage{{xeCJK}}
\usepackage{{array}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage{{amsmath}}
\usepackage{{listings}}
\usepackage{{setspace}}
\usepackage{{indentfirst}}

\setmainfont{{Times New Roman}}
\setsansfont{{Arial}}
\setmonofont{{Menlo}}
\setCJKmainfont[BoldFont=BiauKaiTC]{{BiauKaiTC}}
\setCJKsansfont{{Heiti TC}}
\setCJKmonofont{{PingFang TC}}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
\hypersetup{{hidelinks}}
\sloppy
\setlength{{\parindent}}{{2em}}
\setlength{{\parskip}}{{0pt}}
\onehalfspacing
\renewcommand{{\contentsname}}{{目錄}}

\begin{{document}}
\pagenumbering{{roman}}
{body}
\end{{document}}
"""


def write_latex(path: Path, blocks: List[Block]) -> None:
    path.write_text(render_document(blocks), encoding="utf-8")


def compile_pdf(tex_path: Path) -> None:
    tectonic = shutil.which("tectonic")
    if tectonic is None:
        raise SystemExit("tectonic not found. Install tectonic first, then rerun this script.")
    command = [
        tectonic,
        "--keep-logs",
        "--outdir",
        str(PAPERS),
        str(tex_path),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    PAPERS.mkdir(parents=True, exist_ok=True)
    blocks = build_blocks()
    write_latex(TEX_PATH, blocks)
    compile_pdf(TEX_PATH)
    print(f"Wrote {TEX_PATH}")
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
