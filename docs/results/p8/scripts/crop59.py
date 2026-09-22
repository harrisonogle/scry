import json,sys
from PIL import Image
SP=sys.argv[1]; run='runs/eval/p4/full-none-r1'
for l in open(f'{run}/boxes.jsonl'):
    d=json.loads(l)
    if d['frame']==59:
        b=[b for b in d['boxes'] if 'KdeKloud' in b['text']][0]; break
x0,y0,x1,y1=b['bbox']; print(b['bbox'])
im=Image.open(f'{run}/frames/00059.png').crop((x0-200,y0-30,x1+300,y1+30)); im=im.resize((im.width*2,im.height*2),Image.LANCZOS); im.save(f'{SP}/crops/f59.png')
