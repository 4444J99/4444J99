#!/usr/bin/env python3
"""Check the profile's local references without network access or file writes."""

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (ROOT / "README.md", ROOT / "assets/README.md")


class HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        self.references.extend(
            value for key, value in attrs if key in {"href", "src"} and value
        )


def main():
    errors = []
    checked = set()
    for document in DOCUMENTS:
        if not document.is_file():
            errors.append(f"Missing document: {document.relative_to(ROOT)}")
            continue
        content = document.read_text(encoding="utf-8")
        if not content.strip():
            errors.append(f"Empty document: {document.relative_to(ROOT)}")
        html = HTMLReferences()
        html.feed(content)
        references = re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", content)
        for reference in references + html.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"{document.relative_to(ROOT)}: invalid local target {reference}")
                continue
            checked.add(target)
            if target.suffix.lower() == ".svg":
                try:
                    ET.parse(target)
                except ET.ParseError as exc:
                    errors.append(f"Invalid SVG {target.relative_to(ROOT)}: {exc}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validated {len(DOCUMENTS)} documents and {len(checked)} local targets.")
    print("External URLs require a separate public-access check; no files were rewritten.")


if __name__ == "__main__":
    main()
