"""Presentation layer shared by the three original controllers."""
import tkinter as tk
from tkinter import ttk


def label(parent, text='', style='Muted.TLabel', **kw):
    w=ttk.Label(parent,text=text,style=style,**kw); w.pack(anchor='w',fill='x',pady=(0,5))
    def wrap(event):
        width=max(100,event.width)
        if getattr(w,'_wrap_width',None)!=width:
            w._wrap_width=width;w.configure(wraplength=width)
    w.bind('<Configure>',wrap)
    return w


def panel(parent, title=None, expand=False):
    f=ttk.Frame(parent,style='Panel.TFrame',padding=14)
    f.pack(fill='both' if expand else 'x',expand=expand,pady=(0,10))
    if title: label(f,title,'Section.TLabel')
    return f


class Flow(ttk.Frame):
    """Wrap action buttons at their real requested widths, including DPI changes."""
    def __init__(self,parent,**kw):
        super().__init__(parent,style='Card.TFrame',**kw)
        self.bind('<Configure>',self.reflow)
        self.after_idle(self.reflow)
    def reflow(self,event=None):
        width=self.winfo_width()
        if width<30:return
        children=self.winfo_children()
        signature=(width,tuple((str(c),c.winfo_reqwidth(),c.winfo_reqheight()) for c in children))
        if getattr(self,'_flow_signature',None)==signature:return
        self._flow_signature=signature
        x=y=0; rowh=0
        for child in children:
            w=child.winfo_reqwidth(); h=child.winfo_reqheight()
            if x and x+w>width: x=0; y+=rowh+6; rowh=0
            child.place(x=x,y=y,width=min(w,width),height=h)
            x+=w+7; rowh=max(rowh,h)
        self.configure(height=y+rowh)


def actions(parent,items):
    f=Flow(parent); f.pack(fill='x',pady=(3,5))
    out=[]
    for item in items:
        title,cmd,*style=item
        out.append(ttk.Button(f,text=title,command=cmd,style=style[0] if style else 'TButton'))
    return out


def pathrow(parent,variable,buttons,combo=False):
    f=ttk.Frame(parent,style='Card.TFrame'); f.pack(fill='x',pady=(0,6))
    f.columnconfigure(0,weight=1)
    w=(ttk.Combobox(f,textvariable=variable,state='readonly') if combo else ttk.Entry(f,textvariable=variable))
    w.grid(row=0,column=0,sticky='ew')
    for i,(title,cmd) in enumerate(buttons,1): ttk.Button(f,text=title,command=cmd).grid(row=0,column=i,padx=(8,0))
    return w


def table(parent,columns,headings,widths,tree=False,height=9):
    host=ttk.Frame(parent,style='Card.TFrame');host.pack(fill='both',expand=True)
    host.columnconfigure(0,weight=1);host.rowconfigure(0,weight=1)
    t=ttk.Treeview(host,columns=columns,show='tree headings' if tree else 'headings',height=height)
    keys=('#0',)+tuple(columns) if tree else columns
    for key,title,width in zip(keys,headings,widths):t.heading(key,text=title);t.column(key,width=width,minwidth=70)
    y=ttk.Scrollbar(host,command=t.yview);x=ttk.Scrollbar(host,orient='horizontal',command=t.xview)
    t.configure(yscrollcommand=y.set,xscrollcommand=x.set)
    t.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
    return t


def journal(parent,height=5,disabled=False):
    f=ttk.Frame(parent,style='Card.TFrame');f.pack(fill='both',expand=True)
    t=tk.Text(f,height=height,wrap='word',font=('Consolas',10),relief='flat',padx=10,pady=10,state='disabled' if disabled else 'normal')
    y=ttk.Scrollbar(f,command=t.yview); t.configure(yscrollcommand=y.set)
    y.pack(side='right',fill='y');t.pack(fill='both',expand=True)
    return t


def build_genre(a):
    a.path=tk.StringVar(a);a.genre=tk.StringVar(a);a.year=tk.StringVar(a)
    a.status=tk.StringVar(a,value='Choisis un dossier, puis lance un aperçu.')
    a.mode_label=tk.StringVar(a,value='Aucun dossier sélectionné')
    p=panel(a,'01  /  DOSSIER SOURCE')
    pathrow(p,a.path,[('Dossier unique',a.choose_single),('MUSIC xxxx',a.choose_music)]).configure(state='readonly')
    label(p,'Dossier unique : un genre commun. MUSIC xxxx : un genre par sous-dossier.')
    label(p,textvariable=a.mode_label)
    r=ttk.Frame(p,style='Card.TFrame');r.pack(fill='x',pady=(6,0))
    ttk.Label(r,text='Genre',style='Section.TLabel').grid(row=0,column=0,sticky='w')
    ttk.Label(r,text='Année',style='Section.TLabel').grid(row=0,column=1,sticky='w',padx=(16,0))
    a.genre_entry=ttk.Entry(r,textvariable=a.genre,width=38);a.genre_entry.grid(row=1,column=0,sticky='ew')
    ttk.Entry(r,textvariable=a.year,width=12).grid(row=1,column=1,padx=(16,0));r.columnconfigure(0,weight=1)
    actions(p,[('Analyser / Aperçu',a.scan),('Appliquer Genre + Année',a.apply,'Purple.TButton')])
    p=panel(a,'02  /  APERÇU DES MODIFICATIONS',True)
    a.tree=table(p,('file','oldg','newg','oldy','newy','state'),('Fichier','Genre actuel','Nouveau genre','Année actuelle','Nouvelle année','État'),(330,130,150,110,110,130))
    label(p,textvariable=a.status)
    p=panel(a,'JOURNAL');a.log=journal(p,4)


