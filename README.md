# clipscope — a Claude Code plugin (v0.1.2)

Gives Claude eyes and ears for a short clip: give it a public video link or a local file and it extracts frames, audio and (optionally) a local transcript, so Claude can describe hooks, pacing and captions.

## Requirements (not bundled, not installed by this plugin)
You need these on your PATH: `ffmpeg` (always), `yt-dlp` (for links), `whisper` from openai-whisper (only for `--transcribe`), and Python 3.8+ (the skill calls `python`; where only `python3` exists, ask Claude to run the same command with `python3`). If one is missing the script says which and how to get it.

| Tool | Licence | Note |
|---|---|---|
| yt-dlp | Unlicense | for links |
| openai-whisper | MIT | local transcription; downloads its model on first use |
| ffmpeg | LGPL or GPL, depending on the build you installed | this plugin only calls it as a separate program |

Licensing: this plugin is MIT and bundles nothing. yt-dlp is Unlicense; ffmpeg's licence depends on the build you install (it may be GPL); whisper is MIT. They are your own installs under their own licences.

## Use
Ask Claude to watch a link or file ("watch this reel and tell me how the hook works"). Or run it yourself: `python scripts/clipscope.py <url-or-file> --fps 0.5 --max-frames 24 [--transcribe --lang en] [--audio-metrics] [--out DIR]`.

**Safety notes.** Best effort: the URL and its redirects (HEAD, up to 5 hops, http/https only) are checked and refused when a hop is or resolves to a loopback/private address; requests made inside yt-dlp's extractors and later DNS changes are not covered, so this is not a network sandbox. Network (UNC) paths are refused as sources. `--out` must be a new or empty folder (or under the temp dir); before a run the script deletes only the files it names itself inside `--out` (`clip.*`, `frames/f_*.jpg`, `audio.mp3`, `info_short.json`, transcript and metrics files). Text in `info_short.json` is capped and stripped of control characters. Quality: 720p or lower is preferred (a direct file can be larger), 500 MB cap. Every tool call has a timeout, and ffmpeg reads local files only (`-protocol_whitelist file`). Audio metrics are measured on the downsampled 16 kHz mono mp3, so loudness and peak values are approximate.

## Terms of service and privacy
Downloading videos can be restricted by the platform's terms of service. You are responsible for what you download: use it for public videos and for analysis only, never to re-publish. The plugin uses no login, no cookies and no keys, ignores your yt-dlp configuration, and the only requests the script makes itself are the redirect check (HEAD, or a one-byte GET) to the link you give and its redirect targets; `yt-dlp` contacts the video's host (and whatever servers that site needs), and `whisper` downloads its model on first use (`small` is a few hundred MB). Transcription runs on your machine. A downloaded video stays in the output folder until you delete it; frames come from the start of the clip only (`--fps` x `--max-frames`).

## Licence
MIT.
