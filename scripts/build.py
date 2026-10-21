"""Сборка рабочих CSV этапа «sites» из разборов notes/sites_parts/*.json + облегчённых и воротных сайтов.
Режет блочные скриншоты из полностраничных. Запуск: python3 -I build.py
"""
import csv, json, glob, os, pathlib
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None

ROOT = pathlib.Path('/home/claude/zabory')
PARTS = ROOT / 'notes' / 'sites_parts'
RAW = ROOT / 'notes' / 'raw_sites'
IMG = ROOT / 'img' / 'sites'
BLK = IMG / 'blocks'
BLK.mkdir(exist_ok=True)
DATA = ROOT / 'data'
DATE = '2026-10-20'

FULL_ORDER = ['masterovit.ru', 'prof-zabory.ru', 'sales.prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru',
              'zabor-dlya-vseh.site', 'raduga-zaborov.ru', 'zaborovo.ru', 'p-z-z.ru', 'oblzabor.ru',
              'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
OWNER = {'sales.prof-zabory.ru': 'prof-zabory.ru', 'zabor-dlya-vseh.site': 'zavodzaborov.ru', 'p-z-z.ru': 'zaborovo.ru'}


def w(name, header, rows):
    with open(DATA / name, 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)
    print(name, len(rows))


def fix_full(dom):
    """Обрезать полностраничный скрин по ширине 1440 (у части сайтов карусели раздувают ширину)."""
    p = IMG / f'{dom}_full.jpg'
    if not p.exists():
        return None
    im = Image.open(p)
    if im.width > 1480:
        im = im.crop((0, 0, 1440, im.height))
        im.convert('RGB').save(p, quality=60)
    return im


def crop_block(im, dom, n, y, h):
    if im is None:
        return ''
    y0 = max(0, int(y)); y1 = min(im.height, int(y + min(h, 2200)))
    if y1 - y0 < 30:
        return ''
    c = im.crop((0, y0, min(1440, im.width), y1))
    c = c.resize((900, int(c.height * 900 / c.width)))
    out = BLK / f'{dom}_b{n:02d}.jpg'
    c.convert('RGB').save(out, quality=68)
    return str(out.relative_to(ROOT))


# вырезки, переснятые отдельно (виджет не успел загрузиться на полностраничном скрине)
OVERRIDE_SHOT = {('raduga-zaborov.ru', 11): 'img/sites/blocks/raduga-zaborov.ru_b11_reshoot.jpg'}

# ---------- полные разборы ----------
blocks, offers, prices, services, evals = [], [], [], [], []
for dom in FULL_ORDER:
    d = json.load(open(PARTS / f'{dom}.json'))
    im = fix_full(dom)
    if im is not None:
        im = im.convert('RGB')
        # размыть отзывы (имена и фото частных лиц не сохраняем)
        for b in d['blocks']:
            if 'отзыв' in b[2]:
                box = (0, max(0, int(b[0])), im.width, min(im.height, int(b[0] + b[1])))
                if box[3] > box[1]:
                    im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(14)), box)
        im.save(IMG / f'{dom}_full.jpg', quality=60)
    for i, b in enumerate(d['blocks'], 1):
        y, h, typ, head, summ, cta, lm = b
        shot = OVERRIDE_SHOT.get((dom, i)) or crop_block(im, dom, i, y, h)
        blocks.append([dom, d['page_url'], i, typ, head, summ, cta, lm, shot, f'{y}–{y + h}', DATE])
    o = d['offer']
    offers.append([dom, OWNER.get(dom, dom), d['page_url'], o['h1'], o['subheadline'], o['usp'], o['promos'], o['lead_magnets'],
                   o['guarantees'], o['prepayment'], o['installment'], o['install_time'], o['measurement'],
                   o['fixed_estimate'], o['production'], o['scale'], o['social_proof'], o['contacts'],
                   o['next_step'], o['response_time'], f'img/sites/{dom}_desktop.png', DATE])
    for p in d['prices']:
        prod, unit, pfrom, typ_price, typ_desc, incl, url, note = p
        prices.append([dom, 'полный', prod, unit, pfrom, typ_price, typ_desc, incl, url, note, DATE])
    for s in d['services']:
        services.append([dom, s[0], s[1], s[2], d['page_url'], DATE])
    e = d['eval']
    evals.append([dom, d['page_url'], e['offer_first_screen'], e['query_match'], e['trust'], e['cta'], e['form'],
                  e['speed'], e['mobile'], e['strengths'], e['weaknesses'], DATE])

