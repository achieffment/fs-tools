# Нативный выбор папки Windows через IFileOpenDialog (FOS_PICKFOLDERS).
# В отличие от OpenFileDialog/BrowseForFolder, SetFolder + уникальный SetClientGuid
# жёстко открывают диалог на нужной папке (игнорируя запомненную последнюю папку, MRU)
# и принимают UNC-путь WSL (\\wsl.localhost\...), сохраняя свободную навигацию.
# Входные данные через env: FSTOOLS_FOLDER (стартовая папка), FSTOOLS_HEADER (заголовок).
# Вывод: выбранный путь в stdout, либо ничего при отмене.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
namespace FsTools {
  [ComImport, Guid("43826d1e-e718-42ee-bc55-a1e261c37bfe"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IShellItem {
    void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
    void GetParent(out IShellItem ppsi);
    void GetDisplayName(uint sigdnName, out IntPtr ppszName);
    void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);
    void Compare(IShellItem psi, uint hint, out int piOrder);
  }
  [ComImport, Guid("d57c7288-d4ad-4768-be02-9d969532d960"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IFileOpenDialog {
    [PreserveSig] int Show(IntPtr parent);
    void SetFileTypes(uint cFileTypes, IntPtr rgFilterSpec);
    void SetFileTypeIndex(uint iFileType);
    void GetFileTypeIndex(out uint piFileType);
    void Advise(IntPtr pfde, out uint pdwCookie);
    void Unadvise(uint dwCookie);
    void SetOptions(uint fos);
    void GetOptions(out uint pfos);
    void SetDefaultFolder(IShellItem psi);
    void SetFolder(IShellItem psi);
    void GetFolder(out IShellItem ppsi);
    void GetCurrentSelection(out IShellItem ppsi);
    void SetFileName(string pszName);
    void GetFileName(out IntPtr pszName);
    void SetTitle(string pszTitle);
    void SetOkButtonLabel(string pszText);
    void SetFileNameLabel(string pszLabel);
    void GetResult(out IShellItem ppsi);
    void AddPlace(IShellItem psi, int fdap);
    void SetDefaultExtension(string pszDefaultExtension);
    void Close(int hr);
    void SetClientGuid(ref Guid guid);
    void ClearClientData();
    void SetFilter(IntPtr pFilter);
    void GetResults(out IntPtr ppenum);
    void GetSelectedItems(out IntPtr ppsai);
  }
  [ComImport, Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")]
  public class FileOpenDialog { }
  public static class Picker {
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    static extern void SHCreateItemFromParsingName(string pszPath, IntPtr pbc,
      [MarshalAs(UnmanagedType.LPStruct)] Guid riid,
      [MarshalAs(UnmanagedType.Interface)] out IShellItem ppv);
    // FOS_PICKFOLDERS (0x20). FOS_FORCEFILESYSTEM (0x40) НЕ ставим: виртуальный корень
    // WSL "\\wsl.localhost" (узел "Linux") сообщает SFGAO_FILESYSTEM=False, и этот флаг
    // спрятал бы его из дерева — из-под Windows было бы не добраться до папок WSL.
    // SIGDN_FILESYSPATH (0x80058000) — путь файловой системы выбранного элемента.
    public static string Pick(string initial, string header, IntPtr owner) {
      IFileOpenDialog dlg = (IFileOpenDialog)(new FileOpenDialog());
      try {
        uint opts;
        dlg.GetOptions(out opts);
        dlg.SetOptions(opts | 0x20u);
        if (!string.IsNullOrEmpty(header)) { dlg.SetTitle(header); }
        Guid cg = Guid.NewGuid();
        dlg.SetClientGuid(ref cg);
        if (!string.IsNullOrEmpty(initial)) {
          try {
            IShellItem si;
            SHCreateItemFromParsingName(initial, IntPtr.Zero, typeof(IShellItem).GUID, out si);
            if (si != null) {
              try { dlg.SetFolder(si); }
              finally { Marshal.ReleaseComObject(si); }
            }
          } catch { }
        }
        if (dlg.Show(owner) != 0) { return ""; }
        IShellItem res = null;
        try {
          dlg.GetResult(out res);
          IntPtr p;
          // Без FORCEFILESYSTEM выбор виртуального элемента не имеет пути ФС — тогда
          // GetDisplayName бросает исключение, и мы возвращаем "" (как отмена).
          res.GetDisplayName(0x80058000u, out p);
          string path = Marshal.PtrToStringUni(p);
          Marshal.FreeCoTaskMem(p);
          return path;
        } catch { return ""; }
        finally { if (res != null) { Marshal.ReleaseComObject(res); } }
      } finally { Marshal.ReleaseComObject(dlg); }
    }
  }
}
"@
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.StartPosition = 'CenterScreen'
$owner.Size = New-Object System.Drawing.Size(1, 1)
$owner.Opacity = 0
$owner.Show()
$owner.Activate()
try {
  $path = [FsTools.Picker]::Pick($env:FSTOOLS_FOLDER, $env:FSTOOLS_HEADER, $owner.Handle)
} finally {
  $owner.Close()
  $owner.Dispose()
}
if ($path) { Write-Output $path }
