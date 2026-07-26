#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Правки 25.07.2026, согласованные Игорем «на все три вопроса — ДА»:
  1. Находки по фактуре во все языки: сетка ставок SIEED (до 65% при улучшении ≥40%),
     минимальный приемлемый расход 50 000 €, дотация 11,6 млн €, разграничение софта.
  2. Полоска hero-tick добавлена в английскую версию П1.
  3. FAQ П1 выровнен: микроразметка и видимый текст — одни и те же шесть вопросов.
Работает по словарям. Применяется один раз, затем build.py.
"""
import json, re, sys

LANGS = ["pt", "en", "es", "ru", "de"]
SRC = "_src"


def load(slug, lang):
    return json.load(open(f"{SRC}/{slug}/{lang}.json", encoding="utf-8"))


def save(slug, lang, d):
    json.dump(d, open(f"{SRC}/{slug}/{lang}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def rep(d, old, new, where="body", n=1):
    """Замена с проверкой: если якорь не найден или найден не один раз — падаем."""
    cnt = d[where].count(old)
    assert cnt == n, f"якорь встретился {cnt} раз (ждали {n}): {old[:70]}"
    d[where] = d[where].replace(old, new)


# ─────────────────────────────────────────────────────────────────────────────
# ОБЩИЕ ФОРМУЛИРОВКИ ФАКТОВ — пишутся один раз и используются на П1 и П2
# ─────────────────────────────────────────────────────────────────────────────

# Сетка ставок вместо глухого «ставки дифференцированы».
# ⚠ Условие «≥40%» стоит рядом с числом 65% везде: без него это круглое число без текста авизо.
RATES = {
 "pt": "para intervenções no próprio edifício a taxa base é de <b>30%</b>, com majoração de "
       "<b>20 pontos percentuais</b> para micro e pequenas empresas (10 pontos para médias) e mais "
       "<b>15 pontos</b> (PME) quando o desempenho energético do edifício melhora <b>pelo menos 40%</b> "
       "em energia primária — o máximo da grelha é <b>65%</b>.",
 "en": "for works on the building itself the base rate is <b>30%</b>, plus <b>20 percentage points</b> "
       "for micro and small firms (10 points for medium-sized) and a further <b>15 points</b> (SME) where "
       "the building’s energy performance improves by <b>at least 40%</b> in primary energy — the top of "
       "the scale is <b>65%</b>.",
 "es": "para intervenciones en el propio edificio la tasa base es del <b>30%</b>, más "
       "<b>20 puntos porcentuales</b> para micro y pequeñas empresas (10 puntos para medianas) y otros "
       "<b>15 puntos</b> (pyme) cuando el comportamiento energético del edificio mejora <b>al menos un 40%</b> "
       "en energía primaria — el máximo de la escala es el <b>65%</b>.",
 "ru": "для работ в самом здании базовая ставка <b>30%</b>, плюс <b>20 процентных пунктов</b> микро- и малым "
       "предприятиям (10 пунктов средним) и ещё <b>15 пунктов</b> (МСП), если энергетические характеристики "
       "здания улучшаются <b>не менее чем на 40%</b> по первичной энергии — максимум сетки <b>65%</b>.",
 "de": "für Maßnahmen am Gebäude selbst beträgt der Basissatz <b>30%</b>, zuzüglich <b>20 Prozentpunkte</b> "
       "für Kleinst- und Kleinunternehmen (10 Punkte für mittlere) und weitere <b>15 Punkte</b> (KMU), wenn "
       "sich die Energieeffizienz des Gebäudes um <b>mindestens 40%</b> an Primärenergie verbessert — das "
       "Maximum der Skala liegt bei <b>65%</b>.",
}

# Минимальный приемлемый расход — главный фильтр конкурса, раньше не назывался нигде.
MIN = {
 "pt": "<p><b>Atenção ao mínimo:</b> a despesa elegível do projeto tem de ser de pelo menos <b>50.000€</b> — "
       "é o filtro que mais surpreende. Uma substituição isolada raramente lá chega; um pacote de medidas "
       "numa só candidatura chega.</p>",
 "en": "<p><b>Mind the minimum:</b> the project’s eligible spend must be at least <b>€50,000</b> — the filter "
       "that surprises most people. A single replacement rarely reaches it; a package of measures in one "
       "application does.</p>",
 "es": "<p><b>Atención al mínimo:</b> el gasto elegible del proyecto debe ser de al menos <b>50.000€</b> — es "
       "el filtro que más sorprende. Una sustitución aislada rara vez llega; un paquete de medidas en una "
       "sola solicitud sí.</p>",
 "ru": "<p><b>Внимание на минимум:</b> приемлемый расход проекта должен быть не менее <b>50 000 €</b> — это "
       "фильтр, который удивляет чаще всего. Отдельная замена до него почти не дотягивает, пакет мероприятий "
       "в одной заявке — дотягивает.</p>",
 "de": "<p><b>Achtung Mindestbetrag:</b> die förderfähigen Ausgaben des Projekts müssen mindestens "
       "<b>50.000€</b> betragen — der Filter, der am meisten überrascht. Ein einzelner Austausch erreicht ihn "
       "selten; ein Maßnahmenpaket in einem Antrag schon.</p>",
}

# Разграничение софта: энергетический ПО в SIEED входит, POS и предзаказ — нет.
SOFT = {
 "pt": " Atenção à distinção: <b>software, licenças e sensores de monitorização e gestão de energia são "
       "elegíveis</b> no SIEED; o POS e o pré-pedido não.",
 "en": " Note the distinction: <b>software, licences and sensors for energy monitoring and management are "
       "eligible</b> under SIEED; POS and pre-ordering are not.",
 "es": " Atención a la distinción: el <b>software, las licencias y los sensores de monitorización y gestión "
       "de energía sí son elegibles</b> en el SIEED; el TPV y el pedido anticipado no.",
 "ru": " Важное различение: <b>ПО, лицензии и датчики мониторинга и управления энергией — приемлемый расход</b> "
       "по SIEED; POS и предзаказ — нет.",
 "de": " Wichtige Unterscheidung: <b>Software, Lizenzen und Sensoren für Energiemonitoring und -management "
       "sind förderfähig</b> im SIEED; Kassensysteme und Vorbestellung nicht.",
}


# ─────────────────────────────────────────────────────────────────────────────
# П1 — restauracao-madeira
# ─────────────────────────────────────────────────────────────────────────────
P1_RATE_ANCHOR = {
 "pt": "); para intervenções no próprio edifício as taxas são diferenciadas.",
 "en": "); for works on the building itself the rates differ.",
 "es": "); para intervenciones en el propio edificio las tasas son diferenciadas.",
 "ru": "); для работ в самом здании ставки дифференцированы.",
 "de": "); für Maßnahmen am Gebäude selbst sind die Fördersätze differenziert.",
}

# два вопроса из микроразметки прода, которых не было в видимом тексте
P1_Q_WHAT = {
 "pt": ("Que apoios existem para um café ou restaurante na Madeira em 2026?",
        "Vários. Para equipamento com eficiência energética existe o SIEED – Eficiência Energética 2030 "
        "(aviso M2030-2026-21), aberto de 17 de julho a 10 de setembro de 2026. Para digitalização (POS, site, "
        "encomendas online) existem apoios no âmbito do Madeira 2030 / Portugal 2030. Para a criação de um novo "
        "estabelecimento e para a contratação há linhas próprias. As taxas e limites dependem de cada aviso."),
 "en": ("What grants exist for a café or restaurant in Madeira in 2026?",
        "Several. For energy-efficient equipment there is SIEED – Energy Efficiency 2030 (call M2030-2026-21), "
        "open from 17 July to 10 September 2026. For digitalisation (POS, website, online ordering) there are "
        "grants under Madeira 2030 / Portugal 2030. For opening a new venue and for hiring there are separate "
        "lines. Rates and ceilings depend on each call."),
 "es": ("¿Qué ayudas existen para una cafetería o un restaurante en Madeira en 2026?",
        "Varias. Para equipamiento con eficiencia energética está el SIEED – Eficiencia Energética 2030 "
        "(convocatoria M2030-2026-21), abierta del 17 de julio al 10 de septiembre de 2026. Para digitalización "
        "(TPV, web, pedidos online) hay ayudas en el ámbito de Madeira 2030 / Portugal 2030. Para abrir un nuevo "
        "establecimiento y para la contratación hay líneas propias. Las tasas y los límites dependen de cada "
        "convocatoria."),
 "ru": ("Какие субсидии есть для кафе или ресторана на Мадейре в 2026 году?",
        "Несколько. На энергоэффективное оборудование — SIEED «Энергоэффективность 2030» (авизо M2030-2026-21), "
        "открыт с 17 июля по 10 сентября 2026 года. На цифровизацию (POS, сайт, онлайн-заказы) есть поддержка "
        "в рамках Madeira 2030 / Portugal 2030. На открытие нового заведения и на наём — свои линии. Ставки "
        "и лимиты зависят от каждого авизо."),
 "de": ("Welche Förderungen gibt es 2026 für ein Café oder Restaurant auf Madeira?",
        "Mehrere. Für energieeffiziente Ausstattung gibt es SIEED – Energieeffizienz 2030 (Aufruf M2030-2026-21), "
        "offen vom 17. Juli bis 10. September 2026. Für Digitalisierung (Kassensystem, Website, Online-Bestellung) "
        "gibt es Förderungen im Rahmen von Madeira 2030 / Portugal 2030. Für die Eröffnung eines neuen Lokals und "
        "für Einstellungen gibt es eigene Linien. Sätze und Obergrenzen hängen vom jeweiligen Aufruf ab."),
}
P1_Q_ERROR = {
 "pt": ("Qual é o erro mais comum que faz perder o apoio?",
        "Comprar equipamento ou assinar contratos antes de submeter a candidatura. Em regra, despesas feitas "
        "antes da submissão não são elegíveis. Primeiro candidatar, só depois comprar."),
 "en": ("What is the most common mistake that loses the grant?",
        "Buying equipment or signing contracts before submitting the application. As a rule, spending incurred "
        "before submission is not eligible. Apply first, buy afterwards."),
 "es": ("¿Cuál es el error más común que hace perder la ayuda?",
        "Comprar equipamiento o firmar contratos antes de presentar la solicitud. Por regla general, los gastos "
        "realizados antes de la presentación no son elegibles. Primero solicitar, después comprar."),
 "ru": ("Какая ошибка чаще всего лишает субсидии?",
        "Покупка оборудования или подписание договоров до подачи заявки. Как правило, расходы, сделанные "
        "до подачи, не приемлемы. Сначала подать, потом покупать."),
 "de": ("Welcher Fehler kostet am häufigsten die Förderung?",
        "Ausstattung kaufen oder Verträge unterschreiben, bevor der Antrag eingereicht ist. In der Regel sind "
        "Ausgaben vor der Einreichung nicht förderfähig. Erst beantragen, dann kaufen."),
}

# hero-tick для английской версии П1 (в проде он был только в португальской)
P1_TICK_EN = """
  <div class="hero-tick" aria-hidden="true">
    <span class="flow">State <span class="euro">€</span><span class="euro" style="animation-delay:.5s">€</span><span class="euro" style="animation-delay:1s">€</span> → Business</span>
    <span>part of the investment comes back as public funding</span>
  </div>
