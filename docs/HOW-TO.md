# How to make a video that keeps your motion AND your voice

A numbered, do-this-exactly manual for the working pipeline. It is the same recipe
that produced `runway-final.mp4`, `scene-final.mp4` and `kling-scene.mp4`.

## What you need

1. A source clip of you (e.g. `larp2.mp4`), **at least 4 seconds long**.
2. Reference images of anything you want swapped in (a helicopter, a car, a person).
3. One API key for the generation step (Atlas Cloud **or** ChineseModels).
4. Python 3.12 on this machine. No Replicate token needed.

## Step 1 — Install

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/pip install demucs transformers segment-anything soundfile torchaudio opencv-python
```

Put the SAM checkpoint in the repo root:
`https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth`

DepthAnything downloads itself from HuggingFace on first use. Demucs weights
download on first use. `bin/rubberband.bat` replaces the `rubberband` CLI on Windows.

## Step 2 — Prepare your audio (local, no API)

The pipeline does this for you:
1. Extract the original audio.
2. Isolate vocals with **Demucs** (local).
3. Pitch the vocals **+3 semitones** (models drift pitch down).
4. Embed those pitched vocals into the clip you will submit.

That last bit matters: the model "hears" your real speech and animates your mouth
to it. If you skip it, the lips won't match.

If you also want the **motion lock** for a hard subject swap, run the depth + SAM
composite locally (`--composite`). For simple edits you do not need it.

## Step 3 — Write the prompt the right way

**Use a direct replacement instruction. Never a scene-script.**

Good:
```
Replace the water dispenser with a small helicopter and turn the house into a runway.
Keep the person, their face, clothing, body movement, handheld camera motion, timing
and length exactly unchanged. Do not change anything else.
```

Good (scene with references):
```
Show me getting out of a helicopter on a runway, then pointing to my Rolls Royce
@Image1 and my Lamborghini @Image2, with a driver standing by the cars. Keep my
face, clothing, body movement, handheld camera motion, timing and voice exactly
unchanged.
```

Bad (this is what destroyed your motion):
```
helicopter on a landing strip, point to my Rolls Royce, then a bouncer, suit and a Rolex
```
That is a *scene-script*: the model rebuilds the entire clip, invents new motion,
and synthesises new audio. Do not write prompts like that if you want your motion kept.

Also avoid over-hedging ("keep everything exactly as it is, change only one thing") —
that tends to change almost nothing.

**Reference tokens:** Seedance uses `@Image1`, `@Video1`. Kling uses `@image_1`,
`@video_1`. Keep them straight or the reference is ignored.

## Step 4 — Generate

```bash
# Seedance 2.5 (SUMO), 480p draft, with a reference image
python atlas_run.py --source larp2.mp4 --no-audio-prep --model sumo --resolution 480p \
  --ref refs/helicopter.jpg --prompt "Replace the water dispenser with a small helicopter and turn the house into a runway. Keep the person, their face, clothing, body movement, handheld camera motion, timing and length exactly unchanged. Do not change anything else."

# Kling 4.0 (Moon), 720p
python atlas_run.py --source larp2.mp4 --no-audio-prep --model moon --resolution 720p \
  --ref refs/rolls-royce-ghost.jpg --ref refs/lamborghini.jpg --prompt "Show me getting out of a helicopter on a runway, then pointing to my Rolls Royce @image_1 and my Lamborghini @image_2, with a driver standing by the cars. Keep my face, clothing, body movement, handheld camera motion, timing and voice exactly unchanged."
```

Provider notes you will hit:
- **Atlas:** omit `omni_reference_task_type` entirely. Use `ratio: adaptive`,
  `duration: -1`, source **≥ 4 s**, and a **direct, non-redirecting** media URL.
- **ChineseModels:** it *does* want `omni_reference_task_type: 'edit'`, and it
  sometimes 503s on polling while quoting still works. Resume the existing task.

## Step 5 — Restore your original audio (required)

The model always generates its own audio. Replace it with your **entire original
source audio** afterwards. The runner does this automatically:
`restore_original_audio(generated, source, out)`.

If you only do step 4 and skip this, you get synthesised speech, not your voice.

## Step 6 — Check the result

- Is the person still you (face, clothes, hair)?
- Is the motion the same handheld walk?
- Is the voice your real voice?
- Is the length the same as the source?

If the person or motion changed, the prompt was a scene-script — rewrite it as a
direct replacement. If the voice is wrong, the restore step was skipped.

## Cost (720p, 16 s)

| | Atlas Cloud | ChineseModels | Kinetra |
|---|---|---|---|
| Kling 4.0 (Moon) | $2.74 | $5.47 | $12.04 |
| Seedance 2.5 (Sumo) | $5.40 | $16.38 | $36.04 |

## Troubleshooting (the exact errors and their fixes)

| Error | Cause | Fix |
|---|---|---|
| `ratio adaptive / duration -1` on Atlas | You sent `omni_reference_task_type: 'edit'` | Remove that field |
| Same error, even without omni | Source clip is **2 s** (too short) | Use ≥ 4 s |
| `ffprobe ... exit status 1` on Atlas quote | Media URL redirects | Use a direct host (`uguu.se` or CM reference-media), not tmpfiles |
| `Generation is temporarily unavailable` on CM | Provider hiccup on Seedance | Resume the existing task; do not resubmit |
| Output looks like nothing changed | Prompt over-hedged | Lead with the replacement |
| Output is a different scene/person | Prompt was a scene-script | Use a direct replacement |
| Voice is gibberish | Model generated its own audio | Restore the original source audio |
