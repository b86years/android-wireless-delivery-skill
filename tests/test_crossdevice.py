import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).parents[1] / 'send-to-android' / 'scripts' / 'crossdevice.py'
spec = importlib.util.spec_from_file_location('crossdevice', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeCloud:
    def __init__(self):
        self.files = {}
        self.operations = []
        self.fail_stage = False
        self.corrupt_stage = False
        self.fail_final = False
    def verify_device(self, expected):
        if expected != 'phone-A': raise ValueError('device mismatch')
    def exists(self, path): return path in self.files
    def stage(self, source, path):
        self.operations.append(('stage', path))
        self.files[path] = b'corrupt' if self.corrupt_stage else source.read_bytes()
    def synced_hash(self, path):
        import hashlib
        if self.fail_stage and '-stage-' in path: raise TimeoutError('stage not synced')
        if self.fail_final and path.endswith('example.txt'): raise TimeoutError('target not synced')
        return hashlib.sha256(self.files[path]).hexdigest()
    def rename(self, old, new):
        self.operations.append(('rename', old, new))
        if new in self.files: raise FileExistsError(new)
        self.files[new] = self.files.pop(old)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / 'example.txt'
        self.source.write_bytes(b'new content')
        self.cloud = FakeCloud()
        self.target = 'example.txt'
    def tearDown(self): self.temp.cleanup()
    def send(self, **kwargs): return module.deliver(self.source, self.cloud, 'phone-A', **kwargs)

    def test_wrong_device_stops_before_write(self):
        with self.assertRaises(ValueError): module.deliver(self.source, self.cloud, 'phone-B')
        self.assertEqual(self.cloud.operations, [])
    def test_existing_target_requires_overwrite_permission(self):
        self.cloud.files[self.target] = b'old'
        with self.assertRaises(FileExistsError): self.send()
        self.assertEqual(self.cloud.operations, [])
    def test_stage_sync_failure_leaves_original(self):
        self.cloud.files[self.target] = b'old'; self.cloud.fail_stage = True
        with self.assertRaisesRegex(RuntimeError, 'stage not synced'): self.send(overwrite=True)
        self.assertEqual(self.cloud.files[self.target], b'old')
    def test_corrupt_staged_file_leaves_original(self):
        self.cloud.files[self.target] = b'old'; self.cloud.corrupt_stage = True
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'): self.send(overwrite=True)
        self.assertEqual(self.cloud.files[self.target], b'old')
        self.assertFalse(any(op[0]=='rename' for op in self.cloud.operations))
    def test_overwrite_retains_backup(self):
        self.cloud.files[self.target] = b'old'
        result = self.send(overwrite=True)
        self.assertEqual(self.cloud.files[self.target], b'new content')
        self.assertEqual(self.cloud.files[result['backup']], b'old')
        self.assertEqual(result['result'], 'provider_confirmed')
        self.assertFalse(result['phone_readback_verified'])
    def test_final_sync_failure_does_not_remove_backup(self):
        self.cloud.files[self.target] = b'old'; self.cloud.fail_final = True
        with self.assertRaisesRegex(RuntimeError, 'target not synced'): self.send(overwrite=True)
        self.assertIn(b'old', self.cloud.files.values())
    def test_new_file_creates_without_backup(self):
        result = self.send()
        self.assertIsNone(result['backup'])
        self.assertEqual(self.cloud.files[self.target], b'new content')
    def test_target_appearing_during_transfer_is_not_overwritten(self):
        original_stage = self.cloud.stage
        def race(source, name):
            original_stage(source, name)
            self.cloud.files[self.target] = b'other content'
        self.cloud.stage = race
        with self.assertRaisesRegex(RuntimeError, 'target appeared'): self.send()
        self.assertEqual(self.cloud.files[self.target], b'other content')

    def test_invalid_sync_root_state_fails_closed(self):
        root=Path(self.temp.name) / 'phone-A'
        (root / 'storage').mkdir(parents=True)
        cloud=object.__new__(module.WindowsCloud)
        cloud.base=Path(self.temp.name); cloud.root=root; cloud.folder=root / 'storage'; cloud.expected='phone-A'
        cloud.state=lambda path: 0xffffffff
        with self.assertRaisesRegex(ValueError, 'invalid sync root'): cloud.verify_device('phone-A')

    def make_windows_cloud(self, states):
        cloud=object.__new__(module.WindowsCloud)
        cloud.base=Path(self.temp.name); cloud.root=cloud.base; cloud.folder=cloud.base; cloud.expected='phone-A'; cloud.timeout=1
        cloud.verify_device=lambda expected: None
        reads=iter(states); cloud.state=lambda path: next(reads)
        (cloud.folder / 'f.bin').write_bytes(b'x')
        return cloud

    def test_synced_hash_accepts_two_in_sync_reads(self):
        self.assertEqual(len(self.make_windows_cloud([0x9, 0x9]).synced_hash('f.bin')), 64)

    def test_invalid_state_on_second_read_is_not_confirmed(self):
        # 0xFFFFFFFF & 9 == 9, so the invalid state must be excluded on every read, not only the first.
        with self.assertRaises(TimeoutError): self.make_windows_cloud([0x9, module.INVALID_STATE] + [module.INVALID_STATE] * 50).synced_hash('f.bin')

    @unittest.skipUnless(os.name == 'nt', 'Windows is required')
    def test_regular_file_is_not_a_placeholder_and_missing_file_raises(self):
        path = Path(self.temp.name) / 'ordinary.txt'; path.write_text('example', encoding='utf-8')
        self.assertEqual(module.placeholder_state(path), 0)
        with self.assertRaises(OSError): module.placeholder_state(Path(self.temp.name) / 'missing.txt')

if __name__ == '__main__': unittest.main()
