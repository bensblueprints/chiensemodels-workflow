# Troubleshooting

- Missing Rubber Band: install its CLI, restart the shell and run `doctor.py`.
- Missing credentials: populate this folder's `.env`; restart. Credentials are never obtained from a parent project.
- 401 `Invalid API key. Pass it as: Authorization: Bearer sk-cm-…`: your `CHINESEMODELS_API_KEY` is wrong or missing. Keys start with `sk-cm-`.
- 400 `/resolution must be equal to one of the allowed values`: the API only accepts lowercase `480p`, `720p` or `1080p`.
- 400 `Generation is temporarily unavailable`: the provider channel for that model is down. As of 2026-10-26 this affects `kwaivgi/kling-v4.0/video-edit` (SUMO). Switch `CHINESEMODELS_MODEL` or wait.
- Quote expired: quotes are short-lived. Re-quote; do not reuse a stale `quote_id`.
- Reference-media upload failure: the file is not a decodable PNG/JPEG/WebP/MP4, or it is too large for the provider. The uploader fails before any generation is submitted, so nothing is billed.
- Mask holes, edge noise, chair spill: reject it, run RGB repair and review the full clip again. Cleanup is heuristic; never assume it proves correctness.
- Frame count/index mismatch: composition fails deliberately. Inspect output fps/frame IDs; align the provider output to the same source rather than forcing a shifted mask through.
- Original audio duration mismatch: the exporter permits a short final-frame hold for a 0.25–0.5 second provider rounding gap and records `duration-adjustment.json`. Larger differences are rejected. It never stretches or loops source audio.
- Result URL missing or unreadable: the finished file sits on a signed, expiring CDN URL. The collector downloads it immediately; if a run is interrupted, resume collection rather than re-submitting.
- Restart: retrieval resumes from saved responses (`seedance-response.json`, `hd/response.json`). It never re-submits a paid request. Earlier preparation failures require inspecting the saved Replicate prediction metadata.
- UI fonts: Google Fonts is used, with system fallbacks if offline. Companion artwork is bundled under `static/companions`.
- Lost pending status: use `workflow.py resume JOB` (or `--hd`), not another submit. Completed outputs remain in `runs`.
