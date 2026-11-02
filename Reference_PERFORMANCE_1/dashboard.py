import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageOps

class Dashboard(tk.Canvas):
    def __init__(self,parent,app):
        super().__init__(parent,height=650,highlightthickness=0,bd=0)
        self.app=app;self.photo_source=Image.open(app.asset_path/'dj_banner.png').convert('RGB');self.photo=None;self._job=None
        self._layout_key=None;self._metric_items={};self._photo_size=None
        self._canvas_palette=None;self._icon_items={}
        self.buttons={k:ttk.Button(self,text='Ouvrir '+v[1]+'  ›',style=v[4]+'.TButton',command=lambda key=k:app.show_page(key)) for k,v in app.engines.items()}
        self.workflow=ttk.Button(self,text='▶  Préparer le parcours',style='Green.TButton',command=lambda:app.show_page('Parcours'))
        self.bind('<Configure>',self.queue_draw)
    def queue_draw(self,e=None):
        if not self.winfo_ismapped():return
        if self._job:self.after_cancel(self._job)
        self._job=self.after(16,self.draw)
    def round(self,x,y,w,h,fill,outline,r=12):
        return self.create_polygon(x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y,fill=fill,outline=outline,smooth=True,splinesteps=24)
    def text(self,x,y,text,size=10,color=None,bold=False,width=None,anchor='nw'):
        return self.create_text(x,y,text=text,tags=('copy',),fill=color or self.c['text'],font=(self.app.font_family,size,'bold' if bold else 'normal'),anchor=anchor,width=width or 0)
    def icon(self,x,y,name,color,size=42):
        item=self.create_image(x,y,image=self.app.skin.icon(name,color,size),anchor='nw')
        self._icon_items[item]=(name,color,size)
    def recolor(self,new_colors):
        old=self._canvas_palette
        remap={value:new_colors[key] for key,value in old.items()}
        for item in self.find_all():
            kind=self.type(item)
            options=('fill',) if kind=='text' else ('fill','outline') if kind in ('polygon','oval','rectangle','line') else ()
            updates={}
            for option in options:
                value=self.itemcget(item,option)
                if value in remap and value!=remap[value]:updates[option]=remap[value]
            if updates:self.itemconfigure(item,**updates)
        for item,(name,color,size) in tuple(self._icon_items.items()):
            updated=remap.get(color,color)
            if updated!=color:
                self.itemconfigure(item,image=self.app.skin.icon(name,updated,size))
                self._icon_items[item]=(name,updated,size)
        self.configure(bg=new_colors['bg']);self._canvas_palette=dict(new_colors)
    def draw(self):
        self._job=None
        if not self.winfo_exists() or not self.winfo_ismapped():return
        self.c=c=self.app.colors;w=max(400,self.winfo_width()-2)
        key=(w,self.app.mode)
        if self._layout_key and w==self._layout_key[0]:
            if key!=self._layout_key:
                self.recolor(c);self._layout_key=key
            for engine,items in self._metric_items.items():
                for item,(_,value) in zip(items,self.app.metric_values(engine)):
                    value=str(value)
                    if self.itemcget(item,'text')!=value:self.itemconfigure(item,text=value)
            return
        self._layout_key=key;self._metric_items={};self._icon_items={};self._canvas_palette=dict(c)
        self.configure(bg=c['bg']);self.delete('all')
        # The photo is a real local asset; typography stays selectable/rendered by Tk.
        h=174
        if self._photo_size!=(int(w),h):
            self.photo=ImageTk.PhotoImage(ImageOps.fit(self.photo_source,(int(w),h),centering=(.5,.5)),master=self)
            self._photo_size=(int(w),h)
        self.create_image(0,0,image=self.photo,anchor='nw',tags=('banner',))
        self.text(24,23,'LBR DJ LIBRARY MANAGER',10,'#4288ff',True)
        title='Ton environnement DJ, au même endroit.'
        if w<850:title='Ton environnement DJ,\nau même endroit.'
        self.text(24,53,title,21 if w>1050 else 18,'#f7f9ff',True,width=w-42)
        self.text(24,112 if w>850 else 117,'Organise, synchronise et garde tes bibliothèques à jour.\nRekordbox et Serato, avec tes propres règles et ta structure.',10,'#b6c8e3',width=max(320,w*.58))
        y=188;gap=14;cols=2 if w>=880 else 1;cw=(w-gap*(cols-1))/cols;ch=218
        for i,(key,(_,title,desc,version,color)) in enumerate(self.app.engines.items()):
            x=(i%cols)*(cw+gap);cy=y+(i//cols)*(ch+gap);accent=c[color.lower()]
            self.round(x,cy,cw,ch,c['card'],c['border']);self.icon(x+15,cy+17,{'RekordSync':'sync','MusicGenre':'music','Serato':'transfer','TagStudio':'disc'}[key],accent,40)
            short='Serato Sync' if key=='Serato' and cw<365 else title
            self.text(x+67,cy+18,short,12,bold=True)
            self.text(x+67,cy+42,'v'+version if not version.startswith('FINAL') else version,8,c['green'],True)
            self.text(x+15,cy+73,desc,9,c['muted'],width=cw-30)
            values=self.app.metric_values(key)
            self._metric_items[key]=[]
            sw=(cw-38)/3
            for n,(lab,val) in enumerate(values):
                sx=x+13+n*(sw+6)
                self.round(sx,cy+111,sw,53,c['input'],c['input'],8)
                self.text(sx+9,cy+120,lab,8,c['muted'])
                self._metric_items[key].append(self.text(sx+9,cy+139,str(val),12,bold=True))
            b=self.buttons[key];b.configure(text='Ouvrir '+('Serato Sync' if key=='Serato' and cw<365 else title)+'  ›')
            self.create_window(x+14,cy+176,window=b,anchor='nw',width=cw-28,height=32)
        y+=((len(self.app.engines)+cols-1)//cols)*(ch+gap)
        self.round(0,y,w,73,c['warnbg'],c['warn']);self.icon(16,y+16,'warning','#7c5418',39)
        self.text(69,y+14,'WAV — MARQUEURS NON PRIS EN CHARGE',11,c['warn'],True)
        self.text(69,y+37,'Les WAV fonctionnent dans les crates Serato. Les Hot Cues / Saved Loops WAV sont ignorés.',9,c['text'],width=w-90)
        y+=87;wh=250 if w>=880 else 330
        self.round(0,y,w,wh,c['card'],c['border']);self.icon(16,y+17,'db',c['green'],39)
        self.text(70,y+17,'MISE À JOUR COMPLÈTE',12,bold=True)
        self.text(70,y+42,'Ton parcours de préparation, étape par étape.',9,c['muted'],width=w-340)
        self.create_window(w-218,y+20,window=self.workflow,anchor='nw',width=200,height=34)
        steps=[('MusicGenre','Genre et année','purple'),('Tag Studio','Tags et pochettes','green'),('RekordSync','Bibliothèque & playlists','blue'),('Serato Sync','Crates & marqueurs','orange'),('Vérification','Diagnostic et journal','green')]
        ncols=3 if w>=880 else 2;sw=(w-32-(ncols-1)*12)/ncols
        for i,(title,desc,col) in enumerate(steps):
            sx=16+(i%ncols)*(sw+12);sy=y+76+(i//ncols)*81
            self.round(sx,sy,sw,65,c['input'],c['border'],9)
            self.create_oval(sx+11,sy+17,sx+39,sy+45,fill=c[col],outline='')
            self.text(sx+25,sy+31,str(i+1),10,'white',True,anchor='center')
            self.text(sx+49,sy+14,title,10,bold=True,width=sw-56)
            self.text(sx+49,sy+35,desc,8,c['muted'],width=sw-56)
        self.tag_lower('banner')
        self.after_idle(self.tag_raise,'copy')
        self.configure(height=y+wh+4)
