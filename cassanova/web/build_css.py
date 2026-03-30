"""Recursively resolve CSS @import chains and produce a single bundled file."""

import re
from pathlib import Path

_IMPORT_PATTERN = re.compile(r"""@import\s+url\(['"]?([^'")]+)['"]?\)\s*;""")

_STYLES_DIR = Path(__file__).parent / "static" / "styles" / "app"
_OUTPUT_FILE = _STYLES_DIR / "bundle.css"


def _resolve_imports(css_path: Path, seen: set[Path]) -> str:
    resolved = css_path.resolve()
    if resolved in seen:
        return ""
    seen.add(resolved)

    text = css_path.read_text(encoding="utf-8")
    parts: list[str] = []

    for line in text.splitlines(keepends=True):
        match = _IMPORT_PATTERN.match(line.strip())
        if match:
            import_target = match.group(1)
            import_path = (css_path.parent / import_target).resolve()
            if import_path.exists():
                parts.append(f"\n/* === {import_path.relative_to(_STYLES_DIR)} === */\n")
                parts.append(_resolve_imports(import_path, seen))
            else:
                parts.append(line)
        else:
            parts.append(line)

    return "".join(parts)


def build() -> None:
    entry = _STYLES_DIR / "main.css"
    bundle = _resolve_imports(entry, set())
    _OUTPUT_FILE.write_text(bundle, encoding="utf-8")
    size_kb = _OUTPUT_FILE.stat().st_size / 1024
    print(f"Bundled CSS: {_OUTPUT_FILE} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    build()
