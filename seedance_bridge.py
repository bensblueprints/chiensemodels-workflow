"""ChineseModels generation bridge.

Verified live against https://chinesemodels.ai (600 models, OpenAI-shaped):

  POST /api/reference-media    multipart(file, kind, model)   -> {"url": …}
  POST /v1/generations/quote   {model, prompt, …}             -> {"id","price","currency","expiresAt"}
  POST /v1/generations         {"quote_id": "quote_…"}        -> {"id","status"}
  GET  /v1/generations/{id}                                   -> {"status","outputs"/"url", …}

Auth: `Authorization: Bearer sk-cm-…` (never x-api-key).
Resolution values are lowercase: 480p | 720p | 1080p.

Editing runs on the reference-to-video model (Moon / Seedance 2.5) with
`omni_reference_task_type: "edit"`, `duration: -1` (follow the source) and
`ratio: "adaptive"`. `kwaivgi/kling-v4.0/video-edit` (SUMO) uses `video` +
`duration` in seconds instead; set CHINESEMODELS_MODEL to switch.

Draft then final: a draft is generated at CHINESEMODELS_PREVIEW_RESOLUTION
(default 480p); approving it regenerates at CHINESEMODELS_RESOLUTION (default
1080p). Both are billed. The provider also exposes
`bytedance/seedance-2.5/draft-complete` for a native draft->final hop; adopt it
once its exact request shape is confirmed against a live account.
"""
from pathlib import Path
import json, requests, time, concurrent.futures
from config import credential, setting
from media_host import upload
from audio_workflow import finish_preview

# Reference token each model family uses for its one source clip.
VIDEO_FIELD = {
    'bytedance/seedance-2.5/reference-to-video': 'reference_videos',
    'kwaivgi/kling-v4.0/video-edit': 'video',
}


def base_url():
    return setting('CHINESEMODELS_BASE_URL', 'https://chinesemodels.ai').rstrip('/')


def model_id():
    return setting('CHINESEMODELS_MODEL', 'bytedance/seedance-2.5/reference-to-video')


def resolution(final=False):
    name = 'CHINESEMODELS_RESOLUTION' if final else 'CHINESEMODELS_PREVIEW_RESOLUTION'
    default = '1080p' if final else '480p'
    return setting(name, default).strip().lower()


