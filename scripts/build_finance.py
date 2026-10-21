# Сборка data/finance.csv, data/legal.csv, data/gov_contracts.csv
# Вход: notes/raw_finance/finance_raw.json (ГИР БО, выписки ЕГРЮЛ, карточки zachestnyibiznes, снятые 20.10.2026)
import csv, json, re, sys

BASE = '/home/claude/zabory/'
D = json.load(open(BASE + 'notes/raw_finance/finance_raw.json'))
FIN, EG, EGROW, Z = D['fin'], D['eg'], D['egrow'], D['z']
DATE = '20.10.2026'

# domain, роль в разведке, ИНН (или ОГРНИП для поиска), форма, краткое имя, где подтверждено на сайте
COMP = [
 ('masterovit.ru', 'полный разбор', '5027164485', 'ООО', 'ООО «Мастеровит»', 'https://masterovit.ru/contact/ (реквизиты), /privacy_policy/'),
 ('masterovit.ru (связанное юрлицо)', 'связанная компания', '9721175878', 'ООО', 'ООО «Мастеровит Руф»', 'на сайте не указано; связь по ЕГРЮЛ (общий директор и участники)'),
 ('prof-zabory.ru + sales.prof-zabory.ru', 'полный разбор', '112103967667', 'ИП', 'ИП Коротков К. А.', 'https://prof-zabory.ru/ (подвал: ИНН 112103967667, ОГРНИП 319762700025982)'),
 ('zaborkin.ru', 'полный разбор', '9724131759', 'ООО', 'ООО «Первый строительный»', 'https://zaborkin.ru/contacts/ (реквизиты)'),
 ('zavodzaborov.ru + zabor-dlya-vseh.site', 'полный разбор', '7720405275', 'ООО', 'ООО «Мособлстрой»', 'https://zabor-dlya-vseh.site/privacy-policy.html (оператор ООО «МОСОБЛСТРОЙ», ИНН 7720405275); zavodzaborov.ru — реквизиты подгружаются скриптом, в HTML не найдены'),
 ('raduga-zaborov.ru', 'полный разбор', '774318900413', 'ИП', 'ИП Смирнов М. И.', 'https://raduga-zaborov.ru/ (подвал: ИНН 774318900413)'),
 ('zaborovo.ru + p-z-z.ru', 'полный разбор', '5038104294', 'ООО', 'ООО «Заборово»', 'https://zaborovo.ru/ (подвал: ИНН, КПП, ОГРН); https://p-z-z.ru/ (© ООО «Заборово»)'),
 ('oblzabor.ru', 'полный разбор', '502719578856', 'ИП', 'ИП Толмачёв Е. Н.', 'https://oblzabor.ru/company/requisites/'),
 ('dostup-zabor.ru', 'полный разбор', '443001116031', 'ИП', 'ИП (ИНН 443001116031)', 'https://dostup-zabor.ru/ (подвал: ИНН 443001116031, ОГРН 313443605200020; в тексте сайта — «ООО «Доступные заборы», такое ООО в ГИР БО не найдено)'),
 ('zaboroff.ru', 'полный разбор', '9709008831', 'ООО', 'ООО «ЗАБОРОФФ»', 'https://zaboroff.ru/ (подвал и маркировка рекламы: ИНН 9709008831, ОГРН 1177746882840)'),
 ('pskzabor.ru', 'полный разбор', '5031149240', 'ООО', 'ООО «Строймонтаж 2015»', 'https://pskzabor.ru/ (подвал: ИНН 5031149240, ОГРН 1225000145810)'),
 ('zabormo.ru', 'облегчённо', '504108626267', 'ИП', 'ИП Савка В. М. (бренд «Про Ограда»)', 'https://zabormo.ru/ (подвал: ИНН 504108626267, ОГРНИП 326774600346870)'),
 ('pro-zabor.ru', 'облегчённо', '9725115069', 'ООО', 'ООО «ПРО-СТРОЙ»', 'https://pro-zabor.ru/ (шапка: ИНН 9725115069, ОГРН 1237700123418)'),
 ('moscow.kupitzabor.ru', 'облегчённо', '304026403400040', 'ИП', 'ИП Юскин А. Р. («КупитьЗабор.ру»)', 'https://moscow.kupitzabor.ru/ (подвал: ОГРНИП 304026403400040; ИНН 026411051284 по реестру)'),
 ('33zabora.ru', 'облегчённо', '502704675286', 'ИП', 'ИП Торопов С. Ю.', 'https://33zabora.ru/upload/politika_obrabotki_personalnykh_dannykh.pdf'),
 ('zabor-vam.ru', 'облегчённо', '502757963714', 'ИП', 'ИП Северин В. В.', 'https://zabor-vam.ru/company/requisites/'),
 ('good-zabor.ru', 'облегчённо', '7838091834', 'ООО', 'ООО «СТРОЙ-ЦЕНТР»', 'https://good-zabor.ru/klientam/rekvizity/'),
 ('moskovskie-zabory.ru', 'облегчённо', '7743360119', 'ООО', 'ООО «СВ Компани»', 'https://moskovskie-zabory.ru/ (подвал: © 2025 ООО «СВ Компани», ИНН на сайте нет)'),
 ('ligazaborov.ru', 'облегчённо', '502413692054', 'ИП', 'ИП Гончар Ю. А.', 'https://ligazaborov.ru/ (подвал: ИНН 502413692054)'),
 ('zabory-deshevo.ru', 'облегчённо', '', 'не установлено', 'ООО «Заборы Дешево» (по тексту политики)', 'https://zabory-deshevo.ru/kontakty/ — ИНН/ОГРН на сайте нет; ООО с таким названием в ГИР БО и ЕГРЮЛ не найдено'),
 ('gorodzaborov.ru', 'облегчённо', '7733221469', 'ООО', 'ООО «Строй Модуль»', 'https://gorodzaborov.ru/ (подвал: ООО «СтройМодуль», ИНН 7733221469)'),
 ('alusys.ru', 'ворота', '7731284167', 'ООО', 'ООО «ПК АЛЮСИС»', 'https://alusys.ru/ (блок «О компании»: ИНН 7731284167, ОГРН 1157746495092)'),
 ('vorota750.ru', 'ворота', '504903820510', 'ИП', 'ИП Смирнов В. В.', 'https://vorota750.ru/kontakty'),
 ('naves-pod-avto-msk.ru', 'ворота', '463234585568', 'ИП', 'ИП Бересняков Р. В.', 'https://naves-pod-avto-msk.ru/kontakt'),
 ('otkatnie-vorota.com', 'ворота', '', 'не установлено', 'не указано', 'главная и /zakon-rf-o-personalnyix-dannyix.html — юрлицо, ИНН, ОГРН не указаны'),
 ('gruppa-masterov.ru', 'ворота', '366221844803', 'ИП', 'ИП Солопихин С. И.', 'https://gruppa-masterov.ru/about/politika-konf/ (ИП Солопихин С. И.; ИНН — по таблице команды и реестру)'),
 ('metalsystems.ru', 'ворота', '5074072922', 'ООО', 'ООО «Металлические системы»', 'https://metalsystems.ru/kontakty/ (ОГРН 1215000132820, ИНН 5074072922)'),
 ('zabory-prestige.ru', 'ворота', '490916193013', 'ИП', 'ИП Кречун Д. А.', 'https://zabory-prestige.ru/soglasie-na-obrabotku-personalnykh-dannykh (ИНН 490916193013, ОГРНИП 323508100105962)'),
 ('atlantzabor.ru', 'ворота', '7725395704', 'ООО', 'ООО «СУ-8»', 'https://atlantzabor.ru/politika-konfidencialnosti/ (оператор ООО «СУ-8»; ИНН — по таблице команды и ГИР БО)'),
 ('moskovskie-zabory.ru (предшественник)', 'связанная компания', '7720382660', 'ООО', 'ООО «М-ЗАБОР»', 'на сайте не указано; связь по ЕГРЮЛ (тот же участник и бывший директор, что у ООО «СВ Компани»)'),
]