def build_rekord(a):
    p=panel(a,'01  /  SOURCE ET DESTINATION')
    label(p,'Dossier musique','Section.TLabel');pathrow(p,a.source,[('Parcourir…',a.pick)])
    label(p,'Dossier Rekordbox','Section.TLabel')
    a.rb_combo=pathrow(p,a.rb_folder,[('Actualiser',a.refresh_rb_folders)],True)
    a.rb_combo.bind('<<ComboboxSelected>>',a.on_rb_folder_changed)
    a.analyze_btn,a.sync_btn=actions(p,[('Analyser les changements',a.plan_all),('Synchroniser',a.sync_one_click,'Blue.TButton')])
    opts=Flow(p);opts.pack(fill='x',pady=(4,0))
    ttk.Checkbutton(opts,text='Retirer de la playlist',variable=a.remove_from_playlists)
    ttk.Checkbutton(opts,text='Retirer de la Collection',variable=a.remove_from_collection)
    label(p,textvariable=a.status,wraplength=780)
    p=panel(a,'02  /  PLAYLISTS REKORDBOX',True)
    actions(p,[('Tout sélectionner',a.select_all_playlists),('Tout désélectionner',a.deselect_all_playlists),('Voir les changements',a.show_selected_changes),('Supprimer playlist / dossier',a.delete_selected_target)])
    a.tree=table(p,('files','state'),('Playlist','Fichiers','État'),(330,90,470),True)
    a.tree.bind('<Button-1>',a.on_playlist_click);a.tree.bind('<space>',a.on_playlist_space);a.tree.bind('<Double-1>',a.on_playlist_double_click)
    # Keep the original collapsible-journal contract used by controller methods.
    a.logcard=ttk.Frame(a,style='Card.TFrame',padding=12)
    a.logbody=ttk.Frame(a.logcard,style='Card.TFrame');a.log=journal(a.logbody,6);a.log_visible=False
    tools=ttk.Frame(a,style='Card.TFrame',padding=12);tools.pack(fill='x')
    actions(tools,[('Diagnostic',a.doctor),('Ajouter Collection',a.import_collection),('Sync playlists',a.apply_all),('Vérifier / installer rbsync',a.install)])
    a.log_toggle_btn=ttk.Button(tools,text='Journal technique ▼',command=a.toggle_log);a.log_toggle_btn.pack(anchor='w',pady=(5,0))
    # toggle_log inserts before this direct sibling.
    def toggle():
        if a.log_visible:
            a.logcard.pack_forget();a.logbody.pack_forget();a.log_toggle_btn.configure(text='Journal technique ▼');a.log_visible=False
        else:
            a.logcard.pack(fill='x',before=tools,pady=(0,10));a.logbody.pack(fill='both',expand=True);a.log_toggle_btn.configure(text='Journal technique ▲');a.log_visible=True;a.log.see('end')
    a.toggle_log=toggle;a.log_toggle_btn.configure(command=toggle)
    update_button=a.update_sync_button
    def refresh_button():
        update_button()
        a.sync_btn.configure(text='Créer et synchroniser' if 'CRÉER' in a.sync_btn.cget('text') else 'Synchroniser')
        a.sync_btn.master.after_idle(a.sync_btn.master.reflow)
    a.update_sync_button=refresh_button



def build_serato(a):
    p=panel(a,'01  /  BIBLIOTHÈQUES')
    label(p,'Export XML Rekordbox','Section.TLabel');pathrow(p,a.xml_path,[('Choisir XML',a.choose_xml)])
    label(p,'Dossier Serato','Section.TLabel');pathrow(p,a.serato_path,[('Choisir',a.choose_serato),('Détecter',a.auto_detect_serato)])
    a.refresh_btn=actions(p,[('Actualiser',a.reload_xml)])[0]
    ttk.Checkbutton(p,text='Surveiller les changements du XML',variable=a.auto_watch,command=a.save_settings).pack(anchor='w',pady=5)
    label(p,textvariable=a.source_state);label(p,textvariable=a.serato_state)
    p=panel(a,'02  /  PLAYLISTS ET COMPARAISON',True)
    pathrow(p,a.playlist_filter,[('Effacer la recherche',lambda:a.playlist_filter.set(''))])
    actions(p,[('Tout sélectionner',lambda:a.set_all(True)),('Tout désélectionner',lambda:a.set_all(False)),('Comparer',a.refresh_statuses),('Sélectionner changements',a.select_changed_only)])
    a.tree=table(p,('tracks','status'),('Dossier / Playlist','Titres','État Serato'),(430,90,260),True)
    a.tree.bind('<Button-1>',a.on_tree_click)
    label(p,textvariable=a.summary)
    actions(p,[('Simulation',a.simulate_sync),('Diagnostic',a.run_diagnostic),('Marqueurs',a.marker_preview),('Sync auto',a.sync_changes,'Orange.TButton')])
    label(p,'WAV : crates compatibles. Les Hot Cues / Saved Loops WAV sont ignorés.','Warning.TLabel',wraplength=760)
    p=panel(a,'OUTILS AVANCÉS')
    actions(p,[('Importer vers Serato',lambda:a.run_sync(import_only=True)),('Synchroniser',lambda:a.run_sync(import_only=False)),('Réécrire',a.force_rewrite),('Sauvegardes',a.open_backups),('Restaurer la sauvegarde',a.restore_last_backup),('Historique Serato',a.show_sync_history)])
    p=panel(a,'JOURNAL');a.log=journal(p,6,True);label(p,textvariable=a.status,wraplength=780)
