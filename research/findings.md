# Wireless transfer research

These are research notes behind the experimental `send-to-android` skill, not a support guarantee. No personal device identifiers or transfer logs are included.

Windows File Explorer supports showing one paired Android device at a time. That visible device must be explicitly identified before a file is sent; the separate Phone Link share command may instead use its own selected device.

In one physical-device experiment a new file copied into the Windows mobile-device view reached the phone. A subsequent overwrite reported local copy success but remained a normal local file with Cloud Files placeholder state `0x0`; Windows showed sync paused and an independent phone-side read still contained the old bytes. The local copy and its checksum were therefore not proof of delivery.

An existing phone-backed item returned state `0x9`, indicating the Cloud Files placeholder and in-sync flags. This is provider-reported status, not independent phone readback. `placeholder_state()` in `send-to-android/scripts/crossdevice.py` reads it without claiming that phone contents were verified. Windows hides the reparse flag from processes that do not opt in, so the function first calls `RtlSetProcessPlaceholderCompatibilityMode(2)`; without it every state reads as `0x0`. More tests are required before relying on the flag for this provider, particularly after overwrites, disconnections, reconnections, and device switches.

After the integration was re-enabled, the unsynced local overwrite reverted to the older phone content. A new uniquely named staging file subsequently reached the phone and reported `0x9`. Replacing the old test file with that stage using the Windows Shell file operation returned success, but the target remained at `0x1` and the independent phone-side hash stayed old during observation. Shell success is therefore also insufficient proof of overwrite. The staging and target were disposable test files.

References: Microsoft documents File Explorer mobile-device access and its one-device limit at https://support.microsoft.com/en-us/windows/experience/fileexplorer/setting-up-and-using-your-phone-in-file-explorer and the Cloud Files placeholder states at https://learn.microsoft.com/en-us/windows/win32/api/cfapi/ne-cfapi-cf_placeholder_state.
