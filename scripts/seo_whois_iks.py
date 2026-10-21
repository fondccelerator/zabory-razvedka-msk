"""Этап seo, шаг 4: дата регистрации домена (who.is) и ИКС + знаки Яндекса (webmaster.yandex.ru/siteinfo).
Выход: raw_seo/whois_iks.json. Пауза 1.5 с."""
import re, json, time, sys
import requests

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'}
DOMS = sys.argv[1:]
out = {}
s = requests.Session()
for d in DOMS:
    rec = {'date': time.strftime('%Y-%m-%d')}
    reg = '.'.join(d.split('.')[-2:])
    try:
        time.sleep(1.5)
        r = s.get(f'https://who.is/whois/{reg}', headers=UA, timeout=40)
        t = r.text.replace('\\n', '\n')
        m = re.search(r'(?:created|Creation Date):\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', t, re.I)
        rec['whois_created'] = m.group(1) if m else ''
        m2 = re.search(r'registrar:\s*([A-Z0-9\-\. ]+?)\s*\n', t)
        rec['whois_registrar'] = m2.group(1).strip() if m2 else ''
        m3 = re.search(r'paid-till:\s*([0-9\-]{10})', t)
        rec['whois_paid_till'] = m3.group(1) if m3 else ''
        rec['whois_src'] = f'https://who.is/whois/{reg}'
    except Exception as e:
        rec['whois_error'] = str(e)
    try:
        time.sleep(1.5)
        u = f'https://webmaster.yandex.ru/siteinfo/?site={d}'
        r = s.get(u, headers=UA, timeout=40)
        t = r.text
        rec['iks_src'] = u
        if 'captcha' in r.url or 'showcaptcha' in t[:5000]:
            rec['iks'] = 'капча'
        else:
            m = re.search(r'"quality":\{(.*?)\},"noticesCounter"', t)
            if m:
                q = m.group(1)
                sq = re.search(r'"sqi":(\d+)', q)
                rec['iks'] = int(sq.group(1)) if sq else ''
                ach = re.findall(r'\{([^{}]*?"type":"([A-Z_]+)"[^{}]*?)\}', q)
                rec['achievements'] = []
                for body, typ in ach:
                    if typ == 'SQI':
                        continue
                    v = re.search(r'"value":([0-9.]+)', body)
                    rec['achievements'].append(typ + (f'={v.group(1)}' if v else ''))
                hn = re.search(r'"hostName":"([^"]+)"', q)
                rec['iks_host'] = hn.group(1) if hn else ''
            else:
                rec['iks'] = 'не найдено в ответе'
    except Exception as e:
        rec['iks_error'] = str(e)
    out[d] = rec
    print(d, rec.get('whois_created'), rec.get('iks'), rec.get('achievements'))
json.dump(out, open('/home/claude/zabory/raw_seo/whois_iks.json', 'w'), ensure_ascii=False, indent=1)
