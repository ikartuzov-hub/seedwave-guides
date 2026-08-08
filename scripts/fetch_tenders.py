#!/usr/bin/env python3
"""
SeedWave · Лента 1 «Тендеры и госзакупки» — вычислительный слой.

Скачивает годовой файл контрактов BASE/IMPIC с dados.gov.pt (Domínio Público),
оставляет только Мадейру, сохраняет компактный JSON рядом с сайтом.
Движок страниц не трогается — новая выгрузка = обновлённый data/*.json.

ВАЖНО про фильтр: слово "madeira" по-португальски значит "древесина".
Текстовый поиск по всему документу даёт четверть страны (контракты на
пиломатериалы в Лиссабоне и Порту). Регион определяется ТОЛЬКО по полям:
  NUTs = PT300 · localExecucao = Região Autónoma da Madeira · adjudicante
"""
import json, io, os, re, zipfile, urllib.request, collections

URL = "https://dados.gov.pt/api/1/datasets/r/dc5d0543-6e01-4f7e-8709-bf3815812a08"
OUT_DIR = "data"

RE_NUTS = re.compile(r"PT300")
RE_REGIAO = re.compile(r"Regi[ãa]o Aut[óo]noma da Madeira", re.I)
RE_ENTIDADE = re.compile(
    r"Regi[ãa]o Aut[óo]noma da Madeira|IP-RAM|\bRAM\b|"
    r"Funchal|Porto Santo|C[âa]mara de Lobos|Ribeira Brava|Ponta do Sol|"
    r"Porto Moniz|S[ãa]o Vicente|Santana|Machico", re.I)

# Поля, которые оставляем в компактной выгрузке
KEEP = ["idcontrato", "nAnuncio", "dataPublicacao", "dataCelebracaoContrato",
        "tipoContrato", "tipoprocedimento", "objectoContrato", "descContrato",
        "adjudicante", "adjudicatarios", "cpv", "precoContratual",
        "precoBaseProcedimento", "PrecoTotalEfetivo", "prazoExecucao",
        "localExecucao", "NUTs", "adjudicatarioPMEs", "linkPecasProc"]


def download():
    print(f"Скачиваю {URL}", flush=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "SeedWave/1.0"})
    with urllib.request.urlopen(req, timeout=900) as r:
        data = r.read()
    print(f"Получено {len(data)/1e6:.1f} МБ", flush=True)
    return data


def load_records(blob):
    if blob[:2] != b"PK":
        obj = json.loads(blob)
        return obj if isinstance(obj, list) else [obj]
    zf = zipfile.ZipFile(io.BytesIO(blob))
    out = []
    for name in zf.namelist():
        if name.lower().endswith(".json"):
            obj = json.loads(zf.read(name))
            recs = obj if isinstance(obj, list) else [obj]
            print(f"  {name}: {len(recs)}", flush=True)
            out.extend(recs)
    return out


def txt(rec, key):
    return str(rec.get(key, "") or "")


# Материковые и азорские тёзки мадейрских топонимов
RE_FALSE = re.compile(
    r"da Beira|Beira Baixa|Escudeiros e Penso|Santa Cruz da Graciosa|"
    r"Calheta \(A[çc]ores\)|S[ãa]o Vicente da Beira", re.I)


def is_madeira(rec):
    blob = txt(rec, "adjudicante") + " " + txt(rec, "NUTs") + " " + txt(rec, "localExecucao")
    if RE_FALSE.search(blob) and not RE_NUTS.search(txt(rec, "NUTs")):
        return False
    if RE_NUTS.search(txt(rec, "NUTs")):
        return True
    if RE_REGIAO.search(txt(rec, "localExecucao")):
        return True
    if RE_ENTIDADE.search(txt(rec, "adjudicante")):
        return True
    return False


def money(v):
    """Цена приходит числом (9000.0); строковый формат '1.234.567,89 €' — запасной путь."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").replace("\u20ac", "").replace("\xa0", "").replace(" ", "").strip()
    if not s:
        return 0.0
    if "," in s:                      # европейский формат: точка = тысячи
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parties(rec):
    v = rec.get("adjudicatarios")
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)] if v else []


def is_construction(rec):
    """CPV 45xxxxxx — строительные работы; либо тип контракта Empreitadas."""
    if re.search(r"\b45\d{6}", txt(rec, "cpv")):
        return True
    return "Empreitada" in txt(rec, "tipoContrato")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_recs = load_records(download())
    mad = [r for r in all_recs if isinstance(r, dict) and is_madeira(r)]

    compact = [{k: r.get(k) for k in KEEP if r.get(k) is not None} for r in mad]

    constr = [r for r in mad if is_construction(r)]
    top_all, top_constr = collections.Counter(), collections.Counter()
    sum_all = sum_constr = 0.0
    by_type, by_proc = collections.Counter(), collections.Counter()

    for r in mad:
        val = money(r.get("precoContratual"))
        sum_all += val
        by_type[txt(r, "tipoContrato")[:60]] += 1
        by_proc[txt(r, "tipoprocedimento")[:60]] += 1
        for p in parties(r):
            top_all[p.strip("[]'\" ")[:120]] += val
    for r in constr:
        val = money(r.get("precoContratual"))
        sum_constr += val
        for p in parties(r):
            top_constr[p.strip("[]'\" ")[:120]] += val

    meta = {
        "source": URL,
        "license": "Domínio Público (dados.gov.pt / IMPIC)",
        "total_records_pt": len(all_recs),
        "madeira_records": len(mad),
        "madeira_construction": len(constr),
        "sum_madeira_eur": round(sum_all, 2),
        "sum_construction_eur": round(sum_constr, 2),
        "by_tipo_contrato": by_type.most_common(10),
        "by_tipo_procedimento": by_proc.most_common(10),
        "top_contractors_by_value": [[k, round(v, 2)] for k, v in top_all.most_common(25)],
        "top_construction_by_value": [[k, round(v, 2)] for k, v in top_constr.most_common(25)],
    }

    with open(f"{OUT_DIR}/tenders_madeira.json", "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False)
    with open(f"{OUT_DIR}/tenders_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    size = os.path.getsize(f"{OUT_DIR}/tenders_madeira.json") / 1e6
    print(f"\nМадейра: {len(mad)} из {len(all_recs)} | стройка: {len(constr)} | файл {size:.1f} МБ", flush=True)


if __name__ == "__main__":
    main()
