# watch-clip — a Claude Code plugin (v0.1.0)

Gives Claude eyes and ears for a short clip: give it a public video link or a local file and it extracts frames, audio and (optionally) a local transcript, so Claude can describe hooks, pacing and captions.

## Requirements (not bundled, not installed by this plugin)
You need these on your PATH: `ffmpeg` (always), `yt-dlp` (for links), `whisper` from openai-whisper (only for `--transcribe`), and Python 3.8+ (the skill calls `python`; where only `python3` exists, ask Claude to run the same command with `python3`). If one is missing the script says which and how to get it.

| Tool | Licence | Note |
|---|---|---|
| yt-dlp | Unlicense | for links |
| openai-whisper | MIT | local transcription; downloads its model on first use |
| ffmpeg | LGPL or GPL, depending on the build you installed | this plugin only calls it as a separate program |

## Use
Ask Claude to watch a link or file ("watch this reel and tell me how the hook works"). Or run it yourself: `python scripts/watch_clip.py <url-or-file> --fps 0.5 --max-frames 24 [--transcribe --lang en] [--audio-metrics] [--out DIR]`.

## Terms of service and privacy
Downloading videos can be restricted by the platform's terms of service. You are responsible for what you download: use it for public videos and for analysis only, never to re-publish. The plugin uses no login, no cookies and no keys, ignores your yt-dlp configuration, and the plugin itself makes no network request of its own; `yt-dlp` contacts the video's host (and whatever servers that site needs), and `whisper` downloads its model on first use (`small` is a few hundred MB). Transcription runs on your machine. A downloaded video stays in the output folder until you delete it; frames come from the start of the clip only (`--fps` x `--max-frames`).

## Licence
MIT.