GROUP = {
 '5027164485': 'Группа «Мастеровит»: ООО «Мастеровит» и ООО «Мастеровит Руф» (ИНН 9721175878) — общий генеральный директор Сибгатулин Р. К. и общие участники (Сибгатулин Р. К., Петухов П. В., Хухлей В. Н., Отлётов Д. Г.). Те же участники — в ООО «Мастеровит СПБ» (ИНН 7805820136, создано 17.12.2024; выручка 2025 — 250,2 млн ₽), ООО «Мастеровит СПБ» (ИНН 7842469389, 2012; выручка упала с 210,5 млн ₽ в 2024 до 11,0 млн ₽ в 2025 — оборот перешёл на новое юрлицо), ООО «Парус» (ИНН 7714943243, Раменское, 25.11; выручка 2025 — 76,3 млн ₽), ООО «Ханфорт» (ИНН 9721269710, создано 31.08.2026). Ликвидирован предшественник в Воронеже — ООО «Мастеровит ВРН» (ИНН 3662242254).',
 '9721175878': 'См. ООО «Мастеровит»: тот же директор, участники Сибгатулин Р. К. 45,1%, Петухов П. В. 42,9%, Хухлей В. Н. 6%, Отлётов Д. Г. 6%.',
 '7720405275': 'Участник 90% Панченко Т. В. также генеральный директор и участник ООО «ЦЕНТРЗАБОРОВ» (ИНН 7720824942, 2014, ОКВЭД 47.52; выручка 88,1 млн ₽ в 2021 → 4,7 млн ₽ в 2023 → 0 в 2024 — вероятный предшественник по продажам заборов, оценка). Панченко Т. В. и Сушков Е. В. — участники ООО «ЗЗ-НН» (ИНН 5258147744, Нижний Новгород, 25.11; выручка 2025 — 38,7 млн ₽). Второй сайт zabor-dlya-vseh.site оформлен на это же ООО.',
 '5038104294': 'Один участник и директор Чернецкий И. Б.; других юрлиц у него в реестре нет, есть действующий ИП. Второй сайт p-z-z.ru оформлен на это же ООО.',
 '7743360119': 'Участник 100% и директор Власов Сержиу А. — также участник 100% ООО «М-ЗАБОР» (ИНН 7720382660, 2017, ОКВЭД 25.11; признано банкротом, конкурсное производство; выручка 192,9 млн ₽ в 2023 → 94,3 млн ₽ в 2024; исполнительных производств 85 на 12,2 млн ₽, остаток долга 10,5 млн ₽). Сайт moszabory.ru оформлен на ИП Власов А. А. (ИНН 775101365032, ИП с 07.03.2024, ОКВЭД 49.41), он же участник ООО «ЗМК» (ИНН 7751151743, 2018, отчётности в ГИР БО нет) и бывший директор и участник ООО «Столичные заборы» (ИНН 7706419702, ликвидировано). Совпадение фамилии и отчества с владельцем ООО «СВ Компани» — родство по открытым данным не подтверждено.',
 '7720382660': 'См. ООО «СВ Компани»: тот же участник 100%; по сведениям ЕГРЮЛ на 20.10.2026 — банкротство, конкурсный управляющий.',
 '9709008831': 'Директор и участник 100% Каширин О. В. также руководит ООО «Завод металлоконструкций №1» (ИНН 5018156784) и ООО «Строймонтажкомплект» (ИНН 7707616573); у обоих выручки в ГИР БО за 2021–2025 нет (нулевая отчётность).',
 '5031149240': 'Директор и участник 100% Зиновьев М. И. также руководит ООО «СТАЛЬТЭКМОНТАЖ» (ИНН 5029293165, создано 13.05.2025, Мытищи, ОКВЭД 46.90; выручка 2025 — 4,2 млн ₽, убыток 1,0 млн ₽).',
 '9724131759': 'Директор и участник 100% Павлов А. С.; ранее руководил ООО «Стройдизайнторг» (ИНН 7814616200, ликвидировано).',
 '9725115069': 'Участники Парван Г. и Жунку С. Ф. по 50%; Жунку С. Ф. ранее руководил ООО «Мисс-Стиль» (ИНН 7721248321, ликвидировано).',
 '7838091834': 'Участники Бабаев П. В. и Братухин И. А. по 50%; Бабаев П. В. также руководит ООО «Стройстандарт» (ИНН 9723124815, ОКВЭД 41.20; выручка 2025 — 85,5 млн ₽). Юрадрес в Санкт-Петербурге.',
 '7731284167': 'Участники Алексеев Ю. С. 51%, Апроцкий К. А. 49% (директор). У директора ликвидированы ООО «Алюсис» (ИНН 5032239760), ООО «Алюсис Групп» (ИНН 5032251126), ООО «Поселки 24» (ИНН 5032254110); по ООО «Алюминиевые системы» (ИНН 7731466858) регистрация признана недействительной (по карточке zachestnyibiznes).',
 '7733221469': 'Директор и участник 100% Черкез А. В.; других юрлиц в реестре нет.',
 '5074072922': 'Директор и участник 100% Деминский Д. Н.; других юрлиц в реестре нет.',
 '7725395704': 'Директор и участник 100% Бежан С. М.; других юрлиц в реестре нет.',
 '504108626267': 'ИП зарегистрировано 12.05.2026; у того же лица два прекращённых ИП (2017 и 30.03.2022), на сайте указано «© 2010–2026 Компания «Про Ограда»» — бизнес старше текущего ИП.',
 '502704675286': 'ИП зарегистрировано 18.02.2025; у того же лица два прекращённых ИП (в т. ч. 19.12.2022, ОКВЭД 47.91); счётчик Яндекс Метрики сайта 15030409 — сайт значительно старше ИП (оценка).',
 '304026403400040': 'ИП зарегистрировано 03.02.2004 в Республике Башкортостан, основной ОКВЭД 24.33 (холодная гибка профилей): производитель с московским сайтом-витриной.',
 '112103967667': 'ИП зарегистрировано 30.04.2019 в Ярославской области; на сайте «© 2017». Владелец ИП — участник ООО «Диван и кальян» (ИНН 9724218791) — к заборам не относится.',
 '443001116031': 'ИП зарегистрировано 21.02.2013 в Костромской области; на сайте упоминается «ООО «Доступные заборы», такого ООО в ГИР БО нет.',
}

