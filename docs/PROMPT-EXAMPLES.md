# Prompt examples: what to put, and what not to put

One rule decides almost everything: **write a direct replacement instruction, not a
scene-script.** These are real examples of each, with what happened when we ran them.

## DO — direct replacement

**Pattern:** `Replace <the one thing> with <the new thing>. Keep everything else unchanged.`

### Object swap
```
Replace the water dispenser with a small helicopter. Keep the person, their face,
clothing, body movement, handheld camera motion, timing and length exactly unchanged.
```
Why it works: one named change, everything else preserved. You stay in the shot with
your motion and voice.

### Object + scene swap (our runway result)
```
Replace the water dispenser with a small helicopter and turn the house into a runway.
Keep the person, their face, clothing, body movement, handheld camera motion, timing
and length exactly unchanged. Do not change anything else.
```
Why it works: the change is explicit (dispenser → helicopter, house → runway) and the
preservation is explicit. Person, motion and voice all held on both Seedance and Kling.

### Background only
```
Replace the background so the scene now takes place inside an 1800s haunted mansion.
Keep the three dogs, their poses, movement, camera framing and timing exactly unchanged.
Match the new lighting, shadows and colour so they look naturally placed in the room.
```
Why it works: the background is the only named target, so the dogs and the motion stay.

### Character / species swap
```
Change the cats into dogs. Keep the same scene, set, camera, framing, lighting,
motion and timing. The dogs should match the cats' positions, poses and behaviour,
and stay visually consistent for the whole clip.
```

### Scene with references (our "perfect" scene)
```
Show me getting out of a helicopter on a runway, then pointing to my Rolls Royce
@Image1 and my Lamborghini @Image2, with a driver standing by the cars. Keep my
face, clothing, body movement, handheld camera motion, timing and voice exactly unchanged.
```
Why it works: the references are named by token, the actions are specific, and the
preservation is explicit. Both cars and the driver appeared, with the person kept.

## DON'T — these broke the result

### Scene-script (worst offender)
```
I jump out of a helicopter on a landing strip, then I point to my Rolls Royce, then
I turn and point to my Lamborghini, then a big bouncer bodyguard, and I'm in a suit
wearing a Rolex.
```
**What it did:** regenerated the entire clip — new location, new wardrobe, new camera,
and **your motion and your voice were replaced**. That is the exact prompt that caused
"it didn't keep my motion."

### Over-hedged minimalism
```
Keep this video exactly as it is: the same person, the same face and clothing, the same
body movement, the same handheld camera motion, the same walking route, the same rooms,
the same lighting, the same timing and length. Make exactly one change: the water
dispenser becomes a helicopter. Do not change anything else.
```
**What it did:** basically nothing. The video looked like the original with no visible
change. Over-constraining makes the model timid instead of making the swap.

### Vague target with no replacement named
```
Keep the motion and make it look better.
```
**What it does:** nothing useful. The model has no named object to change.

## Reference tokens (get these right or the reference is ignored)

| Model | Source video | Reference images |
|---|---|---|
| Seedance 2.5 (SUMO) | `@Video1` | `@Image1`, `@Image2` |
| Kling 4.0 (Moon) | `@video_1` | `@image_1`, `@image_2` |

So: Seedance → "point to my Rolls Royce **@Image1** and my Lamborghini **@Image2**";
Kling → same sentence but **@image_1** and **@image_2**.

## The fill-in-the-blank template

```
Replace <object to change> with <what it should become>.
Keep the person, their face, clothing, body movement, handheld camera motion,
timing and length exactly unchanged. Do not change anything else.
```

Add one of these if you need it:
- `and turn the house into a runway` for a scene change;
- `with a driver standing by the cars` for an extra character;
- `using @Image1` / `@image_1` to bind a reference image.

## And always finish with the audio step

Even a perfect prompt leaves the model's generated audio on the result. **Restore the
entire original source audio afterwards** or your voice is replaced by gibberish.
The prompt alone does not preserve your voice; the restore step does.
