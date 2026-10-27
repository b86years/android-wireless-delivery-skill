param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PlaceholderState {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct FindData {
  public uint attributes;
  public System.Runtime.InteropServices.ComTypes.FILETIME created, accessed, written;
  public uint sizeHigh,sizeLow,reserved0,reserved1;
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=260)] public string name;
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=14)] public string alternate;
 }
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr FindFirstFileW(string path,out FindData data);
 [DllImport("kernel32.dll")] static extern bool FindClose(IntPtr handle);
 [DllImport("CldApi.dll")] static extern uint CfGetPlaceholderStateFromFindData(ref FindData data);
 public static uint Read(string path) {
  FindData data; IntPtr handle=FindFirstFileW(path,out data);
  if(handle==new IntPtr(-1)) throw new System.ComponentModel.Win32Exception();
  try { return CfGetPlaceholderStateFromFindData(ref data); } finally { FindClose(handle); }
 }
}
'@
$state = [PlaceholderState]::Read((Resolve-Path -LiteralPath $Path).ProviderPath)
$candidate = (($state -band 1) -ne 0) -and (($state -band 8) -ne 0) -and $state -ne [uint32]::MaxValue
[PSCustomObject]@{ state_hex=('0x{0:X}' -f $state); provider_reports_in_sync=$candidate; phone_readback_verified=$false } | ConvertTo-Json -Compress
if (-not $candidate) { exit 3 }
exit 0
