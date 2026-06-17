"""Unit tests for appstore_shots.py — parsing + orchestration, no real network.

The three HTTP funcs (_http_json / _http_text / _download) are monkeypatched so the
iTunes-API JSON parsing, Google-Play HTML scraping, and the download/manifest
orchestration are all exercised offline and deterministically.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import appstore_shots as A  # noqa: E402


IOS_JSON = {
    "resultCount": 2,
    "results": [
        {"trackName": "Habitica", "sellerName": "HabitRPG",
         "trackViewUrl": "https://apps.apple.com/us/app/id1",
         "screenshotUrls": ["https://is1.example/1.png", "https://is1.example/2.jpg"],
         "ipadScreenshotUrls": ["https://ipad.example/1.png"]},
        {"trackName": "Streaks", "sellerName": "Crunchy",
         "trackViewUrl": "https://apps.apple.com/us/app/id2",
         "screenshotUrls": [],  # falls back to ipad
         "ipadScreenshotUrls": ["https://ipad.example/2.png"]},
    ],
}

ANDROID_SEARCH_HTML = """
<a href="/store/apps/details?id=com.foo.bar">Foo</a>
<a href="/store/apps/details?id=com.foo.bar">dup</a>
<a href="/store/apps/details?id=com.baz.qux">Baz</a>
"""

ANDROID_DETAILS_HTML = """
<title>Foo App - Apps on Google Play</title>
<img src="https://play-lh.googleusercontent.com/ICON=w64-h64-rw"/>
<img src="https://play-lh.googleusercontent.com/SHOTA=w512-h1024"/>
<img src="https://play-lh.googleusercontent.com/SHOTB=w512-h1024-rw"/>
"""


class IosParse(unittest.TestCase):
    def test_search_maps_results_and_ipad_fallback(self):
        A._http_json = lambda url, timeout=15: dict(IOS_JSON)
        apps = A.ios_search("habit", limit=2)
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0]["platform"], "ios")
        self.assertEqual(apps[0]["name"], "Habitica")
        self.assertEqual(apps[0]["shots"], ["https://is1.example/1.png", "https://is1.example/2.jpg"])
        # second app has no iphone shots -> ipad fallback
        self.assertEqual(apps[1]["shots"], ["https://ipad.example/2.png"])

    def test_lookup_one(self):
        A._http_json = lambda url, timeout=15: dict(IOS_JSON)
        apps = A.ios_lookup("1")
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["name"], "Habitica")


class AndroidParse(unittest.TestCase):
    def test_search_extracts_unique_packages(self):
        A._http_text = lambda url, timeout=15: ANDROID_SEARCH_HTML
        pkgs = A.android_search("habit", limit=5)
        self.assertEqual(pkgs, ["com.foo.bar", "com.baz.qux"])

    def test_search_respects_limit(self):
        A._http_text = lambda url, timeout=15: ANDROID_SEARCH_HTML
        self.assertEqual(A.android_search("habit", limit=1), ["com.foo.bar"])

    def test_details_name_and_filters_icon(self):
        A._http_text = lambda url, timeout=15: ANDROID_DETAILS_HTML
        app = A.android_details("com.foo.bar")
        self.assertEqual(app["platform"], "android")
        self.assertEqual(app["name"], "Foo App")
        # the 64x64 icon is filtered; the two 512x1024 screenshots stay
        self.assertEqual(len(app["shots"]), 2)
        self.assertTrue(all("play-lh" in s for s in app["shots"]))


class Helpers(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(A._slug("Foo App!! 2026"), "foo-app-2026")
        self.assertEqual(A._slug(""), "app")

    def test_ext_from_url(self):
        self.assertEqual(A._ext_from_url("https://x/1.jpg"), ".jpg")
        self.assertEqual(A._ext_from_url("https://x/abc=w512-h1024"), ".png")


class Orchestration(unittest.TestCase):
    def setUp(self):
        # canned HTTP for all three sources
        A._http_json = lambda url, timeout=15: dict(IOS_JSON)

        def fake_download(url, path, timeout=30):
            with open(path, "wb") as f:
                f.write(b"img-bytes")
            return 9
        A._download = fake_download

    def test_collect_ios_downloads_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = A.collect("ios", d, term="habit", limit=2)
            # 2 apps, app1 has 2 shots, app2 has 1 -> 3 files total
            self.assertEqual(len(manifest), 2)
            total = sum(len(a["files"]) for a in manifest)
            self.assertEqual(total, 3)
            # files actually written
            for app in manifest:
                for rel in app["files"]:
                    self.assertTrue(os.path.isfile(os.path.join(d, rel)))
            # manifest.json on disk
            with open(os.path.join(d, "manifest.json")) as f:
                self.assertEqual(len(json.load(f)), 2)

    def test_max_shots_cap(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = A.collect("ios", d, term="habit", limit=1, max_shots=1)
            self.assertEqual(len(manifest), 1)
            self.assertEqual(len(manifest[0]["files"]), 1)  # capped from 2 to 1

    def test_collect_android(self):
        A._http_text = lambda url, timeout=15: (
            ANDROID_SEARCH_HTML if "search" in url else ANDROID_DETAILS_HTML)
        with tempfile.TemporaryDirectory() as d:
            manifest = A.collect("android", d, term="habit", limit=1)
            self.assertEqual(len(manifest), 1)
            self.assertEqual(manifest[0]["platform"], "android")
            self.assertEqual(len(manifest[0]["files"]), 2)


if __name__ == "__main__":
    unittest.main()