def num(v):
    return None if v in (None, '') else float(v)

def sschr(q):
    h = Z.get(q, {}).get('sschr_hist', '')
    return {int(y): int(n) for y, n in re.findall(r'(\d{4}) (\d+) ', h + ' ')}

SPECIAL = {
 ('5038104294', '2025'): 'расходы по обычной деятельности (187,8 млн ₽) выше выручки (159,5 млн ₽); прибыль получена за счёт прочих доходов 42,3 млн ₽',
 ('7733221469', '2025'): 'расходы по обычной деятельности выше выручки на 0,1 млн ₽; прибыль за счёт прочих доходов 1,0 млн ₽',
 ('9725115069', '2025'): 'часть расходов (22,3 млн ₽) отражена как прочие расходы — доля строки 2120 несопоставима с прошлым годом',
 ('7720382660', '2024'): 'в 2026 году признано банкротом',
 ('7842469389', '2025'): 'оборот перешёл на новое ООО «Мастеровит СПБ» (ИНН 7805820136)',
 ('9721175878', '2024'): 'дебиторка по строке 1230 — 0,65 млн ₽',
}
fin_rows = []
FIN_HDR = ['domain', 'company', 'inn', 'role', 'year', 'report_form', 'revenue_th_rub', 'cost_line_2120_th_rub', 'gross_profit_th_rub',
           'sales_profit_th_rub', 'commercial_expenses_th_rub', 'admin_expenses_th_rub', 'other_income_th_rub', 'other_expenses_th_rub', 'net_profit_th_rub', 'receivables_th_rub',
           'receivables_line', 'inventories_th_rub', 'payables_th_rub', 'equity_th_rub', 'total_assets_th_rub', 'borrowings_th_rub',
           'employees_avg', 'net_margin_pct', 'cost_share_pct', 'receivable_days', 'revenue_per_employee_mln_rub',
           'source_finance', 'source_employees', 'date_collected', 'note']

