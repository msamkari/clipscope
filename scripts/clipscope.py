#!/usr/bin/env python3
"""clipscope.py <url-or-file> [--fps 0.5] [--max-frames 24] [--out DIR] [--transcribe] [--model small] [--lang CODE] [--audio-metrics]

Lets Claude "watch" a clip: downloads a PUBLIC video (yt-dlp, 720p preferred, 500 MB at most) or reads a local file, then writes
frames/f_###.jpg (from the START of the clip only: fps x max-frames) and audio.mp3 (ffmpeg; a clip without audio just skips transcript and metrics). A downloaded video stays in the output folder as clip.*, optionally transcript.txt/.json (local openai-whisper) and audio_metrics.json.
audio_metrics.json is measured on the 16 kHz mono mp3 made by this script, not on the original audio: loudness and peak are approximate.
--out must be a new or empty folder (or a folder under the system temp dir). Before yt-dlp runs, the URL and its HTTP redirects (HEAD, max 5 hops, 10 s per hop, http/https only) are checked and refused when any hop is, or resolves to, a loopback/private address. This is a best-effort check, not a network sandbox: requests made inside yt-dlp's extractors and DNS changes after the check are NOT covered. UNC/network paths are refused as sources.
Before a run, the files this script itself names inside --out (clip.*, frames/f_*.jpg, audio.mp3, info_short.json, transcript.txt/.json, audio_metrics.json) are deleted; nothing else is touched, so use a new folder. Every tool call has a timeout.
Python standard library only. It uses the tools found on PATH (yt-dlp, ffmpeg, whisper) and installs nothing.
No login, no cookies, no keys. For analysis only: do not re-publish what it downloads.
"""
import argparse, ipaddress, json, os, pathlib, re, shutil, socket, subprocess, sys, tempfile, unicodedata
import urllib.error, urllib.request
MODELS = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo", "tiny.en", "base.en", "small.en", "medium.en"}
from urllib.parse import urlparse, urljoin

INSTALL_HINT = {
    "yt-dlp": "install yt-dlp (https://github.com/yt-dlp/yt-dlp)",
    "ffmpeg": "install ffmpeg (https://ffmpeg.org/download.html)",
    "whisper": "install openai-whisper (pip install openai-whisper) and make sure `whisper` is on PATH",
}


def fail(msg, code=2):
    print("FAIL " + msg, file=sys.stderr)
    sys.exit(code)


def need(tool):
    p = shutil.which(tool)
    if not p:
        fail(f"`{tool}` was not found on PATH: {INSTALL_HINT[tool]}. This plugin does not install anything.")
    return p


TIMEOUT = {"yt-dlp": 900, "ffmpeg": 600, "whisper": 3600, "metrics": 300}