# ---------- облегчённые ----------
# domain, url, h1, offer, promos, price_from_text, prepayment, guarantee, gates_url, gate_mech_4m, gate_auto_4m, gate_note, note
LIGHT = [
 ['zabormo.ru', 'https://zabormo.ru/', 'Заборы под ключ', 'Своё производство без посредников; 8 лет, более 1 500 объектов; гарантия от 2 лет; бесплатный замер в день обращения', 'Покраска каркаса в подарок + скидка на монтаж от 5% (ворота); раздел акций', 'рабица от 355; профнастил от 925; евроштакетник от 1 270; 3D от 1 050 ₽/п.м.', 'Этапы: предоплата 30%, остаток после приёмки; в подвале «без предоплат»', 'До 2 лет (гарантийный талон)', 'https://zabormo.ru/avtomaticheskie-vorota/', 69600, 88000, '4 м под ключ: фундамент 1,5 м М-300, 2 столба 80×80, комплектующие DoorHan; с автоматикой — привод DoorHan 800 и 2 брелка', 'Противоречие «предоплата 30%» и «без предоплат»'],
 ['pro-zabor.ru', 'https://pro-zabor.ru/', 'Установка заборов под ключ в Москве и МО', 'Заборы под ключ за 1 день от 490 руб/м²; более 9 000 заборов; радиус 300 км; расчёт за 15 минут', 'Бутование щебнем в подарок; скидка участникам СВО 3%; скидка пенсионерам и многодетным; «Дачный сезон начинается зимой с 10% скидки»', 'от 490 руб/м²; профнастил 1,5 м от 1 790 ₽/п.м.', 'не найдено на главной', 'Гарантия на все виды монтажа (срок на главной не указан)', 'https://pro-zabor.ru/', '', '', 'На главной карточка «Откатные ворота от 74 990 р.»; отдельная страница ворот не снята', 'Цена на первом экране в руб/м², в таблице за п.м.'],
 ['moscow.kupitzabor.ru', 'https://moscow.kupitzabor.ru/', 'Установка заборов в Москве от производителя под ключ', 'От 1 250 руб/м²; федеральный бренд с 2004 г., более 1 000 км ограждений в год; письменная гарантия до 25 лет на металл', 'Скидка до 20% на доставку материалов «до конца месяца»', 'от 1 250 руб/м²; жалюзи хай-тек от 3 350 ₽/п.м.', 'Оплата за материалы и аванс перед началом работ (этап 5)', 'До 25 лет на металл (письменная)', 'https://moscow.kupitzabor.ru/', '', '', 'Карточки: откатные от 75 000 ₽ (от 3 дней), автоматические от 110 000 ₽ (DoorHan/Came/Nice, от 5 дней), распашные от 35 000 ₽', 'Сеть городских поддоменов'],
 ['33zabora.ru', 'https://33zabora.ru/', 'не размечен (первый экран «Производство и монтаж заборов в Московской области под ключ»)', '10 лет; низкие цены за счёт производства; гарантия 24 месяца на все работы; 2–4 дня от оформления', 'Раздел «Акции» (содержимое на главной не раскрыто)', 'профнастил от 1 850; штакетник от 2 100; 3D от 1 010; рабица от 720 ₽/п.м.', 'не найдено', '24 месяца на работы; на воротах до 5 лет', 'https://33zabora.ru/worota/otkatnie-vorota/', 47150, 96000, '4 × 2 м профнастил на бетонировании, комплект; с CAME/NICE — 96 000 ₽; 3–7 дней', 'Таблица ворот совпадает с zabor-vam.ru (42 600 / 45 550 / 47 150 ₽)'],
 ['zabor-vam.ru', 'https://zabor-vam.ru/', 'Заборы под ключ', 'Производство и монтаж в МО; ответ в течение 10 минут; гарантия 2 года по договору; замер без предоплаты', 'Пенсионерам −3%; фурнитура в подарок; бесплатная доставка; скидка на монтаж 3% (бессрочные акции)', 'от 1 500 ₽/п.м. (раздел цен)', 'В отзыве: предоплата 5 000 ₽; условия на главной не указаны', '2 года', 'https://zabor-vam.ru/product/vorota/otkatnye-vorota/', 66450, '', '4 × 2 м профнастил с установкой — 66 450 ₽ (без установки 47 150 ₽); цена с автоматикой в таблицах не найдена; каталог автоматических от 110 000 ₽', 'Совпадение цен ворот с 33zabora.ru'],
 ['good-zabor.ru', 'https://good-zabor.ru/', 'Забор из профнастила', 'Установка забора от 1 102 руб. за погонный метр; бесплатный замер; проект забора в подарок', '50% скидка на ворота; проект забора в подарок', 'от 1 102 ₽/п.м.; рабица от 881 ₽', 'Блок «Оплата: предоплата 50%»; на странице ворот — «оплата после приёмки»', 'От 1 года на работы (на воротах 24 мес.)', 'https://good-zabor.ru/catalog/otkatnye-vorota.html', '', '', 'Откатные от 28 048 ₽ (размер не указан), карточки 18 000–69 000 ₽', 'Противоречие условий оплаты'],
 ['moskovskie-zabory.ru', 'https://www.moskovskie-zabory.ru/', 'Заборы под ключ', '«Гарантия лучшей цены»; от 495 руб./п.м.; только российский металл; забор за 3 дня; без предоплаты; около 70 бригад; форма «Вызвать замерщика бесплатно — перезвоним в течение 5 минут» на первом экране', 'Скидка 12% от производителя на 3D; скидки при заказе от 50 п.м. (зачёркнутые цены)', 'рабица от 495; профнастил от 1 850; 3D от 1 750; штакетник от 2 290 ₽/п.м.', 'Без предоплаты', '2 года', 'https://www.moskovskie-zabory.ru/zabory-s-vorotami/otkatnie-vorota/', 92000, 132000, '4 × 2 м: механические 92 000 ₽; с автоматикой NICE 132 000 ₽; автоматика отдельно: привод 30 000 + лампа 7 500 + фотоэлементы 7 500', 'Работа круглосуточно и без выходных (заявлено)'],
 ['ligazaborov.ru', 'https://ligazaborov.ru/', 'не размечен (первый экран «Собственное производство. Установка 3D заборов под ключ»)', 'Первый экран: установка 3D-заборов под ключ от 1 400 руб./пог.м.; гарантия лучшей цены; «замер — сегодня, работы — завтра»; оплата после установки; работаем с 2015 г.', 'Генератор, доставка, покраска каркаса, накладной замок, щебень в подарок; кешбэк за друга 3 000 ₽; на воротах — фотоэлементы в подарок', 'от 1 030 ₽/п.м.; 3D от 1 400 ₽/п.м.', 'Оплата после установки (первый экран главной и страницы ворот)', '24 месяца', 'https://ligazaborov.ru/otkatnye-vorota/', '', '', 'Откатные «Стандарт» 3–6 м от 38 500 ₽ (автоматика Comunello/Nice дополнительно); механические из профнастила от 49 980 ₽', 'Первый экран виден после скрытия cookie-плашки (21.10.2026); те же формулировки, что у gorodzaborov.ru, и блок преимуществ как у zaborkin.ru'],
 ['zabory-deshevo.ru', 'https://zabory-deshevo.ru/', 'Заборы в Москве и Московской области', 'Монтаж за 1–3 дня; бесплатный замер; цена в договоре; гарантия на материалы до 10 лет; 10 лет, более 10 000 заборов', 'Уплотнение щебня, доставка, фурнитура, генератор в подарок; скидка на монтаж 10%; пенсионерам 2%; квиз: смета + 3 варианта проекта', 'рабица от 320; профнастил от 1 092 ₽/п.м.', 'Предоплата после договора; оплата за материал при доставке', 'До 10 лет на материалы; в тексте 3 года', 'https://zabory-deshevo.ru/otkatnye-vorota/4-metra/', '', '', 'Отдельная страница «Откатные ворота 4 метра»: от 72 600 ₽ (тип управления не указан), карточки до 115 900 ₽', 'Заявление «в наших бригадах работают только славяне»'],
 ['gorodzaborov.ru', 'https://gorodzaborov.ru/', 'Заборы для дачи и частного дома под ключ', 'Работаем с 2015 г.; «цены актуальны в отличие от конкурентов»; стаж специалистов более 15 лет; более 2 000 объектов', 'Калитка в подарок; замок, трамбовка щебнем, генератор, покраска столбов в подарок; бесплатная доставка', 'рабица от 690; профнастил от 1 450; евроштакетник от 1 640 ₽/п.м.', 'не найдено', 'Исправление недочётов 2 года', 'https://gorodzaborov.ru/vorota/otkatnye/', '', '', 'Откатные от 64 900 ₽, карточки 65 000 и 79 900 ₽ (размер не указан)', '«С 2015 года» и «за 8 лет»; одинаковые формулировки с ligazaborov.ru']
]