def add_fin(domain, name, inn, role, years=('2023', '2024', '2025')):
    f = FIN.get(inn)
    st = sschr(inn)
    for y in years:
        v = (f or {}).get('years', {}).get(y)
        row = dict(domain=domain, company=name, inn=inn, role=role, year=y, date_collected=DATE,
                   source_finance=f"ГИР БО, https://bo.nalog.gov.ru/organizations-card/{f['girbo_id']}" if f else 'ГИР БО — не найдено',
                   source_employees=(Z.get(inn, {}).get('url', '') + ' (ССЧ по данным ФНС)') if st.get(int(y)) is not None else '')
        row['employees_avg'] = st.get(int(y), '')
        if not v or num(v.get('c2110')) is None and num(v.get('c1600')) in (None, 0):
            row['note'] = 'отчётность за год в ГИР БО не найдена' if not v else 'нулевая отчётность'
            fin_rows.append(row); continue
        full = v.get('knd') == '0710099'
        row['report_form'] = 'полная' if full else 'упрощённая'
        rev = num(v.get('c2110')) or 0.0
        g = lambda k: num(v.get('c' + k))
        row['revenue_th_rub'] = rev
        row['cost_line_2120_th_rub'] = g('2120')
        row['gross_profit_th_rub'] = g('2100') if full else ''
        row['sales_profit_th_rub'] = g('2200') if full else ''
        row['commercial_expenses_th_rub'] = g('2210') if full else ''
        row['admin_expenses_th_rub'] = g('2220') if full else ''
        row['net_profit_th_rub'] = g('2400')
        row['other_income_th_rub'] = g('2340')
        row['other_expenses_th_rub'] = g('2350')
        rec = g('1230')
        line = '1230'
        if rec is None and not full and g('1240') is not None:
            rec, line = g('1240'), '1240'
        row['receivables_th_rub'] = rec
        row['receivables_line'] = ('1230 дебиторская задолженность' if full else
                                   ('1230 финансовые и другие оборотные активы (включая дебиторку)' if line == '1230' else '1240 финансовые и другие оборотные активы (включая дебиторку), форма 2025')) if rec is not None else ''
        row['inventories_th_rub'] = g('1210')
        row['payables_th_rub'] = g('1520')
        row['equity_th_rub'] = g('1300')
        row['total_assets_th_rub'] = g('1600')
        b = [x for x in (g('1410'), g('1510')) if x]
        row['borrowings_th_rub'] = sum(b) if b else ''
        if rev:
            np_ = g('2400')
            row['net_margin_pct'] = round(np_ / rev * 100, 1) if np_ is not None else ''
            c = g('2120')
            row['cost_share_pct'] = round(c / rev * 100, 1) if c is not None else ''
            row['receivable_days'] = round(rec / rev * 365) if rec is not None else ''
            e = st.get(int(y))
            row['revenue_per_employee_mln_rub'] = round(rev / 1000 / e, 1) if e else ''
        notes = []
        if not full: notes.append('упрощённая форма: строка 2120 — все расходы по обычной деятельности, валовой прибыли нет; дебиторка включает прочие оборотные активы')
        if full: notes.append('строка 2120 — себестоимость продаж')
        if (inn, y) in SPECIAL: notes.append(SPECIAL[(inn, y)])
        row['note'] = '; '.join(notes)
        fin_rows.append(row)

