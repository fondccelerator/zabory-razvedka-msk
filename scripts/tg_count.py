import sys,re,subprocess,html,statistics
ch=sys.argv[1]; since='2026-07-20'
url=f'https://t.me/s/{ch}'; posts={}
for _ in range(30):
    s=subprocess.run(['curl','-sL','-m','20','-A','Mozilla/5.0',url],capture_output=True,text=True).stdout
    blocks=re.split(r'<div class="tgme_widget_message_wrap',s)[1:]
    if not blocks: break
    for b in blocks:
        pid=re.search(r'data-post="[^/]+/(\d+)"',b); d=re.search(r'<time datetime="([^"]+)"',b)
        v=re.search(r'<span class="tgme_widget_message_views">(.*?)</span>',b)
        if pid and d: posts[int(pid.group(1))]=(d.group(1)[:10], v.group(1) if v else '')
    mn=min(posts) if posts else None
    if not posts or min(p[0] for p in posts.values())<since: break
    url=f'https://t.me/s/{ch}?before={mn}'
def num(x):
    x=x.replace(',','.')
    return float(x[:-1])*1000 if x.endswith('K') else float(x or 0)
w=[p for p in posts.values() if p[0]>=since]
vs=[num(p[1]) for p in w if p[1]]
print(ch,'posts_since',since,len(w),'avg_views',round(statistics.mean(vs)) if vs else '', 'median',statistics.median(vs) if vs else '','newest',max(p[0] for p in posts.values()) if posts else '')
