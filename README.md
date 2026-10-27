# Wireless Android file delivery skill

A Windows skill for sending files to the explicitly selected Android phone through Windows mobile-device File Explorer integration. This integration uses Link to Windows and is separate from the Phone Link “Send to my phone” share command. It does not use ADB or UI automation during transfers.

**Experimental:** tested on one Windows 11 and Android device. A completion result means the Windows sync provider reports the file in sync and the local content hash matches. It is not an independent phone-side readback or a guarantee of support on other devices.

## Requirements and setup

- Windows 11, Android 11 or newer, and Link to Windows with File Explorer integration enabled. See [Microsoft's setup instructions](https://support.microsoft.com/en-us/windows/experience/fileexplorer/setting-up-and-using-your-phone-in-file-explorer).
- Python 3.9 or newer and Windows PowerShell 5.1.
- The user pairs the phone, approves any system permissions, and chooses the phone displayed in File Explorer. An assistant can open `ms-settings:mobile-devices`; it cannot silently grant permissions or scan a QR code for the user.
- The destination folder must already exist on the selected phone. The script requires the exact displayed CrossDevice root name and refuses to proceed if it cannot find exactly that one sync root. This is a name-based guard, not a cryptographic device identity; do not use it when devices are ambiguous or share the same displayed name.

## Use

Install the `send-to-android` directory as a skill. An agent should read `send-to-android/SKILL.md`. Manual example:

```powershell
python send-to-android/scripts/crossdevice.py --device 'Displayed phone name' --folder 'Download\MyFolder' 'C:\path\example.mp4'
```

The folder is relative to the phone's `storage` directory. The result `provider_confirmed` is deliberately distinct from phone-side verification. Requesting `--overwrite` first renames the existing file to a uniquely named backup, waits for provider confirmation, and then renames the staged replacement. The backup is retained. The operation is **not atomic**: the target name can be absent between the two renames. A timeout or disconnection can leave a stage or backup; do not blindly retry or delete them. The error identifies the phase and names for recovery.

Same-name destinations are refused unless `--overwrite` is supplied. Do not process files that another device or process may modify concurrently. Files must be regular files, not directories. If the provider stays pending or disconnects, the script fails instead of treating a locally cached file as delivered.

## Privacy

No account names, device identifiers, IP addresses, pairing codes, user files, local testing logs or compiled Python files are included. Runtime arguments, file names and errors may contain private information; review and redact terminal output before sharing. This software does not contain a custom upload service or analytics. Windows and the phone integration process data under the user's existing Microsoft and device settings; no claim of end-to-end encryption is made.

## Tests

```powershell
python -B -m unittest discover -s tests -v
```

The mock tests cover device mismatch, overwrite authorization, stage failure, checksum mismatch, retained backups and provider-confirmed results. During development, phone-side checks used ADB solely for independent testing; end users do not need it for the routine above.