for dom, role, inn, form, name, _ in COMP:
    if form == 'ООО':
        add_fin(dom, name, inn, role)
# связанные компании (для групп)
REL = [('masterovit.ru (группа)', 'ООО «Мастеровит СПБ» (новое)', '7805820136'), ('masterovit.ru (группа)', 'ООО «Мастеровит СПБ» (старое)', '7842469389'),
       ('masterovit.ru (группа)', 'ООО «Парус»', '7714943243'), ('zavodzaborov.ru (связь по участнику)', 'ООО «ЦЕНТРЗАБОРОВ»', '7720824942'),
       ('zavodzaborov.ru (связь по участнику)', 'ООО «ЗЗ-НН»', '5258147744'), ('good-zabor.ru (связь по участнику)', 'ООО «Стройстандарт»', '9723124815')]
for dom, name, inn in REL:
    add_fin(dom, name, inn, 'связанная компания')

# сумма группы Мастеровит (Москва): Мастеровит + Мастеровит Руф
for y in ('2023', '2024', '2025'):
    a = next(r for r in fin_rows if r['inn'] == '5027164485' and r['year'] == y)
    b = next(r for r in fin_rows if r['inn'] == '9721175878' and r['year'] == y)
    rev = a['revenue_th_rub'] + b['revenue_th_rub']; np_ = a['net_profit_th_rub'] + b['net_profit_th_rub']
    e = (a['employees_avg'] or 0) + (b['employees_avg'] or 0)
    fin_rows.append(dict(domain='masterovit.ru (группа, расчёт)', company='Группа «Мастеровит» (Мастеровит + Мастеровит Руф)', inn='5027164485+9721175878',
                         role='сумма группы (расчёт)', year=y, report_form='сумма двух отчётов', revenue_th_rub=rev, net_profit_th_rub=np_,
                         receivables_th_rub=a['receivables_th_rub'] + b['receivables_th_rub'], employees_avg=e,
                         net_margin_pct=round(np_ / rev * 100, 1), receivable_days=round((a['receivables_th_rub'] + b['receivables_th_rub']) / rev * 365),
                         revenue_per_employee_mln_rub=round(rev / 1000 / e, 1), source_finance='сумма строк ГИР БО двух ООО', source_employees='сумма ССЧ двух ООО',
                         date_collected=DATE, note='внутригрупповые обороты не исключены — сумма может быть завышена'))

