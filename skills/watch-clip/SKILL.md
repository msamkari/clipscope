---
name: watch-clip
description: Watch a public video link (Instagram, TikTok, YouTube, X ...) or a local video file - extract frames and audio, optionally transcribe speech locally. Use when the user sends a video link or file and wants Claude to watch, analyse hooks, pacing or captions, or transcribe it. No login, cookies or keys.
allowed-tools: Read, Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/watch_clip.py *)
---

# watch-clip

Run (the command must have exactly this form, no quotes around the script path):

python ${CLAUDE_PLUGIN_ROOT}/scripts/watch_clip.py <url-or-file> --fps 0.5 --max-frames 24 [--transcribe --model small --lang <code>] [--audio-metrics] [--out <folder in the scratchpad>]

It writes `frames/f_###.jpg`, `audio.mp3`, `info_short.json` (for downloads), and with `--transcribe` `transcript.txt` and `transcript.json`; with `--audio-metrics` `audio_metrics.json` (loudness, true peak, silences over 0.6 s). It prints `OUT <folder>` and `FRAMES <n>`.

Then Read `info_short.json`, Read several frames in parallel to see the video, and Read the transcript.

Rules:
- Public videos only. Never pass cookies, passwords or tokens, and never use yt-dlp's `--cookies`, `--cookies-from-browser`, `--exec`, `--plugin-dirs` or `--update-to` (the script ignores the user's yt-dlp config on purpose).
- Analysis only: never re-upload or re-publish what it downloads. Downloading may be restricted by the platform's terms of service: it is the user's responsibility; mention this once when the user asks for a download.
- If a site blocks the download, report it and ask the user before trying anything else.
- The script uses `yt-dlp`, `ffmpeg` and `whisper` from PATH and installs nothing. If one is missing it says so: tell the user how to install it, do not install it yourself unless they ask.
- Whisper downloads its model on first use (`small` is about 460 MB): say so before the first `--transcribe`. Transcripts of dialects need a human check.
