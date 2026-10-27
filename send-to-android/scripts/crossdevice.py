"""Send to the explicitly selected Windows CrossDevice folder without ADB."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def deliver(source, cloud, expected, overwrite=False):
    source = Path(source).resolve(strict=True)
    if not source.is_file(): raise ValueError('source must be a regular file')
    cloud.verify_device(expected)
    target = source.name
    if cloud.exists(target) and not overwrite: raise FileExistsError('target exists; explicit overwrite required')
    checksum = digest(source)
    nonce = uuid.uuid4().hex
    stage = 'codex-stage-' + nonce + source.suffix
    backup = 'codex-backup-' + nonce + source.suffix
    phase = 'stage'
    try:
        cloud.stage(source, stage)
        if cloud.synced_hash(stage) != checksum: raise ValueError('staged checksum mismatch')
        if digest(source) != checksum: raise ValueError('source changed during transfer')
        cloud.verify_device(expected)
        if cloud.exists(target):
            if not overwrite: raise FileExistsError('target appeared during transfer')
            phase = 'backup'
            old = cloud.synced_hash(target)
            cloud.rename(target, backup)
            if cloud.synced_hash(backup) != old: raise ValueError('backup checksum mismatch')
        else:
            backup = None
        cloud.verify_device(expected)
        phase = 'replace'
        cloud.rename(stage, target)
        if cloud.synced_hash(target) != checksum: raise ValueError('target checksum mismatch')
    except Exception as exc:
        raise RuntimeError('failed or unverified; phase=%s; staged=%s; backup=%s; reason=%s' % (phase,stage,backup,exc)) from exc
    return {'result':'provider_confirmed', 'file':target, 'sha256':checksum, 'backup':backup, 'phone_readback_verified':False}


class WindowsCloud:
    def __init__(self, device, folder, timeout):
        if os.name != 'nt': raise RuntimeError('Windows is required')
        if not device or device in ('.','..') or '/' in device or '\\' in device: raise ValueError('device must be one folder name')
        relative = Path(folder)
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('folder must be relative to storage')
        self.base = Path.home() / 'CrossDevice'
        self.root = self.base / device
        self.folder = self.root / 'storage' / relative
        self.timeout = timeout
        self.expected = device
        self.powershell = Path(os.environ.get('SystemRoot',r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        self.checker = Path(__file__).with_name('cloud-status-check.ps1')

    def state(self,path):
        proc=subprocess.run([str(self.powershell),'-NoProfile','-File',str(self.checker),'-Path',str(path)],capture_output=True,timeout=30)
        if proc.returncode not in (0,3): raise OSError('cannot inspect provider state')
        try: return int(json.loads(proc.stdout.decode('utf-8'))['state_hex'],16)
        except (ValueError,KeyError) as exc: raise OSError('invalid provider state response') from exc

    def verify_device(self, expected):
        roots=[]
        if not self.base.is_dir(): raise ValueError('CrossDevice is not available')
        for item in self.base.iterdir():
            if item.is_dir():
                try:
                    if self.state(item) & 2: roots.append(item.name)
                except OSError: pass
        if expected != self.expected or roots != [expected]: raise ValueError('expected exactly the selected phone sync root')
        if not self.folder.is_dir(): raise ValueError('phone folder is unavailable')
        if not self.folder.resolve().is_relative_to(self.root.resolve()): raise ValueError('phone folder escapes the selected device')
    def path(self,name):
        if Path(name).name != name: raise ValueError('invalid filename')
        return self.folder / name
    def exists(self,name): return self.path(name).exists()
    def stage(self, source, name):
        self.verify_device(self.expected)
        with source.open('rb') as src, self.path(name).open('xb') as dst: shutil.copyfileobj(src,dst,1024*1024)
    def synced_hash(self,name):
        p=self.path(name); deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            self.verify_device(self.expected)
            state=self.state(p)
            if state != 0xffffffff and state & 9 == 9:
                result=digest(p)
                if self.state(p) & 9 == 9: return result
            time.sleep(2)
        raise TimeoutError('sync provider did not confirm ' + name)
    def rename(self,old,new):
        self.verify_device(self.expected)
        os.rename(self.path(old),self.path(new))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device',required=True,help='Exact displayed phone sync-root name')
    p.add_argument('--folder',required=True,help='Folder relative to the phone storage root')
    p.add_argument('--overwrite',action='store_true')
    p.add_argument('--timeout',type=int,default=120)
    p.add_argument('files',nargs='+',type=Path)
    args=p.parse_args()
    try:
        if args.timeout <= 0: raise ValueError('timeout must be positive')
        if len({x.name.casefold() for x in args.files}) != len(args.files): raise ValueError('duplicate target names')
        cloud=WindowsCloud(args.device,args.folder,args.timeout)
        for file in args.files: print(json.dumps(deliver(file,cloud,args.device,args.overwrite),ensure_ascii=False),flush=True)
        return 0
    except (OSError,ValueError,RuntimeError,TimeoutError,subprocess.SubprocessError) as exc:
        print(json.dumps({'result':'failed_or_unverified','error':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 1


if __name__=='__main__': raise SystemExit(main())