with open(BASE + 'data/finance.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, FIN_HDR); w.writeheader()
    fmt = lambda v: int(v) if isinstance(v, float) and v.is_integer() else v
    for r in fin_rows: w.writerow({k: fmt(r.get(k, '')) for k in FIN_HDR})

# ---------- legal.csv
LEG_HDR = ['domain', 'role', 'legal_form', 'legal_name', 'inn', 'ogrn', 'reg_date', 'status', 'address', 'okved_main', 'director', 'founders',
           'charter_capital_rub', 'tax_regime', 'employees_last', 'financial_reporting', 'site_requisites', 'group_links_predecessors',
           'arbitration', 'enforcement_fssp', 'source', 'date_collected']
OGRNIP = {'112103967667': '319762700025982', '774318900413': '317774600251130', '502719578856': '314502727600047', '443001116031': '313443605200020',
          '504108626267': '326774600346870', '304026403400040': '304026403400040', '502704675286': '325774600112390', '502757963714': '324508100186748',
          '502413692054': '319500700009790', '504903820510': '317505300036852', '463234585568': '317463200034511', '366221844803': '315504700017252',
          '490916193013': '323508100105962'}
CAP = {'5027164485': 19900000, '9721175878': 9900000, '7743360119': 250000, '7838091834': 100000, '7720382660': 5215000}
leg = []
for dom, role, inn, form, name, site in COMP:
    z = Z.get(inn, {})
    r = dict(domain=dom, role=role, legal_form=form, legal_name=name, site_requisites=site, date_collected=DATE)
    if form == 'ООО':
        f = FIN.get(inn, {}); e = EG.get(inn, {}); er = EGROW.get(inn, {})
        r.update(inn=inn, ogrn=f.get('ogrn', ''), reg_date=er.get('reg', z.get('reg', '')),
                 status=('банкротство, конкурсное производство (ЕГРЮЛ)' if 'банкрот' in e.get('state', '') else (z.get('status') or 'Действующее')),
                 address=e.get('addr', '').title().replace('Г.О.', 'г.о.'), okved_main=(z.get('okved', '') + ' ' + z.get('okved_name', '')).strip(),
                 director=re.sub(r'^[А-ЯЁ ]+: ', '', (er.get('ruk') or '').split(',')[-1].strip()).strip() + (' (конкурсный управляющий — по ЕГРЮЛ)' if inn == '7720382660' else ''),
                 founders='; '.join(e.get('founders', [])), charter_capital_rub=CAP.get(inn, 10000),
                 tax_regime=('УСН' if 'Упрощ' in z.get('tax', '') else 'ОСНО (спецрежим не применяется)'),
                 employees_last=(lambda s: f"{s[max(s)]} ({max(s)})" if s else 'не найдено')(sschr(inn)),
                 financial_reporting='ГИР БО: ' + ', '.join(sorted(y for y in f.get('years', {}))),
                 source=f"ЕГРЮЛ (egrul.nalog.ru, выписка {DATE}); ГИР БО; {z.get('url', '')}")
        if inn == '7720382660':
            r['director'] = 'конкурсный управляющий (ЕГРЮЛ); до банкротства — Власов Сержиу Андреевич'
    elif form == 'ИП':
        r.update(inn=('026411051284' if inn == '304026403400040' else inn), ogrn=OGRNIP.get(inn, ''), reg_date=z.get('reg', ''), status='Действующее',
                 address='не публикуется (ИП)', okved_main=(z.get('okved', '') + ' ' + z.get('okved_name', '')).strip(),
                 director='—', founders='—', charter_capital_rub='—',
                 tax_regime={'Не применяется': 'спецрежим в реестре не указан (ОСНО или режим ещё не отражён)'}.get(z.get('tax', ''), z.get('tax', '')),
                 employees_last='нет открытых данных', financial_reporting='ИП, отчётности нет',
                 source=f"карточка ИП на zachestnyibiznes.ru (данные ЕГРИП и ФНС), {DATE}")
        if z.get('region_ip'): r['okved_main'] += f"; регион деятельности по ЕГРИП: {z['region_ip']}"
    else:
        r.update(inn='не найдено', ogrn='не найдено', reg_date='', status='', address='', okved_main='', director='', founders='',
                 tax_regime='', employees_last='', financial_reporting='юрлицо не установлено', source='сайт; ГИР БО и ЕГРЮЛ — поиск по названию без результата')
    cp = z.get('courts_phrase', '')
    m = re.findall(r'(\d+) \(в качестве "(\w+)"\)', cp)
    if cp:
        d = {k: v for v, k in m}
        r['arbitration'] = f"ответчик — {d.get('Ответчика', '0')}, истец — {d.get('Истца', '0')}"
        if z.get('arb_cnt'): r['arbitration'] += f"; всего дел с участием — {z['arb_cnt']}"
    r['enforcement_fssp'] = re.sub(r' Оконченные.*', '', z.get('fssp', '')).strip() or ('нет данных в карточке' if form != 'не установлено' else '')
    r['group_links_predecessors'] = GROUP.get(inn, 'общих участников и директоров с другими компаниями списка не найдено' if form == 'ООО' else ('—' if form == 'ИП' else ''))
    leg.append(r)

# суммы арбитража по карточкам (вручную снятые блоки «Количество / Общая сумма»)
ARB_SUM = {'5027164485': '38 дел на 37,1 млн ₽, на рассмотрении 19,1 млн ₽', '7720382660': '39 дел на 39,1 млн ₽, на рассмотрении 3,2 млн ₽',
           '7720405275': '14 дел на 16,3 млн ₽, на рассмотрении 1,9 млн ₽', '7731284167': '16 дел на 35,5 тыс. ₽', '7733221469': '5 дел на 747,6 тыс. ₽',
           '7743360119': '1 дело на 730 тыс. ₽', '9709008831': '1 дело на 457 тыс. ₽', '9721175878': '1 дело на 13,2 млн ₽ (на рассмотрении)',
           '9724131759': '1 дело на 76,2 тыс. ₽', '5031149240': '1 дело на 2,3 млн ₽ (на рассмотрении)', '5074072922': '1 дело на 248,9 тыс. ₽',
           '304026403400040': '15 дел на 388,2 млн ₽, на рассмотрении 4,7 млн ₽', '502719578856': '1 дело на 60 тыс. ₽ (на рассмотрении)',
           '504903820510': '1 дело на 35,2 тыс. ₽ (завершено)'}
for r in leg:
    k = next((c[2] for c in COMP if c[0] == r['domain']), '')
    if k in ARB_SUM: r['arbitration'] = (r.get('arbitration', '') + '; ' + ARB_SUM[k]).strip('; ')
    if r.get('arbitration'): r['arbitration'] += '; суть дел и стороны скрыты (платный доступ), kad.arbitr.ru блокирует запросы'
with open(BASE + 'data/legal.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, LEG_HDR); w.writeheader()
    for r in leg: w.writerow({k: r.get(k, '') for k in LEG_HDR})

# ---------- gov_contracts.csv
GOV_HDR = ['domain', 'company', 'inn', 'contracts_as_supplier', 'total_as_supplier_rub', 'customers', 'law', 'source', 'date_collected', 'note']
GOV = {'5027164485': (1, 32500), '7725395704': (1, 688900)}
gov = []
for dom, role, inn, form, name, _ in COMP:
    if form == 'ООО':
        n, s = GOV.get(inn, (0, 0))
        gov.append(dict(domain=dom, company=name, inn=inn, contracts_as_supplier=n, total_as_supplier_rub=s,
                        customers=('скрыто (платный доступ); ЕИС zakupki.gov.ru требует выполнения JS, не открылся' if n else '—'),
                        law='44-ФЗ / 223-ФЗ (без разбивки)' if n else '—',
                        source=Z.get(inn, {}).get('url', '') + '/zakupki', date_collected=DATE,
                        note='сумма округлена сервисом до 0,1 тыс. ₽' if n else 'контрактов в качестве поставщика не найдено'))
    elif form == 'ИП':
        gov.append(dict(domain=dom, company=name, inn=inn if inn != '304026403400040' else '026411051284', contracts_as_supplier=0, total_as_supplier_rub=0, customers='—', law='—',
                        source=Z.get(inn, {}).get('url', '').split('_')[0] + ' (раздел «Вопросы и ответы»)', date_collected=DATE,
                        note='ИП не зарегистрирован как участник закупок по 44-ФЗ и 223-ФЗ'))
    else:
        gov.append(dict(domain=dom, company=name, inn='', contracts_as_supplier='', total_as_supplier_rub='', customers='', law='',
                        source='', date_collected=DATE, note='юрлицо не установлено — проверка невозможна'))
with open(BASE + 'data/gov_contracts.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, GOV_HDR); w.writeheader()
    for r in gov: w.writerow(r)
print(len(fin_rows), len(leg), len(gov))
