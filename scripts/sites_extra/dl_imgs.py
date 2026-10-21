import subprocess, sys, pathlib, collections, hashlib
from PIL import Image, ImageDraw
OUT=pathlib.Path('/home/claude/zabory/notes/raw_sites/trust_img')
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
groups=collections.OrderedDict()
for l in open(sys.argv[1]):
    if not l.strip(): continue
    g,u=l.split(); groups.setdefault(g,[]).append(u)
per=int(sys.argv[2]) if len(sys.argv)>2 else 4
W=int(sys.argv[3]) if len(sys.argv)>3 else 620
for g,urls in groups.items():
    d=OUT/g; d.mkdir(exist_ok=True); files=[]
    for k,u in enumerate(urls):
        f=d/(f'{k:02d}_'+hashlib.md5(u.encode()).hexdigest()[:6])
        r=subprocess.run(['curl','-sS','-L','--max-time','40','-A',UA,'-o',str(f),'-w','%{http_code}',u],capture_output=True,text=True)
        try:
            im=Image.open(f); im.load(); files.append((k,u,im.convert('RGB')))
        except Exception as e: print('BAD',g,k,u,r.stdout)
    cols=2 if per<=4 else 3
    for s in range(0,len(files),per):
        chunk=files[s:s+per]; ims=[]
        for k,u,im in chunk:
            h=int(im.height*W/im.width); ims.append((k,im.resize((W,h))))
        rows=[ims[i:i+cols] for i in range(0,len(ims),cols)]
        H=sum(max(x[1].height for x in r)+24 for r in rows)
        sheet=Image.new('RGB',(W*cols,H),'white'); y=0; dr=ImageDraw.Draw(sheet)
        for r in rows:
            for c,(k,im) in enumerate(r):
                sheet.paste(im,(c*W,y+24)); dr.text((c*W+5,y+5),f'#{k}',fill='red')
            y+=max(x[1].height for x in r)+24
        p=OUT/f'sheet_{g}_{s//per}.jpg'; sheet.save(p,quality=80); print(p, sheet.size)
