from pathlib import Path
import json,requests,re,time,concurrent.futures
from config import credential, setting
from media_host import upload
from audio_workflow import finish_preview

def base_url():
    return setting('CHIENSEMODELS_BASE_URL','https://api.chiensemodels.ai/v1').rstrip('/')+'/'

def submit(folder,prompt,primary,secondary=None,status=print):
    folder=Path(folder)
    from mask_review import require_approved, is_mesh
    require_approved(folder)
    if (folder/'seedance-response.json').exists():raise ValueError('This job already has a provider response. Resume it; prepare a new job for a deliberate variation.')
    key=credential('CHIENSEMODELS_API_KEY')
    if not setting('CHIENSEMODELS_WEBHOOK_URL'):raise ValueError('Webhook URL required. Install cloudflared and restart the app, or set CHIENSEMODELS_WEBHOOK_URL.')
    if not (folder/'audio-manifest.json').exists():raise ValueError('Audio separation must complete before submission.')
    from audio_workflow import prepare_seedance_video
    status('Pitching isolated vocals +3 semitones and embedding in colored-depth video')
    prepared=folder/'seedance-input.mp4' if is_mesh(folder) else prepare_seedance_video(folder)
    status('Uploading video with embedded vocals and character references')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:urls=list(pool.map(upload,[prepared,primary]+([secondary] if secondary else [])))
    p={'model':setting('CHIENSEMODELS_MODEL','seedance-2.5'),'resolution':'1080p','output_format':'mp4','pass_faces':True,'webhook_url':setting('CHIENSEMODELS_WEBHOOK_URL','')}
    p.update(mode='edit',is_draft=True,aspect_ratio='adaptive',videos=[urls[0]],audios=[],images=urls[1:],prompt=prompt.replace('@Audio1', 'the audio embedded in @Video1')+'\n@Video1 contains the colored-depth composite and embedded isolated vocals pitched up three semitones, without the music bed; use its embedded audio for performance and lip synchronization. '+('@Image1 is the primary character reference; @Image2 is the secondary character reference.' if secondary else '@Image1 is the only replacement character reference.'));p.pop('duration',None)
    if Path(primary).suffix.lower() in ['.mp4','.mov','.webm']:
        import av
        with av.open(str(prepared)) as source:
            seconds=float(source.duration/av.time_base)
            stream=source.streams.video[0]
            ratio=stream.width/stream.height
        ratios={'16:9':16/9,'9:16':9/16,'1:1':1,'4:3':4/3,'3:4':3/4,'21:9':21/9}
        p.update(mode='multi_reference',duration=str(max(4,min(30,round(seconds)))),aspect_ratio=min(ratios,key=lambda r:abs(ratios[r]-ratio)))
        p['videos']=[urls[0],urls[1]]
        p['images']=urls[2:]
        p['prompt']=prompt+'\n@Video1 is the source edit and contains isolated vocals pitched +3 semitones. @Video2 is only the primary character visual identity reference. Use only @Video1 audio for speech timing.'
    if is_mesh(folder):
        mesh_mode=json.loads((folder/'workflow-mode.json').read_text()).get('mode')
        description='depth composite with face mesh overlay' if mesh_mode=='depth_mesh' else 'original video with face mesh overlay'
        p['prompt']=p['prompt'].replace('colored-depth composite',description)+' Remove all face mesh lines and any depth colors from the output; use them only for expression and lip motion guidance. Replace the entire original identity including hair. Preserve the exact embedded dialogue and timing.'
    (folder/'seedance-request.json').write_text(json.dumps(p,indent=2));h={'x-api-key':key}
    r=requests.post(base_url()+'queue',headers=h,json=p,timeout=90)
    if not r.ok:
        (folder/'submission-error.json').write_text(r.text)
        raise ValueError(f'Chiensemodels rejected submission ({r.status_code}): {r.text[:500]}')
    j=r.json();(folder/'seedance-response.json').write_text(json.dumps(j))
    ident=j.get('requestId')
    if not ident:raise ValueError('Chiensemodels did not return a request ID.')
    (folder/'generation.json').write_text(json.dumps({'request_id':ident,'prompt':p['prompt'],'video':'seedance-result.mp4','mode':p['mode']}))
    status('Chiensemodels draft submitted: '+ident)
    return ident

def wait_and_finish(folder,request_id,status=print):
    folder=Path(folder)
    key=credential('CHIENSEMODELS_API_KEY')
    for _ in range(360):
        r=requests.post(base_url()+'status',headers={'x-api-key':key},json={'request_id':request_id},timeout=30);r.raise_for_status();j=r.json()
        (folder/'provider-status.json').write_text(json.dumps(j,indent=2))
        if j.get('status')=='COMPLETED':
            url=j.get('result')
            if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Chiensemodels result URL missing.')
            r=requests.get(url,timeout=180);r.raise_for_status();(folder/'seedance-result.mp4').write_bytes(r.content)
            status('Restoring entire original source audio · discarding generated audio')
            finish_preview(folder/'seedance-result.mp4',folder)
            return
        if j.get('status') in ['FAILED','CANCELED']:raise RuntimeError('Chiensemodels failed: '+str(j.get('error') or j.get('status')))
        time.sleep(10)
    raise TimeoutError('Chiensemodels is still pending. Request ID saved; do not resubmit automatically.')


def submit_hd(folder):
    """Complete the accepted draft; Chiensemodels reuses its original parameters."""
    folder=Path(folder)
    if (folder/'hd/response.json').exists():raise ValueError('HD already submitted. Resume its saved request.')
    generation=json.loads((folder/'generation.json').read_text())
    original=json.loads((folder/'seedance-request.json').read_text())
    if not original.get('is_draft') or not (folder/'final-preview.mp4').exists():
        raise ValueError('A completed draft is required before generating 1080p.')
    payload={'model':original.get('model','seedance-2.5'),'draft_id':generation['request_id'],'webhook_url':original['webhook_url']}
    key=credential('CHIENSEMODELS_API_KEY')
    hd=folder/'hd';hd.mkdir(exist_ok=True)
    # Keep the draft intact and use the exact source audio for the HD export.
    source=hd/'upload.mp4'
    if not source.exists():__import__('shutil').copy2(folder/'upload.mp4',source)
    (hd/'request.json').write_text(json.dumps(payload,indent=2))
    response=requests.post(base_url()+'queue',headers={'x-api-key':key},json=payload,timeout=90)
    response.raise_for_status();data=response.json()
    (hd/'response.json').write_text(json.dumps(data))
    ident=data.get('requestId')
    if not ident:raise ValueError('Chiensemodels did not return a request ID.')
    return ident
