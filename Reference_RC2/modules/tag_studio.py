import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageTk
import os,re,threading,queue,shutil,json
from tag_engine import *

class App(tk.Frame):
 def __init__(self,root):
  super().__init__(root);self.root=self;self.host=self.winfo_toplevel()
  self._populate_job=None;self._cover_token=0;self._rendered_rows={};self._visible_order=()
  self.host.task_completed.append(self.task_done)
  self.dark=True;self.rows={};self.pending={};self.backups=[];self.rb={};self.events=queue.Queue();self.folder='';self.active_filter=''
  self.cols=['file','title','artist','album','genre','date','track','bpm','key','serato','rekordbox']
  self.column_config_path=Path(os.environ.get('APPDATA',str(Path.home()))) / 'LBR Tag Studio' / 'columns.json'
  self.visible_cols=self.load_column_preferences()
  self.theme();self.build();self.root.after(90,self.pump)
 def theme(self):
  c=self.host.colors;self.dark=self.host.mode=='sombre'
  self.bg=c['bg'];self.fg=c['text'];self.pane=c['card'];self.accent=c['green'];self.muted=c['muted']
  self.configure(bg=self.bg)
  if hasattr(self,'tree'):self.tree.tag_configure('pending',foreground=c['green'])
  if hasattr(self,'cover_preview'):self.cover_preview.configure(bg=self.pane,fg=self.muted);self.cover_frame.configure(bg=self.pane)
 def build(self):
  header=ttk.Frame(self.root);header.pack(fill='x',padx=20,pady=(15,9))
  brand=ttk.Frame(header);brand.pack(side='left')
  ttk.Label(brand,text='Éditeur de métadonnées',font=('Segoe UI',13,'bold')).pack(anchor='w')
  ttk.Label(brand,text='Tags • Pochettes • Renommage',style='Muted.TLabel',font=('Segoe UI',8,'bold')).pack(anchor='w',padx=35)

  ttk.Button(header,text='↶  Restaurer',command=self.undo).pack(side='right',padx=3)
  ttk.Button(header,text='✓  Enregistrer les tags',command=self.save,style='Green.TButton').pack(side='right',padx=3)
  from integrated_ui import Flow
  bar=Flow(self.root);bar.pack(fill='x',padx=20,pady=(2,11))
  for label,cmd in [('▣  Ouvrir dossier',self.open_folder),('⟳  Actualiser',self.refresh),('⇩  Import XML Rekordbox',self.load_rb),('✎  Renommer',self.rename),('⇄  Nom → Tags',self.filename_to_tags),('⌕  Remplacer / RegEx',self.replace),('⇧  Exporter',self.export),('✕  Effacer',self.clear_pending)]:
   ttk.Button(bar,text=label,command=cmd)
  searchbar=ttk.Frame(self.root);searchbar.pack(fill='x',padx=20,pady=(0,10))
  ttk.Label(searchbar,text='BIBLIOTHÈQUE MUSICALE',font=('Segoe UI',11,'bold')).pack(side='left')
  self.search=tk.StringVar();self.search.trace_add('write',lambda *_:self.schedule_search())
  ttk.Entry(searchbar,textvariable=self.search,width=24).pack(side='right')
  ttk.Label(searchbar,text='Rechercher   ',style='Muted.TLabel').pack(side='right')
  main=ttk.Panedwindow(self.root,orient='horizontal');main.pack(fill='both',expand=True,padx=20,pady=(0,8))
  left=ttk.Frame(main,style='Panel.TFrame');center=ttk.Frame(main,style='Panel.TFrame');right=ttk.Frame(main,style='Panel.TFrame')
  main.add(left,weight=0);main.add(center,weight=1);main.add(right,weight=0)
  left.configure(width=170);right.configure(width=265)
  left.pack_propagate(False);right.pack_propagate(False)
  ttk.Label(left,text='  DOSSIERS',style='TLabel',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(15,12))
  self.folders=tk.Listbox(left,bg=self.pane,fg=self.fg,selectbackground='#116f81',relief='flat',highlightthickness=0,font=('Segoe UI',10),activestyle='none',borderwidth=0)
  self.folders.pack(fill='both',expand=True,padx=12,pady=(0,12));self.folders.bind('<<ListboxSelect>>',self.select_folder)
  ttk.Label(center,text='  FICHIERS AUDIO   •   Double-clique sur une cellule pour la modifier',style='TLabel',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(15,12))
  frame=ttk.Frame(center,style='Panel.TFrame');frame.pack(fill='both',expand=True,padx=(10,8),pady=(0,10))
  self.tree=ttk.Treeview(frame,columns=self.cols,show='headings',selectmode='extended')
  widths={'file':260,'title':235,'artist':175,'album':160,'genre':115,'date':75,'track':65,'bpm':90,'key':75,'serato':175,'rekordbox':175}
  names={'file':'FICHIER','title':'TITRE','artist':'ARTISTE','album':'ALBUM','genre':'GENRE','date':'ANNÉE','track':'PISTE','bpm':'BPM','key':'TONALITÉ','serato':'SERATO','rekordbox':'REKORDBOX'}
  for c in self.cols:
   self.tree.heading(c,text=names[c],command=lambda col=c:self.sort_by(col));self.tree.column(c,width=widths[c],minwidth=60,stretch=False,anchor='w')
  vs=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview);hs=ttk.Scrollbar(frame,orient='horizontal',command=self.tree.xview)
  self.tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set);self.tree.grid(row=0,column=0,sticky='nsew');vs.grid(row=0,column=1,sticky='ns');hs.grid(row=1,column=0,sticky='ew');frame.grid_rowconfigure(0,weight=1);frame.grid_columnconfigure(0,weight=1)
  self.tree.configure(displaycolumns=self.visible_cols)
  self.column_menu=tk.Menu(self.tree,tearoff=False)
  self.tree.bind('<Button-3>',self.show_column_menu,add='+')
  self.tree.bind('<<TreeviewSelect>>',self.selection);self.tree.bind('<Double-1>',self.edit_cell)
  ttk.Label(right,text='  ÉDITEUR DE TAGS',style='TLabel',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(15,5))
  ttk.Label(right,text='  Sélectionne un ou plusieurs titres',style='TLabel',font=('Segoe UI',9)).pack(anchor='w',pady=(0,12))
  # Scrollable tag editor: cover and all fields remain accessible on laptop screens.
  editor_shell=ttk.Frame(right,style='Panel.TFrame')
  editor_shell.pack(fill='both',expand=True)
  self.editor_canvas=tk.Canvas(editor_shell,bg=self.pane,highlightthickness=0,borderwidth=0)
  editor_scroll=ttk.Scrollbar(editor_shell,orient='vertical',command=self.editor_canvas.yview)
  self.editor_canvas.configure(yscrollcommand=editor_scroll.set)
  editor_scroll.pack(side='right',fill='y')
  self.editor_canvas.pack(side='left',fill='both',expand=True)
  form=ttk.Frame(self.editor_canvas,style='Panel.TFrame')
  self.editor_window=self.editor_canvas.create_window((0,0),window=form,anchor='nw')
  form.bind('<Configure>',lambda e:self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox('all')))
  self.editor_canvas.bind('<Configure>',lambda e:self.editor_canvas.itemconfigure(self.editor_window,width=e.width))
  def wheel(event):
   if event.delta:self.editor_canvas.yview_scroll(int(-event.delta/120),'units')
  def editor_wheel(event):
   if str(event.widget).startswith(str(editor_shell)):wheel(event);return 'break'
  self.host.bind_all('<MouseWheel>',editor_wheel,add='+')
  self.edit_vars={}
  for field in FIELDS:
   field_names={'title':'Titre','artist':'Artiste','album':'Album','genre':'Genre','date':'Année','track':'Piste','bpm':'BPM','key':'Tonalité','comment':'Commentaire'}
   ttk.Label(form,text=field_names[field],style='TLabel',font=('Segoe UI',9,'bold')).pack(anchor='w',padx=14,pady=(6,3))
   v=tk.StringVar();ttk.Entry(form,textvariable=v).pack(fill='x',padx=14,ipady=2);self.edit_vars[field]=v
  ttk.Separator(form,orient='horizontal').pack(fill='x',padx=14,pady=(14,9))
  ttk.Label(form,text='POCHETTE D’ALBUM',style='TLabel',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=14,pady=(0,8))
  # Fixed pixel-size preview area; never set width/height on the image Label:
  # tkinter interprets those dimensions in pixels once an image is assigned.
  self.cover_frame=tk.Frame(form,bg=self.pane,width=190,height=190)
  self.cover_frame.pack(padx=14,pady=(0,8),anchor='center')
  self.cover_frame.pack_propagate(False)
  self.cover_preview=tk.Label(self.cover_frame,text='Aucune pochette',
                              bg=self.pane,fg=self.muted,anchor='center',
                              borderwidth=0,highlightthickness=0)
  self.cover_preview.pack(fill='both',expand=True)
  coverbar=ttk.Frame(form,style='Panel.TFrame');coverbar.pack(fill='x',padx=14,pady=(0,12))
  ttk.Button(coverbar,text='＋ Ajouter / remplacer',command=self.add_cover).pack(fill='x',pady=(0,5))
  ttk.Button(coverbar,text='✕ Supprimer',command=self.remove_cover).pack(fill='x')
  ttk.Label(form,text='Les champs vides sont ignorés en lot.',style='TLabel',font=('Segoe UI',9)).pack(anchor='w',padx=14,pady=(0,12))
  # Primary action stays visible even when the tag form is scrolled.
  ttk.Button(right,text='✓  Appliquer à la sélection',command=self.apply_fields,style='Green.TButton').pack(side='bottom',fill='x',padx=14,pady=(9,12),before=editor_shell)
  self.main_panes=main
  footer=ttk.Frame(self.root);footer.pack(side='bottom',fill='x',padx=20,pady=(0,12),before=main)
  self.status=tk.StringVar(value='Prêt • Aucun fichier modifié sans enregistrement')
  ttk.Label(footer,textvariable=self.status,font=('Segoe UI',9)).pack(side='left')
  self.log_visible=False
  self.log_btn=ttk.Button(footer,text='▸  Journal',command=self.toggle_log);self.log_btn.pack(side='right')
  self.log=tk.Text(self.root,height=5,bg=self.pane,fg=self.fg,relief='flat',font=('Consolas',9),padx=12,pady=8)
  self._pane_resize_job=None
  def size_panes(event=None):
   if self._pane_resize_job:self.root.after_cancel(self._pane_resize_job)
   def fit():
    self._pane_resize_job=None
    width=main.winfo_width()
    if width>500:
     main.sashpos(0,175);main.sashpos(1,max(350,width-275))
   self._pane_resize_job=self.root.after_idle(fit)
  main.bind('<Configure>',size_panes,add='+')
  self.root.after_idle(size_panes)
 def load_column_preferences(self):
  default=['file','title','artist','album','genre','date','track','bpm','key']
  try:
   value=json.loads(self.column_config_path.read_text(encoding='utf-8'))
   if isinstance(value,list):
    valid=[c for c in value if isinstance(c,str) and c in self.cols]
    if valid:return [c for c in self.cols if c in valid]
  except (OSError,ValueError,TypeError):pass
  return default
 def save_column_preferences(self):
  try:
   self.column_config_path.parent.mkdir(parents=True,exist_ok=True)
   self.column_config_path.write_text(json.dumps(self.visible_cols,ensure_ascii=False,indent=2),encoding='utf-8')
  except OSError as exc:self.logmsg('Préférences colonnes : '+str(exc))
 def set_column_visible(self,col,visible):
  if visible:
   self.visible_cols=[c for c in self.cols if c in self.visible_cols or c==col]
  else:
   if len(self.visible_cols)==1:
    messagebox.showinfo('Colonnes','Au moins une colonne doit rester visible.')
    return
   self.visible_cols=[c for c in self.visible_cols if c!=col]
  self.tree.configure(displaycolumns=self.visible_cols)
  self.save_column_preferences()
 def reset_columns(self):
  self.visible_cols=list(self.cols)
  self.tree.configure(displaycolumns=self.visible_cols)
  self.save_column_preferences()
 def show_column_menu(self,event):
  if self.tree.identify_region(event.x,event.y)!='heading':return
  labels={'file':'Fichier','title':'Titre','artist':'Artiste','album':'Album','genre':'Genre','date':'Année','track':'Piste','bpm':'BPM','key':'Tonalité','serato':'Serato','rekordbox':'Rekordbox'}
  self.column_menu.delete(0,'end')
  self.column_menu.add_command(label='COLONNES AFFICHÉES',state='disabled')
  self.column_menu.add_separator()
  self.column_vars={}
  for col in self.cols:
   var=tk.BooleanVar(value=col in self.visible_cols)
   self.column_vars[col]=var
   self.column_menu.add_checkbutton(label=labels[col],variable=var,command=lambda c=col,v=var:self.set_column_visible(c,v.get()))
  self.column_menu.add_separator()
  self.column_menu.add_command(label='Tout afficher',command=self.reset_columns)
  try:self.column_menu.tk_popup(event.x_root,event.y_root)
  finally:self.column_menu.grab_release()
 def toggle_log(self):
  self.log_visible=not self.log_visible
  if self.log_visible:self.log.pack(side='bottom',fill='x',padx=20,pady=(0,12),before=self.main_panes);self.log_btn.configure(text='▾  Journal')
  else:self.log.pack_forget();self.log_btn.configure(text='▸  Journal')
 def logmsg(self,s):self.log.insert('end',s+'\n');self.log.see('end')
 def toggle(self):
  self.host.toggle_theme()
 def open_folder(self):
  p=filedialog.askdirectory(title='Choisir dossier musical')
  if p:self.folder=p;self.refresh()
 def refresh(self):
  if not self.folder:return
  if self.pending and not messagebox.askyesno('Modifications en attente','Actualiser effacera les modifications non enregistrées. Continuer ?'):return
  self.pending={};self.status.set('Analyse en cours…');self.logmsg('Analyse : '+self.folder)
  def worker():
   paths=scan(self.folder);items={}
   for i,p in enumerate(paths):
    try:
     tags=read_tags(p);tags.update(file=Path(p).name,path=p,serato=serato_info(p),rekordbox=self.rb.get(str(Path(p)).lower(),'Non analysé'))
     items[p]=tags
    except Exception as e:self.events.put(('error',f'{Path(p).name} : {e}'))
    if i%100==0:self.events.put(('progress',f'Analyse : {i}/{len(paths)}'))
   self.events.put(('loaded',items))
  threading.Thread(target=worker,daemon=True).start()
 def pump(self):
  self.consume_events();self.root.after(80 if self.host.hub.busy else 350,self.pump)
 def consume_events(self):
  try:
   for _ in range(100):
    typ,data=self.events.get_nowait()
    if typ=='loaded':
     self.rows=data;self.populate();self.folders.delete(0,'end');self.folders.insert('end','Tous les dossiers')
     folders=sorted(set(str(Path(p).parent.relative_to(self.folder)) for p in self.rows))
     for f in folders:self.folders.insert('end',f)
     self.status.set(f'{len(self.rows)} fichiers chargés');self.logmsg(f'{len(self.rows)} fichiers chargés')
    elif typ=='error':self.logmsg('ERREUR : '+data)
    elif typ=='progress':self.status.set(data)
    elif typ=='saved':self.status.set(data);self.logmsg(data);self.populate()
  except queue.Empty:pass
 def populate(self):
  hub=self.host.hub
  if hub.on_ui():
   return hub.run('TagStudio','Affichage des fichiers',self.populate,background=True)
  if not hasattr(self,'tree'):return
  old=set(self.tree.selection());q=self.search.get().casefold()
  # Reuse existing rows: edits no longer destroy/reinsert the entire library.
  stale=set(self._rendered_rows).difference(self.rows)
  if stale:self.tree.delete(*stale)
  for p in stale:self._rendered_rows.pop(p,None)
  visible=[];inserted=False;changes=[]
  for p,t in self.rows.items():
   d={**t,**self.pending.get(p,{})}
   values=tuple(str(d.get(c,'')) for c in self.cols)
   tags=('pending',) if p in self.pending else ()
   state=(values,tags)
   previous=self._rendered_rows.get(p)
   if previous is None:
    changes.append(('insert',p,values,tags));inserted=True
   elif previous!=state:changes.append(('item',p,values,tags))
   self._rendered_rows[p]=state
   if self.active_filter and self.active_filter!='Tous les dossiers' and str(Path(p).parent.relative_to(self.folder))!=self.active_filter:continue
   if q and q not in ' '.join(str(v) for v in d.values()).casefold():continue
   visible.append(p)
  for start in range(0,len(changes),64):hub.post(self._apply_row_changes,changes[start:start+64])
  order=tuple(visible)
  if order!=self._visible_order or stale or inserted:
   self.tree.set_children('',*visible);self._visible_order=order
  self.tree.tag_configure('pending',foreground=self.host.colors['green'])
  self.tree.selection_set([p for p in visible if p in old])
  self.status.set(f'{len(visible)} affichés • {len(self.pending)} modifications en attente')
 def _apply_row_changes(self,changes):
  # Bounded UI batches reduce cross-thread queue traffic during the first load.
  for kind,p,values,tags in changes:
   if kind=='insert':self.tree.insert('', 'end',iid=p,values=values,tags=tags)
   else:self.tree.item(p,values=values,tags=tags)
 def schedule_search(self):
  if self._populate_job:self.root.after_cancel(self._populate_job)
  self._populate_job=self.root.after(150,self._render_request)
 def _render_request(self):
  self._populate_job=None
  self.host.hub.run('TagStudio','Affichage des fichiers',self.populate,background=True)
 def task_done(self,owner):
  if owner=='TagStudio':self.consume_events()
 def select_folder(self,_):
  s=self.folders.curselection()
  if s:self.active_filter=self.folders.get(s[0]);self.populate()
 def selected(self):return list(self.tree.selection())
 def selection(self,_=None):
  sel=self.selected()
  # Reset after the form has recalculated its scroll region and geometry.
  # A delayed reset also handles selection events fired during table refresh.
  self.editor_canvas.yview_moveto(0)
  self.root.after_idle(self.reset_editor_scroll)
  self.root.after(80,self.reset_editor_scroll)
  if not sel:
   self.update_cover_preview(None)
   return
  self.update_cover_preview(sel[0] if len(sel)==1 else None)
  if len(sel)==1:
   d={**self.rows[sel[0]],**self.pending.get(sel[0],{})}
   for k,v in self.edit_vars.items():v.set(d.get(k,''))
  else:
   for k,v in self.edit_vars.items():
    vals={str({**self.rows[p],**self.pending.get(p,{})}.get(k,'')) for p in sel};v.set(next(iter(vals)) if len(vals)==1 else '')
 def reset_editor_scroll(self):
  self.editor_canvas.update_idletasks()
  self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox('all'))
  self.editor_canvas.yview_moveto(0)

 def update_cover_preview(self,path):
  if not self.host.hub.on_ui():return self.host.hub.ui(self.update_cover_preview,path)
  self._cover_token+=1;token=self._cover_token;self.cover_photo=None
  self.cover_preview.configure(image='',text='Aucune pochette' if path else 'Sélectionne un titre')
  if not path:return
  def load_cover():
   try:
    data=read_cover(path)
    if not data:return
    with Image.open(BytesIO(data)) as source:
     im=source.convert('RGB');scale=min(180/im.width,180/im.height)
     im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    def display():
     if token!=self._cover_token:return
     self.cover_photo=ImageTk.PhotoImage(im,master=self);self.cover_preview.configure(image=self.cover_photo,text='')
    self.host.hub.post(display)
   except Exception as e:self.host.hub.post(self.logmsg,'Pochette : '+str(e))
  self.host.hub.run('TagStudio','Pochette',load_cover,background=True)
 def add_cover(self):
  sel=self.selected()
  if not sel:return messagebox.showinfo('Pochette','Sélectionne un ou plusieurs titres.')
  filename=filedialog.askopenfilename(filetypes=[('JPEG / PNG','*.jpg *.jpeg *.png')])
  if not filename:return
  try:
   with Image.open(filename) as im:im.verify()
   data=Path(filename).read_bytes()
   if len(data)>15*1024*1024:raise ValueError('Image trop volumineuse (15 Mo maximum)')
   mime='image/png' if Path(filename).suffix.lower()=='.png' else 'image/jpeg'
  except Exception as e:return messagebox.showerror('Image invalide',str(e))
  self.apply_cover(sel,data,mime,'Ajouter / remplacer')
 def remove_cover(self):
  sel=self.selected()
  if not sel:return messagebox.showinfo('Pochette','Sélectionne un ou plusieurs titres.')
  self.apply_cover(sel,None,None,'Supprimer')
 def apply_cover(self,sel,data,mime,action):
  if not messagebox.askyesno('Confirmation',f'{action} la pochette de {len(sel)} fichier(s) ?\nUne sauvegarde sera créée avant chaque écriture.'):return
  folder=Path.home()/'Documents'/'LBR Tag Studio'/'Backups';ok=0;errors=[]
  for path in sel:
   try:
    backup=safe_write_cover(path,data,mime,folder);self.backups.append((path,backup));ok+=1
   except Exception as e:errors.append(f'{Path(path).name} : {e}')
  self.update_cover_preview(sel[0] if len(sel)==1 else None)
  self.logmsg(f'Pochettes : {ok} modifiée(s), {len(errors)} erreur(s)')
  for err in errors:self.logmsg('ERREUR : '+err)
  messagebox.showinfo('Pochettes',f'{ok} fichier(s) traité(s), {len(errors)} erreur(s).')
 def edit_cell(self,event):
  row=self.tree.identify_row(event.y);col=self.tree.identify_column(event.x)
  if not row or not col:return
  idx=int(col[1:])-1
  if idx<0 or idx>=len(self.visible_cols):return
  key=self.visible_cols[idx]
  if key not in FIELDS:return
  x,y,w,h=self.tree.bbox(row,col);old={**self.rows[row],**self.pending.get(row,{})}.get(key,'')
  e=ttk.Entry(self.tree);e.insert(0,old);e.place(x=x,y=y,width=w,height=h);e.focus_set();e.select_range(0,'end')
  finished=False
  def commit(_=None):
   nonlocal finished
   if finished:return
   finished=True
   value=e.get();e.destroy()
   if value!=old:self.pending.setdefault(row,{})[key]=value;self.populate()
  def cancel(_=None):
   nonlocal finished
   finished=True;e.destroy()
  e.bind('<Return>',commit);e.bind('<Escape>',cancel);e.bind('<FocusOut>',commit)
 def apply_fields(self):
  sel=self.selected()
  if not sel:return messagebox.showinfo('Sélection','Sélectionne au moins un fichier.')
  vals={k:v.get() for k,v in self.edit_vars.items() if v.get()!=''}
  if not vals:return messagebox.showinfo('Champs','Renseigne un champ à appliquer.')
  for p in sel:self.pending.setdefault(p,{}).update(vals)
  self.populate();self.logmsg(f'Préparation : {len(sel)} fichier(s), {len(vals)} champ(s)')
 def clear_pending(self):self.pending.clear();self.populate()
 def save(self):
  if not self.pending:return messagebox.showinfo('Aucune modification','Aucun tag à enregistrer.')
  if not messagebox.askyesno('Confirmer',f'Écrire les tags de {len(self.pending)} fichier(s) ?\nUne sauvegarde .bak sera créée avant chaque écriture.'):return
  changes=dict(self.pending);folder=Path.home()/'Documents'/'LBR Tag Studio'/'Backups';ok=0;errors=[]
  # Synchronous saves keep filesystem state deterministic; UI remains responsive between files.
  def process():
   nonlocal ok
   for p,d in changes.items():
    try:
     backup=safe_write(p,d,folder);self.backups.append((p,backup));self.rows[p].update(read_tags(p));ok+=1;self.pending.pop(p,None)
    except Exception as e:errors.append(f'{Path(p).name}: {e}')
   self.events.put(('saved',f'Enregistrés : {ok} • Erreurs : {len(errors)}'))
   for err in errors:self.events.put(('error',err))
  threading.Thread(target=process,daemon=True).start()
 def undo(self):
  if not self.backups:return messagebox.showinfo('Annulation','Aucune sauvegarde de cette session.')
  if not messagebox.askyesno('Restaurer',f'Restaurer les {len(self.backups)} dernières écritures de cette session ?'):return
  for p,b in reversed(self.backups):
   try:shutil.copy2(b,p);self.rows[p].update(read_tags(p))
   except Exception as e:self.logmsg('ERREUR restauration : '+str(e))
  self.backups.clear();self.populate();self.logmsg('Restaurations terminées')
 def rename(self):
  sel=self.selected()
  if not sel:return
  pattern=simpledialog.askstring('Renommage','Modèle de nom (ex : {artist} - {title})',initialvalue='{artist} - {title}')
  if not pattern:return
  planned=[]
  for p in sel:
   name=rename_pattern({**self.rows[p],**self.pending.get(p,{})},pattern)
   if not name:continue
   dest=str(Path(p).with_name(name+Path(p).suffix))
   if dest!=p:planned.append((p,dest))
  if not planned:return
  if len(set(d for _,d in planned))!=len(planned) or any(Path(d).exists() for _,d in planned):return messagebox.showerror('Conflit','Un nom cible existe déjà ou est en doublon. Opération annulée.')
  if not messagebox.askyesno('Prévisualisation','Renommer '+str(len(planned))+' fichiers ?\n\n'+'\n'.join(f'{Path(p).name} → {Path(d).name}' for p,d in planned[:12])):return
  for p,d in planned:
   try:
    os.rename(p,d);self.rows[d]=self.rows.pop(p);self.rows[d]['file']=Path(d).name;self.rows[d]['path']=d
    if p in self.pending:self.pending[d]=self.pending.pop(p)
   except Exception as e:self.logmsg('ERREUR renommage : '+str(e))
  self.populate()
 def filename_to_tags(self):
  sel=self.selected()
  if not sel:return
  pattern=simpledialog.askstring('Nom → Tags','Modèle de lecture (ex : {artist} - {title})',initialvalue='{artist} - {title}')
  if not pattern:return
  count=0
  try:
   for p in sel:
    d=parse_filename(Path(p).name,pattern)
    if d:
     self.pending.setdefault(p,{}).update({k:v for k,v in d.items() if k in FIELDS});count+=1
   self.populate();self.logmsg(f'Extraction préparée : {count} fichiers')
  except Exception as e:messagebox.showerror('Erreur',str(e))
 def replace(self):
  sel=self.selected()
  if not sel:return
  field=simpledialog.askstring('Remplacement','Champ (title, artist, album, genre, date, track, bpm, key, comment)',initialvalue='title')
  if field not in FIELDS:return
  find=simpledialog.askstring('Rechercher','Texte à rechercher (préfixe re: pour RegEx)')
  if not find:return
  replace=simpledialog.askstring('Remplacer','Remplacer par (vide autorisé)')
  if replace is None:return
  try:
   rx=re.compile(find[3:]) if find.startswith('re:') else None
   for p in sel:
    old=str({**self.rows[p],**self.pending.get(p,{})}.get(field,''));new=rx.sub(replace,old) if rx else old.replace(find,replace)
    if new!=old:self.pending.setdefault(p,{})[field]=new
   self.populate()
  except re.error as e:messagebox.showerror('RegEx',str(e))
 def export(self):
  if not self.rows:return
  p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv'),('HTML','*.html'),('RTF','*.rtf')])
  if not p:return
  rows=[{**self.rows[k],**self.pending.get(k,{})} for k in self.tree.get_children()]
  try:export_report(rows,p);self.logmsg('Export : '+p)
  except Exception as e:messagebox.showerror('Export',str(e))
 def load_rb(self):
  p=filedialog.askopenfilename(filetypes=[('Export Rekordbox XML','*.xml')])
  if not p:return
  try:
   self.rb=rekordbox_xml(p)
   for path,row in self.rows.items():row['rekordbox']=self.rb.get(str(Path(path)).lower(),'Absent du XML')
   self.populate();self.logmsg(f'Rekordbox XML : {len(self.rb)} pistes référencées')
  except Exception as e:messagebox.showerror('XML',str(e))
 def sort_by(self,col):
  items=list(self.tree.get_children());items.sort(key=lambda p:str({**self.rows[p],**self.pending.get(p,{})}.get(col,'')).casefold())
  self.tree.set_children('',*items);self._visible_order=tuple(items)
