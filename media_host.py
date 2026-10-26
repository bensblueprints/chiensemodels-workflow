"""Upload prepared media to ChineseModels' reference-media store.

Verified live against https://chinesemodels.ai (2026-10-26):

  POST /api/reference-media   multipart(file, kind, model)  ->  {"url": "https://…"}
  Auth: Authorization: Bearer sk-cm-…

Every prepared file the generation step needs (the colored-depth composite and
each character reference) is registered here first, so the model receives a
reachable HTTPS URL. No third-party host is involved.
"""
from pathlib import Path
import mimetypes
import requests
from config import credential, setting

VIDEO_EXTS = {'.mp4', '.mov', '.webm'}


def base():
    return setting('CHINESEMODELS_BASE_URL', 'https://chinesemodels.ai').rstrip('/')


def model():
    return setting('CHINESEMODELS_MODEL', 'bytedance/seedance-2.5/reference-to-video')


def kind_for(path):
    return 'video' if Path(path).suffix.lower() in VIDEO_EXTS else 'image'


def upload(path):
    """Register one file and return its public HTTPS URL."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    with path.open('rb') as f:
        r = requests.post(
            base() + '/api/reference-media',
            headers={'Authorization': 'Bearer ' + credential('CHINESEMODELS_API_KEY')},
            files={'file': (path.name, f, mime)},
            data={'kind': kind_for(path), 'model': model()},
            timeout=300, allow_redirects=False,
        )
    if r.status_code >= 400:
        raise RuntimeError(f'ChineseModels reference-media upload failed ({r.status_code}): {r.text[:300]}')
    try:
        url = r.json()['url']
    except (ValueError, KeyError, TypeError):
        raise RuntimeError(f'ChineseModels reference-media returned no URL: {r.text[:300]}')
    if not isinstance(url, str) or not url.startswith('https://'):
        raise RuntimeError('ChineseModels returned a non-HTTPS media URL')
    return url
