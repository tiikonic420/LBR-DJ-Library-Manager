"""Build per-user x64 MSI using Microsoft Windows Installer APIs and makecab.

No downloads, NSIS launch, custom installer actions or policy modifications.
Input: a validated self-contained payload. Output: MSI and auditable file index.
"""
import argparse,ctypes,hashlib,json,os,subprocess,uuid
from pathlib import Path
from ctypes import wintypes as W

msi=ctypes.WinDLL('msi',use_last_error=True)
def api(name,args,restype=W.UINT):
    fn=getattr(msi,name);fn.argtypes=args;fn.restype=restype;return fn
UINTP=ctypes.POINTER(W.UINT)
open_db=api('MsiOpenDatabaseW',[W.LPCWSTR,ctypes.c_void_p,UINTP])
open_view=api('MsiDatabaseOpenViewW',[W.UINT,W.LPCWSTR,UINTP])
execute=api('MsiViewExecute',[W.UINT,W.UINT])
create_record=api('MsiCreateRecord',[W.UINT])
set_string=api('MsiRecordSetStringW',[W.UINT,W.UINT,W.LPCWSTR])
set_int=api('MsiRecordSetInteger',[W.UINT,W.UINT,ctypes.c_int])
set_stream=api('MsiRecordSetStreamW',[W.UINT,W.UINT,W.LPCWSTR])
close=api('MsiCloseHandle',[W.UINT])
commit=api('MsiDatabaseCommit',[W.UINT])
get_error=api('MsiGetLastErrorRecord',[])
format_record=api('MsiFormatRecordW',[W.UINT,W.UINT,W.LPWSTR,ctypes.POINTER(W.DWORD)])
get_summary=api('MsiGetSummaryInformationW',[W.UINT,W.LPCWSTR,W.UINT,UINTP])
set_summary=api('MsiSummaryInfoSetPropertyW',[W.UINT,W.UINT,W.UINT,ctypes.c_int,ctypes.c_void_p,W.LPCWSTR])
persist_summary=api('MsiSummaryInfoPersist',[W.UINT])
get_version=api('MsiGetFileVersionW',[W.LPCWSTR,W.LPWSTR,ctypes.POINTER(W.DWORD),W.LPWSTR,ctypes.POINTER(W.DWORD)])
verify_package=api('MsiVerifyPackageW',[W.LPCWSTR])
class Stream:
    def __init__(self,path):self.path=path
def check(code,context=''):
    if code:
        record=get_error();message=''
        if record:
            size=W.DWORD(8192);buf=ctypes.create_unicode_buffer(8192)
            format_record(0,record,buf,ctypes.byref(size));message=buf.value;close(record)
        raise RuntimeError(f'Windows Installer {code}: {context}: {message}')
class Database:
    def __init__(self,path):
        self.columns={}
        self.handle=W.UINT();check(open_db(str(path),ctypes.c_void_p(3),ctypes.byref(self.handle)),'create database')
    def sql(self,query,values=None):
        view=W.UINT();check(open_view(self.handle,query,ctypes.byref(view)),query)
        record=0
        try:
            if values is not None:
                record=create_record(len(values))
                for i,value in enumerate(values,1):
                    if value is None:continue
                    if isinstance(value,int):check(set_int(record,i,value),query)
                    elif isinstance(value,Stream):check(set_stream(record,i,str(value.path)),query)
                    else:check(set_string(record,i,str(value)),query)
            check(execute(view,record),query)
        finally:
            if record:close(record)
            close(view)
    def table(self,name,columns,keys):
        self.columns[name]=[n for n,t in columns]
        self.sql('CREATE TABLE `'+name+'` ('+', '.join('`'+n+'` '+t.replace(' LOCALIZABLE NOT NULL',' NOT NULL LOCALIZABLE') for n,t in columns)+' PRIMARY KEY '+', '.join('`'+k+'`' for k in keys)+')')
    def row(self,name,values):self.sql('INSERT INTO `'+name+'` ('+','.join('`'+n+'`' for n in self.columns[name])+') VALUES ('+','.join('?' for _ in values)+')',values)
    def finish(self):check(commit(self.handle));close(self.handle)

