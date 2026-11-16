# Changelog

## 0.1.2 (2026-11-15)
- Round-2 fixes. Redirects: before yt-dlp runs, the script now follows the URL's redirect chain itself (HEAD, one-byte ranged GET when HEAD is refused, max 5 hops, 10 s per hop, http/https only) and refuses when any hop is or resolves to a non-public address; the original URL is then passed to yt-dlp. Known limits, stated plainly: requests made inside yt-dlp's extractors (page links, manifests, segments) and DNS answers that change after the check are not covered; a server can also answer the check differently from yt-dlp. SKILL.md and README no longer claim a flat refusal.
- Direct `.mp4` links work: format selector `bv*[height<=720]+ba/b[height<=720]/b` (the 500 MB cap stays); 720p is now a preference, not a hard limit.
- `info_short.json`: every text field is capped (title 200, description 2000, others shorter) and stripped of control, format, bidi and surrogate characters; non-numeric values in numeric fields are dropped.
- UNC/network paths are refused as sources and as `--out`; the `%` guard also runs on the resolved path (a working directory containing `%` is refused with a clear message).
- Documented: the pre-run cleanup touches only the files the script names inside `--out`. README: licensing note (yt-dlp Unlicense, ffmpeg depends on the build and may be GPL, nothing bundled); the "no network request of its own" claim is corrected (the redirect check).
- Tests: 14 -> 28; the out-folder test no longer depends on where the repo lives.
- Not changed: `--ignore-config` does not disable yt-dlp plugin folders, no playlist-item limit, `64:ff9b::/96` forms still count as global, TOCTOU on `--out`, PATH shadowing.

## 0.1.1 (2026-11-15)
- Adversarial test round: a host that cannot be resolved here (for example `127.1`, `2130706433`, `0x7f000001` on Windows) is now refused instead of passed to yt-dlp (fail closed); a failure to create `--out` prints a clean `FAIL` message. Held up: IPv6 loopback and mapped forms, link-local metadata address, userinfo tricks, non-http schemes, option-looking values, `--fps nan/inf/-1`, `--max-frames` extremes, `--model` as a path. Still best effort by design: redirects and DNS changes after the check.

## 0.1.0 (2026-11-14)
- Hardening: refuse hosts that resolve to loopback/private addresses (best effort), timeouts on every tool call, `--out` must be new/empty (or under temp), `-protocol_whitelist file` for ffmpeg inputs, audio metrics documented as measured on the downsampled mp3.
- First release: one skill and one standard-library Python script. Download a public video with yt-dlp (720p at most and 500 MB at most, config ignored, URL after `--`) or read a local file; frames and audio with ffmpeg; optional local transcript with whisper; optional loudness and silence metrics.
- Tool failures print a clean `FAIL` message instead of a traceback; a clip without audio skips transcript and metrics; stale files from an earlier run are removed; the default output folder is a fresh temporary folder; `--model` is limited to the standard whisper names; the skill grants only this plugin's script and treats video text as untrusted data.
- Installs nothing, bundles nothing, no login, cookies or keys.
