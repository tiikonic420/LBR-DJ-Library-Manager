"""One worker for all tools. Tk calls are executed exclusively by the UI thread.

Legacy controllers can retain their validation/backup/write order. The bounded
UI queue streams table/log updates, while returning reads and dialogs in order.
"""
import concurrent.futures
import functools
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

class TkBridge:
    def __init__(self, native, hub):
        self.native=native;self.hub=hub;self.serial=0
    def __getattr__(self,name):
        value=getattr(self.native,name)
        if not callable(value):return value
        if name in ('wantobjects','getint','getdouble','getboolean','splitlist'):
            return value
        return lambda *args:self.hub.ui(value,*args)
    def globalsetvar(self,*args):
        if self.hub.on_ui():return self.native.globalsetvar(*args)
        self.hub.post(self.native.globalsetvar,*args);return ''
    def call(self,*args):
        if self.hub.on_ui():return self.native.call(*args)
        parts=args[0] if len(args)==1 and isinstance(args[0],(tuple,list)) else args
        if not parts:return self.hub.ui(self.native.call,*args)
        if parts[0]=='update':return '' # the normal mainloop remains in charge
        widget=self.hub.widgets.get(str(parts[0]))
        command=str(parts[1]) if len(parts)>1 else ''
        if isinstance(widget,ttk.Treeview) and command=='insert':
            parts=list(parts)
            if '-id' in parts:identifier=parts[parts.index('-id')+1]
            else:
                self.serial+=1;identifier=f'lbr_task_{self.serial}'
                parts=parts[:4]+['-id',identifier]+parts[4:]
            self.hub.post(self.native.call,*parts)
            return identifier
        if command in ('configure','config') and len(parts)>=4:
            self.hub.post(self.native.call,*args);return ''
        if ((isinstance(widget,ttk.Treeview) and ((command in ('item','move') and len(parts)>=5) or (command in ('delete','detach') and len(parts)>=3)))
             or (isinstance(widget,tk.Text) and command in ('insert','see'))):
            self.hub.post(self.native.call,*args);return ''
        return self.hub.ui(self.native.call,*args)

class TaskHub:
    def __init__(self,root):
        self.cache=MetadataCache()
        self.root=root;self.ui_ident=threading.get_ident()
        self.messages=queue.Queue(maxsize=384);self.jobs=queue.Queue()
        self.widgets={};self.busy=False;self.owner='';self.title='';self.stopped=False
        self.pending=set();self.deferred={};self._errors=[];self.listeners=[]
        self._current=None;self._guarded=set();self._native=root.tk
        root.tk=TkBridge(root.tk,self)
        self.worker=threading.Thread(target=self._work,name='LBR-Coordinateur',daemon=True)
        self.worker.start();self._pump_job=root.after(5,self._pump)
        root.bind_class('LBRBusy','<Button-1>',self._guard)
        root.bind_class('LBRBusy','<Double-Button-1>',self._guard)
        root.bind_class('LBRBusy','<KeyPress>',self._guard)
    def on_ui(self):return threading.get_ident()==self.ui_ident
    def ui(self,fn,*args,**kwargs):
        if self.on_ui():return fn(*args,**kwargs)
        future=concurrent.futures.Future()
        self.messages.put((fn,args,kwargs,future))
        return future.result()
    def post(self,fn,*args,**kwargs):
        if self.on_ui():return fn(*args,**kwargs)
        self.messages.put((fn,args,kwargs,None))
    def register(self,root):
        self.widgets[str(root)]=root
        if isinstance(root,(ttk.Button,ttk.Entry,ttk.Combobox,ttk.Checkbutton,ttk.Treeview,tk.Listbox,tk.Text)):
            if isinstance(root,ttk.Button) and 'Journal' in str(root.cget('text')):return
            tags=root.bindtags()
            if 'LBRBusy' not in tags:root.bindtags(('LBRBusy',)+tags)
        for child in root.winfo_children():self.register(child)
    def _guard(self,event):
        if self.busy:
            # Wheel scrolling and page/theme navigation remain available.
            self.root.task_detail.set('Traitement en cours : attends sa fin pour modifier les données.')
            return 'break'
    def run(self,owner,title,fn,*args,background=False,**kwargs):
        if not self.on_ui():return fn(*args,**kwargs)
        if self.stopped:return
        key=(owner,getattr(fn,'__name__',title))
        if self.busy:
            if background:self.deferred[key]=(owner,title,fn,args,kwargs)
            else:self.root.task_detail.set('Une tâche est déjà en cours. La navigation reste disponible.')
            return
        self.busy=True;self.owner=owner;self.title=title;self._errors=[];self._current=key
        self._notify(True,title);self.jobs.put((fn,args,kwargs))
        if self._pump_job:
            self.root.after_cancel(self._pump_job);self._pump_job=self.root.after(0,self._pump)
    def _notify(self,busy,text):
        for callback in self.listeners:callback(busy,self.owner,text)
    def _work(self):
        while True:
            job=self.jobs.get()
            if job is None:return
            fn,args,kwargs=job;failure=None
            try:fn(*args,**kwargs)
            except Exception:failure=traceback.format_exc()
            self.post(self._finish,failure)
    def _finish(self,failure):
        # Runs after all queued table and log writes, preserving operation order.
        if self._errors:failure='\n'.join(self._errors)+(failure or '')
        for callback in getattr(self.root,'task_completed',[]):
            try:callback(self.owner)
            except Exception:failure=(failure or '')+'\n'+traceback.format_exc()
        owner=self.owner;title=self.title;self.busy=False;self._current=None
        self._notify(False,'Erreur' if failure else 'Terminé')
        if failure:
            self.root.report_task_error(owner,title,failure)
        if self.deferred:
            _,(owner,title,fn,args,kwargs)=self.deferred.popitem()
            self.run(owner,title,fn,*args,background=True,**kwargs)
    def _pump(self):
        self._pump_job=None
        if self.stopped:return
        deadline=time.perf_counter()+.006
        while time.perf_counter()<deadline:
            try:fn,args,kwargs,future=self.messages.get_nowait()
            except queue.Empty:break
            try:
                result=fn(*args,**kwargs)
                if future is not None:future.set_result(result)
            except Exception as error:
                if future is not None:future.set_exception(error)
                else:self._errors.append(traceback.format_exc())
        self._pump_job=self.root.after(1 if self.busy or not self.messages.empty() else 60,self._pump)
    def shutdown(self):
        if self.busy:return False
        self.stopped=True
        if self._pump_job:self.root.after_cancel(self._pump_job);self._pump_job=None
        self.jobs.put(None);self.worker.join(timeout=1)
        return True

