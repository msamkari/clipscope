#!/usr/bin/env python3
"""watch_clip.py <url-or-file> [--fps 0.5] [--max-frames 24] [--out DIR] [--transcribe] [--model small] [--lang CODE] [--audio-metrics]

Lets Claude "watch" a clip: downloads a PUBLIC video (yt-dlp, 720p at most, 500 MB at most) or reads a local file, then writes
frames/f_###.jpg (from the START of the clip only: fps x max-frames) and audio.mp3 (ffmpeg; a clip without audio just skips transcript and metrics). A downloaded video stays in the output folder as clip.*, optionally transcript.txt/.json (local openai-whisper) and audio_metrics.json.
Python standard library only. It uses the tools found on PATH (yt-dlp, ffmpeg, whisper) and installs nothing.
No login, no cookies, no keys. For analysis only: do not re-publish what it downloads.
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile
MODELS = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo", "tiny.en", "base.en", "small.en", "medium.en"}
from urllib.parse import urlparse

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


def run(cmd, what, **kw):
    try:
        return subprocess.run(cmd, check=True, **kw)
    except subprocess.CalledProcessError as e:
        fail(f"{what} failed (exit {e.returncode}). Nothing else was tried; ask the user before using other options.", 1)
    except OSError as e:
        fail(f"could not start {what}: {e}", 1)


def is_web_url(s):
    u = urlparse(s)
    return u.scheme in ("http", "https") and bool(u.netloc)


def slug(s):
    return re.sub(r"\W+", "_", s)[-40:].strip("_") or "clip"


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="watch_clip.py")
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
    local = os.path.isfile(a.src)
    if not local and not is_web_url(a.src):
        fail("the source must be an existing local file or an http(s) URL")
    out = (pathlib.Path(a.out) if a.out else pathlib.Path(tempfile.mkdtemp(prefix="watch-clip-"))).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("clip.*")) + list(out.glob("frames/f_*.jpg")) + [out / n for n in ("audio.mp3", "info_short.json", "transcript.txt", "transcript.json", "audio_metrics.json")]:
        if old.is_file() and old != pathlib.Path(a.src).resolve(): old.unlink()  # stale files from an earlier run must never be reused
    ffmpeg = need("ffmpeg")
    if local:
        video = pathlib.Path(a.src)
    else:
        ytdlp = need("yt-dlp")
        # --ignore-config: a user's yt-dlp config (exec hooks, cookies) must never apply here; "--" ends options before the URL.
        run([ytdlp, "--ignore-config", "--no-playlist", "--quiet", "--no-progress", "--max-filesize", "500M",
             "-f", "bv*[height<=720]+ba/b[height<=720]", "--merge-output-format", "mp4", "--write-info-json",
             "-o", str(out / "clip.%(ext)s"), "--", a.src], "yt-dlp", stdout=sys.stderr)
        found = sorted(out.glob("clip.*"))
        found = [f for f in found if f.suffix != ".json"]
        if not found: fail("yt-dlp produced no video file (the site may block downloads, or the video is over 720p only / 500 MB)", 1)
        video = found[0]
        ij = out / "clip.info.json"
        if ij.exists():
            d = json.load(open(ij, encoding="utf-8"))
            keep = {k: d.get(k) for k in ("title", "uploader", "duration", "view_count", "like_count", "comment_count", "upload_date", "description", "webpage_url")}
            if isinstance(keep.get("description"), str): keep["description"] = keep["description"][:2000]
            json.dump(keep, open(out / "info_short.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            ij.unlink()
    frames = out / "frames"
    frames.mkdir(exist_ok=True)
    run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-vf", f"fps={a.fps},scale=540:-2", "-frames:v", str(a.max_frames), str(frames / "f_%03d.jpg")], "ffmpeg (frames)")
    has_audio = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(out / "audio.mp3")]).returncode == 0 and (out / "audio.mp3").is_file()
    if not has_audio:
        print("WARN no audio track: transcript and audio metrics skipped", file=sys.stderr)
    if a.transcribe and has_audio:
        whisper = need("whisper")
        cmd = [whisper, str(out / "audio.mp3"), "--model", a.model, "--output_dir", str(out), "--output_format", "all", "--fp16", "False"]
        if a.lang: cmd += ["--language", a.lang]
        run(cmd, "whisper", env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}, stdout=sys.stderr)
        for ext in ("srt", "vtt", "tsv"):
            p = out / f"audio.{ext}"
            if p.exists(): p.unlink()
        for s, d in (("audio.txt", "transcript.txt"), ("audio.json", "transcript.json")):
            if (out / s).exists(): (out / s).replace(out / d)
    if a.audio_metrics and has_audio:
        r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(out / "audio.mp3"), "-af", "ebur128=peak=true,silencedetect=n=-35dB:d=0.6", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
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