SPEC = [
 ['alusys.ru', 'https://alusys.ru/otkatnyie-vorota/', 'Производим и устанавливаем откатные ворота для частных домов и коммерческих объектов', '15 лет; производство с 2010 г.; гарантия 5 лет; 2 пульта в подарок; срок 14 дней; замер и 3D-макет бесплатно', '4 × 2 м: «средняя рыночная 110 000 ₽, со скидкой 99 000 ₽»; на свайном фундаменте 154 000 → 135 000 ₽; скидка 30% на любые размеры «с 6 июля по 22 октября»', '', 99000, 'Тип управления в акционной карточке не указан; автоматика Came BX708 / Алютех RTO-1000', 'Расчёт без предоплаты', '5 лет'],
 ['vorota750.ru', 'https://vorota750.ru/katalog/vorota/otkatnye', 'Откатные ворота', 'Ворота без предоплаты; изготовление за 1 день; замер бесплатно; демонтаж старых ворот бесплатно; корзина и «купить в 1 клик»', 'Доставка бесплатно при заказе откатных ворот (таблица команды)', 62500, 80500, '4 × 2 м: механические 62 500 ₽, с электроприводом Nice RD 400 — 80 500 ₽ (фурнитура, обшивка профлистом, установка, генератор, доставка до 50 км)', 'Без предоплаты', 'не найдено на странице'],
 ['naves-pod-avto-msk.ru', 'https://naves-pod-avto-msk.ru/vorota', 'Откатные ворота в Москве и Московской области на заказ', 'Производство за 2 дня, установка за 24 часа; предоплата от 10%; калькулятор 3D-модели ворот', 'не найдено', 100000, '', 'Калькулятор: 4 × 2 м профлист без калитки и автоматики — 100 000 ₽ (12 500 ₽/м²); цена с автоматикой в снимке не выведена', 'От 10%', 'Гарантия на монтаж (срок «года гарантии» без цифры в тексте)'],
 ['otkatnie-vorota.com', 'https://otkatnie-vorota.com/', 'Установка откатных ворот «под ключ» в Москве и Московской области', 'Замер бесплатно; бригады со стажем 5–20 лет; гарантия 5 лет; таймер акции «Цены назад!»', 'Акция «Цены назад!» с таймером и полем телефона', 88500, 114400, 'Проекты: механические 4 000 × 1 800 с отдельной калиткой — 88 500 ₽; автоматические 4 000 × 2 000 с калиткой — 114 400–121 300 ₽', 'не найдено', '5 лет'],
 ['gruppa-masterov.ru', 'https://gruppa-masterov.ru/', 'Производим ворота и заборы', 'Откатные ворота от 85 000 ₽; собственное производство; постгарантийное обслуживание; монтаж за 1 день; доставка бесплатно до 30 км', 'Акции «с 15 по 30 сентября 2025 года» (скидка 20% на обшивку, сигнальная лампа в подарок) на странице 20.10.2026', '', '', 'Каталог: откатные от 35 000 ₽, автоматические и на сваях от 85 000 ₽, карточки 79 800–80 100 ₽; цена именно 4 м не выведена', 'не найдено', '12 месяцев на недочёты'],
 ['metalsystems.ru', 'https://metalsystems.ru/otkatnye-vorota/', 'Откатные ворота и заборы под ключ', 'Более 10 лет; более 2 000 ворот в год; установка за 1 день; «цены ниже, чем у конкурентов»; квиз 5 шагов со скидкой или подарком', 'Скидка 10% за расчёт; сезонные скидки 2026; грунт ГФ-21 бесплатно', '', '', 'Каркас откатных ворот 4 200 × 1 900 под проём 3,8–4 м в грунте — 25 900 ₽ (только каркас); цена под ключ 4 м не выведена', 'Есть рассрочка (в отзыве)', '1 год'],
 ['zabory-prestige.ru', 'https://zabory-prestige.ru/otkatnye-vorota', 'Откатные ворота с установкой «под ключ»', 'Ширина 3–6 м, высота 1,5–3 м; сваи или армированная плита; смета за 10–15 минут; автоматика Алютех/Came/Nice', 'Зачёркнутые цены (−5…10%)', 72000, 97000, 'Таблица механических 4 × 2 м — 72 000 ₽; автоматические «от 97 000 ₽» (было 102 000), размер от 3 м', 'не найдено', 'Раздел гарантии (срок на странице ворот не указан)'],
 ['atlantzabor.ru', 'https://atlantzabor.ru/product/vorota/otkatnye', 'Изготовление откатных ворот под ключ в Москве и области', 'Более 1 000 объектов ежегодно; собственное производство; 73 модели в каталоге с корзиной', 'Скидки пенсионерам, постоянным клиентам и при комплексном заказе «забор + ворота + калитка»', '', '', 'Каталог от 60 400 ₽, ворота 6 м от 75 100 ₽; цена 4 м не выведена', 'До 30% в день договора, остаток после приёмки', '2 года']
]

