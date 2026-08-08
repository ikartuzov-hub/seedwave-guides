#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка серии apoios.seedwave.dev по правилу трёх слоёв.

  Слой 1 — движок:  _engine.html + _engine.css   (про язык и контент не знает)
  Слой 2/3 — словари: _src/{slug}/{lang}.json    (весь текст страницы, по одному файлу на язык)
  Выход:  {slug}/index.html          — португальский, канонический адрес
          {slug}/{lang}/index.html   — остальные языки, каждый на своём адресе

Добавить язык = положить новый словарь в _src/{slug}/ и вписать его в LANGS. Больше ничего.
Запуск:  python3 build.py
"""
import json, os, re, shutil, sys

SITE   = "https://apoios.seedwave.dev"
LANGS  = ["pt", "en", "es", "ru", "de"]          # первый — канонический
LOCALE = {"pt": "pt_PT", "en": "en_GB", "es": "es_ES", "ru": "ru_RU", "de": "de_DE"}
HREF   = {"pt": "pt-PT", "en": "en",    "es": "es",    "ru": "ru",    "de": "de"}
NAME   = {"pt": "PT · Português", "en": "EN · English", "es": "ES · Español",
          "ru": "RU · Русский",   "de": "DE · Deutsch"}
UI     = {  # единственное, что движок говорит от себя
  "pt": {"lang": "Idioma",  "theme": "Tema",   "igor": "Quem sou — apoios na Madeira"},
  "en": {"lang": "Language","theme": "Theme",  "igor": "Who I am — Madeira grants"},
  "es": {"lang": "Idioma",  "theme": "Tema",   "igor": "Quién soy — ayudas en Madeira"},
  "ru": {"lang": "Язык",    "theme": "Тема",   "igor": "Кто я — субсидии Мадейры"},
  "de": {"lang": "Sprache", "theme": "Design", "igor": "Wer ich bin — Madeira-Förderungen"},
}
PAGES = ["restauracao-madeira", "sieed-madeira", "cafe-digital-madeira"]
TIMELINE_SLUG = "cronologia"
TL = {  # хроника авизо — тексты движка, по одному словарю на язык
  "pt": {"title": "Cronologia dos apoios da Madeira — o que mudou e quando",
         "desc": "Registo datado de aberturas, prazos e alterações dos apoios públicos na Madeira. Só o que já tem aviso publicado.",
         "h1": "Cronologia dos apoios da Madeira",
         "lead": "O que mudou nos apoios públicos da Madeira, por data. Entra aqui apenas o que já tem aviso ou diploma publicado — anúncios sem texto oficial não entram.",
         "recent": "Últimas atualizações", "all": "Ver a cronologia completa",
         "source": "Fonte", "read": "Guia completo", "empty": "Ainda sem registos publicados.",
         "kind": {"open": "Abertura", "update": "Atualização", "close": "Encerramento"}},
  "en": {"title": "Madeira grants timeline — what changed and when",
         "desc": "Dated record of openings, deadlines and changes to public grants in Madeira. Only what already has a published notice.",
         "h1": "Madeira grants timeline",
         "lead": "What changed in Madeira's public grants, by date. Only entries backed by a published notice or decree — announcements without official text stay out.",
         "recent": "Latest updates", "all": "See the full timeline",
         "source": "Source", "read": "Full guide", "empty": "No published entries yet.",
         "kind": {"open": "Opening", "update": "Update", "close": "Closing"}},
  "es": {"title": "Cronología de las ayudas de Madeira — qué cambió y cuándo",
         "desc": "Registro fechado de aperturas, plazos y cambios en las ayudas públicas de Madeira. Solo lo que ya tiene convocatoria publicada.",
         "h1": "Cronología de las ayudas de Madeira",
         "lead": "Qué cambió en las ayudas públicas de Madeira, por fecha. Solo entra lo que ya tiene convocatoria o decreto publicado.",
         "recent": "Últimas actualizaciones", "all": "Ver la cronología completa",
         "source": "Fuente", "read": "Guía completa", "empty": "Aún sin registros publicados.",
         "kind": {"open": "Apertura", "update": "Actualización", "close": "Cierre"}},
  "ru": {"title": "Хроника субсидий Мадейры — что менялось и когда",
         "desc": "Датированный учёт открытий, сроков и изменений публичной поддержки на Мадейре. Только то, по чему уже вышло авизо.",
         "h1": "Хроника субсидий Мадейры",
         "lead": "Что менялось в публичной поддержке Мадейры, по датам. Сюда попадает только то, по чему уже опубликовано авизо или постановление — анонсы без официального текста не входят.",
         "recent": "Последние обновления", "all": "Смотреть всю хронику",
         "source": "Источник", "read": "Полный гид", "empty": "Пока без опубликованных записей.",
         "kind": {"open": "Открытие", "update": "Обновление", "close": "Закрытие"}},
  "de": {"title": "Chronik der Madeira-Förderungen — was sich wann geändert hat",
         "desc": "Datierte Aufzeichnung von Öffnungen, Fristen und Änderungen öffentlicher Förderungen auf Madeira. Nur mit veröffentlichter Bekanntmachung.",
         "h1": "Chronik der Madeira-Förderungen",
         "lead": "Was sich bei den öffentlichen Förderungen Madeiras geändert hat, nach Datum. Aufgenommen wird nur, wofür bereits eine Bekanntmachung oder ein Erlass vorliegt.",
         "recent": "Letzte Aktualisierungen", "all": "Vollständige Chronik ansehen",
         "source": "Quelle", "read": "Vollständiger Leitfaden", "empty": "Noch keine veröffentlichten Einträge.",
         "kind": {"open": "Eröffnung", "update": "Aktualisierung", "close": "Schließung"}},
}

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, "dist")


def url_of(slug, lang):
    return f"{SITE}/{slug}/" if lang == LANGS[0] else f"{SITE}/{slug}/{lang}/"


def path_of(slug, lang):
    return os.path.join(OUT, slug, "index.html") if lang == LANGS[0] \
        else os.path.join(OUT, slug, lang, "index.html")


def localize_links(body, lang):
    """Внутренние ссылки серии ведут на страницу того же языка."""
    if lang == LANGS[0]:
        return body
    for other in PAGES:
        body = body.replace(f'href="/{other}/"', f'href="/{other}/{lang}/"')
    return body


def jsonld(slug, lang, d):
    url = url_of(slug, lang)
    return json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article",
             "headline": d["article"]["headline"],
             "inLanguage": HREF[lang],
             "datePublished": d["article"]["datePublished"],
             "dateModified": d["article"]["dateModified"],
             "author": {"@type": "Person", "name": "Igor Kartuzov"},
             "publisher": {"@type": "Organization", "name": "SeedWave"},
             "about": d["article"]["about"],
             "mainEntityOfPage": url},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q["q"],
                             "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
                            for q in d["faq"]]},
        ]}, ensure_ascii=False, indent=2)


def load_avisos():
    p = os.path.join(ROOT, "_src", "_data", "avisos.json")
    if not os.path.exists(p):
        return []
    data = json.load(open(p, encoding="utf-8"))["entries"]
    return sorted(data, key=lambda e: e["date"], reverse=True)


def tl_url(lang):
    return f"{SITE}/{TIMELINE_SLUG}/" if lang == LANGS[0] else f"{SITE}/{TIMELINE_SLUG}/{lang}/"


def local(path, lang):
    """Внутренняя ссылка серии на язык страницы."""
    if lang == LANGS[0]:
        return path
    return path.rstrip("/") + f"/{lang}/"


def updates_block(avisos, lang, limit=3):
    """Компактный блок «последние обновления» для страниц серии."""
    t = TL[lang]
    if not avisos:
        return ""
    rows = []
    for e in avisos[:limit]:
        rows.append(
            f'<li><time datetime="{e["date"]}">{e["date"]}</time> '
            f'<strong>{e["program"]}</strong> — {e["text"][lang]}</li>')
    return ('<section class="updates"><h2>' + t["recent"] + "</h2><ul>"
            + "".join(rows) + "</ul>"
            f'<p><a href="{local("/" + TIMELINE_SLUG + "/", lang)}">{t["all"]} →</a></p></section>')


def timeline_body(avisos, lang):
    t = TL[lang]
    if not avisos:
        items = f"<p>{t['empty']}</p>"
    else:
        rows = []
        for e in avisos:
            kind = t["kind"].get(e["kind"], e["kind"])
            rows.append(
                f'<li class="tl-item"><time datetime="{e["date"]}">{e["date"]}</time>'
                f'<span class="tl-kind">{kind}</span>'
                f'<h3>{e["program"]}</h3><p>{e["text"][lang]}</p>'
                f'<p class="tl-meta">{t["source"]}: <a href="{e["sourceUrl"]}" rel="nofollow noopener" target="_blank">{e["source"]}</a>'
                f' · <a href="{local(e["link"], lang)}">{t["read"]} →</a></p></li>')
        items = '<ul class="tl">' + "".join(rows) + "</ul>"
    return (f'<p class="kicker">Apoios · Madeira</p><h1>{t["h1"]}</h1>'
            f'<p class="lead">{t["lead"]}</p>{items}')


def timeline_jsonld(avisos, lang):
    t = TL[lang]
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": t["h1"],
        "description": t["desc"],
        "inLanguage": HREF[lang],
        "url": tl_url(lang),
        "numberOfItems": len(avisos),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "item": {"@type": "CreativeWork", "name": e["program"],
                      "datePublished": e["date"], "text": e["text"][lang],
                      "url": SITE + local(e["link"], lang)}}
            for i, e in enumerate(avisos)],
    }, ensure_ascii=False, indent=2)


def build():
    engine = open(os.path.join(ROOT, "_engine.html"), encoding="utf-8").read()
    avisos = load_avisos()
    css    = open(os.path.join(ROOT, "_engine.css"),  encoding="utf-8").read()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    made = []

    for slug in PAGES:
        for lang in LANGS:
            src = os.path.join(ROOT, "_src", slug, f"{lang}.json")
            if not os.path.exists(src):
                print(f"  пропуск: нет словаря {slug}/{lang}")
                continue
            d = json.load(open(src, encoding="utf-8"))
            url = url_of(slug, lang)

            hreflang = "\n".join(
                f'<link rel="alternate" hreflang="{HREF[l]}" href="{url_of(slug, l)}">'
                for l in LANGS if os.path.exists(os.path.join(ROOT, "_src", slug, f"{l}.json"))
            ) + f'\n<link rel="alternate" hreflang="x-default" href="{url_of(slug, LANGS[0])}">'

            ogalt = "\n".join(f'<meta property="og:locale:alternate" content="{LOCALE[l]}">'
                              for l in LANGS if l != lang)

            def link(l):
                cur = ' class="active" aria-current="true"' if l == lang else ""
                return f'  <a href="{url_of(slug, l)}" hreflang="{HREF[l]}"{cur}>{NAME[l]}</a>'

            links = "\n".join(
                link(l) for l in LANGS
                if os.path.exists(os.path.join(ROOT, "_src", slug, f"{l}.json"))
            )

            html = engine
            for k, v in {
                "{{LANG}}": lang, "{{LANGUPPER}}": lang.upper(),
                "{{TITLE}}": d["head"]["title"], "{{DESCRIPTION}}": d["head"]["description"],
                "{{OGTITLE}}": d["head"]["ogTitle"], "{{OGDESCRIPTION}}": d["head"]["ogDescription"],
                "{{OGIMAGE}}": d["head"]["ogImage"], "{{APPTITLE}}": d["head"]["appTitle"],
                "{{URL}}": url, "{{OGLOCALE}}": LOCALE[lang],
                "{{HREFLANG}}": hreflang, "{{OGALTERNATES}}": ogalt, "{{LANGLINKS}}": links,
                "{{LANGLABEL}}": UI[lang]["lang"], "{{THEMELABEL}}": UI[lang]["theme"],
                "{{IGORANCHOR}}": UI[lang]["igor"],
                "{{JSONLD}}": jsonld(slug, lang, d), "{{CSS}}": css,
                "{{BODY}}": localize_links(d["body"], lang),
                "{{UPDATES}}": updates_block(avisos, lang),
            }.items():
                html = html.replace(k, v)

            assert "{{" not in html, f"незаполненный плейсхолдер в {slug}/{lang}"
            p = path_of(slug, lang)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(html)
            made.append((slug, lang, url, len(html.encode())))
            print(f"  {slug:22} {lang}  →  {os.path.relpath(p, OUT):45} {len(html.encode()):>6} B")

    # ── хроника авизо: тот же движок, свой слой данных ──
    for lang in LANGS:
        url = tl_url(lang)
        t = TL[lang]
        hreflang = "\n".join(
            f'<link rel="alternate" hreflang="{HREF[l]}" href="{tl_url(l)}">' for l in LANGS
        ) + f'\n<link rel="alternate" hreflang="x-default" href="{tl_url(LANGS[0])}">'
        ogalt = "\n".join(f'<meta property="og:locale:alternate" content="{LOCALE[l]}">'
                          for l in LANGS if l != lang)
        def tlink(l, cur=lang):
            a = ' class="active" aria-current="true"' if l == cur else ""
            return f'  <a href="{tl_url(l)}" hreflang="{HREF[l]}"{a}>{NAME[l]}</a>'
        html = engine
        for k, v in {
            "{{LANG}}": lang, "{{LANGUPPER}}": lang.upper(),
            "{{TITLE}}": t["title"], "{{DESCRIPTION}}": t["desc"],
            "{{OGTITLE}}": t["title"], "{{OGDESCRIPTION}}": t["desc"],
            "{{OGIMAGE}}": f"{SITE}/og-igor.png", "{{APPTITLE}}": t["h1"],
            "{{URL}}": url, "{{OGLOCALE}}": LOCALE[lang],
            "{{HREFLANG}}": hreflang, "{{OGALTERNATES}}": ogalt,
            "{{LANGLINKS}}": "\n".join(tlink(l) for l in LANGS),
            "{{LANGLABEL}}": UI[lang]["lang"], "{{THEMELABEL}}": UI[lang]["theme"],
            "{{IGORANCHOR}}": UI[lang]["igor"],
            "{{JSONLD}}": timeline_jsonld(avisos, lang), "{{CSS}}": css,
            "{{BODY}}": timeline_body(avisos, lang), "{{UPDATES}}": "",
        }.items():
            html = html.replace(k, v)
        assert "{{" not in html, f"незаполненный плейсхолдер в хронике/{lang}"
        p = os.path.join(OUT, TIMELINE_SLUG, "index.html") if lang == LANGS[0] \
            else os.path.join(OUT, TIMELINE_SLUG, lang, "index.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(html)
        made.append((TIMELINE_SLUG, lang, url, len(html.encode())))
        print(f"  {TIMELINE_SLUG:22} {lang}  →  {os.path.relpath(p, OUT):45} {len(html.encode()):>6} B")

    # ── лендинг и llms.txt: ссылки на языковые версии подставляет сборка ──
    def langs_of(slug):
        return [l for l in LANGS if os.path.exists(os.path.join(ROOT, "_src", slug, f"{l}.json"))]

    land = open(os.path.join(ROOT, "_src", "_static", "index.html"), encoding="utf-8").read()
    for slug in PAGES:
        row = " · ".join(f'<a href="{url_of(slug, l)}" hreflang="{HREF[l]}">{l.upper()}</a>'
                         for l in langs_of(slug))
        land = land.replace(f"<!--LANGS:{slug}-->", f'<p class="langs">{row}</p>')
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(land)

    llms = open(os.path.join(ROOT, "_src", "_static", "llms.txt"), encoding="utf-8").read()
    llms = llms.replace("{{LANGNOTE}}", "/".join(l.upper() for l in LANGS)
                        + " — cada língua no seu próprio endereço:")
    for slug in PAGES:
        rows = []
        for l in langs_of(slug):
            d = json.load(open(os.path.join(ROOT, "_src", slug, f"{l}.json"), encoding="utf-8"))
            rows.append(f'  - [{d["article"]["headline"]}]({url_of(slug, l)}) — {l.upper()}')
        llms = llms.replace(f"<!--LANGS:{slug}-->", "\n".join(rows))
    open(os.path.join(OUT, "llms.txt"), "w", encoding="utf-8").write(llms)

    # ── sitemap.xml с языковыми альтернативами ──
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
           f'  <url><loc>{SITE}/</loc></url>',
           f'  <url><loc>{SITE}/igor/</loc></url>']
    for lang in LANGS:
        xml.append(f"  <url>\n    <loc>{tl_url(lang)}</loc>")
        for l in LANGS:
            xml.append(f'    <xhtml:link rel="alternate" hreflang="{HREF[l]}" href="{tl_url(l)}"/>')
        xml.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{tl_url(LANGS[0])}"/>')
        xml.append("  </url>")
    for slug in PAGES:
        langs = [l for l in LANGS if os.path.exists(os.path.join(ROOT, "_src", slug, f"{l}.json"))]
        for lang in langs:
            xml.append(f"  <url>\n    <loc>{url_of(slug, lang)}</loc>")
            for l in langs:
                xml.append(f'    <xhtml:link rel="alternate" hreflang="{HREF[l]}" href="{url_of(slug, l)}"/>')
            xml.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url_of(slug, LANGS[0])}"/>')
            xml.append("  </url>")
    xml.append("</urlset>")
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(xml) + "\n")

    open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")

    print(f"\nСобрано страниц: {len(made)} · sitemap.xml · robots.txt")
    return made


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
