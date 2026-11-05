import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate-profile.py"
spec = importlib.util.spec_from_file_location("validate_profile", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ProfileValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "profile"
        self.root.mkdir()
        self.document = self.root / "README.md"

    def validate(self, markdown, files=()):
        self.document.write_text(markdown, encoding="utf-8")
        for name in files:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("File existence only; contents are not parsed.", encoding="utf-8")
        return validator.validate_documents(self.root, (self.document,))

    def test_reference_links_and_images(self):
        errors, checked = self.validate(
            "[Full][doc] [doc][] [doc] ![Image][picture]\n\n"
            "[doc]: target.md\n[picture]: image.svg\n",
            ("target.md", "image.svg"),
        )
        self.assertEqual(errors, [])
        self.assertEqual(checked, {self.root / "target.md", self.root / "image.svg"})

    def test_angle_destinations_with_spaces(self):
        errors, checked = self.validate(
            '[Document](<a b.md> "Title") ![Image](<chart image.svg>)',
            ("a b.md", "chart image.svg"),
        )
        self.assertEqual(errors, [])
        self.assertEqual(checked, {self.root / "a b.md", self.root / "chart image.svg"})

    def test_balanced_and_escaped_parentheses(self):
        errors, checked = self.validate(
            r"[Balanced](draft(v2).md) [Escaped](draft\(v2\).md)",
            ("draft(v2).md",),
        )
        self.assertEqual(errors, [])
        self.assertEqual(checked, {self.root / "draft(v2).md"})

    def test_code_examples_are_not_links(self):
        errors, checked = self.validate(
            '```markdown\n[Missing](missing.md)\n<img src="missing.svg">\n```\n\n'
            '`[Missing](inline.md)`\n\n    [Missing](indented.md)\n'
        )
        self.assertEqual(errors, [])
        self.assertEqual(checked, set())

    def test_missing_targets_fail_for_links_and_images(self):
        for markdown in (
            "[Missing](missing.md)",
            "[Missing][doc]\n\n[doc]: missing.md\n",
            "![Missing](missing.svg)",
        ):
            with self.subTest(markdown=markdown):
                errors, checked = self.validate(markdown)
                self.assertEqual(len(errors), 1)
                self.assertIn("invalid local file target", errors[0])
                self.assertEqual(checked, set())

    def test_html_link_and_image_destinations(self):
        errors, checked = self.validate(
            '<a href="a&amp;b.md">Read</a><img src="image.svg" />',
            ("a&b.md", "image.svg"),
        )
        self.assertEqual(errors, [])
        self.assertEqual(checked, {self.root / "a&b.md", self.root / "image.svg"})

    def test_external_urls_and_fragments_are_out_of_scope(self):
        errors, checked = self.validate(
            "[Web](https://example.invalid/missing) [Mail](mailto:example@example.invalid) "
            "[CDN](//example.invalid/missing) [Anchor](#missing) "
            "[Local](target.md?view=1#missing)",
            ("target.md",),
        )
        self.assertEqual(errors, [])
        self.assertEqual(checked, {self.root / "target.md"})

    def test_directory_is_not_a_file_target(self):
        (self.root / "directory").mkdir()
        errors, checked = self.validate("[Directory](directory/)")
        self.assertEqual(len(errors), 1)
        self.assertEqual(checked, set())

    def test_path_traversal_cannot_escape_repository(self):
        (self.root.parent / "outside.md").write_text("Outside", encoding="utf-8")
        for destination in ("../outside.md", "%2e%2e/outside.md"):
            with self.subTest(destination=destination):
                errors, checked = self.validate(f"[Outside]({destination})")
                self.assertEqual(len(errors), 1)
                self.assertEqual(checked, set())

    def test_symlink_cannot_escape_repository(self):
        outside = self.root.parent / "outside.md"
        outside.write_text("Outside", encoding="utf-8")
        (self.root / "linked.md").symlink_to(outside)
        errors, checked = self.validate("[Outside](linked.md)")
        self.assertEqual(len(errors), 1)
        self.assertEqual(checked, set())


if __name__ == "__main__":
    unittest.main()
