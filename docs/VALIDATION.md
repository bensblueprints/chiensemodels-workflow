# Validation status

This package is a provider-swapped rebuild of the open-source Genjustsu workflow. Read this before trusting it for billed work.

## What is verified

- All Python modules compile (`python -m compileall`).
- The local unit suite (`tests/`) covers mask-fingerprint invalidation, duplicate-submission protection, the self-contained Edit draft payload, result download/restoration dispatch, the approved-draft HD payload, rejection of missing mask frames, byte-identical original-audio restoration, primary-host retry and fallback switching, and mesh submission behavior. These tests mock every remote call.
- The synthetic compositing check (`test_composite.py`) validates mask selection and frame alignment without any network access.
- Every provider reference is centralized in `seedance_bridge.py` (`base_url()`, the payloads, `submit_hd`) and `.env`, so the endpoint can be corrected in one place.

## What is NOT verified

- **The live Chiensemodels endpoint contract.** The request/response shapes (`POST /queue`, `POST /status`, `requestId`, `status`, `result`) mirror the contract this workflow was originally built against. The Chiensemodels base URL and field names have not been confirmed against a live account and must be checked in your dashboard before the first paid submission. See `docs/CHIENSEMODELS-API.md`.
- No live Demucs / depth / SAM / Seedance / Kling generation was run in this build.
- No cross-platform clean install (macOS/Linux/WSL) was run in this build.
- The `MEDIA_HOST`/fallback and mesh paths are exercised only through mocked tests here.

## Before your first paid run

1. Confirm your Chiensemodels endpoint paths, auth header and payload fields; adjust `seedance_bridge.py` and `.env` if they differ.
2. Run one short clip end to end and verify the draft, the 1080p upgrade, and byte-for-byte original-audio restoration.
3. Keep the callback tunnel alive for the whole job; polling is authoritative if callbacks are delayed.
