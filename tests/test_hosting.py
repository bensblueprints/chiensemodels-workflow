import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from media_host import upload, kind_for


class ReferenceMediaTests(unittest.TestCase):
    def test_upload_returns_provider_url_and_sends_role(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'composite.mp4'
            path.write_bytes(b'video')
            response = Mock(status_code=200)
            response.json.return_value = {'url': 'https://chinesemodels.ai/api/reference-media/abc.mp4'}
            with patch('media_host.credential', return_value='sk-cm-test'), \
                 patch('media_host.setting', side_effect=lambda k, d='': {'CHINESEMODELS_BASE_URL': 'https://chinesemodels.ai',
                                                                          'CHINESEMODELS_MODEL': 'bytedance/seedance-2.5/reference-to-video'}.get(k, d)), \
                 patch('media_host.requests.post', return_value=response) as post:
                url = upload(path)
            self.assertEqual(url, 'https://chinesemodels.ai/api/reference-media/abc.mp4')
            self.assertEqual(post.call_args.args[0], 'https://chinesemodels.ai/api/reference-media')
            self.assertEqual(post.call_args.kwargs['data']['kind'], 'video')
            self.assertEqual(post.call_args.kwargs['data']['model'], 'bytedance/seedance-2.5/reference-to-video')
            self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer sk-cm-test')

    def test_kind_splits_video_from_image(self):
        self.assertEqual(kind_for('composite.MP4'), 'video')
        self.assertEqual(kind_for('character.webp'), 'image')

    def test_error_status_raises_before_any_generation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'composite.mp4'
            path.write_bytes(b'video')
            response = Mock(status_code=413, text='too large')
            with patch('media_host.credential', return_value='sk-cm-test'), \
                 patch('media_host.setting', return_value='https://chinesemodels.ai'), \
                 patch('media_host.requests.post', return_value=response):
                with self.assertRaises(RuntimeError):
                    upload(path)

    def test_non_https_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'composite.mp4'
            path.write_bytes(b'video')
            response = Mock(status_code=200)
            response.json.return_value = {'url': 'http://insecure.example/x.mp4'}
            with patch('media_host.credential', return_value='sk-cm-test'), \
                 patch('media_host.setting', return_value='https://chinesemodels.ai'), \
                 patch('media_host.requests.post', return_value=response):
                with self.assertRaises(RuntimeError):
                    upload(path)
