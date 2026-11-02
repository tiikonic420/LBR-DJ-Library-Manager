"""Durable journal reuse, worker concurrency and real abrupt-process recovery."""
import os,sys,json,tempfile,threading,subprocess,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Sources_application'))
from reliability import Journal
class JournalWindows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'tasks.sqlite'
    def test_full_durability_and_explicit_close(self):
        j=Journal(self.path)
        try:
            with j.connect() as db:
                self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0],'wal')
                self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0],2)
            i=j.start('fictif','durable');j.update(i,state='completed',done=1,total=1)
        finally:j.close()
        r=Journal(self.path)
        try:self.assertEqual(r.list()[0]['state'],'completed')
        finally:r.close()
    def test_ui_and_worker_access_remain_serialized(self):
        j=Journal(self.path);errors=[];i=j.start('fictif','concurrent')
        def worker():
            try:
                for n in range(100):j.update(i,done=n,total=100)
            except Exception as e:errors.append(repr(e))
        t=threading.Thread(target=worker);t.start()
        try:
            for _ in range(100):self.assertEqual(len(j.list()),1)
            t.join(15);self.assertFalse(t.is_alive());self.assertEqual(errors,[]);self.assertEqual(j.list()[0]['done'],99)
        finally:t.join();j.close()
    def test_abrupt_exit_preserves_running_task_for_recovery(self):
        source=Path(__file__).resolve().parents[1]/'Sources_application'
        code='import sys,os;sys.path.insert(0,sys.argv[1]);from reliability import Journal;j=Journal(sys.argv[2]);i=j.start("fictif","crash");j.update(i,done=7,total=10);os._exit(73)'
        cp=subprocess.run([sys.executable,'-c',code,str(source),str(self.path)],capture_output=True,timeout=20)
        self.assertEqual(cp.returncode,73,cp.stderr)
        j=Journal(self.path)
        try:
            row=j.list()[0];self.assertEqual(row['state'],'interrupted');self.assertEqual(row['done'],7)
        finally:j.close()
if __name__=='__main__':unittest.main(verbosity=2)
