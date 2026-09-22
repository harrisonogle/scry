import json,re,glob
BASE='<repo>/runs/eval/'
pat=re.compile(r"\bb\d{1,3}\b|(?<!search )(?<!text )(?<!check )(?<!dialog )(?<!combo )(?<!input )(?<!filter )(?<!drop-down )(?<!dropdown )(?<!selection )\bbox(?:es)?\b|\bnumbered\b|\boverlay\b|\bmagenta\b|(?<!link )\btargets?\b|\bannotat|image [12]\b|\bcoordinat|\brectangle|\bx0\b|\breading (?:list|order)\b|\bOCR\b|\bbounding\b|\d{2,4}, ?\d{2,4}, ?\d{2,4}|\bbox ids?\b|\bpixel|\bscrambl|\bthe (?:user|prompt|message)\b|\bscaled\b|\bdetected\b|\bno text\b|\bunlabel|\billegible|\bunreadable|too small", re.I)
for phase,pre in (('p5','d'),('p3','s')):
    n=0; hit=[]
    for d in sorted(glob.glob(BASE+phase+'/*-'+pre+'*-r*')):
        name=d.split('/')[-1]
        if phase=='p3' and not any(x in name for x in ('s100','s067','s050')): continue
        for l in open(d+'/annotations.jsonl'):
            a=json.loads(l); n+=1
            for m in pat.finditer(a['description'] or ''):
                hit.append((name,a['frame'],m.group(0),a['description'][max(0,m.start()-90):m.end()+90].replace('\n',' ')))
    print('==',phase,'descriptions',n,'pattern hits',len(hit))
    for h in hit: print('  ',h)
