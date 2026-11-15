# Changelog

## 0.1.1 (2026-11-15)
- Adversarial test round: a host that cannot be resolved here (for example `127.1`, `2130706433`, `0x7f000001` on Windows) is now refused instead of passed to yt-dlp (fail closed); a failure to create `--out` prints a clean `FAIL` message. Held up: IPv6 loopback and mapped forms, link-local metadata address, userinfo tricks, non-http schemes, option-looking values, `--fps nan/inf/-1`, `--max-frames` extremes, `--model` as a path. Still best effort by design: redirects and DNS changes after the check.

## 0.1.0 (2026-11-14)
- Hardening: refuse hosts that resolve to loopback/private addresses (best effort), timeouts on every tool call, `--out` must be new/empty (or under temp), `-protocol_whitelist file` for ffmpeg inputs, audio metrics documented as measured on the downsampled mp3.
- First release: one skill and one standard-library Python script. Download a public video with yt-dlp (720p at most and 500 MB at most, config ignored, URL after `--`) or read a local file; frames and audio with ffmpeg; optional local transcript with whisper; optional loudness and silence metrics.
- Tool failures print a clean `FAIL` message instead of a traceback; a clip without audio skips transcript and metrics; stale files from an earlier run are removed; the default output folder is a fresh temporary folder; `--model` is limited to the standard whisper names; the skill grants only this plugin's script and treats video text as untrusted data.
- Installs nothing, bundles nothing, no login, cookies or keys.
