# Chiensemodels / Seedance and Kling integration

This is an integration guide for the request/response shapes used by this workflow, derived from the working implementation. It is not a copy of a complete vendor specification. Buy a Seedance or Kling API key at [chiensemodels.ai](https://chiensemodels.ai) and confirm current account support, endpoint paths and limits in your Chiensemodels dashboard.

> **Confirm the live contract before first use.** The request/response shapes below mirror the queue/status contract this workflow was built against. The public Chiensemodels endpoint paths and field names must be checked against your dashboard; if they differ, edit the single place they live: `base_url()` and the payloads in `seedance_bridge.py`, plus the base URL and model in `.env`.

Base URL: `https://api.chiensemodels.ai/v1` (override with `CHIENSEMODELS_BASE_URL`).
Authentication: `x-api-key: YOUR_KEY` (server-side only).
Model selector: `CHIENSEMODELS_MODEL` (default `seedance-2.5`; use `kling` for a Kling key).

## Submit a draft — POST /queue

```json
{
  "model": "seedance-2.5",
  "mode": "edit",
  "resolution": "1080p",
  "aspect_ratio": "adaptive",
  "is_draft": true,
  "output_format": "mp4",
  "pass_faces": true,
  "videos": ["https://YOUR_HOST/prepared.mp4"],
  "images": ["https://YOUR_HOST/character.png"],
  "audios": [],
  "prompt": "Replace the complete subject with @Image1. Match @Video1 timing and embedded audio exactly.",
  "webhook_url": "https://YOUR_RECEIVER/callback"
}
```

Response used by the app: `{"requestId":"PROVIDER_ID"}`. Save it immediately. Edit uses one input video. For video identity references use `mode: "multi_reference"`, `videos: [prepared_url, identity_url]`, a supported aspect ratio and a whole-second duration string. The adapter chooses nearest duration from 4–30 seconds and nearest aspect ratio. These are adapter constraints, not a promise of every account's supported limits. `@Video1` controls movement/audio; `@Video2` controls appearance only. An optional second image is `@Image1` in this mode, not `@Image2`.

Images should be actual decodable PNG/JPEG/WebP bytes, not an HTML download page renamed as an image. References must be reachable remotely. Local paths and localhost URLs are not provider-accessible.

## Poll — POST /status

Body: `{"request_id":"PROVIDER_ID"}`.
The collector polls every 10 seconds, for up to 360 attempts. It reads `status`, saves `provider-status.json`, downloads the HTTPS `result` on `COMPLETED`, and reports `FAILED`/`CANCELED` with the provider error. A timeout leaves request IDs saved; resume collection, do not requeue automatically. Transport errors also preserve the ID for recovery.

`webhook_url` is required: an empty value is rejected. Set your own HTTPS receiver or install cloudflared and use launch.py, which starts webhook.py behind a temporary Quick Tunnel. The receiver accepts callbacks but never mutates jobs; polling remains authoritative. The receiver exposes no files or UI. Keep the tunnel alive while generation runs; its URL changes on restart.

## Complete an approved draft — POST /queue

```json
{"model": "seedance-2.5", "draft_id": "ACCEPTED_DRAFT_REQUEST_ID", "webhook_url": ""}
```

Do not send a new creative prompt or input files with draft completion. The provider reuses the draft settings (1080p requested initially). This is a separate billed operation and requires approval. Save the new request ID in `hd/response.json`, poll it, then restore the full original soundtrack. Never overwrite the draft preview.

## Local routes

- `POST /jobs`: multipart `video`, `prompt` (segmentation subject), `provider`.
- `GET /jobs/{id}`: local progress.
- `GET /jobs/{id}/mask-review`: artifact fingerprint and approval.
- `POST /jobs/{id}/mask-review`: `approved`, `fingerprint`, `note`.
- `POST /jobs/{id}/seedance`: `prompt`, `primary` (primary reference), optional `secondary` (second image).
- `POST /jobs/{id}/hd`, `GET /jobs/{id}/hd`: approved upgrade and progress.
- `POST /jobs/{id}/finish`: manually upload returned `video` and restore original audio.
- `/docs`: FastAPI-generated local endpoint documentation.

No paid POST is automatically retried after an ambiguous timeout. Check the provider dashboard before deliberately creating another request. Public media may expire while queued; use a longer-lived host if necessary.

Get access at [Chiensemodels.ai](https://chiensemodels.ai) and obtain your own Seedance or Kling key. The integration requests human-face support with `pass_faces: true`; provider terms and account limitations still apply.
