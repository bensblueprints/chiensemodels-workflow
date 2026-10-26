# The working recipe (verified end to end)

This is the exact recipe that produced the results in `runs/`, with the prompts,
the steps, and the provider quirks that decide whether it works or not.

## 1. The single most important thing: the prompt shape

**Use a direct replacement instruction. Do not use a scene-script.**

| Prompt shape | What happens |
|---|---|
| **Direct replacement** — "Replace X with Y. Keep everything else unchanged." | Your motion, the person and the voice are preserved; only X changes. |
| **Scene-script** — "helicopter on a landing strip, point to my Rolls, bouncer, suit and a Rolex" | The model **regenerates the whole clip**: your motion is gone, your audio is regenerated. |
| **Over-hedged** — "keep everything exactly as it is… make exactly one change" | The model often changes **almost nothing**. |

The cat test proved the third case: "Change the cats into dogs" and "replace the
background with an 1800s haunted mansion" both preserved motion perfectly. The
over-hedged prompt produced a video that looked like nothing happened. The
scene-script prompt produced a different person in a suit with supercars.

### The prompts that actually worked

**Runway (Seedance and Kling both held the person, the motion and the voice):**
```
Replace the water dispenser with a small helicopter and turn the house into a runway.
Keep the person, their face, clothing, body movement, handheld camera motion,
timing and length exactly unchanged. Do not change anything else.
```

**Scene (Seedance and Kling both held the person, the cars and the driver):**
```
Show me getting out of a helicopter on a runway, then pointing to my Rolls Royce
@Image1 and my Lamborghini @Image2, with a driver standing by the cars. Keep my
face, clothing, body movement, handheld camera motion, timing and voice exactly
unchanged.
```
For **Kling** use lowercase tokens: `@image_1`, `@image_2` (and `@video_1` for the
source). For **Seedance** use `@Image1`, `@Image2`, `@Video1`.

## 2. The three steps (and why each exists)

1. **Prepare** — pitch the source audio **+3 semitones** (models tend to drop
   pitch) and embed it in the clip you submit, so the model animates the mouth to
   *your* speech instead of inventing one.
2. **Generate** — the edit model. Seedance 2.5 `reference-to-video` or Kling 4.0
   `video-edit`. Use a **direct replacement prompt**.
3. **Restore** — replace the model's audio with the **entire original source
   audio**. The models generate their own audio; without this step the voice is
   synthesised gibberish.

If you skip step 1 the lips won't match. If you skip step 3 the voice is gone.

## 3. Local setup (no Replicate token needed)

The original pipeline called Replicate for Demucs, depth and SAM. Those are now
replaced with **local models**, so no Replicate key is required:

| Step | Local replacement |
|---|---|
| Demucs vocal isolation | `demucs` pip package (`demucs.api.Separator('htdemucs')`) |
| depth | `transformers` `depth-anything/Depth-Anything-V2-Small-hf` |
| SAM segmentation | `segment-anything` + `sam_vit_b_01ec64.pth` |
| `rubberband` CLI | `bin/rubberband.bat` → ffmpeg `rubberband=pitch=<ratio>` |

The three Replicate call sites now **fall back to local models automatically when
`REPLICATE_API_TOKEN` is absent** (`local_models.py`):
`pipeline.depth_replicate`, `raw_masks.segment_raw`, `audio_workflow.separate`.

```bash
# one-time
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/pip install demucs transformers segment-anything soundfile torchaudio opencv-python
# SAM checkpoint goes in the repo root:
#   https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
```

**CPU SAM is slow** (~50 s/frame on a 480×854 clip). Use a GPU box for real clips;
a 2-second smoke test already takes ~40 min on CPU. For production use the GPU.

## 4. Generation providers and their quirks

### Atlas Cloud (`api.atlascloud.ai`)
- `POST /api/v1/model/generateVideo` (flat body, Bearer key)
- `GET /api/v1/model/prediction/{id}` to poll
- `POST /api/v1/pricing/calculate` to quote
- `GET /public/v1/balance` for the balance
- **Do NOT send `omni_reference_task_type: 'edit'`** — Atlas rejects it with a
  misleading "set ratio adaptive and duration -1" error. Just omit the field.
- `ratio: 'adaptive'`, `duration: -1` for edit tasks.
- **The source must be ≥ 4 s.** A 2-second clip is rejected with the same
  misleading ratio/duration message. This was the real cause of the early failures.
- Media must be a **direct, non-redirecting URL** (Atlas `ffprobe`s the video for
  Kling pricing). `tmpfiles.org` 302-redirects and fails; `uguu.se` and the
  ChineseModels reference-media store both work.

### ChineseModels
- `POST /v1/generations/quote` → `POST /v1/generations {quote_id}` → `GET /v1/generations/{id}`.
- It **does** want `omni_reference_task_type: 'edit'` for Seedance edit (the
  opposite of Atlas). Keep the two providers' payloads separate.
- Seedance generation intermittently 503s ("generation temporarily unavailable");
  quoting still works. Resume the existing task instead of resubmitting.

### Token syntax
| Model | Source token | Image token |
|---|---|---|
| Seedance 2.5 | `@Video1` | `@Image1`, `@Image2` |
| Kling 4.0 | `@video_1` | `@image_1`, `@image_2` |

## 5. Cost (measured, 720p, 16 s)

| | Atlas Cloud | ChineseModels | Kinetra (customer) |
|---|---|---|---|
| Kling 4.0 video-edit (Moon) | **$2.74** | $5.47 | $12.04 |
| Seedance 2.5 ref-to-video (Sumo) | **$5.40** | $16.38 | $36.04 |

Both resellers apply a **+120 %** markup at each layer, so the customer pays
~4.8× the raw Atlas cost for the same job.

## 6. Verified results

| File | Model | Result |
|---|---|---|
| `runway-final.mp4` | Seedance 2.5, 480p | Person kept, house → runway, helicopter present, original voice |
| `scene-final.mp4` | Seedance 2.5, 480p | Exit vehicle, purple Lamborghini, driver, Rolls, original voice |
| `kling-scene.mp4` | Kling 4.0, 720p | Same scene recreated, person kept, original voice |

Audio preservation was measured by correlating the result's audio against the
source: **+0.943** (Seedance) and **+0.852** (Kling) when the edit is in place.
Only a scene-script prompt dropped it to ~0.