def run(cmd, what, timeout=600, **kw):
    try:
        return subprocess.run(cmd, check=True, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        fail(f"{what} timed out after {timeout} s and was stopped.", 1)
    except subprocess.CalledProcessError as e:
        fail(f"{what} failed (exit {e.returncode}). Nothing else was tried; ask the user before using other options.", 1)
    except OSError as e:
        fail(f"could not start {what}: {e}", 1)


def is_web_url(s):
    u = urlparse(s)
    return u.scheme in ("http", "https") and bool(u.netloc)


def public_host_error(url, resolver=socket.getaddrinfo):
    """Return an error string if the URL's host is, or resolves to, a non-public address; else None. Best effort only."""
    host = urlparse(url).hostname
    if not host: return "the URL has no host"
    try:
        infos = resolver(host, None)
    except OSError:
        return f"host {host} cannot be resolved here; refusing to fetch it"  # fail closed: odd forms (127.1, 0x7f000001) must not slip through
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            return f"host {host} resolves to a non-public address ({ip}); refusing to fetch it"
    return None


MAX_HOPS = 5
HOP_TIMEOUT = 10


class Refused(Exception):
    """A redirect hop (or the URL itself) failed the public-host check."""


def is_unc(s):
    return s.startswith("\\\\") or s.startswith("//")


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    """Follows redirects one by one and checks every hop's host with public_host_error (http/https only, MAX_HOPS at most)."""

    def __init__(self, resolver=socket.getaddrinfo):
        self.resolver = resolver
        self.hops = 0

    http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302  # Python < 3.11 does not follow 308 by itself

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops += 1
        if self.hops > MAX_HOPS:
            raise Refused(f"more than {MAX_HOPS} redirects; refusing to fetch it")
        target = urljoin(req.full_url, newurl)
        if urlparse(target).scheme not in ("http", "https"):
            raise Refused("a redirect leaves http/https; refusing to fetch it")
        err = public_host_error(target, self.resolver)
        if err:
            raise Refused("a redirect hop was refused: " + err)
        return urllib.request.Request(target, headers=dict(req.headers), method=req.get_method())  # req.headers only: header_items() would carry the previous hop's Host


def follow_redirects(url, resolver=socket.getaddrinfo, timeout=HOP_TIMEOUT):
    """Walk the redirect chain of `url` ourselves; return an error string if any hop is non-public (or the chain cannot be checked), else None.
    Best effort: what yt-dlp's extractors request internally, and DNS answers that change after this check, are not covered."""
    if urlparse(url).scheme not in ("http", "https"):
        return "the URL is not http/https"
    err = public_host_error(url, resolver)
    if err: return err
    handler = CheckedRedirect(resolver)
    opener = urllib.request.build_opener(handler)
    ua = {"User-Agent": "clipscope-redirect-check"}
    req = urllib.request.Request(url, headers=ua, method="HEAD")
    try:
        for attempt in (0, 1):
            try:
                opener.open(req, timeout=timeout).close()
            except urllib.error.HTTPError as e:
                e.close()
                if e.code in (405, 501) and attempt == 0:  # HEAD not allowed: ask for one byte with GET instead
                    req = urllib.request.Request(e.geturl() or url, headers=dict(ua, Range="bytes=0-0"), method="GET")
                    continue
                if e.code in (301, 302, 303, 307, 308):  # urllib itself declined to follow (for example file://): never pass that on
                    return "a redirect could not be followed and checked; refusing to fetch it"
                # any other HTTP status ends the chain (every hop up to here was checked); yt-dlp reports a real failure itself
            break
    except Refused as e:
        return str(e)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"could not check the redirects of this URL ({type(e).__name__}); refusing to fetch it"
    return None


_DROP = {"Cf", "Cs", "Co"}
_SPACE = {"Cc", "Zl", "Zp"}


def clean(v, n=200):
    """Text from a video page is untrusted: drop control/format/surrogate/private-use characters, collapse whitespace, cap the length."""
    out = []
    for ch in str(v):
        cat = unicodedata.category(ch)
        if cat in _DROP: continue
        out.append(" " if (cat in _SPACE or ch.isspace()) else ch)
    return " ".join("".join(out).split())[:n]


def check_out_dir(out):
    if out.exists():
        if not out.is_dir(): fail("--out must be a folder")
        tmp = pathlib.Path(tempfile.gettempdir()).resolve()
        if any(out.iterdir()) and tmp not in out.parents:
            fail("--out must be a new or empty folder (or a folder under the system temp dir)")


def slug(s):
    return re.sub(r"\W+", "_", s)[-40:].strip("_") or "clip"


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="clipscope.py")
    ap.add_argument("src", help="public video URL (http/https) or a local video file")
    ap.add_argument("--fps", type=float, default=0.5)
    ap.add_argument("--max-frames", type=int, default=24)
    ap.add_argument("--out", default=None)
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--model", default="small")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--audio-metrics", action="store_true")
    a = ap.parse_args(argv)
    if not (0 < a.fps <= 30): fail("--fps must be between 0 and 30")
    if not (1 <= a.max_frames <= 200): fail("--max-frames must be between 1 and 200")
    if a.lang is not None and not re.fullmatch(r"[A-Za-z]{2,3}", a.lang): fail("--lang must be a language code such as en or ar")
    if a.model not in MODELS: fail("--model must be one of: " + ", ".join(sorted(MODELS)))
    if a.out is not None and "%" in a.out: fail("--out must not contain %")
    return a


