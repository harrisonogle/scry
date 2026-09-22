import sys
from PIL import Image, ImageDraw
SP=sys.argv[1]; run='runs/eval/p4/full-none-r1'
rows=[]
for f,y in [(208,785),(209,783),(211,820),(212,819),(189,836),(202,736),(204,785)]:
    im=Image.open(f'{run}/frames/{f:05d}.png').convert('RGB')
    c=im.crop((650,y-8,1610,y+28)); c=c.resize((c.width*2,c.height*2),Image.LANCZOS)
    lab=Image.new('RGB',(90,c.height),'white'); ImageDraw.Draw(lab).text((5,c.height//2-6),str(f),fill='black')
    row=Image.new('RGB',(90+c.width,c.height)); row.paste(lab,(0,0)); row.paste(c,(90,0)); rows.append(row)
H=sum(r.height+4 for r in rows); W=max(r.width for r in rows)
sheet=Image.new('RGB',(W,H),'red'); y=0
for r in rows: sheet.paste(r,(0,y)); y+=r.height+4
sheet.save(f'{SP}/crops/sheet4.png')
