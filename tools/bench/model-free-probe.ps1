param([string]$Engine = "$PSScriptRoot\vulkan", [switch]$Child, [string]$Permit = '', [string]$Result = '')
$ErrorActionPreference = 'Stop'
# Diagnostic only: no Python, model or network request required.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class DustyProbe {
 [DllImport("kernel32", CharSet=CharSet.Unicode)] public static extern IntPtr LoadLibraryEx(string p, IntPtr h, uint f);
 [DllImport("kernel32")] public static extern IntPtr GetProcAddress(IntPtr h, string n);
 [DllImport("kernel32")] public static extern IntPtr CreateJobObject(IntPtr a, IntPtr n);
 [DllImport("kernel32")] public static extern bool SetInformationJobObject(IntPtr j,int c,IntPtr p,uint s);
 [DllImport("kernel32")] public static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32")] public static extern bool CloseHandle(IntPtr h);
 [StructLayout(LayoutKind.Sequential)] public struct CI { public uint type; public IntPtr next; public uint flags; public IntPtr app; public uint layers; public IntPtr layerNames; public uint extensions; public IntPtr extensionNames; }
 [DllImport("vulkan-1",CallingConvention=CallingConvention.Cdecl)] static extern int vkCreateInstance(ref CI ci,IntPtr a,out IntPtr i);
 [DllImport("vulkan-1",CallingConvention=CallingConvention.Cdecl)] static extern int vkEnumeratePhysicalDevices(IntPtr i,ref uint n,IntPtr devices);
 [DllImport("vulkan-1",CallingConvention=CallingConvention.Cdecl)] static extern void vkGetPhysicalDeviceProperties(IntPtr d,IntPtr p);
 [DllImport("vulkan-1",CallingConvention=CallingConvention.Cdecl)] static extern void vkDestroyInstance(IntPtr i,IntPtr a);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Load([MarshalAs(UnmanagedType.LPUTF8Str)]string p);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate UIntPtr Count(IntPtr p);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Get(IntPtr p,UIntPtr i);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr One(IntPtr p);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Init(IntPtr p,IntPtr a);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Alloc(IntPtr p,UIntPtr s);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void Clear(IntPtr p,byte b);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void Free(IntPtr p);
 static Delegate Fn(IntPtr h,string n,Type t) { var p=GetProcAddress(h,n); if(p==IntPtr.Zero)throw new Exception("export"); return Marshal.GetDelegateForFunctionPointer(p,t); }
 static bool Software(string n) { n=n.ToLowerInvariant();return n.Contains("lavapipe")||n.Contains("llvmpipe")||n.Contains("swiftshader")||n.Contains("basic render")||n.Contains("software"); }
 public static bool Run(string folder) {
  var names=new System.Collections.Generic.HashSet<string>();
  CI ci=new CI();ci.type=1;IntPtr instance;
  if(vkCreateInstance(ref ci,IntPtr.Zero,out instance)!=0)return false;
  try {
   uint n=0;if(vkEnumeratePhysicalDevices(instance,ref n,IntPtr.Zero)!=0||n>64)return false;
   IntPtr devices=Marshal.AllocHGlobal((int)n*IntPtr.Size),props=Marshal.AllocHGlobal(4096);
   try { if(vkEnumeratePhysicalDevices(instance,ref n,devices)!=0)return false;
    for(int k=0;k<n;k++){vkGetPhysicalDeviceProperties(Marshal.ReadIntPtr(devices,k*IntPtr.Size),props);
     int type=Marshal.ReadInt32(props,16),vendor=Marshal.ReadInt32(props,8);
     string name=Marshal.PtrToStringAnsi(IntPtr.Add(props,20));
     if((type==1||type==2)&&vendor!=0x1414&&vendor!=0x1ae0&&!Software(name))names.Add(name);
    }
   }finally{Marshal.FreeHGlobal(props);Marshal.FreeHGlobal(devices);}
  }finally{vkDestroyInstance(instance,IntPtr.Zero);}
  if(names.Count==0)return false;
  IntPtr api=LoadLibraryEx(System.IO.Path.Combine(folder,"ggml.dll"),IntPtr.Zero,0x1100);
  IntPtr b=LoadLibraryEx(System.IO.Path.Combine(folder,"ggml-base.dll"),IntPtr.Zero,0x1100);
  if(api==IntPtr.Zero||b==IntPtr.Zero)return false;
  var load=(Load)Fn(api,"ggml_backend_load",typeof(Load));
  var count=(Count)Fn(b,"ggml_backend_reg_dev_count",typeof(Count));
  var get=(Get)Fn(b,"ggml_backend_reg_dev_get",typeof(Get));
  var description=(One)Fn(b,"ggml_backend_dev_description",typeof(One));
  var init=(Init)Fn(b,"ggml_backend_dev_init",typeof(Init));
  var alloc=(Alloc)Fn(b,"ggml_backend_alloc_buffer",typeof(Alloc));
  var clear=(Clear)Fn(b,"ggml_backend_buffer_clear",typeof(Clear));
  var sync=(Free)Fn(b,"ggml_backend_synchronize",typeof(Free));
  var freebuffer=(Free)Fn(b,"ggml_backend_buffer_free",typeof(Free));
  var free=(Free)Fn(b,"ggml_backend_free",typeof(Free));
  IntPtr reg=load(System.IO.Path.Combine(folder,"ggml-vulkan.dll"));if(reg==IntPtr.Zero)return false;
  for(ulong i=0;i<count(reg).ToUInt64();i++){
   var dev=get(reg,(UIntPtr)i);string name=Marshal.PtrToStringAnsi(description(dev));
   if(!names.Contains(name)||Software(name))continue;
   var backend=init(dev,IntPtr.Zero);if(backend==IntPtr.Zero)continue;
   try {var buffer=alloc(backend,(UIntPtr)4096);if(buffer==IntPtr.Zero)continue;
    try{clear(buffer,0);sync(backend);return true;}finally{freebuffer(buffer);}
   }finally{free(backend);}
  }return false;
 }
}
'@
if ($Child) {
    while (-not (Test-Path -LiteralPath $Permit)) { Start-Sleep -Milliseconds 20 }
    $env:GGML_VK_VISIBLE_DEVICES = $null
    $ok = $false
    try { $ok = [DustyProbe]::Run([IO.Path]::GetFullPath($Engine)) } catch { }
    @{real_gpu_found=$ok;model_file_opened=$false} | ConvertTo-Json -Compress | Set-Content -LiteralPath $Result -Encoding ascii
    exit 0
}
$Engine = [IO.Path]::GetFullPath($Engine)
$work = Join-Path $PSScriptRoot ('probe-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
$permitPath=Join-Path $work 'go';$resultPath=Join-Path $work 'result.json'
$job=[DustyProbe]::CreateJobObject([IntPtr]::Zero,[IntPtr]::Zero)
$size=if([IntPtr]::Size -eq 8){144}else{112}
$limits=[Runtime.InteropServices.Marshal]::AllocHGlobal($size)
$process=$null
try {
    for($i=0;$i -lt $size;$i++){[Runtime.InteropServices.Marshal]::WriteByte($limits,$i,0)}
    [Runtime.InteropServices.Marshal]::WriteInt32($limits,16,0x2000)
    if(-not [DustyProbe]::SetInformationJobObject($job,9,$limits,$size)){throw 'Job limit failed'}
    $shell=(Get-Process -Id $PID).Path
    $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Child','-Engine',('"'+$Engine+'"'),'-Permit',('"'+$permitPath+'"'),'-Result',('"'+$resultPath+'"'))
    $process=Start-Process -FilePath $shell -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $work 'out') -RedirectStandardError (Join-Path $work 'err')
    if(-not [DustyProbe]::AssignProcessToJobObject($job,$process.Handle)){throw 'Job assignment failed'}
    New-Item -ItemType File -Path $permitPath | Out-Null
    if(-not $process.WaitForExit(8000)){throw 'Probe timed out'}
    if(Test-Path -LiteralPath $resultPath){Get-Content -LiteralPath $resultPath}else{'{"real_gpu_found":false,"model_file_opened":false}'}
} catch { '{"real_gpu_found":false,"model_file_opened":false,"fallback":"Small"}' }
finally {
    [void][DustyProbe]::CloseHandle($job)
    [Runtime.InteropServices.Marshal]::FreeHGlobal($limits)
    if($process){$process.WaitForExit(2000)|Out-Null}
    if((Split-Path ([IO.Path]::GetFullPath($work)) -Parent) -eq $PSScriptRoot){Remove-Item -LiteralPath $work -Recurse -Force}
}