def main(argv=None):
    a = parse_args(sys.argv[1:] if argv is None else argv)
    if is_unc(a.src):
        fail("network (UNC) paths are not accepted as a source; copy the file to a local folder first")
    local = os.path.isfile(a.src)
    if not local and not is_web_url(a.src):
        fail("the source must be an existing local file or an http(s) URL")
    if not local:
        err = follow_redirects(a.src)
        if err: fail(err)
    if a.out and is_unc(a.out): fail("--out must be a local folder, not a network (UNC) path")
    out = (pathlib.Path(a.out) if a.out else pathlib.Path(tempfile.mkdtemp(prefix="clipscope-"))).resolve()
    if "%" in str(out): fail("the resolved output path must not contain % (yt-dlp and ffmpeg read it as a pattern); choose another --out")
    check_out_dir(out)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        fail(f"cannot create --out {out}: {e}")
    for old in list(out.glob("clip.*")) + list(out.glob("frames/f_*.jpg")) + [out / n for n in ("audio.mp3", "info_short.json", "transcript.txt", "transcript.json", "audio_metrics.json")]:
        if old.is_file() and old != pathlib.Path(a.src).resolve(): old.unlink()  # stale files from an earlier run must never be reused
    ffmpeg = need("ffmpeg")
    if local:
        video = pathlib.Path(a.src)
    else:
        ytdlp = need("yt-dlp")
        # --ignore-config: a user's yt-dlp config (exec hooks, cookies) must never apply here; "--" ends options before the URL.
        run([ytdlp, "--ignore-config", "--no-playlist", "--quiet", "--no-progress", "--max-filesize", "500M",
             "-f", "bv*[height<=720]+ba/b[height<=720]/b", "--merge-output-format", "mp4", "--write-info-json",
             "-o", str(out / "clip.%(ext)s"), "--", a.src], "yt-dlp", timeout=TIMEOUT["yt-dlp"], stdout=sys.stderr)
        found = sorted(out.glob("clip.*"))
        found = [f for f in found if f.suffix != ".json"]
        if not found: fail("yt-dlp produced no video file (the site may block downloads, or the video is over 500 MB)", 1)
        video = found[0]
        ij = out / "clip.info.json"
        if ij.exists():
            d = json.load(open(ij, encoding="utf-8"))
            caps = {"title": 200, "uploader": 200, "upload_date": 20, "description": 2000, "webpage_url": 500}
            keep = {}
            for k in ("title", "uploader", "duration", "view_count", "like_count", "comment_count", "upload_date", "description", "webpage_url"):
                v = d.get(k)
                if k in caps: keep[k] = clean(v, caps[k]) if isinstance(v, str) else None
                else: keep[k] = v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
            json.dump(keep, open(out / "info_short.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            ij.unlink()
    frames = out / "frames"
    frames.mkdir(exist_ok=True)
    run([ffmpeg, "-y", "-loglevel", "error", "-protocol_whitelist", "file", "-i", str(video), "-vf", f"fps={a.fps},scale=540:-2", "-frames:v", str(a.max_frames), str(frames / "f_%03d.jpg")], "ffmpeg (frames)", timeout=TIMEOUT["ffmpeg"])
    try:
        has_audio = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-protocol_whitelist", "file", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(out / "audio.mp3")], timeout=TIMEOUT["ffmpeg"]).returncode == 0 and (out / "audio.mp3").is_file()
    except subprocess.TimeoutExpired:
        fail("ffmpeg (audio) timed out and was stopped.", 1)
    if not has_audio:
        print("WARN no audio track: transcript and audio metrics skipped", file=sys.stderr)
    if a.transcribe and has_audio:
        whisper = need("whisper")
        cmd = [whisper, str(out / "audio.mp3"), "--model", a.model, "--output_dir", str(out), "--output_format", "all", "--fp16", "False"]
        if a.lang: cmd += ["--language", a.lang]
        run(cmd, "whisper", timeout=TIMEOUT["whisper"], env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}, stdout=sys.stderr)
        for ext in ("srt", "vtt", "tsv"):
            p = out / f"audio.{ext}"
            if p.exists(): p.unlink()
        for s, d in (("audio.txt", "transcript.txt"), ("audio.json", "transcript.json")):
            if (out / s).exists(): (out / s).replace(out / d)
    if a.audio_metrics and has_audio:
        try:
            r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-protocol_whitelist", "file", "-i", str(out / "audio.mp3"), "-af", "ebur128=peak=true,silencedetect=n=-35dB:d=0.6", "-f", "null", "-"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT["metrics"]).stderr
        except subprocess.TimeoutExpired:
            fail("ffmpeg (audio metrics) timed out and was stopped.", 1)
        def last(pat):
            m = re.findall(pat, r)
            return float(m[-1]) if m else None
        sil = re.findall(r"silence_duration: ([\d.]+)", r)
        json.dump({"integrated_lufs": last(r"I:\s+(-?[\d.]+) LUFS"), "loudness_range_lu": last(r"LRA:\s+([\d.]+) LU"),
                   "true_peak_dbtp": last(r"Peak:\s+(-?[\d.]+) dBFS"), "silences_over_0_6s": len(sil),
                   "silence_total_s": round(sum(map(float, sil)), 2)}, open(out / "audio_metrics.json", "w"), indent=1)
    print("OUT", out)
    print("FRAMES", len(list(frames.glob("*.jpg"))))


if __name__ == "__main__":
    main()
