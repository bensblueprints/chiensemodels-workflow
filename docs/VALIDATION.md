# Validation status

Read this before trusting this workflow for billed work.

## Verified against the live provider (2026-10-26)

Using a real `sk-cm-…` key, read-only and non-billing calls:

- `GET /v1/models` returned 600 models; `bytedance/seedance-2.5/reference-to-video`
  and `kwaivgi/kling-v4.0/video-edit` are both present, as is
  `bytedance/seedance-2.5/draft-complete`.
- `POST /v1/generations/quote` for the Seedance edit contract returned a real
  quote: **$10.797696 @720p** and **$21.25228 @1080p** (`{"id":"quote_…","price":…,"currency":"USD","expiresAt":…}`).
- Resolution is validated as **lowercase**: `480p`/`720p`/`1080p` succeed,
  uppercase returns `400 /resolution must be equal to one of the allowed values`.
- `POST /v1/generations/quote` for `kwaivgi/kling-v4.0/video-edit` (SUMO)
  returned `400 Generation is temporarily unavailable. Check existing tasks before
  retrying a submission.` SUMO cannot render through this route until the provider
  restores that channel.

No billed generation was submitted during this validation.

## Verified locally

- Every Python module compiles (`python -m compileall`).
- The unit suite (`tests/`) covers mask-fingerprint invalidation, duplicate-submission
  protection, the quote→submit edit contract, result download and audio restoration,
  the approved-final-resolution path, reference-media upload (role, auth, HTTPS and
  error handling), primary/fallback-free upload behavior, and mesh submission. These
  tests mock every remote call.
- The synthetic compositing check (`test_composite.py`) validates mask selection and
  frame alignment with no network access.

## NOT verified

- No end-to-end billed edit (draft or final) has been run through this workflow.
- No cross-platform clean install (macOS/Linux/WSL) was run.
- `CHINESEMODELS_MODEL`, `CHINESEMODELS_PREVIEW_RESOLUTION` and
  `CHINESEMODELS_RESOLUTION` are the intended knobs; the Kling path is untestable
  while its channel is down.
- The exact request shape of `bytedance/seedance-2.5/draft-complete` is not confirmed,
  so the final pass is implemented as a second generation rather than the native hop.

## Before your first paid run

1. Confirm your balance in the Chinesemodels dashboard.
2. Run one short clip end to end and verify the draft, the final pass, and byte-for-byte
   original-audio restoration.
3. Keep the server running until the preview is saved; retrieval resumes from the saved
   response and never re-submits a paid request.
