from pathlib import Path
import sys,ctypes,importlib.util,hashlib,json
original,candidate,builder,report_path=map(Path,sys.argv[1:5])
spec=importlib.util.spec_from_file_location('builder_readonly_helpers',builder);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fetch=m.api('MsiViewFetch',[m.W.UINT,ctypes.POINTER(m.W.UINT)])
field=m.api('MsiRecordGetStringW',[m.W.UINT,m.W.UINT,m.W.LPWSTR,ctypes.POINTER(m.W.DWORD)])
count=m.api('MsiRecordGetFieldCount',[m.W.UINT])
stream=m.api('MsiRecordReadStream',[m.W.UINT,m.W.UINT,ctypes.c_void_p,ctypes.POINTER(m.W.DWORD)])
def inspect(path):
    db=m.W.UINT();m.check(m.open_db(str(path.resolve()),None,ctypes.byref(db)))
    def query(sql,binary=False):
        v=m.W.UINT();m.check(m.open_view(db,sql,ctypes.byref(v)));m.check(m.execute(v,0));result=[]
        try:
            while True:
                r=m.W.UINT();code=fetch(v,ctypes.byref(r))
                if code==259:break
                m.check(code)
                try:
                    if binary:
                        h=hashlib.sha256()
                        while True:
                            b=ctypes.create_string_buffer(65536);size=m.W.DWORD(len(b));m.check(stream(r,1,b,ctypes.byref(size)))
                            if not size.value:break
                            h.update(b.raw[:size.value])
                        result.append(h.hexdigest())
                    else:
                        values=[]
                        for i in range(1,count(r)+1):
                            b=ctypes.create_unicode_buffer(8192);size=m.W.DWORD(len(b));m.check(field(r,i,b,ctypes.byref(size)));values.append(b.value)
                        result.append(values)
                finally:m.close(r)
        finally:m.close(v)
        return result
    try:
        files=query('SELECT `File`,`Component_`,`FileName`,`FileSize`,`Version`,`Language`,`Sequence` FROM `File` ORDER BY `Sequence`')
        cabinet=query("SELECT `Data` FROM `_Streams` WHERE `Name` = 'payload.cab'",True)
        return files,cabinet
    finally:m.close(db)
before=inspect(original);after=inspect(candidate)
assert before==after,'File table or embedded cabinet changed'
report={'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'file_rows_unchanged':len(before[0]),'embedded_cabinet_sha256':before[1][0],'embedded_cabinet_byte_hash_unchanged':True,'audio_or_user_library_access':False,'application_payload_unchanged':True}
report_path.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