def identifier(prefix,name):return prefix+hashlib.sha256(name.casefold().encode()).hexdigest()[:24]
NAMESPACE=uuid.UUID('46e2b9ea-7c1a-5e3c-9866-90efcc0ad299')
def guid(name):return '{'+str(uuid.uuid5(NAMESPACE,name)).upper()+'}'
def pe_version(path):
    if path.suffix.lower() not in ('.exe','.dll','.pyd'):return None,None
    ver=ctypes.create_unicode_buffer(128);lang=ctypes.create_unicode_buffer(256)
    a=W.DWORD(128);b=W.DWORD(256)
    if get_version(str(path),ver,ctypes.byref(a),lang,ctypes.byref(b))==0:return ver.value or None,lang.value or None
    return None,None

def build(payload,output,work):
    assert payload.is_dir() and not output.exists()
    work.mkdir(parents=True,exist_ok=True)
    files=sorted((p for p in payload.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.suffix.lower() not in ('.pyc','.pyo')),key=lambda p:p.relative_to(payload).as_posix().casefold())
    assert files and len(files)<32767
    index=[]
    for seq,path in enumerate(files,1):
        rel=path.relative_to(payload).as_posix()
        index.append({'id':identifier('F',rel),'component':identifier('C',rel),'relative':rel,
                      'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sequence':seq})
    cabinet=work/'payload.cab'
    lines=['.OPTION EXPLICIT','.Set Cabinet=on','.Set Compress=on','.Set CompressionType=LZX','.Set CompressionMemory=21',
           '.Set MaxDiskSize=0','.Set MaxCabinetSize=0','.Set CabinetNameTemplate=payload.cab',
           '.Set DiskDirectoryTemplate='+str(work),'.Set DiskDirectory1='+str(work),'.Set RptFileName='+str(work/'makecab.rpt'),'.Set InfFileName='+str(work/'makecab.inf')]
    lines += ['"'+str(payload/row['relative'])+'" '+row['id'] for row in index]
    ddf=work/'payload.ddf';ddf.write_text('\n'.join(lines)+'\n',encoding='utf8')
    result=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/makecab.exe'),'/V1','/F',str(ddf)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (work/'makecab.log').write_bytes(result.stdout)
    if result.returncode:raise RuntimeError('makecab failed; see '+str(work/'makecab.log'))
    assert cabinet.is_file()
    db=Database(output)
    db.table('Property',[('Property','CHAR(72) NOT NULL'),('Value','CHAR(0) LOCALIZABLE NOT NULL')],['Property'])
    product=guid('Product 5.0.9 R10')
    for key,value in {'ProductCode':product,'UpgradeCode':guid('LBR MSI family'),'ProductName':'LBR DJ Library Manager 5.0 RC R10',
          'ProductVersion':'5.0.10','ProductLanguage':'1036','Manufacturer':'LBR Software',
          'INSTALLLEVEL':'1','DefaultUIFont':'NormalFont','ARPPRODUCTICON':'LBRIcon','ARPNOMODIFY':'1',
          'MSIRESTARTMANAGERCONTROL':'DisableShutdown',
          'DESKTOPSHORTCUT':'1','DISABLEADVTSHORTCUTS':'1'}.items():db.row('Property',[key,value])
    db.table('Directory',[('Directory','CHAR(72) NOT NULL'),('Directory_Parent','CHAR(72)'),('DefaultDir','CHAR(255) LOCALIZABLE NOT NULL')],['Directory'])
    for row in [('TARGETDIR',None,'SourceDir'),('LocalAppDataFolder','TARGETDIR','.'),('ProgramsFolder','LocalAppDataFolder','Programs'),
                ('VendorFolder','ProgramsFolder','LBRSOFT|LBR Software'),('INSTALLFOLDER','VendorFolder','LBRR10|LBR DJ Library Manager R10'),
                ('ProgramMenuFolder','TARGETDIR','.'),('MenuFolder','ProgramMenuFolder','LBRSOFT|LBR Software'),
                ('DesktopFolder','TARGETDIR','.'),('System64Folder','TARGETDIR','.')]:db.row('Directory',row)
    directories={'.':'INSTALLFOLDER'}
    for n,rel in enumerate(sorted({str(Path(row['relative']).parent).replace('\\','/') for row in index},key=lambda v:(len(Path(v).parts),v)),1):
        if rel=='.':continue
        parts=Path(rel).parts
        for depth in range(1,len(parts)+1):
            partial='/'.join(parts[:depth])
            if partial in directories:continue
            parent='/'.join(parts[:depth-1]) or '.'
            ident=identifier('D',partial);directories[partial]=ident
            db.row('Directory',[ident,directories[parent],('D'+str(len(directories)).zfill(6))+'|'+parts[depth-1]])
    db.table('Component',[('Component','CHAR(72) NOT NULL'),('ComponentId','CHAR(38)'),('Directory_','CHAR(72) NOT NULL'),('Attributes','SHORT NOT NULL'),('Condition','CHAR(255)'),('KeyPath','CHAR(72)')],['Component'])
    db.table('Feature',[('Feature','CHAR(38) NOT NULL'),('Feature_Parent','CHAR(38)'),('Title','CHAR(64) LOCALIZABLE'),('Description','CHAR(255) LOCALIZABLE'),('Display','SHORT'),('Level','SHORT NOT NULL'),('Directory_','CHAR(72)'),('Attributes','SHORT NOT NULL')],['Feature'])
    db.row('Feature',['Main',None,'LBR DJ Library Manager','Programme complet, moteurs et Python 3.13',1,1,'INSTALLFOLDER',0])
    db.table('FeatureComponents',[('Feature_','CHAR(38) NOT NULL'),('Component_','CHAR(72) NOT NULL')],['Feature_','Component_'])
    db.table('File',[('File','CHAR(72) NOT NULL'),('Component_','CHAR(72) NOT NULL'),('FileName','CHAR(255) LOCALIZABLE NOT NULL'),('FileSize','LONG NOT NULL'),('Version','CHAR(72)'),('Language','CHAR(20)'),('Attributes','SHORT'),('Sequence','SHORT NOT NULL')],['File'])
    for row in index:
        path=payload/row['relative'];directory=directories[str(Path(row['relative']).parent).replace('\\','/')]
        db.row('Component',[row['component'],guid('component/'+row['relative']),directory,256,None,row['id']])
        db.row('FeatureComponents',['Main',row['component']])
        version,language=pe_version(path)
        db.row('File',[row['id'],row['component'],'F'+str(row['sequence']).zfill(6)+'|'+path.name,row['size'],version,language,512|16384,row['sequence']])
    db.table('Media',[('DiskId','SHORT NOT NULL'),('LastSequence','SHORT NOT NULL'),('DiskPrompt','CHAR(64) LOCALIZABLE'),('Cabinet','CHAR(255)'),('VolumeLabel','CHAR(32)'),('Source','CHAR(72)')],['DiskId'])
    db.row('Media',[1,len(index),None,'#payload.cab',None,None])
    db.sql('INSERT INTO `_Streams` (`Name`, `Data`) VALUES (?, ?)', ['payload.cab',Stream(cabinet)])
    db.table('Registry',[('Registry','CHAR(72) NOT NULL'),('Root','SHORT NOT NULL'),('Key','CHAR(255) LOCALIZABLE NOT NULL'),('Name','CHAR(255) LOCALIZABLE'),('Value','CHAR(0) LOCALIZABLE'),('Component_','CHAR(72) NOT NULL')],['Registry'])
    for comp,condition in [('MenuShortcuts',None),('DesktopShortcut','DESKTOPSHORTCUT=1')]:
        db.row('Component',[comp,guid(comp),'INSTALLFOLDER',256|4,condition,comp+'Key'])
        db.row('FeatureComponents',['Main',comp])
        db.row('Registry',[comp+'Key',1,r'Software\LBR Software\DJ Library Manager MSI R10',comp,'#1',comp])
    db.table('Shortcut',[('Shortcut','CHAR(72) NOT NULL'),('Directory_','CHAR(72) NOT NULL'),('Name','CHAR(128) LOCALIZABLE NOT NULL'),('Component_','CHAR(72) NOT NULL'),('Target','CHAR(255)'),('Arguments','CHAR(255)'),('Description','CHAR(255) LOCALIZABLE'),('Hotkey','SHORT'),('Icon_','CHAR(72)'),('IconIndex','SHORT'),('ShowCmd','SHORT'),('WkDir','CHAR(72)')],['Shortcut'])
    for key,directory,comp in [('StartLBR','MenuFolder','MenuShortcuts'),('DesktopLBR','DesktopFolder','DesktopShortcut')]:
        db.row('Shortcut',[key,directory,'LBRR10|LBR DJ Library Manager R10',comp,'[INSTALLFOLDER]LBR_DJ_Library_Manager.exe',None,'LBR DJ Library Manager 5.0 RC R10',None,'LBRIcon',0,1,'INSTALLFOLDER'])
    db.row('Shortcut',['UninstallLBR','MenuFolder','UNLBRR10|Désinstaller LBR R10','MenuShortcuts','[System64Folder]msiexec.exe','/x '+product,'Désinstaller le programme ; conserver les sauvegardes',None,None,None,1,'INSTALLFOLDER'])
    db.table('RemoveFile',[('FileKey','CHAR(72) NOT NULL'),('Component_','CHAR(72) NOT NULL'),('FileName','CHAR(255) LOCALIZABLE'),('DirProperty','CHAR(72) NOT NULL'),('InstallMode','SHORT NOT NULL')],['FileKey'])
    db.row('RemoveFile',['RemoveMenuFolder','MenuShortcuts',None,'MenuFolder',2])
    # Only generated bytecode in known application/runtime cache directories.
    # Both install and uninstall clean old R10 residue; no recursive deletion.
    cache_parents={}
    for item in index:
        path=Path(item['relative'])
        if path.suffix in ('.py','.pyw'):
            parent=path.parent.as_posix()
            cache_parents.setdefault(parent,item['component'])
    for parent,component in sorted(cache_parents.items()):
        cache=parent+'/__pycache__';cache_id=identifier('D',cache)
        assert cache not in directories
        db.row('Directory',[cache_id,directories[parent],'PYCACHE|__pycache__'])
        db.row('RemoveFile',[identifier('RF',cache),component,'*.pyc',cache_id,3])
        db.row('RemoveFile',[identifier('RD',cache),component,None,cache_id,3])
    db.table('Icon',[('Name','CHAR(72) NOT NULL'),('Data','OBJECT NOT NULL')],['Name'])
    db.row('Icon',['LBRIcon',Stream(payload/'_internal/app/assets/lbr.ico')])
    db.table('LaunchCondition',[('Condition','CHAR(255) NOT NULL'),('Description','CHAR(255) LOCALIZABLE NOT NULL')],['Condition'])
    db.table('RegLocator',[('Signature_','CHAR(72) NOT NULL'),('Root','SHORT NOT NULL'),('Key','CHAR(255) NOT NULL'),('Name','CHAR(255)'),('Type','SHORT')],['Signature_'])
    db.row('RegLocator',['OSMajor',2,r'SOFTWARE\Microsoft\Windows NT\CurrentVersion','CurrentMajorVersionNumber',18])
    db.table('AppSearch',[('Property','CHAR(72) NOT NULL'),('Signature_','CHAR(72) NOT NULL')],['Property','Signature_'])
    # AppSearch queries this table even for a raw RegLocator search. It must
    # exist; absence causes Windows Installer 2228 before the welcome screen.
    db.table('Signature',[('Signature','CHAR(72) NOT NULL'),('FileName','CHAR(255) NOT NULL'),
        ('MinVersion','CHAR(20)'),('MaxVersion','CHAR(20)'),('MinSize','LONG'),('MaxSize','LONG'),
        ('MinDate','LONG'),('MaxDate','LONG'),('Languages','CHAR(255)')],['Signature'])
    db.row('AppSearch',['LBR_OS_MAJOR','OSMajor'])
    db.row('LaunchCondition',['Installed OR (VersionNT64 AND LBR_OS_MAJOR = "#10")','Windows 10 ou 11 x64 est nécessaire.'])
    db.row('LaunchCondition',['NOT ALLUSERS','Cette installation est réservée à l’utilisateur courant.'])
    db.table('InstallExecuteSequence',[('Action','CHAR(72) NOT NULL'),('Condition','CHAR(255)'),('Sequence','SHORT')],['Action'])
    seq=[('LaunchConditions',100),('ValidateProductID',700),('CostInitialize',800),('FileCost',900),('CostFinalize',1000),('InstallValidate',1400),('InstallInitialize',1500),('ProcessComponents',1600),('UnpublishFeatures',1800),('RemoveRegistryValues',2600),('RemoveShortcuts',3200),('RemoveFiles',3500),('RemoveFolders',3600),('CreateFolders',3700),('InstallFiles',4000),('CreateShortcuts',4500),('WriteRegistryValues',5000),('RegisterUser',6000),('RegisterProduct',6100),('PublishFeatures',6300),('PublishProduct',6400),('InstallFinalize',6600)]
    db.row('InstallExecuteSequence',['AppSearch',None,50])
    for action,number in seq:db.row('InstallExecuteSequence',[action,None,number])
    db.table('TextStyle',[('TextStyle','CHAR(72) NOT NULL'),('FaceName','CHAR(32) NOT NULL'),('Size','SHORT NOT NULL'),('Color','LONG'),('StyleBits','SHORT')],['TextStyle'])
    for name,size,bits in [('NormalFont',9,0),('TitleFont',16,1)]:db.row('TextStyle',[name,'Segoe UI',size,0,bits])
    db.table('Dialog',[('Dialog','CHAR(72) NOT NULL'),('HCentering','SHORT NOT NULL'),('VCentering','SHORT NOT NULL'),('Width','SHORT NOT NULL'),('Height','SHORT NOT NULL'),('Attributes','LONG'),('Title','CHAR(128) LOCALIZABLE'),('Control_First','CHAR(50)'),('Control_Default','CHAR(50)'),('Control_Cancel','CHAR(50)')],['Dialog'])
    db.table('Control',[('Dialog_','CHAR(72) NOT NULL'),('Control','CHAR(50) NOT NULL'),('Type','CHAR(20) NOT NULL'),('X','SHORT NOT NULL'),('Y','SHORT NOT NULL'),('Width','SHORT NOT NULL'),('Height','SHORT NOT NULL'),('Attributes','LONG'),('Property','CHAR(72)'),('Text','CHAR(0) LOCALIZABLE'),('Control_Next','CHAR(50)'),('Help','CHAR(50) LOCALIZABLE')],['Dialog_','Control'])
    db.table('ControlEvent',[('Dialog_','CHAR(72) NOT NULL'),('Control_','CHAR(50) NOT NULL'),('Event','CHAR(50) NOT NULL'),('Argument','CHAR(255) NOT NULL'),('Condition','CHAR(255)'),('Ordering','SHORT')],['Dialog_','Control_','Event','Argument','Condition'])
    for name,title,body,button,event in [
        ('WelcomeDlg','Installer LBR DJ Library Manager','Installation personnelle complète : Python 3.13, les quatre outils DJ et leurs protections.\n\nFerme LBR avant de commencer. Tes bibliothèques musicales et sauvegardes restent conservées.\n\nCandidate 5.0 RC R10 : essais de distribution à terminer.','Installer','Return'),
        ('ExitDlg','Installation terminée','Tu peux ouvrir LBR DJ Library Manager depuis le Bureau ou le menu Démarrer.\n\nPour le retirer : Paramètres Windows > Applications > LBR DJ Library Manager.','Fermer','Return'),
        ('ErrorDlg','Installation interrompue','L’installation n’a pas abouti. Consulte le journal Windows Installer. Aucune validation d’installation réussie ne doit être déduite de ce message.','Fermer','Exit'),
        ('UserExitDlg','Installation annulée','L’installation a été annulée.','Fermer','Exit')]:
        db.row('Dialog',[name,50,50,390,250,3,'LBR DJ Library Manager','Next','Next','Cancel' if name=='WelcomeDlg' else 'Next'])
        db.row('Control',[name,'Title','Text',20,18,350,28,3,None,'{\\TitleFont}'+title,None,None])
        db.row('Control',[name,'Body','Text',20,60,350,135,3,None,body,None,None])
        db.row('Control',[name,'Next','PushButton',280,215,85,20,3,None,button,'Cancel' if name=='WelcomeDlg' else 'Next',None])
        db.row('ControlEvent',[name,'Next','EndDialog',event,'1',1])
        if name=='WelcomeDlg':
            db.row('Control',[name,'Cancel','PushButton',185,215,85,20,3,None,'Annuler','Next',None])
            db.row('ControlEvent',[name,'Cancel','EndDialog','Exit','1',1])
    db.table('InstallUISequence',[('Action','CHAR(72) NOT NULL'),('Condition','CHAR(255)'),('Sequence','SHORT')],['Action'])
    db.table('EventMapping',[('Dialog_','CHAR(72) NOT NULL'),('Control_','CHAR(50) NOT NULL'),('Event','CHAR(50) NOT NULL'),('Attribute','CHAR(50) NOT NULL')],['Dialog_','Control_','Event'])
    db.row('Dialog',['ProgressDlg',50,50,390,250,1,'LBR DJ Library Manager','Cancel','Cancel','Cancel'])
    for values in [
        ['ProgressDlg','Title','Text',20,18,350,28,3,None,'{\\TitleFont}Installation en cours',None,None],
        ['ProgressDlg','Action','Text',20,85,350,40,3,None,'Préparation…',None,None],
        ['ProgressDlg','Progress','ProgressBar',20,145,350,15,65537,None,None,None,None],
        ['ProgressDlg','Cancel','PushButton',280,215,85,20,3,None,'Annuler','Cancel',None]]:db.row('Control',values)
    db.row('ControlEvent',['ProgressDlg','Cancel','EndDialog','Exit','1',1])
    db.row('EventMapping',['ProgressDlg','Action','ActionText','Text'])
    db.row('EventMapping',['ProgressDlg','Progress','SetProgress','Progress'])
    db.row('InstallUISequence',['ProgressDlg',None,1240])
    for action,cond,number in [('AppSearch',None,50),('LaunchConditions',None,100),('CostInitialize',None,800),('FileCost',None,900),('CostFinalize',None,1000),('WelcomeDlg','NOT Installed',1230),('ExecuteAction',None,1300),('ExitDlg','NOT Installed',-1),('ErrorDlg',None,-3),('UserExitDlg',None,-2)]:db.row('InstallUISequence',[action,cond,number])
    summary=W.UINT();check(get_summary(db.handle,None,20,ctypes.byref(summary)))
    for pid,value in {1:1252,2:'Installation LBR DJ Library Manager',3:'5.0 RC R10',4:'LBR Software',7:'x64;1036',9:guid('Package '+hashlib.sha256(cabinet.read_bytes()).hexdigest()),14:500,15:10,18:'LBR Windows Installer API builder',19:2}.items():
        check(set_summary(summary,pid,2 if pid==1 else 3 if isinstance(value,int) else 30,value if isinstance(value,int) else 0,None,value if isinstance(value,str) else None))
    check(persist_summary(summary));close(summary);db.finish();check(verify_package(str(output)),'verify package')
    report={'product_code':product,'product_version':'5.0.10','display_version':'5.0 RC R10','files':len(index),
            'payload_bytes':sum(r['size'] for r in index),'cabinet_sha256':hashlib.sha256(cabinet.read_bytes()).hexdigest(),
            'msi_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'MsiVerifyPackage':0,'per_user':True,
            'custom_actions':False,'uninstall':'Windows Installer / Apps settings','security_changes':[],
            'installation_tested':False,'file_index':index}
    output.with_suffix('.manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='file_index'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--payload',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    build(a.payload.resolve(),a.output.resolve(),a.work.resolve())
