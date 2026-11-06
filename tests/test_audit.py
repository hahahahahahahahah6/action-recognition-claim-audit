import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from action_recognition_claim_audit.audit import audit, evidence, main, matches, ACTIONRECOGNITION, NOACTIONRECOGNITION, GENERIC_NAMES

class AuditTests(unittest.TestCase):
    def test_phrase_oracle(self):
        self.assertEqual(list(ACTIONRECOGNITION), ['action recognition', 'action-recognition', 'action classification', 'action-classification', 'recognizes actions', 'recognize actions', 'recognizing actions', 'recognized actions', 'recognize human actions', 'recognizes human actions', 'human action recognition', 'video action recognition', 'video-based action recognition', 'action recognition support', 'supports action recognition', 'action recognition capability', 'action recognition feature', 'action recognition pipeline', 'action recognition system', 'action recognition tool', 'action recognition framework', 'action recognition library', 'action recognition api', 'action recognition model', 'action recognition models', 'action recognition engine', 'action recognition module', 'action recognition function', 'action recognition functionality', 'action recognition workflow', 'action recognition method', 'action recognition approach', 'action recognition service', 'action recognition results', 'action recognition performance', 'action recognition task', 'action recognition tasks', 'action recognition algorithm', 'action recognition algorithms', 'action recognition configuration', 'action recognition script', 'action detection', 'detect actions', 'detects actions', 'detecting actions', 'classify actions', 'classifies actions', 'classifying actions', 'action recognition mode', 'recognize actions in video'])
        self.assertEqual(list(NOACTIONRECOGNITION), ['does not recognize actions', 'do not recognize actions', "doesn't recognize actions", "don't recognize actions", 'no action recognition', 'without action recognition', 'never recognizes actions', 'does not support action recognition', 'action recognition not supported', 'action recognition unsupported', 'no action recognition support', 'lacks action recognition', 'missing action recognition', 'action recognition disabled', 'no action recognition model', 'without action recognition support', 'does not provide action recognition', 'no automatic action recognition', 'action recognition not available', 'no action recognition capability', 'does not recognize human actions', 'without an action recognition model', 'does not perform action recognition', 'never performs action recognition'])

    def test_generic_oracle(self):
        self.assertEqual(list(GENERIC_NAMES), ['recognize_action', 'recognize_actions', 'detect_action', 'detect_actions', 'classify_action', 'classify_actions', 'predict_action', 'predict_actions', 'identify_action', 'identify_actions', 'recognize_human_action', 'recognize_human_actions', 'classify_video_action', 'classify_video_actions', 'predict_video_action', 'recognize_video_action', 'detect_video_action', 'get_action_label', 'get_action_labels', 'extract_action', 'extract_actions', 'analyze_action', 'analyze_actions', 'run_action_recognition'])

    def fixture(self, readme='', code='', extra=None, flags=()):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'README.md').write_text(readme)
            (root/'app.py').write_text(code)
            for name, text in (extra or {}).items():
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                status = main(['audit', str(root)] + list(flags))
            return status, out.getvalue()

    def test_inventory_matching(self):
        for phrase in ACTIONRECOGNITION:
            with self.subTest(phrase=phrase):
                self.assertEqual(matches(phrase, ACTIONRECOGNITION)[0], [phrase])
        for phrase in NOACTIONRECOGNITION:
            with self.subTest(phrase=phrase):
                denials, rest = matches(phrase, NOACTIONRECOGNITION)
                self.assertEqual(denials, [phrase])
                self.assertEqual(matches(rest, ACTIONRECOGNITION)[0], [])
        self.assertEqual(matches('video action recognition', ACTIONRECOGNITION)[0], ['video action recognition'])

    def test_generics(self):
        for name in GENERIC_NAMES:
            for code in ('x.'+name+'()', 'from unknown import '+name+' as run; run()'):
                with self.subTest(code=code): self.assertTrue(evidence(code))

    def test_split_modules(self):
        self.assertEqual(self.fixture('action recognition', 'from torchvision.models.video import r3d_18; m=r3d_18()', {'other.py': 'm.forward(x)'})[0], 2)

    def test_matching(self):
        self.assertEqual(matches('action recognition', ACTIONRECOGNITION)[0], ['action recognition'])
        self.assertEqual(self.fixture('does not recognize actions')[0], 0)
        self.assertEqual(self.fixture('ACTION RECOGNITION')[0], 2)
        self.assertEqual(self.fixture('```text\naction recognition\n```')[0], 0)
        self.assertEqual(self.fixture('`action recognition`')[0], 2)
        self.assertEqual(matches('we detect actions in the audit log', ACTIONRECOGNITION)[0], ['detect actions'])

    def test_cli_good(self):
        self.assertEqual(self.fixture('action recognition', 'x.recognize_action()'), (0, 'PASS\n'))

    def test_cli_bad(self):
        status, out = self.fixture('action recognition')
        self.assertEqual(status, 2)
        self.assertIn('HIGH documented-action-recognition-claim-false', out)

    def test_cli_test_only(self):
        extra = {'tests/sample.md': 'action recognition'}
        status, out = self.fixture(extra=extra)
        self.assertEqual(status, 0)
        self.assertIn('MEDIUM', out)
        self.assertEqual(self.fixture(extra=extra, flags=['--fail-on', 'medium'])[0], 2)

    def test_cli_denial(self):
        status, out = self.fixture('no action recognition', 'x.recognize_action()')
        self.assertEqual(status, 2)
        self.assertIn('HIGH documented-no-action-recognition-claim-false', out)

    def test_cli_no_claim(self):
        self.assertEqual(self.fixture('A useful tool.'), (0, 'PASS\n'))

    def test_cli_json(self):
        status, out = self.fixture('action recognition', flags=['--json'])
        f = json.loads(out)[0]
        self.assertEqual(status, 2)
        self.assertEqual(f['verdict'], 'FAIL')
        self.assertTrue(f['message'])

    def test_cli_ignore(self):
        self.assertEqual(self.fixture(extra={'docs/claim.md': 'action recognition'}, flags=['--ignore', 'docs/'])[0], 0)

    def test_cli_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            main(['--version'])
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), '0.1.0')

    def test_readme(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(self.fixture((root/'README.md').read_text()), (0, 'PASS\n'))

    def test_io_and_usage(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['audit', '/nonexistent-r142-directory']), 1)
            with self.assertRaises(SystemExit) as cm: main(['audit', '--unknown'])
        self.assertEqual(cm.exception.code, 1)

    def test_virtualenv_excluded(self):
        status, out = self.fixture('action recognition', extra={
            'custom-env/pyvenv.cfg': 'home = /usr/bin',
            'custom-env/lib/model.py': 'x.recognize_action()',
        })
        self.assertEqual(status, 2)

    def test_verbose(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(self.fixture(flags=['--verbose'])[0], 0)
        self.assertIn('scope:', err.getvalue())

    def test_model_pairs(self):
        groups = {
            'torchvision.models.video': ('r3d_18', 'mc3_18', 'r2plus1d_18', 's3d', 'mvit_v1_b', 'mvit_v2_s'),
            'pytorchvideo.models': ('slowfast_r50', 'slowfast_r101', 'x3d_m', 'x3d_s', 'x3d_xs', 'x3d_l'),
            'transformers': ('VideoMAEForVideoClassification', 'VivitForVideoClassification', 'VideoSwinForVideoClassification'),
        }
        for module, names in groups.items():
            for name in names:
                for setup, expression in [
                    (f'from {module} import {name}; ', name),
                    (f'from {module} import {name} as F; ', 'F'),
                    (f'import {module} as lib; ', 'lib.' + name),
                    (f'import {module}; ', module + '.' + name),
                ]:
                    for run in ('m(x)', 'm.forward(x)'):
                        with self.subTest(module=module, name=name, setup=setup, run=run):
                            self.assertTrue(evidence(setup + 'm=' + expression + '(); ' + run))
                    for run in ('(x)', '.forward(x)'):
                        self.assertTrue(evidence(setup + expression + '()' + run))
                    self.assertFalse(evidence(setup + expression + '()'))
                    self.assertFalse(evidence(setup + 'm=' + expression + '(); other(x)'))
                self.assertFalse(evidence(f'from {module} import {name}\ndef {name}(): pass\n{name}()(x)'))

    def test_mmaction_pair(self):
        for code in [
            'from mmaction.apis import init_recognizer as init, inference_recognizer as run; init(); run(x)',
            'import mmaction.apis as a; a.init_recognizer(); a.inference_recognizer(x)',
        ]:
            self.assertTrue(evidence(code))
        for name in ('init_recognizer', 'inference_recognizer'):
            self.assertFalse(evidence('from mmaction.apis import init_recognizer, inference_recognizer\ndef '+name+'(): pass\ninit_recognizer(); inference_recognizer(x)'))
        self.assertFalse(evidence('from mmaction.apis import init_recognizer; init_recognizer()'))
        self.assertEqual(self.fixture('action recognition', 'from mmaction.apis import init_recognizer; init_recognizer()', {'other.py': 'from mmaction.apis import inference_recognizer; inference_recognizer(x)'})[0], 2)

    def test_pipeline(self):
        for setup, factory in [('from transformers import pipeline; ', 'pipeline'), ('from transformers import pipeline as P; ', 'P'), ('import transformers as t; ', 't.pipeline')]:
            self.assertTrue(evidence(setup+factory+'("video-classification")(x)'))
            self.assertTrue(evidence(setup+'m='+factory+'("video-classification"); m(x)'))
            self.assertFalse(evidence(setup+factory+'("video-classification")'))
            for task in ('image-classification', 'object-detection', 'text-classification'):
                self.assertFalse(evidence(setup+factory+'("'+task+'")(x)'))
        self.assertFalse(evidence('from transformers import pipeline\ndef pipeline(x): pass\npipeline("video-classification")(x)'))

    def test_rejections(self):
        cases = [
            'import torchvision, pytorchvideo, mmaction, transformers',
            'from torchvision.models import resnet18; resnet18()(x)',
            'from torchvision.models import efficientnet_b0; efficientnet_b0().forward(x)',
            'from torchvision.models import vit_b_16; vit_b_16()(x)',
            'from ultralytics import YOLO; YOLO().predict(x)',
            'from torchvision.models.detection import fasterrcnn_resnet50_fpn; fasterrcnn_resnet50_fpn()(x)',
            'from detectron2.engine import DefaultPredictor; DefaultPredictor()(x)',
            'p=PoseEstimator(); p.keypoints(x)',
            'from torchvision.models.optical_flow import raft_large; raft_large()(x,y)',
            't=Tracker(); t.update(x)',
            'from diffusers import VideoPipeline; VideoPipeline()(x)',
            'import cv2; cap=cv2.VideoCapture(x); cap.read()',
            'from decord import VideoReader; v=VideoReader(x); v[0]',
            'from transformers import VideoMAEModel; VideoMAEModel()(x)',
            '"action recognition recognize actions" # action recognition',
            '"""recognize actions"""',
            'from unknown import recognize_action; recognize_action',
            'recognize_action()',
            'import subprocess; subprocess.run(["recognition-cli", "clip"])',
            'this is invalid python!',
            'from unknown import recognize_action\ndef recognize_action(): pass\nrecognize_action()',
            'from unknown import recognize_action\nclass recognize_action: pass\nrecognize_action()',
        ]
        for code in cases:
            with self.subTest(code=code): self.assertFalse(evidence(code))

if __name__ == '__main__':
    unittest.main()
