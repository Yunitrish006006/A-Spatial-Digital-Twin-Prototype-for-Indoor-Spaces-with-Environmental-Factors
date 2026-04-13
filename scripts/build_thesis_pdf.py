from pathlib import Path
import shutil
import subprocess
import sys
from typing import Dict, Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
OUTPUTS = ROOT / "outputs"
PAPERS = OUTPUTS / "papers"

sys.path.insert(0, str(SCRIPT_DIR))
from build_thesis_docx import Block, build_blocks  # noqa: E402


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


def render_paragraph(text: str, align: str) -> str:
    escaped = latex_escape(text).replace("\n", r"\\")
    if align == "center":
        return r"\begin{center}" + escaped + r"\end{center}" + "\n"
    return escaped + "\n\n"


def render_bullets(items: Iterable[object]) -> str:
    lines = [r"\begin{itemize}"]
    lines.extend(rf"\item {latex_escape(item)}" for item in items)
    lines.append(r"\end{itemize}")
    return "\n".join(lines) + "\n"


def render_code(text: str) -> str:
    safe_text = str(text).replace("→", "->").replace("Σ", "sum")
    return "\n".join([r"\begin{Verbatim}[fontsize=\small]", safe_text, r"\end{Verbatim}"]) + "\n"


def column_spec(column_count: int) -> str:
    if column_count <= 1:
        return r"|p{0.88\textwidth}|"
    if column_count == 2:
        return r"|p{0.24\textwidth}|p{0.62\textwidth}|"
    width = 0.82 / column_count
    return "|" + "|".join(rf"p{{{width:.3f}\textwidth}}" for _ in range(column_count)) + "|"


def render_table(headers: List[object], rows: List[List[object]]) -> str:
    spec = column_spec(len(headers))
    lines = [r"\begin{center}", r"\small", rf"\begin{{longtable}}{{{spec}}}", r"\hline"]
    lines.append(" & ".join(rf"\textbf{{{latex_escape(header)}}}" for header in headers) + r" \\")
    lines.extend([r"\hline", r"\endfirsthead", r"\hline"])
    lines.append(" & ".join(rf"\textbf{{{latex_escape(header)}}}" for header in headers) + r" \\")
    lines.extend([r"\hline", r"\endhead"])
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        lines.append(" & ".join(latex_escape(cell) for cell in padded[: len(headers)]) + r" \\")
        lines.append(r"\hline")
    lines.extend([r"\end{longtable}", r"\end{center}"])
    return "\n".join(lines) + "\n"


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
    if kind == "page_break":
        return r"\clearpage" + "\n"
    raise ValueError(f"Unsupported block type: {kind}")


def render_document(blocks: List[Block]) -> str:
    body = "\n".join(render_block(block) for block in blocks)
    return rf"""\documentclass[12pt,a4paper]{{article}}
\usepackage[margin=2.5cm]{{geometry}}
\usepackage{{fontspec}}
\usepackage{{xeCJK}}
\usepackage{{setspace}}
\usepackage{{longtable}}
\usepackage{{fancyvrb}}
\usepackage{{array}}
\usepackage{{hyperref}}

\setmainfont{{Times New Roman}}
\setsansfont{{Arial}}
\setmonofont{{Menlo}}
\setCJKmainfont{{PingFang TC}}
\setCJKsansfont{{Heiti TC}}
\setCJKmonofont{{PingFang TC}}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
\hypersetup{{hidelinks}}
\onehalfspacing
\sloppy
\setlength{{\parindent}}{{2em}}
\setlength{{\parskip}}{{0.35em}}
\renewcommand{{\contentsname}}{{目錄}}

\begin{{document}}
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
