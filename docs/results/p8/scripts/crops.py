import json, sys
from PIL import Image, ImageDraw
SP=sys.argv[1]
run='runs/eval/p4/full-none-r1'
B={}
for l in open(f'{run}/boxes.jsonl'):
    d=json.loads(l); B[d['frame']]=d['boxes']
frames=[155,157,161,162,163,165,166,167,168,172,173,174,175,176,178,179,185,189,190,191,192,193,194,195,196,197,199,200,205,206,207]
rows=[]
for f in frames:
    ps=[b for b in B[f] if 'msadmin>' in b['text']]
    last=max(ps,key=lambda b:b['bbox'][1])
    x0,y0,x1,y1=last['bbox']
    im=Image.open(f'{run}/frames/{f:05d}.png').convert('RGB')
    c=im.crop((650,y0-6,1610,y1+6))
    c=c.resize((c.width*2,c.height*2),Image.LANCZOS)
    lab=Image.new('RGB',(90,c.height),'white'); ImageDraw.Draw(lab).text((5,c.height//2-6),str(f),fill='black')
    row=Image.new('RGB',(90+c.width,c.height)); row.paste(lab,(0,0)); row.paste(c,(90,0))
    rows.append(row)
for i in range(0,len(rows),8):
    grp=rows[i:i+8]
    H=sum(r.height+4 for r in grp); W=max(r.width for r in grp)
    sheet=Image.new('RGB',(W,H),'red'); y=0
    for r in grp:
        sheet.paste(r,(0,y)); y+=r.height+4
    sheet.save(f'{SP}/crops/sheet{i//8}.png')
print('ok')