light_rows = []
for r in LIGHT:
    dom, url, h1, offer, promos, pfrom, prep, guar, gurl, g4m, g4a, gnote, note = r
    light_rows.append([dom, url, h1, offer, promos, pfrom, prep, guar, note, f'img/sites/{dom}_desktop.png', f'img/sites/{dom}_mobile.png', DATE])
w('sites_light.csv', ['domain', 'page_url', 'h1', 'offer', 'promos', 'price_from', 'prepayment', 'guarantee', 'note',
                      'screenshot_desktop', 'screenshot_mobile', 'date'], light_rows)

# ---------- ворота: сводная (строго 4 м отдельно от цен «от» без размера) ----------
# domain, group, url, mech_4m, auto_4m, from_mech, from_auto, conditions
GATES = [
 ['masterovit.ru','полный разбор','https://www.masterovit.ru/otkatnie-vorota/',78793,'',75884,116713,'4 × 1,95 м на винтовых сваях без наполнения полотна; цены 4 м с автоматикой нет (оценка ≈119 600 ₽: 78 793 + разница 40 829 между эконом с автоматикой R-Tech и без)'],
 ['prof-zabory.ru','полный разбор','https://prof-zabory.ru/ustanovka-vorot-i-kalitok/otkatnye',72050,110050,71250,109250,'4 × 2 м под ключ, профнастил или евроштакетник, доставка до 100 км; автоматика ALUTECH с фотоэлементами и лампой (+38 000 ₽); 3 года бесплатного обслуживания автоматики'],
 ['zaborkin.ru','полный разбор','https://zaborkin.ru/vorota/otkatnie/','','',72150,123350,'4 м не опубликован; 3,5 × 2 м на винтовых сваях: механические 72 150 ₽, автоматика (Италия) +51 200 ₽ с установкой; «акция −10%» от завышенной суммы'],
 ['zavodzaborov.ru','полный разбор','https://zavodzaborov.ru/otkatnye-vorota/',101400,144100,80760,123460,'4 × 2 м с установкой на бетонном основании; на сваях 80 760 / 123 460 ₽; автоматика +42 700 ₽; изготовление от 5 рабочих дней'],
 ['raduga-zaborov.ru','полный разбор','https://raduga-zaborov.ru/otkatnye-vorota/',70173,'',69045,'','4 × 2 м на винтовых сваях (ориентировочно), тип управления в таблице не указан; на бетонной тумбе 84 773 ₽; цена автоматики не опубликована'],
 ['zaborovo.ru','полный разбор','https://zaborovo.ru/otkatnye-vorota',74200,103200,72500,101500,'Проём 4 м: механические с роликами Doorhan и порошковой окраской; автоматические с приводом Doorhan Sliding-500, наполнение не входит'],
 ['p-z-z.ru','полный разбор (второй сайт)','https://p-z-z.ru/','','',42981,74605,'Цены карточек без размеров'],
 ['oblzabor.ru','полный разбор','https://www.oblzabor.ru/otkatnye-vorota/','','','',31428,'Карточка 4 000 × 2 000, профнастил, автоматика NICE, доставка и монтаж — 31 428 ₽ «по акции» от 36 142 ₽; цена ниже рынка в 3–4 раза, требует проверки звонком | QA 20.10.2026: на странице «Цена от 36142 31428 руб.» — цена «от» с зачёркнутой, та же сумма у карточки 3 000 мм с Faac; перенесено из цены 4 м в «от»'],
 ['dostup-zabor.ru','полный разбор','https://dostup-zabor.ru/vorota/otkatnye/',26500,'','',72080,'Карточка «Откатные ворота 4 метра» 26 500 ₽ без раскрытого состава; под ключ с автоматикой CAME/Nice «от 72 080 ₽» без размера; без предоплаты'],
 ['zaboroff.ru','полный разбор','https://www.zaboroff.ru/gates/','','',75000,75000,'Механические и автоматические на сваях — одинаково «от 75 000 ₽/п.м.» (−10% от 82 500); размер не указан'],
 ['pskzabor.ru','полный разбор','https://pskzabor.ru/vorota-i-kalitki/mehanicheskie-otkatnye-vorota/',65000,'',34000,59000,'Механические 4 × 2 м по таблице — 65 000 ₽; автоматические «от 59 000 ₽» без зашивки, размер не указан'],
 ['zabormo.ru','облегчённо','https://zabormo.ru/avtomaticheskie-vorota/',69600,88000,35000,55000,'Проём 4 м под ключ: фундамент 1,5 м М-300, 2 столба 80×80, комплектующие DoorHan; автоматика — привод DoorHan 800 и 2 брелка'],
 ['pro-zabor.ru','облегчённо','https://pro-zabor.ru/','','',74990,'','Только карточка на главной «откатные ворота от 74 990 р.»'],
 ['moscow.kupitzabor.ru','облегчённо','https://moscow.kupitzabor.ru/','','',75000,110000,'Карточки на главной: откатные от 75 000 ₽ (от 3 дней), автоматические от 110 000 ₽ (DoorHan/Came/Nice, от 5 дней)'],
 ['33zabora.ru','облегчённо','https://33zabora.ru/worota/otkatnie-vorota/',47150,96000,42600,96000,'4 × 2 м профнастил на бетонировании, «комплект»; с CAME/NICE 96 000 ₽; 3–7 дней, гарантия до 5 лет; таблица совпадает с zabor-vam.ru'],
 ['zabor-vam.ru','облегчённо','https://zabor-vam.ru/product/vorota/otkatnye-vorota/',66450,'',42600,110000,'Таблица «с установкой»: профнастил 4 × 2 м — 66 450 ₽; таблица без пометки установки — 47 150 ₽ (как у 33zabora.ru); каталог автоматических от 110 000 ₽'],
 ['good-zabor.ru','облегчённо','https://good-zabor.ru/catalog/otkatnye-vorota.html','','',28048,'','Каталог от 28 048 ₽ без размеров; «50% скидка на ворота»'],
 ['moskovskie-zabory.ru','облегчённо','https://www.moskovskie-zabory.ru/zabory-s-vorotami/otkatnie-vorota/',92000,132000,89000,129000,'4 × 2 м: механические 92 000 ₽, с автоматикой NICE 132 000 ₽; автоматика отдельно: привод 30 000 + лампа 7 500 + фотоэлементы 7 500 ₽'],
 ['ligazaborov.ru','облегчённо','https://ligazaborov.ru/otkatnye-vorota/','','',38500,'','«Стандарт» 3–6 м от 38 500 ₽ (автоматика Comunello/Nice дополнительно); механические из профнастила от 49 980 ₽; фотоэлементы в подарок'],
 ['zabory-deshevo.ru','облегчённо','https://zabory-deshevo.ru/otkatnye-vorota/4-metra/','','',72600,'','Страница «Откатные ворота 4 метра»: от 72 600 ₽, тип управления и состав не указаны'],
 ['gorodzaborov.ru','облегчённо','https://gorodzaborov.ru/vorota/otkatnye/','','',64900,'','Карточки 64 900 / 65 000 / 79 900 ₽ без размеров'],
 ['alusys.ru','специализированный','https://alusys.ru/otkatnyie-vorota/','','',99000,'','Акция: проём 4 × 2 м «средняя рыночная 110 000 ₽ → 99 000 ₽» (тип управления не указан), на свайном фундаменте 135 000 ₽; скидка 30% «с 6 июля по 22 октября»; гарантия 5 лет, 2 пульта в подарок'],
 ['vorota750.ru','специализированный','https://vorota750.ru/katalog/vorota/otkatnye',62500,80500,32000,67000,'4 × 2 м: механические 62 500 ₽, с приводом Nice RD 400 — 80 500 ₽ (обшивка профлистом, фурнитура, установка, генератор, доставка до 50 км); без предоплаты'],
 ['naves-pod-avto-msk.ru','специализированный','https://naves-pod-avto-msk.ru/vorota',100000,'',60000,'','Калькулятор: 4 × 2 м профлист без калитки и автоматики — 100 000 ₽ (12 500 ₽/м²); предоплата от 10%'],
 ['otkatnie-vorota.com','специализированный','https://otkatnie-vorota.com/',88500,114400,45000,'','Проекты с отдельной калиткой: механические 4 000 × 1 800 — 88 500 ₽; автоматические 4 000 × 2 000 — 114 400–121 300 ₽'],
 ['gruppa-masterov.ru','специализированный','https://gruppa-masterov.ru/','','',35000,85000,'Каталог: откатные от 35 000 ₽, автоматические и на сваях от 85 000 ₽; акции «с 15 по 30 сентября 2025 года» на странице'],
 ['metalsystems.ru','специализированный','https://metalsystems.ru/otkatnye-vorota/','','',25900,'','Только каркас 4 200 × 1 900 под проём 3,8–4 м — 25 900 ₽; цена под ключ не выведена; гарантия 1 год'],
 ['zabory-prestige.ru','специализированный','https://zabory-prestige.ru/otkatnye-vorota',72000,'',54000,97000,'Механические 4 × 2 м по таблице — 72 000 ₽; автоматические «от 97 000 ₽» (было 102 000) без размера'],
 ['atlantzabor.ru','специализированный','https://atlantzabor.ru/product/vorota/otkatnye','','',60400,'','Каталог от 60 400 ₽; предоплата до 30%, остаток после приёмки; гарантия 2 года'],
]

