import sys
from PIL import Image
SP=sys.argv[1]; run='runs/eval/p4/full-none-r1'
im=Image.open(f'{run}/frames/00213.png').crop((650,755,1610,860)); im=im.resize((im.width*2,im.height*2),Image.LANCZOS); im.save(f'{SP}/crops/f213.png')
