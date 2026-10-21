# Обезличивание сырых выгрузок Авито (Apify) на месте.
# Листинги: у аккаунтов частных лиц и у аккаунтов компаний с личным именем в названии
#   имя продавца заменяется меткой, ссылка на профиль и хеш-домен удаляются (остаётся seller.key — sha1),
#   в описаниях таких продавцов маскируются имена и телефоны; телефоны маскируются во всех описаниях.
# Профили: у отзывов удаляются author, authorAvatar, images; имена в тексте отзыва и ответа продавца маскируются.
import json, hashlib, re, sys, os
sys.path.insert(0, '/home/claude/zabory/notes/scripts/reviews')
from redact import redact, PHONE, PATR, FIO, FIO2, NAME_RX, SURN  # noqa: E402


def light_redact(t):
    # для текстов компаний: имена сотрудников и телефоны, без маскировки чисел
    t = PHONE.sub('[телефон]', t)
    t = PATR.sub('[отчество]', t)
    t = FIO.sub('[ФИО]', t); t = FIO2.sub('[ФИО]', t)
    t = NAME_RX.sub('[имя]', t)
    t = SURN.sub('[фамилия]', t)
    return t

RAW = '/home/claude/zabory/notes/raw_avito'
FILES = ['zabor_pod_klyuch_msk.json', 'otkatnye_vorota_msk.json', 'ustanovka_zabora_mo.json']
LABELS = os.path.join(RAW, '_seller_labels.json')

FIRST = set('''александр алексей анатолий андрей антон артем артём артур богдан борис вадим валентин валерий василий виктор виталий владимир владислав вячеслав геннадий георгий глеб григорий давид даниил денис дмитрий евгений егор иван игорь илья кирилл константин леонид максим марат михаил никита николай олег павел петр пётр роман руслан семен семён сергей сергеи станислав степан тимофей тимур федор фёдор юрий ярослав саид артак родион alexander artak ivan dmitry sergey andrey'''.split())
EMAIL = re.compile(r'[\w.\-]+@[\w\-]+\.[\w.]+')
TG = re.compile(r'(?<!\w)@[A-Za-z0-9_]{4,}')
HOMO_UP = str.maketrans({'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У',
                         'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у', 'k': 'к', 'm': 'м', 'n': 'п', 'u': 'и', 'r': 'г'})


def clean_text(t):
    def fix(m):
        w = m.group(0)
        return w.translate(HOMO_UP) if (re.search('[А-Яа-яЁё]', w) and re.search('[A-Za-z]', w)) else w
    return re.sub(r'[A-Za-zА-Яа-яЁё]+', fix, t or '')


def is_personal_name(name):
    if not name:
        return True
    n = name.lower().replace('"', ' ')
    if re.match(r'^\s*ип\b', n):
        return True
    words = re.findall(r'[a-zа-яё]+', n)
    return any(w in FIRST for w in words) and len(words) <= 3


def key_of(i):
    base = i.get('seller.key') or i.get('seller.profileUrl') or i.get('seller.domain') or ('noseller-' + str(i['id']))
    if i.get('seller.key'):
        return base
    return hashlib.sha1(base.encode()).hexdigest()[:12]


def main():
    labels = json.load(open(LABELS)) if os.path.exists(LABELS) else {}
    cnt = {'p': sum(1 for v in labels.values() if v['kind'] == 'private'),
           'c': sum(1 for v in labels.values() if v['kind'] == 'company_personal')}
    for f in FILES:
        path = os.path.join(RAW, f)
        d = json.load(open(path))
        for i in d['items']:
            k = key_of(i)
            i['seller.key'] = k
            name = i.get('seller.name')
            private = i.get('userType') != 'company'
            if k not in labels:
                if private:
                    cnt['p'] += 1
                    labels[k] = {'kind': 'private', 'label': f'частный мастер №{cnt["p"]}'}
                elif is_personal_name(name):
                    cnt['c'] += 1
                    labels[k] = {'kind': 'company_personal', 'label': f'компания без названия (личное имя скрыто) №{cnt["c"]}'}
                else:
                    labels[k] = {'kind': 'company', 'label': name}
            lab = labels[k]
            desc = i.get('description') or ''
            if lab['kind'] != 'company':
                desc = clean_text(desc)
                if name:
                    desc = desc.replace(name, '[имя]')
                desc = redact(desc)
                desc = EMAIL.sub('[почта]', desc)
                desc = TG.sub('[ник]', desc)
                i['seller.name'] = lab['label']
                i['seller.profileUrl'] = None
                i['seller.domain'] = None
            else:
                desc = light_redact(clean_text(desc))
            i['description'] = desc
        d['_anonymized'] = 'имена частных лиц и личные имена в названиях заменены метками, телефоны маскированы; 2026-10-21'
        tmp = path + '.tmp'
        json.dump(d, open(tmp, 'w'), ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    # профили
    path = os.path.join(RAW, 'seller_profiles.json')
    d = json.load(open(path))
    for p in d['items']:
        if p.get('about'):
            p['about'] = light_redact(p['about'])
        for it in p.get('showcaseItems') or []:
            if it.get('description'):
                it['description'] = light_redact(clean_text(it['description']))
        for r in p.get('reviews') or []:
            for f in ('author', 'authorAvatar', 'images'):
                r.pop(f, None)
            r['text'] = EMAIL.sub('[почта]', redact(r.get('text') or ''))
            sr = r.get('sellerReply')
            if sr:
                sr['text'] = EMAIL.sub('[почта]', redact(sr.get('text') or ''))
    d['_anonymized'] = 'у отзывов удалены author, authorAvatar, images; имена и телефоны в текстах маскированы; 2026-10-21'
    tmp = path + '.tmp'
    json.dump(d, open(tmp, 'w'), ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    json.dump(labels, open(LABELS, 'w'), ensure_ascii=False, indent=1)
    print('labels', cnt)


if __name__ == '__main__':
    main()
