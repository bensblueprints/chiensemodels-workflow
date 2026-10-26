"""Local, token-free replacements for the Genjustsu pipeline's Replicate calls.

DepthAnything (transformers) for depth, Segment Anything for masks, Demucs for
vocal isolation. All run on this machine; no Replicate / HuggingFace Space call.
Artifacts match the originals exactly, so pipeline.composite and
prepare_seedance_video keep working unchanged.
"""
from pathlib import Path

import av
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent


def depth_local(src, dst):
    """Write a grayscale depth video, same role as depth_replicate()."""
    from transformers import pipeline as hf_pipeline
    model = hf_pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf')
    c = av.open(str(src)); vs = c.streams.video[0]
    out = av.open(str(dst), 'w')
    st = out.add_stream('libx264', rate=vs.average_rate)
    st.width, st.height, st.pix_fmt = vs.width, vs.height, 'yuv420p'
    st.options = {'crf': '18'}
    for frame in c.decode(vs):
        rgb = frame.to_ndarray(format='rgb24')
        a = np.asarray(model(Image.fromarray(rgb))['depth'], dtype=np.float32)
        a = (a - a.min()) / max(float(a.max() - a.min()), 1e-6)
        gray = (255 - a * 255).astype(np.uint8)
        vf = av.VideoFrame.from_ndarray(np.stack([gray] * 3, axis=-1), format='rgb24')
        vf.pts = frame.pts
        for p in st.encode(vf):
            out.mux(p)
    for p in st.encode():
        out.mux(p)
    out.close(); c.close()


def segment_raw_local(video, folder, prompt='person'):
    """Segment the largest subject per frame locally -> mask_0000.png ... (white=subject)."""
    from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
    folder = Path(folder)
    out = folder / 'raw-masks'
    out.mkdir(exist_ok=True)
    ckpt = ROOT / 'sam_vit_b_01ec64.pth'
    sam = sam_model_registry['vit_b'](checkpoint=str(ckpt))
    gen = SamAutomaticMaskGenerator(sam)
    c = av.open(str(video))
    idx = 0
    for frame in c.decode(c.streams.video[0]):
        rgb = frame.to_ndarray(format='rgb24')
        masks = gen.generate(rgb)
        if masks:
            m = max(masks, key=lambda m: m['area'])['segmentation'].astype(np.uint8) * 255
        else:
            m = np.zeros(rgb.shape[:2], dtype=np.uint8)
        Image.fromarray(m).save(out / ('mask_%04d.png' % idx))
        idx += 1
    c.close()
    return out


def separate_local(src, folder, status=print):
    """Demucs htdemucs locally, replacing audio_workflow.separate()'s Replicate call."""
    import json
    import soundfile as sf
    from demucs.api import Separator
    from audio_workflow import read_audio, write_audio
    folder = Path(folder)
    if (folder / 'audio-manifest.json').exists():
        return
    status('Audio · local Demucs separation (no Replicate token)')
    original = read_audio(src)
    write_audio(folder / 'original-audio.wav', original)
    sep = Separator('htdemucs')
    _, separated = sep.separate_audio_file(str(folder / 'original-audio.wav'))
    rate = sep.samplerate
    music = np.zeros_like(original)
    for name, audio in separated.items():
        a = audio.cpu().numpy()
        sf.write(str(folder / (name + '.wav')), a.T, rate)
        if name != 'vocals':
            n = min(music.shape[1], a.shape[1])
            music[:, :n] += a[:, :n]
    write_audio(folder / 'music.wav', np.clip(music, -1, 1))
    (folder / 'audio-manifest.json').write_text(json.dumps({
        'seedance_video': 'composite-silent.mp4',
        'seedance_audio': 'vocals.wav',
        'final_audio': 'upload.mp4 (entire original audio track)',
        'discard_seedance_audio': True,
        'separation': 'Demucs htdemucs, local (no Replicate)',
    }, indent=2))