# Сопоставимость состава ворот 4 м (I8): наполнение полотна, фундамент, высота, привод.
# Сопоставимыми считаются: проём 4 м, полотно с наполнением (или наполнение не исключено), высота 1,9–2,0 м, монтаж включён, без калитки.
# domain: (infill, foundation, height_m, drive, comparable_mech, comparable_auto, note, mech_for_median, auto_for_median)
COMP = {
 'masterovit.ru': ('нет (наполнение не входит)', 'винтовые сваи', '1,95', 'R-Tech / CAME BX-608 (цены 4 м нет)', 'нет', 'нет', 'без наполнения полотна', '', ''),
 'prof-zabory.ru': ('да (профнастил или евроштакетник)', 'не указан', '2,0', 'ALUTECH + фотоэлементы и лампа', 'да', 'да', '', 72050, 110050),
 'zavodzaborov.ru': ('да', 'винтовые сваи (в медиане); на бетоне 101 400 / 144 100 ₽', '2,0', 'марка не указана', 'да', 'да', 'для сравнения взят вариант на сваях', 80760, 123460),
 'raduga-zaborov.ru': ('не указано (ориентир «под ключ»)', 'винтовые сваи', '2,0', 'цена автоматики не опубликована', 'да', 'нет', 'тип управления не указан', 70173, ''),
 'zaborovo.ru': ('механические — не исключено; автоматические — нет', 'не указан', 'не указана (проём 4 м)', 'Doorhan Sliding-500', 'да', 'нет', 'автоматические без наполнения', 74200, ''),
 'dostup-zabor.ru': ('не раскрыто', 'не раскрыт', 'не указана', 'CAME / Nice (размер не указан)', 'нет', 'нет', 'состав карточки 26 500 ₽ не раскрыт', '', ''),
 'pskzabor.ru': ('не указано', 'не указан', '2,0', 'размер с автоматикой не опубликован', 'да', 'нет', '', 65000, ''),
 'zabormo.ru': ('да (профнастил)', 'бетон М-300, 1,5 м', 'не указана (проём 4 м)', 'DoorHan 800', 'да', 'да', '', 69600, 88000),
 '33zabora.ru': ('да (профнастил)', 'бетонирование', '2,0', 'CAME / NICE', 'да', 'да', '', 47150, 96000),
 'zabor-vam.ru': ('да (профнастил)', 'не указан', '2,0', 'цена с автоматикой в таблице не найдена', 'да', 'нет', 'взята таблица «с установкой»', 66450, ''),
 'moskovskie-zabory.ru': ('не указано', 'не указан', '2,0', 'NICE', 'да', 'да', '', 92000, 132000),
 'vorota750.ru': ('да (профлист)', 'не указан', '2,0', 'Nice RD 400', 'да', 'да', 'включены генератор и доставка до 50 км', 62500, 80500),
 'naves-pod-avto-msk.ru': ('да (профлист)', 'не указан', '2,0', 'без автоматики', 'да', 'нет', 'цена калькулятора', 100000, ''),
 'otkatnie-vorota.com': ('да', 'не указан', '1,8 (механические) / 2,0 (автоматические)', 'не указан', 'нет', 'нет', 'проекты с отдельной калиткой, разная высота', '', ''),
 'zabory-prestige.ru': ('не указано', 'сваи или плита', '2,0', 'Алютех / Came (размер не указан)', 'да', 'нет', '', 72000, ''),
}
offers_by = {r[0]: r for r in offers}
LIGHT_BY = {r[0]: r for r in LIGHT}
SPEC_BY = {r[0]: r for r in SPEC}
gates = []
for dom, grp, url, m4, a4, fm, fa, cond in GATES:
    if dom in offers_by:
        guar, prep = offers_by[dom][8][:220], offers_by[dom][9][:220]
    elif dom in LIGHT_BY:
        guar, prep = LIGHT_BY[dom][7], LIGHT_BY[dom][6]
    else:
        guar, prep = SPEC_BY[dom][9], SPEC_BY[dom][8]
    shot = f'img/sites/{dom}_gates_desktop.png' if (IMG / f'{dom}_gates_desktop.png').exists() else ''
    c = COMP.get(dom, ('', '', '', '', 'нет', 'нет', 'цена 4 м не опубликована', '', ''))
    sur = (c[8] - c[7]) if (c[7] != '' and c[8] != '') else ''
    gates.append([dom, grp, url, m4, a4, fm, fa, c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8],
                  sur, 'оценка' if sur != '' else '', cond, guar, prep, shot, DATE])
    if grp in ('облегчённо', 'специализированный'):
        if m4 != '':
            prices.append([dom, grp, 'откатные ворота', 'за шт.', m4, '', '4 м, механические', cond, url, '', DATE])
        if a4 != '':
            prices.append([dom, grp, 'откатные ворота с автоматикой', 'за шт.', a4, '', '4 м, с автоматикой', cond, url, '', DATE])
