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
            self.assertIn("FAIL", r.stderr, args)
        for args in (["--out", "x%y"], ["--model", "foo.pt"]):
            r = run("https://example.test/v", *args)
            self.assertEqual(r.returncode, 2, args)
            self.assertIn("FAIL", r.stderr, args)

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

    def _fake_tools(self, ok=True):
        d = pathlib.Path(tempfile.mkdtemp())
        body = "import sys\nsys.exit(%d)\n" % (0 if ok else 3)
        for n in ("ffmpeg", "yt-dlp"):
            (d / (n + ".py")).write_text(body, encoding="utf-8")
            (d / (n + ".cmd")).write_text('@"%s" "%%~dp0%s.py" %%*\r\n' % (sys.executable, n), encoding="utf-8")
            sh = d / n
            sh.write_text('#!/bin/sh\nexec "%s" "$(dirname "$0")/%s.py" "$@"\n' % (sys.executable, n), encoding="utf-8")
            sh.chmod(0o755)
        return d

    def _env_with(self, d):
        env = dict(os.environ)
        env["PATH"] = str(d) + os.pathsep + env.get("PATH", "")
        return env

    def test_tool_failure_is_a_clean_message_not_a_traceback(self):
        d = self._fake_tools(ok=False)
        f = d / "a.mp4"; f.write_bytes(b"x")
        r = run(str(f), "--out", str(d / "o"), env=self._env_with(d))
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("FAIL", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_stale_frames_are_removed(self):
        d = self._fake_tools(ok=True)
        f = d / "a.mp4"; f.write_bytes(b"x")
        o = d / "o"; (o / "frames").mkdir(parents=True); (o / "frames" / "f_099.jpg").write_bytes(b"old")
        run(str(f), "--out", str(o), env=self._env_with(d))
        self.assertFalse((o / "frames" / "f_099.jpg").exists())

    def test_skill_grants_only_the_plugin_script(self):
        t = (ROOT / "skills" / "watch-clip" / "SKILL.md").read_text(encoding="utf-8")
        line = [l for l in t.splitlines() if l.startswith("allowed-tools:")][0]
        self.assertEqual(line, "allowed-tools: Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/watch_clip.py *)")

    def test_no_personal_paths_or_secrets(self):
        import re
        for p in ROOT.rglob("*"):
            if p.is_file() and p.name != "test_watch_clip.py" and ".git" not in p.parts and "__pycache__" not in p.parts and p.suffix in (".py", ".md", ".json"):
                t = p.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"C:[\\/]Users|@gmail|sk-[A-Za-z0-9]{16}", t), str(p))


if __name__ == "__main__":
    unittest.main()
