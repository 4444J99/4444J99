#!/usr/bin/env python3
"""Check rendered link/image destinations for local file existence inside the repo.

External URLs, fragments, and target file contents are outside this validator's
scope. Validation performs no network access or file writes.
"""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (ROOT / "README.md", ROOT / "assets/README.md")


class HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        attribute = {"a": "href", "img": "src"}.get(tag)
        self.references.extend(
            value for key, value in attrs if key == attribute and value
        )


def rendered_references(content):
    html = HTMLReferences()
    html.feed(MarkdownIt("commonmark").render(content))
    html.close()
    return html.references


def validate_documents(root, documents):
    root = root.resolve()
    errors = []
    checked = set()
    for document in documents:
        if not document.is_file():
            errors.append(f"Missing document: {document.relative_to(root)}")
            continue
        content = document.read_text(encoding="utf-8")
        if not content.strip():
            errors.append(f"Empty document: {document.relative_to(root)}")
        for reference in rendered_references(content):
            try:
                parsed = urlsplit(reference)
            except ValueError:
                errors.append(f"{document.relative_to(root)}: invalid destination {reference}")
                continue
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"{document.relative_to(root)}: invalid local file target {reference}")
                continue
            checked.add(target)
    return errors, checked


def main():
    errors, checked = validate_documents(ROOT, DOCUMENTS)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validated {len(DOCUMENTS)} documents and {len(checked)} local file targets.")
    print("External URLs, fragments, and target contents are not validated; no files were rewritten.")


if __name__ == "__main__":
    main()
