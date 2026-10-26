# ChineseModels integration

Verified live against https://chinesemodels.ai on 2026-10-26.

Base URL: `https://chinesemodels.ai`
Auth: `Authorization: Bearer sk-cm-…` (server-side only; keys start with `sk-cm-`).

The catalogue exposes 600 models. This workflow edits video through one of them:

| Product | `CHINESEMODELS_MODEL` |
|---|---|
| Moon (Seedance) | `bytedance/seedance-2.5/reference-to-video` |
| SUMO (Kling) | `kwaivgi/kling-v4.0/video-edit` |

Switch by editing the single `CHINESEMODELS_MODEL` value in `.env`.

## Upload prepared media — POST /api/reference-media

Multipart: `file`, `kind` (`video` or `image`), `model`.
Response: `{"url": "https://…"}`. That URL is what the model receives.

## Quote — POST /v1/generations/quote

Seedance 2.5 edit request:

```json
{
  "model": "bytedance/seedance-2.5/reference-to-video",
  "prompt": "Edit the source video …",
  "reference_videos": ["https://…/composite.mp4"],
  "reference_images": ["https://…/character.png"],
  "duration": -1,
  "ratio": "adaptive",
  "omni_reference_task_type": "edit",
  "resolution": "720p"
}
```

Response: `{"id": "quote_…", "model": "…", "price": 10.797696, "currency": "USD", "expiresAt": 1792993612399}`.

Resolution is **lowercase** — `480p`, `720p`, `1080p`. Uppercase is rejected with
`/resolution must be equal to one of the allowed values`.

For `kwaivgi/kling-v4.0/video-edit`, send `video` (a single URL string) and a
whole-second `duration` instead of `reference_videos` and `duration: -1`.

## Submit — POST /v1/generations

Body `{"quote_id": "quote_…"}` → `{"id": "…", "status": "…"}`.
Quotes expire; a stale quote is rejected, so re-quote rather than reusing one.

## Poll — GET /v1/generations/{id}

Returns `status` (and usually `progress`). Terminal states are `completed`,
`failed` and `cancelled`. The finished file URL is on the provider CDN, signed
and expiring — download it immediately and re-store it locally.

There is **no webhook step**: this flow is poll-only, which is why the workflow
needs no tunnel or callback receiver.

## Draft then final

The draft pass generates at `CHINESEMODELS_PREVIEW_RESOLUTION` (default `480p`);
once you approve the draft, the final pass regenerates at
`CHINESEMODELS_RESOLUTION` (default `1080p`). Both are separate, billed
generations. The provider also lists `bytedance/seedance-2.5/draft-complete`
for a native draft→final hop; adopt it once its exact request shape is
confirmed against a live account.

## Local routes

- `POST /jobs`: multipart `video`, `prompt` (segmentation subject), `provider`.
- `GET /jobs/{id}`: local progress.
- `GET /jobs/{id}/mask-review`: artifact fingerprint and approval.
- `POST /jobs/{id}/mask-review`: `approved`, `fingerprint`, `note`.
- `POST /jobs/{id}/seedance`: `prompt`, `primary` (primary reference), optional `secondary` (second image).
- `POST /jobs/{id}/hd`, `GET /jobs/{id}/hd`: approved final resolution and progress.
- `POST /jobs/{id}/finish`: manually upload a returned `video` and restore original audio.
- `/docs`: FastAPI-generated local endpoint documentation.

No paid POST is automatically retried after an ambiguous timeout. Check your
ChineseModels dashboard before deliberately creating another request.

## Provider state on 2026-10-26

- **Seedance 2.5 reference-to-video** — quoting works. A 720p edit quoted
  $10.80; the same at 1080p quoted $21.25.
- **Kling 4.0 video-edit (SUMO)** — every quote returned
  `Generation is temporarily unavailable. Check existing tasks before retrying a
  submission.` SUMO cannot render through this route until the provider restores
  that channel.

Buy your Seedance or Kling key at [chinesemodels.ai](https://chinesemodels.ai).
