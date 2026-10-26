# Model how-to guides

A practical guide for each of the two models: what it's for, the exact inputs, the
prompt pattern, tokens, settings, cost, and the gotchas that decide whether it works.

---

## SUMO — Seedance 2.5 `bytedance/seedance-2.5/reference-to-video`

**Use it for:** in-place video edits where you want your motion and voice kept while
changing an object, the background, or a character.

### Inputs
- **Source video**, **≥ 4 seconds** (shorter is rejected with a misleading
  "ratio adaptive / duration -1" error).
- **Reference images** (optional) — the thing to swap in (helicopter, car, person).
- **Prompt** written as a **direct replacement**, never a scene-script.

### Settings that work
| Field | Value |
|---|---|
| `model` | `bytedance/seedance-2.5/reference-to-video` |
| `reference_videos` | `[<source video URL>]` (exactly one) |
| `reference_images` | `[<reference image URL>, ...]` |
| `duration` | `-1` (match source length) |
| `ratio` | `adaptive` |
| `resolution` | `480p` (draft) / `720p` / `1080p` |
| `generate_audio` | `true` |

**Provider differences (important):**
- **Atlas Cloud:** do **not** send `omni_reference_task_type`. It gets rejected with
  a misleading ratio/duration error.
- **ChineseModels:** it **does** want `omni_reference_task_type: 'edit'`, and it
  sometimes 503s on polling while quoting still works — resume the existing task.

### Tokens
`@Video1` for the source, `@Image1`, `@Image2` for reference images.

### Example prompts

**Object swap (house → helicopter, you kept):**
```
Replace the water dispenser with a small helicopter. Keep the person, their face,
clothing, body movement, handheld camera motion, timing and length exactly unchanged.
```

**Object + scene (our runway result):**
```
Replace the water dispenser with a small helicopter and turn the house into a runway.
Keep the person, their face, clothing, body movement, handheld camera motion, timing
and length exactly unchanged. Do not change anything else.
```

**Scene with two car references:**
```
Show me getting out of a helicopter on a runway, then pointing to my Rolls Royce
@Image1 and my Lamborghini @Image2, with a driver standing by the cars. Keep my
face, clothing, body movement, handheld camera motion, timing and voice exactly unchanged.
```

### What NOT to write (this destroyed motion on SUMO)
```
I jump out of a helicopter on a landing strip, then point to my Rolls Royce, then my
Lamborghini, then a bouncer, suit and a Rolex.
```
That regenerated the whole clip: new scene, new wardrobe, new motion, new audio.

### Cost (16s)
Atlas **$5.40** · ChineseModels **$16.38** · Kinetra **$36.04**
Note Seedance has a ~$5 base cost per generation, so short clips aren't cheap either.

---

## Moon — Kling 4.0 `kwaivgi/kling-v4.0/video-edit`

**Use it for:** the same in-place edits. In our tests Kling also preserved motion and
voice with a direct prompt, and it was the cheaper of the two.

### Inputs
- **Source video** (`video` field, a single URL, not `reference_videos`).
- **Reference images** (optional).
- **Prompt** as a **direct replacement**.

### Settings that work
| Field | Value |
|---|---|
| `model` | `kwaivgi/kling-v4.0/video-edit` |
| `video` | `<source video URL>` |
| `reference_images` | `[<reference image URL>, ...]` |
| `duration` | whole seconds, e.g. `16` |
| `resolution` | `720p` (lowest available) / `1080p` |

Kling has **no 480p tier** — the cheapest is 720p. Its pricing `ffprobe`s the source
video, so the media URL must be **direct, non-redirecting** (tmpfiles redirects fail).

### Tokens
`@video_1` for the source, `@image_1`, `@image_2` for reference images — **lowercase**.

### Example prompts

**Same runway recipe, Kling tokens:**
```
Replace the water dispenser with a small helicopter and turn the house into a runway.
Keep the person, their face, clothing, body movement, handheld camera motion, timing
and length exactly unchanged. Do not change anything else.
```

**Same scene, Kling tokens:**
```
Show me getting out of a helicopter on a runway, then pointing to my Rolls Royce
@image_1 and my Lamborghini @image_2, with a driver standing by the cars. Keep my
face, clothing, body movement, handheld camera motion, timing and voice exactly unchanged.
```

### What NOT to write
Same as SUMO: no scene-scripts (they regenerate motion and audio), and no over-hedged
"keep everything exactly as it is, change only one thing" (it changes almost nothing).

### Cost (16s)
Atlas **$2.74** · ChineseModels **$5.47** · Kinetra **$12.04**

---

## Both models: the two things you must not skip

1. **Prompt = direct replacement.** This is what keeps your motion. Scene-scripts
   regenerate everything; over-hedged prompts change nothing.
2. **Restore the original audio afterwards.** The models generate their own audio.
   The restore step is what makes your real voice come back — the prompt alone won't.

For fully-worked examples of good vs bad prompts, see `PROMPT-EXAMPLES.md`.
For the end-to-end pipeline (prepare → generate → restore), see `HOW-TO.md`.
