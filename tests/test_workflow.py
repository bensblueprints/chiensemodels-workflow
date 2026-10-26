import unittest, tempfile, json
from pathlib import Path
from unittest.mock import Mock, patch

import mask_review, seedance_bridge


class WorkflowTests(unittest.TestCase):
    def test_mask_changed_invalidates_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in mask_review.FILES:
                (p / name).write_bytes(b'original')
            fingerprint = mask_review.fingerprint(p)
            mask_review.review(p, True, 'Entire clip reviewed', fingerprint)
            mask_review.require_approved(p)
            (p / 'mask.mp4').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                mask_review.require_approved(p)
            with self.assertRaises(ValueError):
                mask_review.review(p, True, 'stale', fingerprint)

    def test_existing_submission_not_requeued(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'seedance-response.json').write_text('{}')
            with patch('mask_review.require_approved'), patch('seedance_bridge._generate') as generate:
                with self.assertRaises(ValueError):
                    seedance_bridge.submit(p, 'prompt', 'reference.png')
                generate.assert_not_called()

    def test_draft_quotes_then_submits_with_the_edit_contract(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'audio-manifest.json').write_text('{}')
            calls = []

            def fake_call(method, path, body=None, timeout=90):
                calls.append((method, path, body))
                if path == '/v1/generations/quote':
                    return {'id': 'quote_1', 'price': 1.5}
                return {'id': 'task_1', 'status': 'queued'}

            with patch('mask_review.require_approved'), \
                 patch('seedance_bridge.credential', return_value='sk-cm-test'), \
                 patch('seedance_bridge.upload', return_value='https://chinesemodels.ai/reference/one.mp4'), \
                 patch('audio_workflow.prepare_seedance_video', return_value=p / 'seedance-input.mp4'), \
                 patch('seedance_bridge._call', side_effect=fake_call):
                task = seedance_bridge.submit(p, 'Replace one subject', 'reference.png')

            self.assertEqual(task, 'task_1')
            request = json.loads((p / 'seedance-request.json').read_text())
            self.assertEqual(request['model'], 'bytedance/seedance-2.5/reference-to-video')
            self.assertEqual(request['duration'], -1)
            self.assertEqual(request['ratio'], 'adaptive')
            self.assertEqual(request['omni_reference_task_type'], 'edit')
            self.assertEqual(request['resolution'], '480p')
            self.assertEqual(len(request['reference_videos']), 1)
            self.assertEqual([c[1] for c in calls], ['/v1/generations/quote', '/v1/generations'])
            self.assertEqual(calls[1][2], {'quote_id': 'quote_1'})
            self.assertTrue((p / 'generation.json').exists())
            self.assertEqual(json.loads((p / 'seedance-response.json').read_text())['requestId'], 'task_1')

    def test_collection_downloads_and_restores(self):
        with tempfile.TemporaryDirectory() as d:
            media = Mock()
            media.content = b'video'

            def fake_call(method, path, body=None, timeout=90):
                return {'status': 'completed', 'outputs': ['https://cdn.example/result.mp4']}

            with patch('seedance_bridge._call', side_effect=fake_call), \
                 patch('seedance_bridge.requests.get', return_value=media), \
                 patch('seedance_bridge.finish_preview') as restore:
                seedance_bridge.wait_and_finish(d, 'task_1')
            self.assertEqual((Path(d) / 'seedance-result.mp4').read_bytes(), b'video')
            restore.assert_called_once()

    def test_hd_requires_a_completed_draft_and_never_repeats(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'generation.json').write_text(json.dumps({'request_id': 'draft'}))
            (p / 'seedance-request.json').write_text(json.dumps({'model': 'm'}))
            with self.assertRaises(ValueError):
                seedance_bridge.submit_hd(p)

        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ('upload.mp4', 'final-preview.mp4'):
                (p / name).write_bytes(b'test')
            (p / 'generation.json').write_text(json.dumps({'request_id': 'draft'}))
            (p / 'seedance-request.json').write_text(json.dumps({'model': 'm'}))
            with patch('seedance_bridge._generate', return_value='hd_task') as generate:
                self.assertEqual(seedance_bridge.submit_hd(p), 'hd_task')
                self.assertEqual(generate.call_args.args[1], '1080p')
            self.assertTrue((p / 'hd/response.json').exists())
            with self.assertRaises(ValueError):
                seedance_bridge.submit_hd(p)


if __name__ == '__main__':
    unittest.main()
