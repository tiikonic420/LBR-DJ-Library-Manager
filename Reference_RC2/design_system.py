"""Rounded native widgets and vector icons; no business logic."""
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

class Skin:
    def __init__(self,app):self.app=app;self.images={};self.icons={}
    def patch(self,name,fill,border=None,radius=9):
        if name in self.images:return self.images[name]
        scale=3;im=Image.new('RGBA',(120,120));d=ImageDraw.Draw(im)
        d.rounded_rectangle((1,1,118,118),radius=radius*scale,fill=fill,outline=border or fill,width=3)
        im=im.resize((40,40),Image.Resampling.LANCZOS)
        self.images[name]=ImageTk.PhotoImage(im,master=self.app)
        return self.images[name]
    def apply(self,c):
        s=self.app.style
        for role,key in [('Panel','card'),('Inset','input'),('Warning','warnbg')]:
            name='Studio'+self.app.mode+role;image=self.patch(name,c[key],c['border'] if role!='Warning' else c['warn'])
            if name not in s.element_names():s.element_create(name,'image',image,border=13,sticky='nsew')
            s.layout(role+'.TFrame',[(name,{'sticky':'nsew'})]);s.configure(role+'.TFrame',background=c[key])
        roles={'TButton':('hover','border'),'Blue.TButton':('blue','blue'),'Purple.TButton':('purple','purple'),'Orange.TButton':('orange','orange'),'Green.TButton':('green','green'),'Nav.TButton':('side','side'),'Active.Nav.TButton':('blue','blue')}
        for idx,(style,(bg,border)) in enumerate(roles.items()):
            name='StudioButton'+self.app.mode+str(idx)
            im=self.patch(name,c[bg],c[border]);hover=self.patch(name+'Hover',c[bg] if bg not in ('hover','side') else c['hover'],c['blue'] if bg in ('hover','side') else c[bg])
            disabled=self.patch(name+'Disabled',c['input'],c['border']);focus=self.patch(name+'Focus',c[bg],c['text'])
            if name not in s.element_names():s.element_create(name,'image',im,('disabled',disabled),('active',hover),('focus',focus),border=10,padding=0,sticky='nsew')
            s.layout(style,[(name,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
            fg='white' if bg in ('blue','purple','orange','green') else c['text']
            s.configure(style,background=c['card'],foreground=fg,padding=(13,7),borderwidth=0)
            s.map(style,foreground=[('disabled',c['muted']),('!disabled',fg)])
        s.configure('Nav.TButton',background=c['side'],anchor='w',padding=(10,9),foreground=c['muted'])
        s.configure('Active.Nav.TButton',background=c['side'],anchor='w',padding=(10,9))
        for name in ['TEntry','TCombobox']:
            s.configure(name,bordercolor=c['border'],lightcolor=c['border'],darkcolor=c['border'])
            s.map(name,bordercolor=[('focus',c['blue'])],lightcolor=[('focus',c['blue'])],darkcolor=[('focus',c['blue'])])
        s.configure('Horizontal.TProgressbar',background=c['green'],troughcolor=c['input'],borderwidth=0,thickness=5)
        s.configure('Inset.TLabel',background=c['input'],foreground=c['muted'])
        s.configure('Good.TLabel',background=c['card'],foreground=c['green'],font=(self.app.font_family,9,'bold'))
        s.configure('Big.TLabel',background=c['card'],foreground=c['text'],font=(self.app.font_family,17,'bold'))
        s.configure('BlueText.TLabel',background=c['card'],foreground='#78aaff' if self.app.mode=='sombre' else c['blue'],font=(self.app.font_family,10,'bold'))
    def icon(self,name,color,size=40,tile=True):
        key=(name,color,size,tile)
        if key in self.icons:return self.icons[key]
        k=4;im=Image.new('RGBA',(size*k,size*k));d=ImageDraw.Draw(im);S=size*k
        if tile:d.rounded_rectangle((0,0,S-1,S-1),radius=S*.22,fill=color)
        stroke='white' if tile else color
        def line(points,width=2.3):d.line([(x*S/32,y*S/32) for x,y in points],fill=stroke,width=max(2,int(width*S/32)),joint='curve')
        def ellipse(box,fill=None,width=2):d.ellipse(tuple(v*S/32 for v in box),fill=fill,outline=stroke,width=max(2,int(width*S/32)))
        if name=='home':
            line([(6,15),(16,6),(26,15)]);line([(9,14),(9,26),(23,26),(23,14)]);line([(14,26),(14,19),(18,19),(18,26)])
        elif name=='music':
            line([(13,23),(13,9),(24,7),(24,21)]);line([(13,13),(24,11)])
            ellipse((7,21,14,26),stroke);ellipse((18,19,25,24),stroke)
        elif name=='sync':
            d.arc((7*S/32,7*S/32,25*S/32,25*S/32),35,205,fill=stroke,width=int(2.3*S/32));d.arc((7*S/32,7*S/32,25*S/32,25*S/32),215,385,fill=stroke,width=int(2.3*S/32));line([(5,10),(7,17),(13,14)]);line([(19,18),(25,15),(27,22)])
        elif name=='transfer':line([(6,11),(25,11),(20,6)]);line([(26,21),(7,21),(12,26)])
        elif name=='folder':line([(6,10),(6,25),(26,25),(26,12),(17,12),(14,8),(6,8),(6,10)])
        elif name=='play':d.polygon([(12*S/32,7*S/32),(25*S/32,16*S/32),(12*S/32,25*S/32)],fill=stroke)
        elif name=='gear':
            import math
            for i in range(8):
                a=i*math.pi/4;line([(16+8*math.cos(a),16+8*math.sin(a)),(16+12*math.cos(a),16+12*math.sin(a))],4)
            ellipse((8,8,24,24),stroke);d.ellipse((12*S/32,12*S/32,20*S/32,20*S/32),fill=color if tile else '#101927')
        elif name=='db':
            for y in [10,16,22]:d.arc((7*S/32,(y-4)*S/32,25*S/32,(y+4)*S/32),0,180,fill=stroke,width=int(2*S/32))
            ellipse((7,6,25,14));line([(7,10),(7,22)]);line([(25,10),(25,22)])
        elif name=='warning':
            d.polygon([(16*S/32,5*S/32),(29*S/32,27*S/32),(3*S/32,27*S/32)],fill=stroke);d.line([(16*S/32,12*S/32),(16*S/32,19*S/32)],fill=color,width=int(2*S/32));d.ellipse((15*S/32,22*S/32,17*S/32,24*S/32),fill=color)
        else:ellipse((6,6,26,26));ellipse((13,13,19,19),stroke)
        photo=ImageTk.PhotoImage(im.resize((size,size),Image.Resampling.LANCZOS),master=self.app);self.icons[key]=photo;return photo
