import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / 'send-to-android' / 'scripts' / 'cloud-status-check.ps1'


@unittest.skipUnless(shutil.which('powershell') or shutil.which('pwsh'), 'PowerShell is required')
class CloudStatusTests(unittest.TestCase):
    def test_regular_local_file_cannot_prove_phone_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ordinary.txt'
            path.write_text('example', encoding='utf-8')
            result = subprocess.run([shutil.which('pwsh') or shutil.which('powershell'), '-NoProfile', '-File', str(SCRIPT), '-Path', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
            state = json.loads(result.stdout)
            self.assertFalse(state['provider_reports_in_sync'])
            self.assertFalse(state['phone_readback_verified'])

if __name__ == '__main__': unittest.main()
