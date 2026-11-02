using System;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Tools.WindowsInstallerXml;
using Microsoft.Tools.WindowsInstallerXml.Msi;

public class FullIceLog : ValidatorExtension {
    public int Errors;
    public int Warnings;
    public override void Log(string message, string action) {
        Console.WriteLine("ICE_RAW\t" + action + "\t" + message);
        string[] fields = message.Split('\t');
        if (fields.Length > 1) {
            if (fields[1] == "0" || fields[1] == "1") Errors++;
            if (fields[1] == "2") Warnings++;
        }
        base.Log(message, action);
    }
}
public class RunFullIce {
    [DllImport("msi.dll", CharSet=CharSet.Unicode)]
    static extern uint MsiEnableLog(uint mode, string path, uint attributes);
    [STAThread]
    public static int Main(string[] args) {
        if (args.Length != 4) return 90;
        try {
            Console.WriteLine("INPUT\t" + args[0]);
            Console.WriteLine("CUBE\t" + args[1]);
            using (Database db = new Database(args[1], OpenDatabase.ReadOnly)) {
                using (View view = db.OpenExecuteView("SELECT `Action` FROM `_ICESequence` ORDER BY `Sequence`")) {
                    Record rec;
                    while ((rec = view.Fetch()) != null) {
                        using (rec) Console.WriteLine("EXPECTED_ICE\t" + rec.GetString(1));
                    }
                }
            }
            uint logResult = MsiEnableLog(0x3fff, args[3], 0);
            Console.WriteLine("MSI_LOG_INIT\t" + logResult);
            if (logResult != 0) return 91;
            Validator validator = new Validator();
            FullIceLog extension = new FullIceLog();
            extension.Message += delegate(object sender, MessageEventArgs e) {
                Console.WriteLine("VALIDATOR_MESSAGE\t" + e.GetType().Name + "\t" + e.ToString());
            };
            validator.Extension = extension;
            validator.ICEs = null;
            validator.SuppressedICEs = new string[0];
            validator.TempFilesLocation = args[2];
            validator.AddCubeFile(args[1]);
            Console.WriteLine("SUPPRESSED_ICES\t0");
            bool valid = validator.Validate(args[0]);
            Console.WriteLine("VALIDATOR_RETURN\t" + valid);
            Console.WriteLine("ICE_ERRORS\t" + extension.Errors);
            Console.WriteLine("ICE_WARNINGS\t" + extension.Warnings);
            return valid && extension.Errors == 0 ? 0 : 2;
        } catch (Exception error) {
            Console.WriteLine("HARNESS_EXCEPTION\t" + error.ToString());
            return 99;
        } finally { MsiEnableLog(0, null, 0); }
    }
}
