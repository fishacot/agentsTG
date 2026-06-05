"""List docs with optional YAML frontmatter (summary, read_when)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOCS = _ROOT / "docs"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _scan_docs(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not root.is_dir():
        return rows
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(_ROOT).as_posix()
        fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "path": rel,
                "summary": fm.get("summary", ""),
                "read_when": fm.get("read_when", ""),
            }
        )
    return rows


def _print_table(rows: list[dict[str, str]]) -> None:
    path_w = max(len(r["path"]) for r in rows) if rows else 4
    print(f"{'path':<{path_w}}  summary")
    print("-" * (path_w + 10))
    for row in rows:
        summary = row["summary"] or "—"
        read_when = row["read_when"]
        extra = f"  [read_when: {read_when}]" if read_when else ""
        print(f"{row['path']:<{path_w}}  {summary}{extra}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List docs/*.md with optional frontmatter fields."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of a table",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_DOCS,
        help="Docs root (default: docs/)",
    )
    args = parser.parse_args()

    rows = _scan_docs(args.root.resolve())
    if not rows:
        print(f"No markdown files under {args.root}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
