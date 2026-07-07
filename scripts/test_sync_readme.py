#!/usr/bin/env python3
"""Tests for scripts/sync-readme.py marker rendering.

Run:  python3 scripts/test_sync_readme.py
"""

import importlib.util
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("sync_readme", _HERE / "sync-readme.py")
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)


class RenderTests(unittest.TestCase):
    def test_replaces_marker_body(self):
        text = "x <!-- v:total_repos -->1<!-- /v --> y"
        out, warns = sr.render(text, {"total_repos": "171"})
        self.assertEqual(out, "x <!-- v:total_repos -->171<!-- /v --> y")
        self.assertEqual(warns, [])

    def test_multiple_markers_one_line(self):
        text = ("<!-- v:total_repos -->0<!-- /v --> / "
                "<!-- v:total_organs -->0<!-- /v -->")
        out, _ = sr.render(text, {"total_repos": "171", "total_organs": "10"})
        self.assertIn("<!-- v:total_repos -->171<!-- /v -->", out)
        self.assertIn("<!-- v:total_organs -->10<!-- /v -->", out)

    def test_profile_proof_metrics_render(self):
        text = (
            "<!-- v:public_repos -->0<!-- /v --> public / "
            "<!-- v:owned_ecosystem_repos -->0<!-- /v --> owned / "
            "<!-- v:contributed_repos -->0<!-- /v --> contributed"
        )
        out, warns = sr.render(
            text,
            {
                "public_repos": "203",
                "owned_ecosystem_repos": "301",
                "contributed_repos": "321",
            },
        )
        self.assertIn("<!-- v:public_repos -->203<!-- /v -->", out)
        self.assertIn("<!-- v:owned_ecosystem_repos -->301<!-- /v -->", out)
        self.assertIn("<!-- v:contributed_repos -->321<!-- /v -->", out)
        self.assertEqual(warns, [])

    def test_marker_without_data_is_left_and_warned(self):
        text = "<!-- v:unknown -->keep<!-- /v -->"
        out, warns = sr.render(text, {})
        self.assertEqual(out, text)
        self.assertTrue(any("unknown" in w for w in warns))

    def test_none_value_renders_empty(self):
        # main() normalizes None -> "" before render; the body must then be empty.
        text = "<!-- v:total_repos -->placeholder<!-- /v -->"
        data = {"total_repos": ("" if None is None else str(None))}
        out, _ = sr.render(text, data)
        self.assertEqual(out, "<!-- v:total_repos --><!-- /v -->")

    def test_data_without_marker_warns(self):
        out, warns = sr.render("no markers here", {"orphan": "1"})
        self.assertEqual(out, "no markers here")
        self.assertTrue(any("orphan" in w for w in warns))

    def test_idempotent(self):
        text = "<!-- v:total_repos -->171<!-- /v -->"
        once, _ = sr.render(text, {"total_repos": "171"})
        twice, _ = sr.render(once, {"total_repos": "171"})
        self.assertEqual(once, twice)

    def test_check_fails_when_marker_missing(self):
        # A data key with no marker in the README must fail --check, not pass silently.
        import os
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d) / "ecosystem.yml"
            rp = Path(d) / "README.md"
            dp.write_text("total_repos: 171\n", encoding="utf-8")
            rp.write_text("# readme with no markers\n", encoding="utf-8")
            os.environ["ECOSYSTEM_DATA"] = str(dp)
            os.environ["README_PATH"] = str(rp)
            old_argv = sys.argv
            try:
                sys.argv = ["sync-readme.py", "--check"]
                self.assertEqual(sr.main(), 1)
            finally:
                sys.argv = old_argv
                del os.environ["ECOSYSTEM_DATA"]
                del os.environ["README_PATH"]

    def test_real_readme_in_sync_with_data(self):
        """The committed README must already match the committed data file."""
        data_raw = sr.yaml.safe_load((sr.REPO_ROOT / "data/ecosystem.yml").read_text(encoding="utf-8"))
        # Mirror main()'s normalization (None -> "") so the guard matches real behavior.
        data = {k: ("" if v is None else str(v)) for k, v in data_raw.items()}
        readme = (sr.REPO_ROOT / "README.md").read_text(encoding="utf-8")
        out, _ = sr.render(readme, data)
        self.assertEqual(out, readme, "README.md is out of sync with data/ecosystem.yml")


if __name__ == "__main__":
    unittest.main()