def headers():
    return {
        'Authorization': 'Bearer ' + credential('CHINESEMODELS_API_KEY'),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def _call(method, path, body=None, timeout=90):
    r = requests.request(method, base_url() + path, headers=headers(),
                         json=body, timeout=timeout, allow_redirects=False)
    if r.status_code >= 400:
        try:
            message = r.json()['error']['message']
        except (ValueError, KeyError, TypeError):
            message = r.text[:400]
        raise ValueError(f'ChineseModels rejected the request ({r.status_code}): {message}')
    try:
        return r.json()
    except ValueError:
        raise ValueError(f'ChineseModels returned a non-JSON response: {r.text[:300]}')


def build_payload(source_url, image_urls, prompt, res, seconds=None):
    """Assemble the provider payload for the selected model."""
    model = model_id()
    field = VIDEO_FIELD.get(model, 'reference_videos')
    payload = {'model': model, 'prompt': prompt, 'resolution': res}
    if field == 'video':
        payload['video'] = source_url
        payload['duration'] = max(3, min(30, int(round(seconds or 5))))
    else:
        payload['reference_videos'] = [source_url]
        payload['duration'] = -1
        payload['ratio'] = 'adaptive'
        payload['omni_reference_task_type'] = 'edit'
    if image_urls:
        payload['reference_images'] = image_urls
    return payload


def _generate(folder, res, status):
    """Quote then submit the saved payload at `res`; return the provider task id."""
    request = json.loads((folder / 'seedance-request.json').read_text())
    payload = {**request, 'resolution': res}
    status(f'ChineseModels · quoting {payload["model"]} at {res}')
    quote = _call('POST', '/v1/generations/quote', payload)
    if not quote.get('id'):
        raise ValueError('ChineseModels returned no quote id.')
    (folder / 'quote.json').write_text(json.dumps(quote, indent=2))
    status(f'Quote accepted · ${float(quote.get("price", 0)):.4f} · submitting')
    task = _call('POST', '/v1/generations', {'quote_id': quote['id']})
    if not task.get('id'):
        raise ValueError('ChineseModels returned no task id.')
    (folder / 'seedance-response.json').write_text(json.dumps({**task, 'requestId': task['id']}))
    (folder / 'generation.json').write_text(json.dumps({
        'request_id': task['id'], 'quote_id': quote['id'], 'resolution': res,
        'price_usd': quote.get('price'), 'prompt': payload['prompt'], 'model': payload['model'],
    }))
    status('ChineseModels task submitted: ' + task['id'])
    return task['id']


def submit(folder, prompt, primary, secondary=None, status=print):
    folder = Path(folder)
    from mask_review import require_approved, is_mesh
    require_approved(folder)
    if (folder / 'seedance-response.json').exists():
        raise ValueError('This job already has a provider response. Resume it; prepare a new job for a deliberate variation.')
    if not (folder / 'audio-manifest.json').exists():
        raise ValueError('Audio separation must complete before submission.')
    credential('CHINESEMODELS_API_KEY')
    from audio_workflow import prepare_seedance_video
    status('Pitching isolated vocals +3 semitones and embedding in colored-depth video')
    prepared = folder / 'seedance-input.mp4' if is_mesh(folder) else prepare_seedance_video(folder)
    status('Uploading prepared video and character references to ChineseModels')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        urls = list(pool.map(upload, [prepared, primary] + ([secondary] if secondary else [])))
    secondary_note = ('@Image1 is the primary character reference; @Image2 is the secondary character reference.'
                      if secondary else '@Image1 is the only replacement character reference.')
    full = (prompt.replace('@Audio1', 'the audio embedded in the source video')
            + '\nThe source video already contains the isolated vocals pitched up three semitones; '
              'use its embedded audio for performance and lip synchronization. ' + secondary_note)
    if is_mesh(folder):
        mesh_mode = json.loads((folder / 'workflow-mode.json').read_text()).get('mode')
        description = ('depth composite with face mesh overlay' if mesh_mode == 'depth_mesh'
                       else 'original video with face mesh overlay')
        full = (full.replace('colored-depth composite', description)
                + ' Remove all face mesh lines and any depth colors from the output; use them only for '
                  'expression and lip motion guidance. Replace the entire original identity including hair. '
                  'Preserve the exact embedded dialogue and timing.')
    seconds = None
    try:
        import av
        with av.open(str(prepared)) as source:
            seconds = float(source.duration / av.time_base)
    except Exception:
        seconds = None
    payload = build_payload(urls[0], urls[1:], full, resolution(final=False), seconds)
    (folder / 'seedance-request.json').write_text(json.dumps(payload, indent=2))
    return _generate(folder, resolution(final=False), status)


def wait_and_finish(folder, request_id, status=print):
    folder = Path(folder)
    for _ in range(360):
        body = _call('GET', '/v1/generations/' + request_id, timeout=60)
        (folder / 'provider-status.json').write_text(json.dumps(body, indent=2))
        state = str(body.get('status', '')).lower()
        if body.get('progress') is not None:
            status(f'Rendering · {body.get("progress")}')
        if state in ('completed', 'succeeded', 'success'):
            outputs = body.get('outputs') or body.get('output') or body.get('url')
            url = outputs[0] if isinstance(outputs, list) and outputs else outputs
            if not isinstance(url, str) or not url.startswith('https://'):
                raise ValueError(f'ChineseModels completed without a result URL: {str(body)[:300]}')
            r = requests.get(url, timeout=600)
            r.raise_for_status()
            (folder / 'seedance-result.mp4').write_bytes(r.content)
            status('Restoring entire original source audio · discarding generated audio')
            finish_preview(folder / 'seedance-result.mp4', folder)
            return
        if state in ('failed', 'error', 'cancelled', 'canceled'):
            raise RuntimeError('ChineseModels failed: ' + str(body.get('error') or body.get('fail_reason') or state))
        time.sleep(10)
    raise TimeoutError('ChineseModels is still pending. Request ID saved; do not resubmit automatically.')


def submit_hd(folder):
    """Regenerate the accepted draft at the final resolution."""
    folder = Path(folder)
    if (folder / 'hd/response.json').exists():
        raise ValueError('HD already submitted. Resume its saved request.')
    generation = json.loads((folder / 'generation.json').read_text())
    if not (folder / 'final-preview.mp4').exists():
        raise ValueError('A completed draft is required before generating the final resolution.')
    hd = folder / 'hd'
    hd.mkdir(exist_ok=True)
    (hd / 'seedance-request.json').write_bytes((folder / 'seedance-request.json').read_bytes())
    (hd / 'draft.json').write_text(json.dumps({'draft_task': generation['request_id']}))
    source = hd / 'upload.mp4'
    if not source.exists():
        __import__('shutil').copy2(folder / 'upload.mp4', source)
    task_id = _generate(hd, resolution(final=True), print)
    (hd / 'response.json').write_text(json.dumps({'requestId': task_id}))
    return task_id
