"""LBR DJ Library Manager 2.0 — a single Tk application, three embedded engines."""
import importlib
import json
import math
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from pathlib import Path
from datetime import datetime
from integrated_ui import panel, label, actions

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'modules'))
CONFIG=Path(os.getenv('APPDATA',Path.home()))/'LBR-DJ-Library-Manager'/'interface.json'
ENGINES={
 'RekordSync':('rekordsync_v5_0_6','RekordSync','Bibliothèque & playlists Rekordbox','5.0.6','Blue'),
 'MusicGenre':('musicgenre_v2','MusicGenre','Genre & année depuis tes dossiers','FINAL V2','Purple'),
 'Serato':('rekordbox_serato_v1_4','Rekordbox → Serato','Crates, Hot Cues & Saved Loops','1.4 FINAL','Orange')}
PALETTES={
 'sombre':dict(bg='#0b111c',side='#0e1624',card='#141f30',input='#101a2a',text='#edf3ff',muted='#9badc7',border='#26364f',hover='#20324d',blue='#2862ef',purple='#833de1',orange='#d94b18',green='#16c99a',warn='#ffbf59',warnbg='#342819'),
 'clair':dict(bg='#edf2f8',side='#ffffff',card='#ffffff',input='#f3f6fb',text='#13243d',muted='#516581',border='#cfdaea',hover='#e0e9f8',blue='#2156d8',purple='#7131c9',orange='#bd3e10',green='#087c60',warn='#865100',warnbg='#fff2d9')}

