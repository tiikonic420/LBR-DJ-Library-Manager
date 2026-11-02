"""Studio 4.0 RC2 — display performance improvements on the user-validated integrated controllers."""
import os
import importlib
import json
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import manager_core as core
from manager_core import ENGINES, PALETTES
from integrated_ui import panel, label, actions
from design_system import Skin
from dashboard import Dashboard

CONFIG=core.CONFIG
ENGINES['TagStudio']=('tag_studio','Tag Studio','Tags, pochettes et renommage','1.6 intégré','Green')
PALETTES['sombre'].update(bg='#090f19',side='#0b121e',card='#101927',input='#141f30',border='#253248',hover='#1b2940',blue='#245fff',purple='#8733f4',orange='#f15a18',green='#00a876',warn='#d99b30',warnbg='#2a2115')

class LBRManager(core.LBRManager):
    engines=ENGINES
    asset_path=Path(__file__).resolve().parent/'assets'
    @property
    def colors(self):return PALETTES[self.mode]
    def __init__(self):
        super().__init__()
        self.title('LBR DJ Library Manager — Studio 4.0 RC2')
        self._open_windows=set()
        self.bind_all('<Map>',self.on_widget_map,add='+')
    def build_shell(self):
        self.skin=Skin(self);self.metric_snapshot=None
        self.path_vars={k:tk.StringVar(self,value=self.settings.get(k,'')) for k in ['music','xml','serato']}
        self.side=ttk.Frame(self,style='Sidebar.TFrame',width=232,padding=(15,22));self.side.pack(side='left',fill='y');self.side.pack_propagate(False)
        brand=ttk.Frame(self.side,style='Sidebar.TFrame');brand.pack(fill='x',pady=(0,4))
        ttk.Label(brand,image=self.skin.icon('disc','#245fff',32),style='SideMuted.TLabel').pack(side='left',padx=(0,9))
        ttk.Label(brand,text='LBR',style='Logo.TLabel').pack(side='left')
        ttk.Label(self.side,text='DJ LIBRARY MANAGER',style='SideMuted.TLabel').pack(anchor='w',padx=4)
        ttk.Label(self.side,text='STUDIO 4.0 RC2',style='SideMuted.TLabel').pack(anchor='w',padx=4,pady=(4,25))
        for key,title,icon in [('Accueil','Accueil','home'),('RekordSync','RekordSync','sync'),('MusicGenre','MusicGenre','music'),('TagStudio','Tag Studio','disc'),('Serato','Rekordbox → Serato','transfer'),('Parcours','Mise à jour complète','play'),('Paramètres','Paramètres','gear')]:
            b=ttk.Button(self.side,text='  '+title,image=self.skin.icon(icon,'#a8bcda',20,False),compound='left',style='Nav.TButton',command=lambda k=key:self.show_page(k));b.pack(fill='x',pady=4);self.nav[key]=b
        foot=ttk.Frame(self.side,style='Sidebar.TFrame');foot.pack(side='bottom',fill='x',pady=4)
        ttk.Label(foot,text='VERSIONS INTÉGRÉES',style='SideMuted.TLabel').pack(anchor='w',pady=(0,9))
        for t in ['●  RekordSync 5.0.6','●  MusicGenre FINAL V2','●  Serato Sync 1.4 FINAL','●  Tag Studio 1.6']:ttk.Label(foot,text=t,style='SideMuted.TLabel').pack(anchor='w',pady=3)
        self.main=ttk.Frame(self,style='App.TFrame');self.main.pack(side='left',fill='both',expand=True)
        self.header=ttk.Frame(self.main,style='App.TFrame',padding=(20,17));self.header.pack(fill='x')
        self.header.columnconfigure(1,weight=1)
        self.header_icon=ttk.Label(self.header,image=self.skin.icon('home','#245fff',42),style='Status.TLabel');self.header_icon.grid(row=0,column=0,rowspan=2,padx=(0,13))
        self.heading=ttk.Label(self.header,text='Tableau de bord',style='Header.TLabel');self.heading.grid(row=0,column=1,sticky='w')
        self.subtitle=ttk.Label(self.header,text='Ton environnement DJ, au même endroit.',style='Status.TLabel');self.subtitle.grid(row=1,column=1,sticky='w',pady=(4,0))
        self.theme_box=ttk.Frame(self.header,style='App.TFrame');self.theme_box.grid(row=0,column=2,rowspan=2,padx=(14,0))
        self.theme_buttons={}
        for i,(mode,title) in enumerate([('clair','☀  Clair'),('sombre','☾  Sombre')]):
            b=ttk.Button(self.theme_box,text=title,command=lambda m=mode:self.set_theme(m));b.grid(row=0,column=i,padx=3);self.theme_buttons[mode]=b
        self.theme_btn=ttk.Button(self.header) # compatibility with the validated base theme method
        self.content=ttk.Frame(self.main,style='App.TFrame');self.content.pack(fill='both',expand=True,padx=(20,10))
        status=ttk.Frame(self.main,style='App.TFrame',padding=(20,8));status.pack(side='bottom',fill='x',before=self.content)
        ttk.Label(status,textvariable=self.status,style='Status.TLabel').pack(side='left')
        self.task_detail=tk.StringVar(self,value='Coordinateur commun · Prêt')
        self.task_bar=ttk.Frame(self.main,style='App.TFrame',padding=(20,4))
        self.task_bar.pack(side='bottom',fill='x',before=self.content)
        self.task_progress=ttk.Progressbar(self.task_bar,mode='indeterminate',length=90)
        self.task_progress.pack(side='left',padx=(0,10))
        self.task_label=ttk.Label(self.task_bar,textvariable=self.task_detail,style='Status.TLabel');self.task_label.pack(side='left')
        self.task_progress.pack_forget()
        self.hub.listeners.append(self.task_changed)
        self.make_home();self.make_workflow();self.make_settings()
    def page(self,key):
        if key=='TagStudio':
            p=ttk.Frame(self.content,style='App.TFrame');self.pages[key]=p;return p
        return super().page(key)
    def make_home(self):
        p=self.page('Accueil');self.dashboard=Dashboard(p,self);self.dashboard.pack(fill='x')
    def draw_art(self,c):pass
    def metric_values(self,key):
        a=self.apps.get(key)
        if key=='TagStudio':return [('Fichiers',len(a.rows) if a else '—'),('À enregistrer',len(a.pending) if a else '—'),('Session','Ouverte' if a else 'Fermée')]
        if not a:
            labs={'RekordSync':['Éléments','Sélectionnés','Session'],'MusicGenre':['Analysés','À modifier','Session'],'Serato':['Playlists','Titres','Session']}[key]
            return list(zip(labs,['—','—','Fermée']))
        if key=='MusicGenre':return [('Analysés',len(a.rows)),('À modifier',sum(r[5]=='À modifier' for r in a.rows)),('Session','Ouverte')]
        if key=='RekordSync':return [('Éléments',len(a.rows)),('Sélectionnés',sum(bool(v) for v in a.playlist_selected.values())),('Session','Ouverte')]
        return [('Playlists',len(a.playlists)),('Titres',len({t for p in a.playlists for t in p.tracks})),('Session','Ouverte')]
    def refresh_metrics(self):
        if self.current!='Accueil':
            self.after(1000,self.refresh_metrics);return
        snapshot=tuple((k,str(self.metric_values(k))) for k in ENGINES)
        if snapshot!=self.metric_snapshot:self.metric_snapshot=snapshot;self.dashboard.queue_draw()
        self.after(1000,self.refresh_metrics)
    def show_page(self,key):
        if key==self.current:return
        if key not in self.pages:
            body=self.page(key)
            try:
                module=importlib.import_module(ENGINES[key][0])
                self.prepare_module(key,module)
                app=module.App(body);app.pack(fill='both',expand=True);self.apps[key]=app
                self.apply_defaults(key)
                self.hub.register(app)
            except Exception as e:
                self.apps.pop(key,None)
                for widget in body.winfo_children():widget.destroy()
                box=panel(body,'Impossible de charger cet outil')
                label(box,str(e),wraplength=750)
                label(box,'Lance INSTALLER_DEPENDANCES.bat si une dépendance manque.',wraplength=750)
                actions(box,[('Réessayer',lambda:self.retry(key))])
            self.color_native(self.pages[key])
        old=self.current
        if old in self.pages:self.pages[old].pack_forget()
        self.theme_scope(self.pages[key])
        self.pages[key].pack(fill='both',expand=True)
        self.current=key
        if old in self.nav:self.nav[old]._lbr_base_style='Nav.TButton';self.nav[old].configure(style=self.mode+'.Nav.TButton')
        self.nav[key]._lbr_base_style='Active.Nav.TButton';self.nav[key].configure(style=self.mode+'.Active.Nav.TButton')
        self.heading.configure(text=ENGINES[key][1] if key in ENGINES else {'Accueil':'Tableau de bord','Parcours':'Mise à jour complète','Paramètres':'Paramètres'}[key])
        self.status.set('Espace intégré  •  '+self.heading.cget('text'))
        icons={'Accueil':'home','RekordSync':'sync','MusicGenre':'music','Serato':'transfer','TagStudio':'disc','Parcours':'db','Paramètres':'gear'}
        subtitles={'Accueil':'Ton environnement DJ, au même endroit.','RekordSync':'Prépare et synchronise ta bibliothèque Rekordbox.','MusicGenre':'Organise les genres et les années de tes morceaux.','Serato':'Retrouve tes playlists et marqueurs dans Serato.','TagStudio':'Édite tes tags, tes pochettes et tes noms de fichiers.','Parcours':'Prépare tes bibliothèques, étape par étape.','Paramètres':'Configure ton environnement DJ selon tes besoins.'}
        self.header_icon.configure(image=self.skin.icon(icons[key],self.colors['blue'],42))
        self.subtitle.configure(text=subtitles[key])
        if key=='Parcours':self.heading.configure(text='Mise à jour complète')
        if key=='Accueil':self.after_idle(self.dashboard.queue_draw)
    def apply_defaults(self,key):
        a=self.apps[key]
        if key=='TagStudio' and self.settings.get('music'):a.folder=self.settings['music']
        # Defaults are applied only to a freshly created page, never to an in-progress analysis.
        if key=='RekordSync' and self.settings.get('music'):a.source.set(self.settings['music'])
        if key=='Serato':
            if self.settings.get('xml'):a.xml_path.set(self.settings['xml'])
            if self.settings.get('serato'):a.serato_path.set(self.settings['serato'])
        if key=='MusicGenre' and self.settings.get('music'):
            import musicgenre_v2 as genre
            folder=self.settings['music'];a.folder=folder;a.mode='music';a.path.set(folder)
            a.genre.set('AUTOMATIQUE PAR SOUS-DOSSIER');a.genre_entry.configure(state='disabled');a.year.set(genre.detect_year(Path(folder).name));a.mode_label.set('Mode MUSIC xxxx — un genre par premier sous-dossier')
    def make_settings(self):
        p=self.page('Paramètres');self.setting_pages={};self.setting_tabs={}
        tabs=ttk.Frame(p,style='App.TFrame');tabs.pack(fill='x',pady=(0,12))
        for i,(key,name) in enumerate([('Configuration','⚙  Configuration'),('Apparence','◐  Apparence'),('À propos','ⓘ  À propos')]):
            tabs.columnconfigure(i,weight=1,uniform='tabs');b=ttk.Button(tabs,text=name,command=lambda k=key:self.show_settings(k));b.grid(row=0,column=i,sticky='ew',padx=(0,8 if i<2 else 0));self.setting_tabs[key]=b
        self.setting_host=ttk.Frame(p,style='App.TFrame');self.setting_host.pack(fill='both',expand=True)
        cfg=ttk.Frame(self.setting_host,style='App.TFrame');self.setting_pages['Configuration']=cfg
        box=panel(cfg);label(box,'Configuration commune','Big.TLabel');label(box,'Définis les chemins proposés lors de la première ouverture de chaque outil.',wraplength=850)
        inner=ttk.Frame(box,style='Inset.TFrame',padding=17);inner.pack(fill='x',pady=(9,5))
        label(inner,'EMPLACEMENTS DES DOSSIERS','BlueText.TLabel')
        for key,title,desc,icon,col in [('music','Dossier musique','Dossier MUSIC xxxx et ses sous-dossiers','music','orange'),('xml','XML Rekordbox','Export de la bibliothèque Rekordbox','folder','blue'),('serato','Dossier _Serato_','Destination des crates Serato','folder','green')]:
            row=ttk.Frame(inner,style='Card.TFrame');row.pack(fill='x',pady=8);row.columnconfigure(1,weight=1)
            ttk.Label(row,image=self.skin.icon(icon,self.colors[col],32),style='TLabel').grid(row=0,column=0,rowspan=2,padx=(0,13))
            ttk.Label(row,text=title,style='CardTitle.TLabel').grid(row=0,column=1,sticky='w')
            ttk.Label(row,text=desc,style='Muted.TLabel').grid(row=1,column=1,sticky='w',pady=(3,6))
            field=ttk.Frame(row,style='Card.TFrame');field.grid(row=2,column=0,columnspan=2,sticky='ew');field.columnconfigure(0,weight=1)
            ttk.Entry(field,textvariable=self.path_vars[key]).grid(row=0,column=0,sticky='ew')
            ttk.Button(field,text='Parcourir…',command=lambda k=key:self.pick_common(k)).grid(row=0,column=1,padx=(7,0))
            def adapt_row(e,r=row,f=field):
                wide=e.width>=850
                if getattr(r,'_wide_layout',None)==wide:return
                r._wide_layout=wide
                if wide:
                    r.columnconfigure(1,weight=0,minsize=300);r.columnconfigure(2,weight=1)
                    f.grid_configure(row=0,column=2,rowspan=2,columnspan=1,padx=(20,0))
                else:
                    r.columnconfigure(1,weight=1,minsize=0);r.columnconfigure(2,weight=0)
                    f.grid_configure(row=2,column=0,rowspan=1,columnspan=2,padx=0)
            row.bind('<Configure>',adapt_row)

        label(box,'Les outils déjà ouverts gardent leurs sélections. Les nouveaux chemins seront proposés à la prochaine session.',wraplength=840)
        actions(box,[('Enregistrer la configuration',self.save_common,'Blue.TButton'),('Effacer les chemins communs',self.clear_common)])
        self.config_status=tk.StringVar(self,value='Les chemins propres aux moteurs restent disponibles dans chaque outil.')
        label(box,textvariable=self.config_status,wraplength=840)
        self.make_settings_footer(cfg)
        appear=ttk.Frame(self.setting_host,style='App.TFrame');self.setting_pages['Apparence']=appear
        box=panel(appear);label(box,'Une interface à ton image','Big.TLabel');label(box,'Le thème s’applique immédiatement aux quatre outils et reste mémorisé.',wraplength=780)
        actions(box,[('☾  Utiliser le mode sombre',lambda:self.set_theme('sombre'),'Blue.TButton'),('☀  Utiliser le mode clair',lambda:self.set_theme('clair'))])
        label(box,'Contraste renforcé, cartes arrondies et code couleur par moteur : bleu pour RekordSync, violet pour MusicGenre, orange pour Serato.',wraplength=800)
        about=ttk.Frame(self.setting_host,style='App.TFrame');self.setting_pages['À propos']=about
        box=panel(about);label(box,'LBR DJ Library Manager','Big.TLabel');label(box,'STUDIO 4.0 RC2  •  LBR SOFTWARE','BlueText.TLabel')
        label(box,'Version gratuite • Candidate à la publication',wraplength=800)
        actions(box,[('Ouvrir les journaux',self.open_logs),('Diagnostic installation',self.diagnose_install),('Guide utilisateur',self.open_guide)])
        for _,title,desc,version,_ in ENGINES.values():label(box,f'{title}  /  {version} — {desc}',wraplength=800)
        label(box,'Quatre outils intégrés, un coordinateur commun. Les analyses et les écritures passent par la même file de traitement ; la navigation reste disponible.',wraplength=800)
        label(box,'WAV : compatibles avec les crates Serato. La synchronisation des Hot Cues / Saved Loops vers WAV n’est pas prise en charge ; leurs marqueurs sont ignorés.','Warning.TLabel',wraplength=800)
        self.show_settings('Configuration')
    def make_settings_footer(self,parent):
        f=ttk.Frame(parent,style='App.TFrame');f.pack(fill='x')
        for i in range(2):f.columnconfigure(i,weight=1,uniform='foot')
        a=ttk.Frame(f,style='Panel.TFrame',padding=16);a.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        label(a,'MOTEURS INTÉGRÉS','BlueText.TLabel')
        for key,(_,title,_,version,_) in ENGINES.items():label(a,f'{title}   ·   {version}',wraplength=390)
        b=ttk.Frame(f,style='Panel.TFrame',padding=16);b.grid(row=0,column=1,sticky='nsew');label(b,'OUTILS RAPIDES','BlueText.TLabel')
        actions(b,[('Dossier musique',lambda:self.open_common('music')),('Dossier Serato',lambda:self.open_common('serato')),('Emplacement XML',lambda:self.open_common('xml'))])
    def diagnose_install(self):
        def job():
            from diagnostics import write_report
            path=write_report()
            self.hub.ui(messagebox.showinfo,'Diagnostic installation','Rapport enregistré :\n'+str(path),parent=self)
        self.hub.run('Manager','Diagnostic installation',job)
    def open_logs(self):
        path=Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'LBR-DJ-Library-Manager'/'logs'
        path.mkdir(parents=True,exist_ok=True)
        if os.name=='nt':os.startfile(str(path))
    def open_guide(self):
        path=Path(__file__).resolve().parents[2]/'Documentation'/'GUIDE_UTILISATEUR.txt'
        if path.is_file() and os.name=='nt':os.startfile(str(path))
        else:messagebox.showinfo('Guide utilisateur','Consulte le dossier Documentation livré avec le logiciel.',parent=self)
    def show_settings(self,key):
        for p in self.setting_pages.values():p.pack_forget()
        self.setting_pages[key].pack(fill='both',expand=True)
        for k,b in self.setting_tabs.items():
            b._lbr_base_style='Blue.TButton' if k==key else 'TButton'
            b.configure(style=(self.mode+'.' if getattr(self,'_themes_ready',False) else '')+b._lbr_base_style)
    def pick_common(self,key):
        value=filedialog.askopenfilename(parent=self,title='Export XML Rekordbox',filetypes=[('XML','*.xml')]) if key=='xml' else filedialog.askdirectory(parent=self,title='Choisir le dossier')
        if value:self.path_vars[key].set(value)
    def save_common(self):
        values={k:v.get().strip() for k,v in self.path_vars.items()}
        for key,val in values.items():
            if val and not (Path(val).is_file() if key=='xml' else Path(val).is_dir()):messagebox.showwarning('Chemin introuvable','Vérifie ce chemin :\n'+val,parent=self);return
        self.settings.update(values)
        if self.persist_settings():self.config_status.set('Configuration enregistrée. Les outils déjà ouverts restent inchangés.')
    def clear_common(self):
        for v in self.path_vars.values():v.set('')
        self.config_status.set('Champs effacés. Clique sur Enregistrer pour confirmer.')
    def open_common(self,key):
        value=self.path_vars[key].get().strip()
        if not value:messagebox.showinfo('Dossier','Choisis un chemin dans la configuration.',parent=self);return
        p=Path(value).parent if key=='xml' else Path(value)
        if not p.is_dir():messagebox.showwarning('Dossier introuvable',str(p),parent=self);return
        try:
            if os.name=='nt':os.startfile(str(p))
            elif sys.platform=='darwin':subprocess.Popen(['open',str(p)])
            else:subprocess.Popen(['xdg-open',str(p)])
        except OSError as e:messagebox.showerror('Ouverture impossible',str(e),parent=self)
    def set_theme(self,mode):
        if mode==self.mode:return
        self.mode=mode;self.settings['theme']=mode;self.apply_theme();self.persist_settings()
    def persist_settings(self):
        try:
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            temp=CONFIG.with_suffix('.tmp');temp.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(CONFIG);return True
        except OSError as e:self.status.set('Réglages non enregistrés : '+str(e));return False
    def retry(self,key):
        self.pages.pop(key).destroy()
        self.current=''
        self.show_page(key)
    def color_native(self,root):
        c=self.colors
        if isinstance(root,tk.Text):root.configure(bg=c['input'],fg=c['text'],insertbackground=c['text'],selectbackground=c['blue'],selectforeground='white')
        elif isinstance(root,(tk.Frame,tk.Canvas)):root.configure(bg=c['bg'])
        for child in root.winfo_children():self.color_native(child)
    def theme_scope(self,root):
        # Local style changes avoid Tk's global ThemeChanged font/layout invalidation.
        if getattr(root,'_lbr_mode',None)==self.mode:return
        c=self.colors
        def walk(w):
            self.theme_widget(w)
            for child in tuple(w.children.values()):walk(child)
        walk(root);root._lbr_mode=self.mode
    def theme_widget(self,w):
        c=self.colors
        stamp=(self.mode,getattr(w,'_lbr_base_style',None))
        if getattr(w,'_lbr_theme_stamp',None)==stamp:return
        if isinstance(w,ttk.Widget):
            base=getattr(w,'_lbr_base_style',None)
            if base is None:
                base=str(w.cget('style')) or w.winfo_class()
                w._lbr_base_style=base
            target=self.mode+'.'+base
            if base in self._style_names:
                # Known widgets need no Tcl style read on each palette switch.
                if getattr(w,'_lbr_theme_stamp',None) is not None or str(w.cget('style'))!=target:
                    w.configure(style=target)
        elif isinstance(w,tk.Listbox):
            if w.cget('background')!=c['input']:w.configure(bg=c['input'],fg=c['text'],selectbackground=c['blue'],selectforeground='white')
        elif isinstance(w,tk.Text):
            if w.cget('background')!=c['input']:
                w.configure(bg=c['input'],fg=c['text'],insertbackground=c['text'],selectbackground=c['blue'],selectforeground='white')
        elif isinstance(w,(tk.Frame,tk.Canvas,tk.Toplevel)):
            if w.cget('background')!=c['bg']:w.configure(bg=c['bg'])
        w._lbr_theme_stamp=(self.mode,getattr(w,'_lbr_base_style',None))
    def on_widget_map(self,event):
        # Also covers engine preview windows and widgets created after startup.
        if isinstance(event.widget,tk.Toplevel):self._open_windows.add(event.widget)
        if isinstance(event.widget,tk.Widget):self.theme_widget(event.widget)
    def apply_theme(self):
        if not getattr(self,'_themes_ready',False):
            chosen=self.mode;s=self.style
            names=set()
            original={method:getattr(s,method) for method in ('configure','map','layout')}
            def record(method):
                def call(name,*args,**kw):
                    names.add(name);return original[method](name,*args,**kw)
                return call
            # Build both palettes once, in one ttk theme. Each style owns its colors.
            for mode in ('clair','sombre'):
                self.mode=mode
                for method in original:setattr(s,method,record(method))
                try:
                    super().apply_theme();self.skin.apply(self.colors)
                finally:
                    for method,fn in original.items():setattr(s,method,fn)
                names.update(['Brand.TLabel','Tool.TButton','TLabelframe','TLabelframe.Label','TPanedwindow','Horizontal.TPanedwindow','Vertical.TPanedwindow','TFrame','TLabel','TButton','TEntry','TCombobox','TCheckbutton',
                              'TRadiobutton','Treeview','Treeview.Heading','TScrollbar',
                              'Horizontal.TScrollbar','Vertical.TScrollbar','TSeparator',
                              'Horizontal.TSeparator','Vertical.TSeparator','TProgressbar',
                              'Horizontal.TProgressbar','Vertical.TProgressbar'])
                # Read each inherited style once per palette, not once per descendant.
                configs={};style_maps={}
                for name in sorted(names):
                    if name=='.':continue
                    chain=['.']
                    parts=name.split('.')
                    chain.extend('.'.join(parts[i:]) for i in range(len(parts)-1,-1,-1))
                    cfg={};maps={}
                    for parent in chain:
                        if parent not in configs:
                            configs[parent]=s.configure(parent) or {}
                            style_maps[parent]=s.map(parent) or {}
                        cfg.update(configs[parent]);maps.update(style_maps[parent])
                    variant=(name.split('.')[0]+'.'+mode+'.'+name.split('.',1)[1]) if name.startswith(('Horizontal.','Vertical.')) else mode+'.'+name
                    s.configure(variant,**cfg);s.map(variant,**maps)
                    try:s.layout(variant,s.layout(name))
                    except tk.TclError:pass
            self._style_names=names;self.mode=chosen;self._themes_ready=True
        c=self.colors;self.configure(bg=c['bg'])
        self.theme_scope(self.side);self.theme_scope(self.header)
        # Footer and host use the same palette, without walking hidden pages.
        self.main.configure(style=self.mode+'.App.TFrame')
        self.content.configure(style=self.mode+'.App.TFrame')
        for child in self.main.winfo_children():
            if child not in (self.header,self.content):self.theme_scope(child)
        if self.current in self.pages:self.theme_scope(self.pages[self.current])
        self.option_add('*TCombobox*Listbox.background',c['input'])
        self.option_add('*TCombobox*Listbox.foreground',c['text'])
        for mode,button in self.theme_buttons.items():
            button._lbr_base_style='Blue.TButton' if mode==self.mode else 'TButton'
            button.configure(style=self.mode+'.'+button._lbr_base_style)
        icons={'Accueil':'home','RekordSync':'sync','MusicGenre':'music','Serato':'transfer','TagStudio':'disc','Parcours':'db','Paramètres':'gear'}
        self.header_icon.configure(image=self.skin.icon(icons.get(self.current,'home'),c['blue'],42))
        for child in tuple(getattr(self,'_open_windows',())):
            if child.winfo_exists():self.theme_scope(child)
            else:self._open_windows.discard(child)
        if 'TagStudio' in self.apps:self.apps['TagStudio'].theme()
        self.dashboard.queue_draw()

    def prepare_module(self,key,module):
        from task_hub import managed,ThreadFacade,DialogFacade
        if getattr(module,'_coordinated',False):return
        specs={
            'MusicGenre':(['scan','apply'],['scan']),
            'RekordSync':(['scan','refresh_rb_folders','doctor','plan_all','import_collection','apply_all','sync_one_click','delete_selected_target'],['scan','refresh_rb_folders']),
            'Serato':(['startup_load','watch_xml','load_xml','reload_xml','auto_detect_serato','refresh_statuses','apply_playlist_filter','select_changed_only','simulate_sync','marker_preview','run_diagnostic','sync_changes','hotcue_preview','force_rewrite','run_sync','restore_last_backup'],['startup_load','watch_xml','load_xml','refresh_statuses','apply_playlist_filter']),
            'TagStudio':(['refresh','save','undo','rename','apply_cover','filename_to_tags','replace','export','load_rb','sort_by','apply_fields','clear_pending'],['refresh'])}
        cache=self.hub.cache
        for name in ({'MusicGenre':['read_tags'],'TagStudio':['read_tags','serato_info']}.get(key,[])):
            reader=getattr(module,name)
            setattr(module,name,lambda path,_fn=reader,_ns=key+name:cache.read(_ns,_fn,path))
        for name in ({'MusicGenre':['write_tags'],'TagStudio':['safe_write','safe_write_cover']}.get(key,[])):
            writer=getattr(module,name)
            def write(path,*args,_fn=writer,**kw):
                try:return _fn(path,*args,**kw)
                finally:cache.invalidate(path)
            setattr(module,name,write)
        names,background=specs[key]
        managed(module.App,names,key,background)
        if hasattr(module,'threading'):module.threading=ThreadFacade(self.hub,key)
        for name in ('simpledialog','filedialog','messagebox'):
            if hasattr(module,name):setattr(module,name,DialogFacade(self.hub,getattr(module,name)))
        module._coordinated=True
    def task_changed(self,busy,owner,title):
        if busy:
            self.task_progress.pack(side='left',padx=(0,10),before=self.task_label)
            self.task_progress.start(12)
            self.task_detail.set(ENGINES.get(owner,('',owner))[1]+' · '+title+'…')
        else:
            self.task_progress.stop();self.task_progress.pack_forget()
            self.task_detail.set('Coordinateur commun · '+title)
            self.metric_snapshot=None
    def report_task_error(self,owner,title,details):
        from datetime import datetime
        log=Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'LBR-DJ-Library-Manager'/'logs'/'tasks.log';log.parent.mkdir(parents=True,exist_ok=True)
        if log.exists() and log.stat().st_size>3*1024*1024:log.replace(log.with_suffix('.previous.log'))
        with log.open('a',encoding='utf-8') as f:f.write(f'\n{datetime.now().isoformat()} {owner} / {title}\n{details}\n')
        messagebox.showerror('Traitement interrompu','Une erreur est survenue. Consulte le journal :\n'+str(log),parent=self)
    def close(self):
        if self.hub.busy or self.hub.deferred:
            messagebox.showinfo('Traitement en cours','Attends la fin du traitement avant de fermer. Les écritures en cours doivent se terminer.',parent=self);return
        tag=self.apps.get('TagStudio')
        if tag and tag.pending and not messagebox.askyesno('Modifications non enregistrées','Fermer et abandonner les tags non enregistrés ?',parent=self):return
        if self.hub.shutdown():self.destroy()

if __name__=='__main__':
    LBRManager().mainloop()
