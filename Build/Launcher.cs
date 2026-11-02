using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;
[assembly: AssemblyTitle("LBR DJ Library Manager")]
[assembly: AssemblyCompany("LBR Software")]
[assembly: AssemblyProduct("LBR DJ Library Manager 5.0 RC R10")]
[assembly: AssemblyVersion("5.0.10.1")]
[assembly: AssemblyFileVersion("5.0.10.1")]
internal static class Launcher {
    [STAThread]
    static int Main(string[] args) {
        bool created;
        using (Mutex mutex = new Mutex(true, @"Local\LBRSoftware.DJLibraryManager", out created)) {
            if (!created) {
                MessageBox.Show("LBR DJ Library Manager est déjà ouvert.", "LBR DJ Library Manager", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return 2;
            }
            try {
                string root = AppDomain.CurrentDomain.BaseDirectory;
                string python = Path.Combine(root, @"_internal\python\pythonw.exe");
                string app = Path.Combine(root, @"_internal\app\start.pyw");
                if (!File.Exists(python) || !File.Exists(app)) throw new FileNotFoundException("Installation incomplète. Réinstalle le programme depuis son installateur.");
                ProcessStartInfo info = new ProcessStartInfo(python, "-I -B \"" + app + "\"");
                info.WorkingDirectory = Path.GetDirectoryName(app);
                info.UseShellExecute = false;
                info.CreateNoWindow = true;
                info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
                using (Process process = Process.Start(info)) {
                    process.WaitForExit();
                    return process.ExitCode;
                }
            } catch (Exception error) {
                MessageBox.Show(error.Message, "LBR DJ Library Manager", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 10;
            } finally { mutex.ReleaseMutex(); }
        }
    }
}
