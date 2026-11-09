"""Checks for pagination, data privacy and failure preservation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

import generate


class ProfileTests(unittest.TestCase):
    def test_public_owned_repositories_across_pages(self):
        repo = {"id": 1, "private": False, "owner": {"login": "Masood-zone"}, "stargazers_count": 2}
        other = {**repo, "owner": {"login": "someone-else"}}
        private = {**repo, "private": True}
        with patch.object(generate, "github", side_effect=[{"followers": 12}, [{**repo, "id": n} for n in range(100)], [{**repo, "id": 100}, repo, other, private]]) as request:
            self.assertEqual(generate.fetch_stats("Masood-zone"), {"public_repos": 101, "stars": 202, "followers": 12})
            self.assertIn("page=2", request.call_args.args[0])

    def test_failed_fetch_preserves_panels(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "profile.json").write_text('{"username":"Masood-zone"}')
            for theme in generate.THEMES:
                (root / f"assets/profile-{theme}.svg").write_text("previous")
            with patch.object(generate, "ROOT", root), patch.object(generate, "fetch_stats", side_effect=RuntimeError("API unavailable")):
                with self.assertRaises(RuntimeError):
                    generate.main()
            for theme in generate.THEMES:
                self.assertEqual((root / f"assets/profile-{theme}.svg").read_text(), "previous")

    def test_both_panels_are_valid_xml(self):
        config = json.loads((generate.ROOT / "profile.json").read_text())
        config["name"] = "Name & <test>"
        art = generate.artwork()
        for theme in generate.THEMES:
            svg = generate.render(config, {"public_repos": 222, "stars": 0, "followers": 12}, theme, art)
            root = ElementTree.fromstring(svg)
            self.assertEqual(root.attrib["viewBox"], "0 0 1000 550")
            self.assertIn("Name &amp; &lt;test&gt;", svg)


if __name__ == "__main__":
    unittest.main()
