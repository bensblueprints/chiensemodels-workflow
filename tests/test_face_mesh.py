import unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch

import mask_review, seedance_bridge


class FaceMeshTests(unittest.TestCase):
    def test_mesh_approval_tracks_overlay_and_audio_without_masks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'workflow-mode.json').write_text('{"mode":"face_mesh"}')
            for n in ['original.mp4', 'face-landmarks.json', 'composite-silent.mp4', 'seedance-input.mp4']:
                (p / n).write_bytes(b'test')
            mask_review.review(p, True, 'Full mesh reviewed', mask_review.fingerprint(p))
            mask_review.require_approved(p)
            (p / 'seedance-input.mp4').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                mask_review.require_approved(p)

    def test_mesh_submission_does_not_rebuild_depth_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'workflow-mode.json').write_text('{"mode":"face_mesh"}')
            (p / 'audio-manifest.json').write_text('{}')
            calls = []

            def fake_call(method, path, body=None, timeout=90):
                calls.append((method, path, body))
                return {'id': 'quote_1', 'price': 1.0} if path == '/v1/generations/quote' else {'id': 'mesh-test'}

            with patch('mask_review.require_approved'), \
                 patch('seedance_bridge.credential', return_value='sk-cm-test'), \
                 patch('seedance_bridge.upload', return_value='https://chinesemodels.ai/reference/video.mp4'), \
                 patch('audio_workflow.prepare_seedance_video') as prepare, \
                 patch('seedance_bridge._call', side_effect=fake_call):
                seedance_bridge.submit(p, 'Replace subject', 'reference.png')
            prepare.assert_not_called()
            prompt = json.loads((p / 'seedance-request.json').read_text())['prompt']
            self.assertIn('Remove all face mesh lines', prompt)
            self.assertNotIn('colored-depth', prompt)


if __name__ == '__main__':
    unittest.main()