w('sites_gates.csv', ['domain', 'group', 'gates_url', 'price_mech_4m_rub', 'price_auto_4m_rub', 'price_from_mech_rub',
                      'price_from_auto_rub', 'infill_included', 'foundation', 'height_m', 'drive', 'comparable_mech',
                      'comparable_auto', 'comparable_note', 'mech_4m_for_median_rub', 'auto_4m_for_median_rub',
                      'auto_surcharge_rub', 'surcharge_status', 'conditions', 'guarantee', 'prepayment', 'screenshot', 'date'], gates)
import statistics as _st
_m = [g[14] for g in gates if g[14] != '']; _a = [g[15] for g in gates if g[15] != '']; _s = [g[16] for g in gates if g[16] != '']
print('медиана механика', len(_m), min(_m), max(_m), _st.median(_m), '| автоматика', len(_a), min(_a), max(_a), _st.median(_a),
      '| надбавка', len(_s), min(_s), max(_s), _st.median(_s))
spec_rows = [[r[0], r[1], r[2], r[3], r[4], f'img/sites/{r[0]}_gates_desktop.png', f'img/sites/{r[0]}_gates_mobile.png', DATE] for r in SPEC]
w('sites_gates_specialists.csv', ['domain', 'page_url', 'h1', 'offer', 'promos', 'screenshot_desktop', 'screenshot_mobile', 'date'], spec_rows)

