import os, pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = str(ROOT / "scripts" / "watch_clip.py")


def run(*args, env=None):
    e = dict(os.environ)
    if env is not None: e = env
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e)


class WatchClipTests(unittest.TestCase):
    def test_rejects_non_http_source(self):
        for bad in ("file:///etc/passwd", "ftp://x.test/a.mp4", "javascript:alert(1)", "not-a-file-or-url"):
            r = run(bad)
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("http(s) URL", r.stderr)

    def test_rejects_bad_options(self):
        for args in (["--fps", "0"], ["--fps", "99"], ["--max-frames", "0"], ["--max-frames", "9999"], ["--lang", "ar;rm"], ["--model", "../x"]):
            r = run("https://example.test/v", *args)
            self.assertEqual(r.returncode, 2, args)

    def test_missing_ffmpeg_gives_install_hint_and_installs_nothing(self):
        d = tempfile.mkdtemp()
        f = pathlib.Path(d) / "a.mp4"; f.write_bytes(b"x")
        env = {"PATH": d, "SystemRoot": os.environ.get("SystemRoot", "")}
        r = run(str(f), "--out", str(pathlib.Path(d) / "o"), env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("ffmpeg", r.stderr)
        self.assertIn("does not install anything", r.stderr)

    def test_url_is_passed_after_double_dash_and_config_ignored(self):
        src = pathlib.Path(SCRIPT).read_text(encoding="utf-8")
        self.assertIn('"--ignore-config"', src)
        self.assertIn('"--", a.src', src)
        for banned in ("--cookies", "--exec", "--plugin-dirs", "--update-to", "cookies-from-browser"):
            self.assertNotIn(banned, src)

    def test_no_personal_paths_or_secrets(self):
        import re
        for p in ROOT.rglob("*"):
            if p.is_file() and p.name != "test_watch_clip.py" and ".git" not in p.parts and "__pycache__" not in p.parts and p.suffix in (".py", ".md", ".json"):
                t = p.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"C:[\\/]Users|@gmail|sk-[A-Za-z0-9]{16}", t), str(p))


if __name__ == "__main__":
    unittest.main()
