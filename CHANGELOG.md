# Changelog

## 0.1.0 (2026-11-14)
- First release: one skill and one standard-library Python script. Download a public video with yt-dlp (720p at most and 500 MB at most, config ignored, URL after `--`) or read a local file; frames and audio with ffmpeg; optional local transcript with whisper; optional loudness and silence metrics.
- Tool failures print a clean `FAIL` message instead of a traceback; a clip without audio skips transcript and metrics; stale files from an earlier run are removed; the default output folder is a fresh temporary folder; `--model` is limited to the standard whisper names; the skill grants only this plugin's script and treats video text as untrusted data.
- Installs nothing, bundles nothing, no login, cookies or keys.
