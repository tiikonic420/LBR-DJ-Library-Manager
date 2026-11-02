"""Create a distinct MSI-only review candidate; never change the published input."""
from pathlib import Path
import sys,ctypes,importlib.util,shutil,hashlib,json,xml.etree.ElementTree as ET
source,out,schema,builder=map(Path,sys.argv[1:5])
original=hashlib.sha256(source.read_bytes()).hexdigest()
assert original=='86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228'
assert not out.exists();shutil.copy2(source,out)
spec=importlib.util.spec_from_file_location('msi_builder_helpers',builder);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
db=m.Database.__new__(m.Database);db.columns={};db.handle=m.W.UINT()
m.check(m.open_db(str(out),ctypes.c_void_p(1),ctypes.byref(db.handle)))
db.handle=db.handle.value
fetch=m.api('MsiViewFetch',[m.W.UINT,ctypes.POINTER(m.W.UINT)])
field=m.api('MsiRecordGetStringW',[m.W.UINT,m.W.UINT,m.W.LPWSTR,ctypes.POINTER(m.W.DWORD)])
count=m.api('MsiRecordGetFieldCount',[m.W.UINT])
def rows(query):
    view=m.W.UINT();m.check(m.open_view(db.handle,query,ctypes.byref(view)));m.check(m.execute(view,0));result=[]
    try:
        while True:
            record=m.W.UINT();code=fetch(view,ctypes.byref(record))
            if code==259:break
            m.check(code)
            try:
                row=[]
                for n in range(1,count(record)+1):
                    b=ctypes.create_unicode_buffer(8192);length=m.W.DWORD(len(b));m.check(field(record,n,b,ctypes.byref(length)));row.append(b.value)
                result.append(row)
            finally:m.close(record)
    finally:m.close(view)
    return result
def register(name):db.columns[name]=[x[0] for x in rows("SELECT `Name` FROM `_Columns` WHERE `Table` = '"+name+"' ORDER BY `Number`")]
for name in ['Property','Registry','RemoveFile','Dialog','Control','ControlEvent']:register(name)
# Use registry key paths for components installed into the user profile.
for component,attr in rows('SELECT `Component`,`Attributes` FROM `Component`'):
    if component in ('MenuShortcuts','DesktopShortcut'):continue
    marker='K'+component
    db.row('Registry',[marker,1,r'Software\LBR Software\DJ Library Manager MSI R10 ICE1\Components',component,'#1',component])
    db.sql('UPDATE `Component` SET `Attributes` = ?, `KeyPath` = ? WHERE `Component` = ?',[int(attr)|4,marker,component])
# Component identity must change when its key path semantics change.
for component, in rows('SELECT `Component` FROM `Component`'):
    db.sql('UPDATE `Component` SET `ComponentId` = ? WHERE `Component` = ?',[m.guid('ICE1/component/'+component),component])
db.sql('UPDATE `Registry` SET `Key` = ? WHERE `Key` = ?',[r'Software\LBR Software\DJ Library Manager MSI R10 ICE1',r'Software\LBR Software\DJ Library Manager MSI R10'])
# Explicit empty-directory cleanup only; never recurse or target backup/profile data.
covered={x[0] for x in rows('SELECT `DirProperty` FROM `RemoveFile` WHERE `FileName` IS NULL')}
skip={'TARGETDIR','LocalAppDataFolder','ProgramMenuFolder','DesktopFolder','System64Folder'}
for directory, in rows('SELECT `Directory` FROM `Directory`'):
    if directory not in covered|skip:db.row('RemoveFile',[m.identifier('RI',directory),'MenuShortcuts',None,directory,2])
db.sql('UPDATE `File` SET `Attributes` = 16384')
# Fully authored standard MSI dialogs required by ICE20.
db.row('Property',['ErrorDialog','SystemErrorDlg'])
db.row('Dialog',['SystemErrorDlg',50,50,390,250,131,'LBR - Windows Installer','ErrorText',None,None])
db.row('Control',['SystemErrorDlg','ErrorText','Text',20,30,350,150,3,None,'[ErrorText]',None,None])
for name,event,label in [('A','ErrorAbort','Abandonner'),('C','ErrorCancel','Annuler'),('I','ErrorIgnore','Ignorer'),('N','ErrorNo','Non'),('O','ErrorOk','OK'),('R','ErrorRetry','Reessayer'),('Y','ErrorYes','Oui')]:
    db.row('Control',['SystemErrorDlg',name,'PushButton',20,215,85,20,3,None,label,None,None]);db.row('ControlEvent',['SystemErrorDlg',name,'EndDialog',event,'1',1])