w('sites_blocks.csv', ['domain', 'page_url', 'block_order', 'block_type', 'headline', 'content_summary', 'cta_text', 'lead_magnet',
                       'screenshot_path', 'y_range_px', 'date'], blocks)
w('sites_offers.csv', ['domain', 'company_site', 'page_url', 'h1_first_screen', 'subheadline', 'usp', 'promos', 'lead_magnets',
                       'guarantees', 'prepayment', 'installment', 'install_time', 'measurement', 'fixed_estimate',
                       'production_claimed', 'scale_claimed', 'social_proof', 'contacts_messengers', 'next_step',
                       'response_time', 'screenshot_first_screen', 'date'], offers)
UNIT_SITE = {('pskzabor.ru', '3D'): ('за кв.м', 'руб./м²'), ('pskzabor.ru', 'жалюзи'): ('за кв.м', 'руб./м²'),
             ('zaboroff.ru', 'откатные ворота'): ('за шт.', '₽/п.м. (ошибка единицы на сайте)'),
             ('zaboroff.ru', 'откатные ворота с автоматикой'): ('за шт.', '₽/п.м. (ошибка единицы на сайте)'),
             ('zaboroff.ru', 'распашные ворота'): ('за шт.', '₽/п.м. (ошибка единицы на сайте)'),
             ('prof-zabory.ru', 'калитка'): ('за шт.', 'руб. пог/метр при ширине калитки 1 м')}