class Viewport(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent,style='App.TFrame')
        self.canvas=tk.Canvas(self,highlightthickness=0,bd=0)
        self.scroll=ttk.Scrollbar(self,command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.body=ttk.Frame(self.canvas,style='App.TFrame')
        self.window=self.canvas.create_window(0,0,window=self.body,anchor='nw')
        self.canvas.bind('<Configure>',self.resize);self.body.bind('<Configure>',self.region)
    def resize(self,e):self.canvas.itemconfigure(self.window,width=e.width)
    def region(self,e=None):self.canvas.configure(scrollregion=self.canvas.bbox('all'))

class LBRManager(tk.Tk):
    def __init__(self):
        super().__init__()
        from task_hub import TaskHub
        self.hub=TaskHub(self);self.task_completed=[]
        self.font_family='Segoe UI' if 'Segoe UI' in tkfont.families(self) else 'Helvetica'
        self.title('LBR DJ Library Manager • Studio 2.0')
        self.geometry(f'{min(1440,self.winfo_screenwidth()-40)}x{min(900,self.winfo_screenheight()-80)}')
        self.minsize(980,600)
        try:self.settings=json.loads(CONFIG.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.settings={}
        if not isinstance(self.settings,dict):self.settings={}
        self.mode=self.settings.get('theme','sombre')
        if self.mode not in PALETTES:self.mode='sombre'
        self.pages={};self.apps={};self.nav={};self.metrics={};self.current='';self.events=[]
        self.style=ttk.Style(self);self.style.theme_use('clam')
        self.status=tk.StringVar(self,value='Bienvenue • choisis un outil pour commencer')
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.build_shell();self.apply_theme();self.show_page('Accueil')
        self.bind_all('<MouseWheel>',self.wheel,add='+')
        self.bind_all('<Button-4>',self.wheel,add='+');self.bind_all('<Button-5>',self.wheel,add='+')
        self.after(800,self.refresh_metrics)

    def build_shell(self):
        self.side=ttk.Frame(self,style='Sidebar.TFrame',width=240,padding=(16,24))
        self.side.pack(side='left',fill='y');self.side.pack_propagate(False)
        ttk.Label(self.side,text='LBR',style='Logo.TLabel').pack(anchor='w')
        ttk.Label(self.side,text='DJ LIBRARY MANAGER',style='SideMuted.TLabel').pack(anchor='w',pady=(0,4))
        ttk.Label(self.side,text='STUDIO  /  2.0',style='SideMuted.TLabel').pack(anchor='w',pady=(0,26))
        for key,text in [('Accueil','⌂   Tableau de bord'),('RekordSync','↻   RekordSync'),('MusicGenre','♫   MusicGenre'),('Serato','⇄   Rekordbox → Serato'),('Parcours','▷   Parcours guidé'),('Paramètres','⚙   Paramètres')]:
            b=ttk.Button(self.side,text=text,style='Nav.TButton',command=lambda k=key:self.show_page(k));b.pack(fill='x',pady=4);self.nav[key]=b
        foot=ttk.Frame(self.side,style='Sidebar.TFrame');foot.pack(side='bottom',fill='x')
        ttk.Label(foot,text='MOTEURS INTÉGRÉS',style='SideMuted.TLabel').pack(anchor='w',pady=(0,10))
        for key,(_,title,_,ver,_) in ENGINES.items():
            short='Serato Sync' if key=='Serato' else title
            ttk.Label(foot,text=f'{short}  ·  {ver}',style='SideMuted.TLabel').pack(anchor='w',pady=3)
        self.main=ttk.Frame(self,style='App.TFrame');self.main.pack(side='left',fill='both',expand=True)
        header=ttk.Frame(self.main,style='App.TFrame',padding=(24,18));header.pack(fill='x')
        self.heading=ttk.Label(header,text='Tableau de bord',style='Header.TLabel');self.heading.pack(side='left')
        self.theme_btn=ttk.Button(header,text='',command=self.toggle_theme);self.theme_btn.pack(side='right')
        self.content=ttk.Frame(self.main,style='App.TFrame');self.content.pack(fill='both',expand=True,padx=(24,12))
        status=ttk.Frame(self.main,style='App.TFrame',padding=(24,10));status.pack(fill='x')
        ttk.Label(status,textvariable=self.status,style='Status.TLabel').pack(side='left')
        self.make_home();self.make_workflow();self.make_settings()

    def page(self,key):
        p=Viewport(self.content);self.pages[key]=p;return p.body

    def make_home(self):
        p=self.page('Accueil')
        hero=ttk.Frame(p,style='Card.TFrame',padding=22);hero.pack(fill='x',pady=(0,18))
        self.art=tk.Canvas(hero,width=215,height=168,highlightthickness=0,bd=0);self.art.pack(side='right',padx=(12,0))
        def adapt_hero(e):
            if e.width<850:self.art.pack_forget()
            elif not self.art.winfo_manager():self.art.pack(side='right',padx=(12,0),before=hero.winfo_children()[1])
        hero.bind('<Configure>',adapt_hero)
        label(hero,'LBR  /  TON ESPACE DJ','Accent.TLabel')
        title=ttk.Label(hero,text='Toute ta musique.\nUn seul espace.',style='Hero.TLabel');title.pack(anchor='w',pady=(4,10))
        label(hero,'Organise tes titres et synchronise tes bibliothèques.\nTes trois outils réunis, de la préparation au mix.',wraplength=510)
        cards=ttk.Frame(p,style='App.TFrame');cards.pack(fill='x')
        for i,(key,(_,title,desc,ver,color)) in enumerate(ENGINES.items()):
            cards.columnconfigure(i,weight=1,uniform='cards')
            card=ttk.Frame(cards,style='Card.TFrame',padding=17);card.grid(row=0,column=i,sticky='nsew',padx=(0,12 if i<2 else 0))
            label(card,('↻','♫','⇄')[i],color+'.Icon.TLabel')
            label(card,title,'CardTitle.TLabel');label(card,ver,'Muted.TLabel')
            d=label(card,desc,wraplength=210);card.bind('<Configure>',lambda e,w=d:w.configure(wraplength=max(120,e.width-36)))
            ttk.Separator(card).pack(fill='x',pady=12)
            v=tk.StringVar(self,value='Non ouvert');self.metrics[key]=v
            label(card,textvariable=v,wraplength=210)
            ttk.Button(card,text='Ouvrir  →',style=color+'.TButton',command=lambda k=key:self.show_page(k)).pack(fill='x',pady=(10,0))
        warning=ttk.Frame(p,style='Warning.TFrame',padding=16);warning.pack(fill='x',pady=(18,18))
        label(warning,'WAV  /  MARQUEURS NON PRIS EN CHARGE','Warning.TLabel')
        w=label(warning,'Les WAV fonctionnent dans les crates Serato. La synchronisation des Hot Cues et Saved Loops vers les WAV n’est pas prise en charge : leurs marqueurs sont ignorés.','Warning.TLabel',wraplength=820)
        warning.bind('<Configure>',lambda e:w.configure(wraplength=max(200,e.width-36)))
        f=panel(p,'TON PARCOURS DE PRÉPARATION')
        label(f,'01  MusicGenre     →     02  RekordSync     →     03  Rekordbox → Serato','CardTitle.TLabel',wraplength=750)
        label(f,'Avance étape par étape, avec un aperçu avant les modifications.',wraplength=750)
        actions(f,[('Ouvrir le parcours guidé',lambda:self.show_page('Parcours'),'Blue.TButton')])

    def make_workflow(self):
        p=self.page('Parcours')
        label(p,'Prépare ton prochain set','Header.TLabel')
        label(p,'Chaque étape ouvre son outil ici. Tu gardes la main sur les analyses et les écritures.',wraplength=780)
        for num,key,text in [('01','MusicGenre','Choisis ton dossier, vérifie les genres et les années, puis applique les changements.'),('02','TagStudio','Corrige les titres, artistes et pochettes si nécessaire, puis enregistre les tags.'),('03','RekordSync','Ferme Rekordbox, analyse les différences et synchronise les playlists.'),('04','Serato','Dans Rekordbox, exporte un XML à jour. Charge-le ici, lance une simulation, puis Sync auto.')]:
            f=panel(p,f'{num}  /  {ENGINES[key][1]}');label(f,text,wraplength=780)
            actions(f,[('Ouvrir '+ENGINES[key][1],lambda k=key:self.show_page(k),ENGINES[key][4]+'.TButton')])
        f=panel(p,'05  /  VÉRIFICATION');label(f,'Consulte les journaux et le diagnostic Serato pour vérifier le résultat.',wraplength=780)

    def make_settings(self):
        p=self.page('Paramètres')
        f=panel(p,'APPARENCE');label(f,'Le thème s’applique aux trois outils et reste mémorisé au prochain lancement.',wraplength=780)
        actions(f,[('Mode clair',lambda:self.set_theme('clair')),('Mode sombre',lambda:self.set_theme('sombre'))])
        f=panel(p,'TON ESPACE DE TRAVAIL');label(f,'Les outils restent ouverts en arrière-plan lorsque tu changes de page. Les chemins et réglages de RekordSync et Serato sont conservés par leurs moteurs.',wraplength=780)
        f=panel(p,'VERSIONS INTÉGRÉES')
        for _,title,desc,ver,_ in ENGINES.values():label(f,f'{title}  /  {ver} — {desc}',wraplength=780)
        label(f,'Interface Studio 2.0 • Les confirmations et dialogues de fichiers restent des fenêtres système.',wraplength=780)

    def show_page(self,key):
        if key not in self.pages:
            body=self.page(key)
            try:
                module=importlib.import_module(ENGINES[key][0])
                app=module.App(body);app.pack(fill='both',expand=True);self.apps[key]=app
            except Exception as e:
                for w in body.winfo_children():w.destroy()
                f=panel(body,'Impossible de charger cet outil')
                label(f,str(e),wraplength=750)
                label(f,'Si mutagen manque, lance INSTALLER_DEPENDANCES.bat puis redémarre l’application.',wraplength=750)
                actions(f,[('Réessayer',lambda:self.retry(key))])
            self.apply_theme()
        for p in self.pages.values():p.pack_forget()
        self.pages[key].pack(fill='both',expand=True)
        self.current=key
        self.heading.configure(text=ENGINES[key][1] if key in ENGINES else {'Accueil':'Tableau de bord','Parcours':'Parcours guidé','Paramètres':'Paramètres'}[key])
        for k,b in self.nav.items():b.configure(style='Active.Nav.TButton' if k==key else 'Nav.TButton')
        self.status.set('Espace intégré  •  '+self.heading.cget('text'))

    def retry(self,key):
        self.pages.pop(key).destroy();self.show_page(key)

    def wheel(self,e):
        w=e.widget
        if isinstance(w,(tk.Text,ttk.Treeview,ttk.Combobox)):return
        page=self.pages.get(self.current)
        if not page or not hasattr(page,'canvas'):return
        if page.body.winfo_height()<=page.canvas.winfo_height():return
        delta=-1 if getattr(e,'num',None)==4 else 1 if getattr(e,'num',None)==5 else int(-e.delta/120)
        page.canvas.yview_scroll(delta,'units')

    def refresh_metrics(self):
        for k,a in self.apps.items():
            if k=='MusicGenre':v=f'{len(a.rows)} titres analysés\n{sum(r[5]=="À modifier" for r in a.rows)} à modifier'
            elif k=='RekordSync':v=f'{len(a.tree.get_children())} éléments affichés\nSession ouverte'
            else:v=f'{len(a.playlists)} playlists chargées\n{len(a.checked)} sélectionnées'
            self.metrics[k].set(v)
        self.after(1000,self.refresh_metrics)

    def toggle_theme(self):self.set_theme('clair' if self.mode=='sombre' else 'sombre')
    def set_theme(self,mode):
        self.mode=mode;self.apply_theme()
        try:
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            CONFIG.write_text(json.dumps({'theme':mode}),encoding='utf-8')
        except OSError as e:self.status.set('Thème appliqué, mais non enregistré : '+str(e))

    def apply_theme(self):
        c=PALETTES[self.mode];s=self.style;self.configure(bg=c['bg'])
        s.configure('.',font=(self.font_family,10),background=c['card'],foreground=c['text'],bordercolor=c['border'],troughcolor=c['bg'],selectbackground=c['blue'],selectforeground='white')
        for n,bg in [('TFrame','card'),('App.TFrame','bg'),('Card.TFrame','card'),('Sidebar.TFrame','side'),('Warning.TFrame','warnbg')]:s.configure(n,background=c[bg])
        for n,bg,fg,font in [('TLabel','card','text',(self.font_family,10)),('Status.TLabel','bg','muted',(self.font_family,10)),('Muted.TLabel','card','muted',(self.font_family,10)),('Section.TLabel','card','muted',(self.font_family,9,'bold')),('CardTitle.TLabel','card','text',(self.font_family,12,'bold')),('Header.TLabel','bg','text',(self.font_family,20,'bold')),('Hero.TLabel','card','text',(self.font_family,27,'bold')),('Logo.TLabel','side','text',(self.font_family,32,'bold')),('SideMuted.TLabel','side','muted',(self.font_family,9)),('Accent.TLabel','card','blue',(self.font_family,10,'bold')),('Warning.TLabel','warnbg','warn',(self.font_family,10))]:s.configure(n,background=c[bg],foreground=c[fg],font=font)
        s.configure('TButton',background=c['hover'],foreground=c['text'],padding=(12,8),borderwidth=0,font=(self.font_family,10))
        s.map('TButton',background=[('disabled',c['border']),('active',c['border'])],foreground=[('disabled',c['muted'])])
        for name,key in [('Blue','blue'),('Purple','purple'),('Orange','orange')]:
            s.configure(name+'.TButton',background=c[key],foreground='white',font=(self.font_family,10,'bold'),padding=(14,10))
            s.map(name+'.TButton',background=[('disabled',c['border']),('active',c[key])],foreground=[('disabled',c['muted']),('!disabled','white')])
            s.configure(name+'.Icon.TLabel',background=c['card'],foreground=c[key],font=(self.font_family,27,'bold'))
        s.configure('Nav.TButton',background=c['side'],foreground=c['muted'],anchor='w',padding=(10,12))
        s.map('Nav.TButton',background=[('active',c['hover'])],foreground=[('active',c['text'])])
        s.configure('Active.Nav.TButton',background=c['blue'],foreground='white')
        s.map('Active.Nav.TButton',background=[('active',c['blue'])],foreground=[('active','white')])
        for name in ['TEntry','TCombobox']:
            s.configure(name,fieldbackground=c['input'],foreground=c['text'],insertcolor=c['text'],padding=8,arrowsize=14)
            s.map(name,fieldbackground=[('readonly',c['input']),('disabled',c['bg'])],foreground=[('readonly',c['text']),('disabled',c['muted'])],selectbackground=[('!disabled',c['blue'])],selectforeground=[('!disabled','white')])
        s.configure('TCheckbutton',background=c['card'],foreground=c['text'],padding=4)
        s.map('TCheckbutton',background=[('active',c['card'])],foreground=[('disabled',c['muted'])])
        s.configure('Treeview',background=c['input'],fieldbackground=c['input'],foreground=c['text'],rowheight=32,borderwidth=0)
        s.map('Treeview',background=[('selected',c['blue'])],foreground=[('selected','white')])
        s.configure('Treeview.Heading',background=c['hover'],foreground=c['muted'],font=(self.font_family,9,'bold'),padding=9,relief='flat')
        s.map('Treeview.Heading',background=[('active',c['border'])])
        s.configure('TScrollbar',background=c['border'],troughcolor=c['bg'],borderwidth=0,arrowsize=12)
        self.option_add('*TCombobox*Listbox.background',c['input']);self.option_add('*TCombobox*Listbox.foreground',c['text'])
        def walk(w):
            if isinstance(w,tk.Text):w.configure(bg=c['input'],fg=c['text'],insertbackground=c['text'],selectbackground=c['blue'],selectforeground='white')
            elif isinstance(w,(tk.Frame,tk.Canvas)):w.configure(bg=c['bg'])
            for child in w.winfo_children():walk(child)
        walk(self)
        self.theme_btn.configure(text='☀  Mode clair' if self.mode=='sombre' else '☾  Mode sombre')
        self.draw_art(c)

    def draw_art(self,c):
        a=self.art;a.delete('all');a.configure(bg=c['card'])
        for i in range(6):
            x=12+i*32;a.create_line(x,12,x,155,fill=c['border'])
        for r,col in [(73,c['border']),(65,c['input']),(53,c['hover']),(45,c['input']),(25,c['blue'])]:a.create_oval(113-r,84-r,113+r,84+r,fill=col,outline=c['border'])
        a.create_arc(40,11,186,157,start=25,extent=105,outline=c['blue'],width=4,style='arc')
        a.create_arc(40,11,186,157,start=210,extent=55,outline=c['orange'],width=4,style='arc')
        a.create_text(113,84,text='LBR',fill='white',font=(self.font_family,12,'bold'))
        for i,h in enumerate([9,18,26,13,35,22,11]):a.create_rectangle(4+i*6,160-h,7+i*6,160,fill=c['purple'],outline='')

    def close(self):
        import threading
        if any(t.is_alive() and t is not threading.main_thread() for t in threading.enumerate()):
            messagebox.showwarning('Traitement en cours','Attends la fin du traitement avant de fermer l’application.',parent=self);return
        self.destroy()

if __name__=='__main__':
    LBRManager().mainloop()
