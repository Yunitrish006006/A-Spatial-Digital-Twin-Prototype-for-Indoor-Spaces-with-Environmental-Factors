import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MARKDOWN = ROOT / "docs" / "thesis" / "system_architecture_diagrams_zh.md"
OUTPUT_DIR = ROOT / "outputs" / "figures" / "architecture"


def slugify(text: str) -> str:
    normalized = re.sub(r"^\d+\.\s*", "", text.strip())
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "diagram"


def extract_mermaid_diagrams(markdown: str):
    pattern = re.compile(r"^##\s+(.+?)\n+```mermaid\n(.*?)\n```", re.MULTILINE | re.DOTALL)
    return [(title.strip(), body.strip() + "\n") for title, body in pattern.findall(markdown)]


def render_diagram(title: str, mermaid_source: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{slugify(title)}.svg"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        source_path = temp_dir_path / "diagram.mmd"
        source_path.write_text(mermaid_source, encoding="utf-8")
        subprocess.run(
            [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli",
                "-i",
                str(source_path),
                "-o",
                str(output_path),
                "-b",
                "transparent",
            ],
            check=True,
            cwd=str(ROOT),
        )
    return output_path


def main() -> None:
    markdown = SOURCE_MARKDOWN.read_text(encoding="utf-8")
    diagrams = extract_mermaid_diagrams(markdown)
    if not diagrams:
        raise SystemExit("No Mermaid diagrams found in source markdown.")

    rendered = [render_diagram(title, body) for title, body in diagrams]
    expected_names = {path.name for path in rendered}
    for stale in OUTPUT_DIR.glob("*.svg"):
        if stale.name not in expected_names:
            stale.unlink()
    print("Rendered architecture diagrams:")
    for path in rendered:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