class DialogFacade:
    """Create, run and destroy each modal dialog entirely on the Tk thread.

    Marshaling individual Tcl calls is insufficient for simpledialog: its
    visibility wait may otherwise run after the window was already mapped.
    Keep the standard modal lifecycle together, while the worker awaits input.
    This proxy is local to each engine; tkinter modules are not monkeypatched.
    """
    def __init__(self,hub,module):self.hub=hub;self.module=module
    def __getattr__(self,name):
        value=getattr(self.module,name)
        if not callable(value) or not name.startswith(('ask','show')):return value
        @functools.wraps(value)
        def dialog(*args,**kwargs):
            kwargs.setdefault('parent',self.hub.root)
            return self.hub.ui(value,*args,**kwargs)
        return dialog

class ThreadFacade:
    """Route the legacy controllers' job threads through the shared worker."""
    def __init__(self,hub,owner):self.hub=hub;self.owner=owner
    def __getattr__(self,name):return getattr(threading,name)
    def Thread(self,group=None,target=None,name=None,args=(),kwargs=None,daemon=None):
        hub=self.hub;owner=self.owner
        class Job:
            def start(self):return hub.run(owner,name or 'Traitement',target,*args,**(kwargs or {}))
        return Job()

def managed(cls,names,owner,background=()):
    """Wrap entry points before construction, so button commands use the hub."""
    for name in names:
        original=getattr(cls,name)
        @functools.wraps(original)
        def call(self,*args,__fn=original,__name=name,**kwargs):
            hub=self.winfo_toplevel().hub
            titles={'scan':'Analyse des fichiers','apply':'Écriture Genre / Année','refresh':'Analyse des tags','save':'Enregistrement des tags','undo':'Restauration','rename':'Renommage','apply_cover':'Écriture des pochettes','load_xml':'Lecture XML Rekordbox','reload_xml':'Actualisation XML','refresh_rb_folders':'Lecture de Rekordbox','run_sync':'Synchronisation Serato','sync_changes':'Synchronisation Serato','sync_one_click':'Synchronisation Rekordbox','plan_all':'Analyse des différences','doctor':'Diagnostic rbsync','startup_load':'Chargement Serato','watch_xml':'Vérification du XML','load_rb':'Import XML','export':'Export du rapport','refresh_statuses':'Comparaison des playlists','apply_playlist_filter':'Filtrage des playlists'}
            return hub.run(owner,titles.get(__name,'Traitement'),__fn,self,*args,
                           background=__name in background,**kwargs)
        setattr(cls,name,call)

class MetadataCache:
    """Bounded metadata-only cache; a changed file identity invalidates its entry."""
    def __init__(self):
        from collections import OrderedDict
        self.entries=OrderedDict();self.size=0;self.hits=0
    def read(self,namespace,reader,path):
        import os,copy,json
        def signature():
            s=os.stat(path);return (s.st_mtime_ns,s.st_ctime_ns,s.st_size,s.st_ino)
        key=(namespace,os.path.normcase(os.path.abspath(path)))
        try:stamp=signature()
        except OSError:return reader(path)
        entry=self.entries.get(key)
        if entry and entry[0]==stamp:
            self.hits+=1;self.entries.move_to_end(key);return copy.deepcopy(entry[1])
        data=reader(path)
        try:
            if signature()!=stamp:return data
        except OSError:return data
        cost=len(json.dumps(data,ensure_ascii=False,default=str).encode('utf-8'))
        if cost>65536:return data
        old=self.entries.pop(key,None)
        if old:self.size-=old[2]
        self.entries[key]=(stamp,copy.deepcopy(data),cost);self.size+=cost
        while len(self.entries)>8000 or self.size>32*1024*1024:
            _,old=self.entries.popitem(last=False);self.size-=old[2]
        return data
    def invalidate(self,path):
        import os
        path=os.path.normcase(os.path.abspath(path))
        for key in [key for key in self.entries if key[1]==path]:
            self.size-=self.entries.pop(key)[2]
