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


def build():
    engine = open(os.path.join(ROOT, "_engine.html"), encoding="utf-8").read()
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
            }.items():
                html = html.replace(k, v)

            assert "{{" not in html, f"незаполненный плейсхолдер в {slug}/{lang}"
            p = path_of(slug, lang)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(html)
            made.append((slug, lang, url, len(html.encode())))
            print(f"  {slug:22} {lang}  →  {os.path.relpath(p, OUT):45} {len(html.encode()):>6} B")

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