"""
P1_GEO_EN = ('  <p class="geo">📍 Madeira · Portugal — a guide for <b>café and restaurant</b> owners '
             '(hospitality / HoReCa). Not Spain, not mainland-only schemes.</p>\n')

# «Автоматизация кафе субсидируется?» — куда дописать разграничение софта
P1_AUTO_TAIL = {
 "pt": "Confirmar sempre a janela e a taxa no aviso.</p></details>",
 "en": "Always confirm the window and rate in the call.</p></details>",
 "es": "Confirmar siempre la ventana y la tasa en la convocatoria.</p></details>",
 "ru": "Окно и ставку всегда сверяйте с авизо.</p></details>",
 "de": "Zeitfenster und Fördersatz immer im Aufruf prüfen.</p></details>",
}


def patch_p1():
    slug = "restauracao-madeira"
    for lang in LANGS:
        d = load(slug, lang)

        # 1. сетка ставок + минимум в карточке SIEED
        rep(d, P1_RATE_ANCHOR[lang], "); " + RATES[lang])
        m = re.search(r'(<div class="card">\s*<span class="tag open">.*?)(\n  </div>)', d["body"], re.S)
        assert m, "не найдена карточка SIEED"
        d["body"] = d["body"].replace(m.group(0), m.group(1) + "\n    " + MIN[lang] + m.group(2))

        # 2. разграничение софта в ответ про автоматизацию
        rep(d, P1_AUTO_TAIL[lang], SOFT[lang].strip() + " " + P1_AUTO_TAIL[lang])

        # 3. hero-tick в английскую версию
        if lang == "en":
            rep(d, P1_GEO_EN, P1_GEO_EN + P1_TICK_EN)

        # 4. FAQ: два вопроса из микроразметки становятся видимыми, разметка = видимый текст
        q1, a1 = P1_Q_WHAT[lang]
        q2, a2 = P1_Q_ERROR[lang]
        first = re.search(r'(  <details><summary>)', d["body"])
        d["body"] = d["body"][:first.start()] + \
            f'  <details><summary>{q1}</summary><p>{a1}</p></details>\n' + d["body"][first.start():]
        last = list(re.finditer(r'  <details>.*?</details>\n', d["body"], re.S))[-1]
        d["body"] = d["body"][:last.end()] + \
            f'  <details><summary>{q2}</summary><p>{a2}</p></details>\n' + d["body"][last.end():]
        # микроразметка строится строго из видимых вопросов
        d["faq"] = [{"q": q, "a": re.sub(r"<[^>]+>", "", a)}
                    for q, a in re.findall(r"<summary>(.*?)</summary><p>(.*?)</p>", d["body"], re.S)]
        assert len(d["faq"]) == 6, f"ждали 6 вопросов, получилось {len(d['faq'])}"
        save(slug, lang, d)
        print(f"  П1 {lang}: ставки+минимум, софт, FAQ {len(d['faq'])} видимых = разметка"
              + (", hero-tick добавлен" if lang == "en" else ""))


# ─────────────────────────────────────────────────────────────────────────────
# П2 — sieed-madeira
# ─────────────────────────────────────────────────────────────────────────────
P2_RATE_ANCHOR = {
 "pt": "Em edifícios, as taxas variam com a dimensão da empresa.",
 "en": "For buildings, the rates vary with the size of the company.",
 "es": "En edificios, las tasas varían según el tamaño de la empresa.",
 "ru": "По работам в зданиях ставки зависят от размера компании.",
 "de": "Bei Gebäuden richten sich die Sätze nach der Größe des Unternehmens.",
}
P2_RATE_NEW = {
 "pt": "Em intervenções no próprio edifício a taxa base é de <b>30%</b>, com majoração de <b>20 pontos "
       "percentuais</b> para micro e pequenas empresas (10 pontos para médias) e mais <b>15 pontos</b> (PME) "
       "quando o desempenho energético do edifício melhora <b>pelo menos 40%</b> em energia primária — "
       "o máximo da grelha é <b>65%</b>.",
 "en": "For works on the building itself the base rate is <b>30%</b>, plus <b>20 percentage points</b> for "
       "micro and small firms (10 points for medium-sized) and a further <b>15 points</b> (SME) where the "
       "building’s energy performance improves by <b>at least 40%</b> in primary energy — the top of the "
       "scale is <b>65%</b>.",
 "es": "En intervenciones en el propio edificio la tasa base es del <b>30%</b>, más <b>20 puntos porcentuales</b> "
       "para micro y pequeñas empresas (10 puntos para medianas) y otros <b>15 puntos</b> (pyme) cuando el "
       "comportamiento energético del edificio mejora <b>al menos un 40%</b> en energía primaria — el máximo "
       "de la escala es el <b>65%</b>.",
 "ru": "По работам в самом здании базовая ставка <b>30%</b>, плюс <b>20 процентных пунктов</b> микро- и малым "
       "предприятиям (10 пунктов средним) и ещё <b>15 пунктов</b> (МСП), если энергетические характеристики "
       "здания улучшаются <b>не менее чем на 40%</b> по первичной энергии — максимум сетки <b>65%</b>.",
 "de": "Bei Maßnahmen am Gebäude selbst beträgt der Basissatz <b>30%</b>, zuzüglich <b>20 Prozentpunkte</b> für "
       "Kleinst- und Kleinunternehmen (10 Punkte für mittlere) und weitere <b>15 Punkte</b> (KMU), wenn sich "
       "die Energieeffizienz des Gebäudes um <b>mindestens 40%</b> an Primärenergie verbessert — das Maximum "
       "der Skala liegt bei <b>65%</b>.",
}
P2_DOT_ANCHOR = {
 "pt": "Dotação do aviso: 10 milhões de euros — FEDER",
 "en": "Budget of the call: 10 million euros — FEDER",
 "es": "Dotación de la convocatoria: 10 millones de euros — FEDER",
 "ru": "Бюджет конкурса: 10 миллионов евро — FEDER",
 "de": "Mittelausstattung des Aufrufs: 10 Millionen Euro — FEDER",
}
P2_DOT_NEW = {
 "pt": "Dotação do aviso: <b>11,6 milhões de euros</b> — 10 milhões do FEDER e 1,6 milhões do orçamento da Região",
 "en": "Budget of the call: <b>€11.6 million</b> — €10 million FEDER plus €1.6 million from the Region’s own budget",
 "es": "Dotación de la convocatoria: <b>11,6 millones de euros</b> — 10 millones del FEDER y 1,6 millones del presupuesto de la Región",
 "ru": "Бюджет конкурса: <b>11,6 млн евро</b> — 10 млн из FEDER и 1,6 млн из бюджета региона",
 "de": "Mittelausstattung des Aufrufs: <b>11,6 Millionen Euro</b> — 10 Millionen aus dem FEDER und 1,6 Millionen aus dem Regionalhaushalt",
}
P2_SOFT_ANCHOR = {
 "pt": "(POS, encomendas online) NÃO entra aqui — essa tem programa próprio.",
 "en": "(POS, online orders) does NOT belong here — it has its own programme.",
 "es": "(TPV, pedidos online) NO entra aquí — esa tiene programa propio.",
 "ru": "(POS, онлайн-заказы) сюда НЕ входит: у неё своя программа.",
 "de": "(Kassensysteme, Online-Bestellungen) gehört NICHT hierher — dafür gibt es ein eigenes Programm.",
}
P2_SOFT_ADD = {
 "pt": " Mas atenção à distinção: <b>software, licenças e sensores de monitorização e gestão de energia são "
       "despesa elegível no SIEED</b> — o que não entra é o POS e o pré-pedido.",
 "en": " But note the distinction: <b>software, licences and sensors for energy monitoring and management are "
       "an eligible cost under SIEED</b> — what is excluded is POS and pre-ordering.",
 "es": " Pero atención a la distinción: el <b>software, las licencias y los sensores de monitorización y gestión "
       "de energía sí son gasto elegible en el SIEED</b> — lo que no entra es el TPV y el pedido anticipado.",
 "ru": " Но важное различение: <b>ПО, лицензии и датчики мониторинга и управления энергией — приемлемый расход "
       "по SIEED</b>; не входят именно POS и предзаказ.",
 "de": " Aber wichtige Unterscheidung: <b>Software, Lizenzen und Sensoren für Energiemonitoring und -management "
       "sind im SIEED förderfähig</b> — nicht förderfähig sind Kassensysteme und Vorbestellung.",
}
P2_SMALL_ANCHOR = {
 "pt": "O limite superior (300k/450k) é teto, não mínimo.",
 "en": "The upper limit (300k/450k) is a ceiling, not a minimum.",
 "es": "El límite superior (300k/450k) es un techo, no un mínimo.",
 "ru": "Верхний предел (300k/450k) — это потолок, а не минимум.",
 "de": "Die Obergrenze (300k/450k) ist eine Decke, kein Mindestbetrag.",
}
P2_SMALL_NEW = {
 "pt": "Mas atenção ao mínimo: a despesa elegível do projeto tem de ser de pelo menos <b>50.000€</b> — uma "
       "substituição isolada raramente lá chega, um pacote de medidas chega. O limite superior (300k/450k) "
       "é teto, não mínimo.",
 "en": "But mind the minimum: the project’s eligible spend must be at least <b>€50,000</b> — a single "
       "replacement rarely reaches it, a package of measures does. The upper limit (300k/450k) is a ceiling, "
       "not a minimum.",
 "es": "Pero atención al mínimo: el gasto elegible del proyecto debe ser de al menos <b>50.000€</b> — una "
       "sustitución aislada rara vez llega, un paquete de medidas sí. El límite superior (300k/450k) es techo, "
       "no mínimo.",
 "ru": "Но внимание на минимум: приемлемый расход проекта должен быть не менее <b>50 000 €</b> — отдельная "
       "замена до него почти не дотягивает, пакет мероприятий дотягивает. Верхний предел (300k/450k) — это "
       "потолок, а не минимум.",
 "de": "Aber Achtung Mindestbetrag: die förderfähigen Ausgaben des Projekts müssen mindestens <b>50.000€</b> "
       "betragen — ein einzelner Austausch erreicht das selten, ein Maßnahmenpaket schon. Die Obergrenze "
       "(300k/450k) ist eine Decke, kein Mindestbetrag.",
}


def patch_p2():
    slug = "sieed-madeira"
    for lang in LANGS:
        d = load(slug, lang)
        rep(d, P2_RATE_ANCHOR[lang], P2_RATE_NEW[lang])
        rep(d, P2_DOT_ANCHOR[lang], P2_DOT_NEW[lang])
        rep(d, P2_SOFT_ANCHOR[lang], P2_SOFT_ANCHOR[lang] + P2_SOFT_ADD[lang])
        rep(d, P2_SMALL_ANCHOR[lang], P2_SMALL_NEW[lang])
        d["faq"] = [{"q": q, "a": re.sub(r"<[^>]+>", "", a)}
                    for q, a in re.findall(r"<summary>(.*?)</summary><p>(.*?)</p>", d["body"], re.S)]
        save(slug, lang, d)
        print(f"  П2 {lang}: ставки, дотация 11,6 млн, софт, минимум 50k, FAQ {len(d['faq'])} = разметка")


# ─────────────────────────────────────────────────────────────────────────────
# П3 — cafe-digital-madeira (единственная находка, которая её касается)
# ─────────────────────────────────────────────────────────────────────────────
P3_ANCHOR = {
 "pt": "POS, pré-pedido e software de gestão não entram nesse aviso.",
 "en": "POS, pre-ordering and management software are not covered by that call.",
 "es": "El TPV, el pedido anticipado y el software de gestión no entran en esa convocatoria.",
 "ru": "POS, предзаказ и софт управления рестораном в это авизо не входят.",
 "de": "Kassensysteme, Vorbestellung und Verwaltungssoftware fallen nicht unter diesen Aufruf.",
}
P3_ADD = {
 "pt": " Há uma exceção que vale conhecer: <b>software, licenças e sensores de monitorização e gestão de energia "
       "são despesa elegível no SIEED</b>. Software no SIEED entra — mas o energético, não o comercial.",
 "en": " There is one exception worth knowing: <b>software, licences and sensors for energy monitoring and "
       "management are an eligible cost under SIEED</b>. Software does fit SIEED — the energy kind, not the "
       "commercial kind.",
 "es": " Hay una excepción que conviene conocer: el <b>software, las licencias y los sensores de monitorización "
       "y gestión de energía sí son gasto elegible en el SIEED</b>. El software sí entra en el SIEED — el "
       "energético, no el comercial.",
 "ru": " Есть исключение, о котором стоит знать: <b>ПО, лицензии и датчики мониторинга и управления энергией — "
       "приемлемый расход по SIEED</b>. Софт в SIEED входит — но энергетический, а не коммерческий.",
 "de": " Es gibt eine Ausnahme, die man kennen sollte: <b>Software, Lizenzen und Sensoren für Energiemonitoring "
       "und -management sind im SIEED förderfähig</b>. Software passt also doch in SIEED — die energetische, "
       "nicht die kommerzielle.",
}


def patch_p3():
    slug = "cafe-digital-madeira"
    for lang in LANGS:
        d = load(slug, lang)
        n = d["body"].count(P3_ANCHOR[lang])
        assert n >= 1, f"якорь П3 не найден: {lang}"
        d["body"] = d["body"].replace(P3_ANCHOR[lang], P3_ANCHOR[lang] + P3_ADD[lang])
        d["faq"] = [{"q": q, "a": re.sub(r"<[^>]+>", "", a)}
                    for q, a in re.findall(r"<summary>(.*?)</summary><p>(.*?)</p>", d["body"], re.S)]
        save(slug, lang, d)
        print(f"  П3 {lang}: разграничение софта ×{n}, FAQ {len(d['faq'])} = разметка")


if __name__ == "__main__":
    print("П1 — restauracao-madeira");  patch_p1()
    print("П2 — sieed-madeira");        patch_p2()
    print("П3 — cafe-digital-madeira"); patch_p3()
    print("\nСловари обновлены. Дальше: python3 build.py")