db.table('ListBox',[('Property','CHAR(72) NOT NULL'),('Order','SHORT NOT NULL'),('Value','CHAR(64) NOT NULL'),('Text','CHAR(0) LOCALIZABLE')],['Property','Order'])
db.row('Dialog',['FilesInUse',50,50,390,250,3,'Fichiers utilises','Retry','Retry','Exit'])
db.row('Control',['FilesInUse','Body','Text',20,15,350,45,3,None,'Fermez les applications indiquees avant de continuer.',None,None])
db.row('Control',['FilesInUse','Processes','ListBox',20,65,350,130,3,'FileInUseProcess',None,'Retry',None])
for name,x,next_control,label in [('Retry',20,'Ignore','Reessayer'),('Ignore',145,'Exit','Ignorer'),('Exit',270,'Processes','Annuler')]:
    db.row('Control',['FilesInUse',name,'PushButton',x,215,95,20,3,None,label,next_control,None]);db.row('ControlEvent',['FilesInUse',name,'EndDialog',name,'1',1])
# Distinct review identity and locations; published R10 package remains unchanged.
product=m.guid('Product R10 ICE1')
for key,value in [('ProductCode',product),('ProductName','LBR DJ Library Manager 5.0 RC R10 ICE1')]:db.sql('UPDATE `Property` SET `Value` = ? WHERE `Property` = ?',[value,key])
db.sql('UPDATE `Directory` SET `DefaultDir` = ? WHERE `Directory` = ?',['LBRICE1|LBR DJ Library Manager R10 ICE1','INSTALLFOLDER'])
db.sql('UPDATE `Directory` SET `DefaultDir` = ? WHERE `Directory` = ?',['LBRICE1|LBR Software R10 ICE1','MenuFolder'])
for key in ['StartLBR','DesktopLBR']:db.sql('UPDATE `Shortcut` SET `Name` = ? WHERE `Shortcut` = ?',['LBRICE1|LBR DJ Library Manager R10 ICE1',key])
db.sql('UPDATE `Shortcut` SET `Name` = ?, `Arguments` = ? WHERE `Shortcut` = ?',['UNICE1|Desinstaller LBR R10 ICE1','/x '+product,'UninstallLBR'])
# Supply official WiX standard table validation metadata, without relaxing values.
defs=ET.parse(schema).getroot();ns={'w':'http://schemas.microsoft.com/wix/2006/tables'}
tables={t.get('name'):t for t in defs.findall('w:tableDefinition',ns)}
db.table('_Validation',[('Table','CHAR(32) NOT NULL'),('Column','CHAR(32) NOT NULL'),('Nullable','CHAR(4) NOT NULL'),('MinValue','LONG'),('MaxValue','LONG'),('KeyTable','CHAR(255)'),('KeyColumn','SHORT'),('Category','CHAR(32)'),('Set','CHAR(255)'),('Description','CHAR(255)')],['Table','Column'])
categories={'wildCardFilename':'WildCardFilename','formattedSddl':'FormattedSDDLText'}
validation_rows=0
for name, in rows('SELECT `Name` FROM `_Tables`'):
    if name.startswith('_') and name!='_Validation':continue
    assert name in tables,'No official metadata for '+name
    existing={x[0] for x in rows("SELECT `Name` FROM `_Columns` WHERE `Table` = '"+name+"'")}
    for c in tables[name]:
        if c.get('name') not in existing:continue
        cat=c.get('category');cat=categories.get(cat,cat[:1].upper()+cat[1:]) if cat else None
        db.row('_Validation',[name,c.get('name'),'Y' if c.get('nullable')=='yes' else 'N',int(c.get('minValue')) if c.get('minValue') else None,int(c.get('maxValue')) if c.get('maxValue') else None,c.get('keyTable'),int(c.get('keyColumn')) if c.get('keyColumn') else None,cat,c.get('set'),c.get('description','')[:255] or None]);validation_rows+=1
summary=m.W.UINT();m.check(m.get_summary(db.handle,None,20,ctypes.byref(summary)))
for pid,value in [(3,'5.0 RC R10 ICE1 - installer review only'),(9,m.guid('Package ICE1 '+original))]:m.check(m.set_summary(summary,pid,30,0,None,value))
m.check(m.persist_summary(summary));m.close(summary);db.finish();m.check(m.verify_package(str(out)))
assert hashlib.sha256(source.read_bytes()).hexdigest()==original
report={'source_sha256':original,'candidate_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'candidate':out.name,'label':'R10 ICE1 - MSI-only review candidate','published_input_unchanged':True,'product_code':product,'application_payload_unchanged':True,'validation_metadata_rows':validation_rows,'registry_key_paths_added':True,'cleanup':'empty installer directories only; no recursive deletion','signed':False,'installation_tested':False}
out.with_suffix('.patch.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
