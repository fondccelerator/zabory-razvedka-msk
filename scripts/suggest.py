import sys,subprocess,json,urllib.parse
for q in sys.argv[1:]:
    u='https://suggest.yandex.ru/suggest-ff.cgi?srv=morda_ru_desktop&lr=213&uil=ru&part='+urllib.parse.quote(q)
    s=subprocess.run(['curl','-sL','-m','15','-A','Mozilla/5.0',u],capture_output=True,text=True).stdout
    try:
        d=json.loads(s); sug=[x if isinstance(x,str) else x[1] if isinstance(x,list) and len(x)>1 else str(x) for x in d[1]]
    except Exception as e:
        sug=['ERR '+s[:80]]
    print(q,'=>',' | '.join(sug[:10]))