FENCE = {'профнастил', 'евроштакетник', 'рабица', '3D', 'жалюзи'}
for r in prices:
    unit, site_unit = UNIT_SITE.get((r[0], r[2]), (r[3], r[3]))
    r[3] = unit
    if r[2] in FENCE:
        cmp_ = 'да' if unit == 'за п.м.' and site_unit == unit else 'нет: другая единица'
    elif 'ворота' in r[2]:
        cmp_ = 'см. sites_gates.csv (сопоставимость состава)'
    else:
        cmp_ = 'нет'
    r.insert(4, site_unit); r.insert(5, cmp_)
w('sites_prices.csv', ['domain', 'group', 'product', 'unit', 'unit_on_site', 'comparable_in_per_unit_compare', 'price_from_rub', 'typical_set_price_rub', 'typical_set_desc',
                       'includes', 'source_url', 'note', 'date'], prices)
w('sites_services.csv', ['domain', 'service', 'category', 'note', 'source_url', 'date'], services)
w('sites_landing_eval.csv', ['domain', 'page_url', 'offer_first_screen', 'query_match', 'trust', 'cta', 'form', 'speed',
                             'mobile', 'strengths', 'weaknesses', 'date'], evals)

# ---------- скорость: замер загрузки в облачном прогоне + Lighthouse ----------
speed = []
for dom in FULL_ORDER + [r[0] for r in LIGHT] + [r[0] + '_gates' for r in SPEC]:
    f = RAW / f'{dom}.json'
    if not f.exists():
        continue
    d = json.load(open(f))
    pd, pm = d.get('perf_desktop') or {}, d.get('perf_mobile') or {}
    row = [dom.replace('_gates', ''), d['url'], round((pd.get('ttfb') or 0) / 1000, 2), round((pd.get('lcp') or 0) / 1000, 1),
           round((pd.get('load') or 0) / 1000, 1), pd.get('n_res'), pd.get('kb'), round(pd.get('cls') or 0, 3),
           round((pm.get('lcp') or 0) / 1000, 1), round(pm.get('cls') or 0, 3), 'да' if pm.get('mobile_overflow') else 'нет']
    lhs = []
    for mode in ('mobile', 'desktop'):
        lf = RAW / 'lighthouse' / f"{dom}_{mode}.json"
        if lf.exists():
            try:
                L = json.load(open(lf)); a = L['audits']
                lhs += [round(L['categories']['performance']['score'] * 100), round(a['largest-contentful-paint']['numericValue'] / 1000, 1),
                        round(a['total-byte-weight']['numericValue'] / 1024)]
            except Exception:
                lhs += ['ошибка', '', '']
        else:
            lhs += ['не снято', '', '']
    speed.append(row + lhs + ['не снято: PageSpeed API вернул 429 (дневная квота без ключа исчерпана)', DATE])
w('sites_speed.csv', ['domain', 'url', 'ttfb_s', 'lcp_desktop_s', 'load_desktop_s', 'requests', 'transfer_kb_resource_timing', 'cls_desktop',
                      'lcp_mobile_s', 'cls_mobile', 'mobile_horizontal_scroll', 'lighthouse_mobile_score', 'lighthouse_mobile_lcp_s', 'lighthouse_mobile_kb',
                      'lighthouse_desktop_score', 'lighthouse_desktop_lcp_s', 'lighthouse_desktop_kb', 'pagespeed_api', 'date'], speed)
