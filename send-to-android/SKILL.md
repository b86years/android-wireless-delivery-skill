---
name: send-to-android
description: Send files to the explicitly selected Android device through Windows File Explorer mobile-device integration, with provider-status checks and preserved overwrite backups; does not require ADB or Computer Use during routine transfers.
---

# Send files to an Android phone

Identify the user's intended files, phone, and destination folder. Use only explicitly authorized files. The user must approve overwrite before using `--overwrite`.

Windows 11 must have the phone paired through Mobile devices with “Show mobile device in File Explorer” enabled. Open `ms-settings:mobile-devices` if setup is needed. Pairing, QR scanning and permission decisions remain with the user. Do not automate UI or circumvent authorization.

Inspect `%USERPROFILE%\CrossDevice`; require one active sync root with the exact device name the user identifies. Do not proceed when the device is ambiguous, similarly named, disconnected, or the folder is unknown. A displayed name is not a cryptographic device identity. The target folder must already exist under the selected phone's `storage` directory.

Run `scripts/crossdevice.py --device <exact-name> --folder <relative-folder> <files...>`; add `--overwrite` only with authorization. It stages each file, requires provider in-sync state and a matching local hash, preserves a uniquely named backup of an existing target, then renames the stage. It does not assume that a successful copy means delivery. On failure, preserve staged and backup files, report their names and the phase, and do not blindly retry. The two renames are not atomic; avoid concurrent edits on the phone.

Report `provider_confirmed` as the Windows provider's confirmation, **not** an independent phone-side readback. Phone playback and independent device verification require separate evidence. Treat local paths, device names and terminal output as private; never publish logs without redaction.
