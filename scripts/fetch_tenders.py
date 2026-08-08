#!/usr/bin/env python3
"""
SeedWave · Лента 1 «Тендеры и госзакупки» — замер данных BASE/IMPIC.
Скачивает годовой файл контрактов 2026 с dados.gov.pt, фильтрует Мадейру,
сохраняет компактный JSON + мета-отчёт. Движок страниц не трогает.
"""
import json, io, os, re, sys, zipfile, urllib.request, collections

URL = "https://dados.gov.pt/api/1/datasets/r/dc5d0543-6e01-4f7e-8709-bf3815812a08"
OUT_DIR = "data"
MADEIRA_RE = re.compile(r"madeira|funchal|c[âa]mara de lobos|ribeira brava|ponta do sol|calheta|porto moniz|s[ãa]o vicente|santana|machico|santa cruz|porto santo|pt3\b|pt30", re.I)
CPV_CONSTR = ("45",)  # CPV 45xxxxxx — строительные работы

def download():
    print(f"Скачиваю {URL} ...", flush=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (SeedWave data probe)"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = r.read()
    print(f"Получено {len(data)/1e6:.1f} МБ", flush=True)
    return data

def iter_records(blob):
    """Возвращает (имя_файла, список_записей) для каждого пригодного файла в zip; либо сам blob как json."""
    if blob[:2] == b"PK":
        zf = zipfile.ZipFile(io.BytesIO(blob))
        names = zf.namelist()
        print("Файлы в архиве:", names, flush=True)
        for name in names:
            low = name.lower()
            if low.endswith(".json"):
                try:
                    obj = json.loads(zf.read(name))
                    yield name, normalize(obj)
                except Exception as e:
                    print(f"  ! {name}: {e}", flush=True)
            elif low.endswith((".csv", ".txt")):
                import csv
                text = zf.read(name).decode("utf-8", errors="replace")
                delim = ";" if text[:2000].count(";") > text[:2000].count(",") else ","
                rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
                yield name, rows
            elif low.endswith((".xlsx", ".xls")):
                print(f"  (xlsx пропущен на первом замере: {name})", flush=True)
    else:
        obj = json.loads(blob)
        yield "root.json", normalize(obj)

def normalize(obj):
    """OCDS: releases/records; либо список; либо dict со списком внутри."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("releases", "records", "data", "items", "contratos", "results"):
            if isinstance(obj.get(k), list):
                return obj[k]
        return [obj]
    return []

def flat_str(rec, _depth=0):
    """Строковое представление записи для текстового фильтра (без глубокой рекурсии)."""
    try:
        return json.dumps(rec, ensure_ascii=False, default=str)[:6000].lower()
    except Exception:
        return str(rec).lower()

def get_first(rec, keys):
    for k in keys:
        v = rec.get(k)
        if v:
            return v
    return None

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    blob = download()
    meta = {"source": URL, "files": [], "total_records": 0, "madeira_records": 0}
    madeira = []
    sample_keys = None

    for name, records in iter_records(blob):
        n = len(records)
        meta["files"].append({"name": name, "records": n})
        meta["total_records"] += n
        print(f"{name}: {n} записей", flush=True)
        if records and sample_keys is None:
            sample_keys = sorted(records[0].keys()) if isinstance(records[0], dict) else None
        for rec in records:
            if isinstance(rec, dict) and MADEIRA_RE.search(flat_str(rec)):
                madeira.append(rec)

    meta["madeira_records"] = len(madeira)
    meta["sample_keys"] = sample_keys

    # Топ подрядчиков по стройке (CPV 45*) среди мадейрских записей
    top = collections.Counter()
    for rec in madeira:
        s = flat_str(rec)
        cpv_hit = bool(re.search(r'"cpv[^"]*"\s*:\s*"?45', s)) or '"45' in s[:0]  # cpv поле
        if not cpv_hit:
            # запасной вариант: искать 45xxxxxx-x паттерн CPV
            cpv_hit = bool(re.search(r"\b45\d{6}-\d\b", s))
        if cpv_hit:
            adj = get_first(rec, ["adjudicatarios", "adjudicatario", "suppliers", "supplier", "awardedParty", "entidadeAdjudicataria"])
            label = None
            if isinstance(adj, list) and adj:
                a0 = adj[0]
                label = a0.get("name") or a0.get("nome") if isinstance(a0, dict) else str(a0)
            elif isinstance(adj, dict):
                label = adj.get("name") or adj.get("nome")
            elif adj:
                label = str(adj)
            if label:
                top[label.strip()[:120]] += 1
    meta["top_construction_contractors_madeira"] = top.most_common(20)

    with open(f"{OUT_DIR}/tenders_madeira.json", "w", encoding="utf-8") as f:
        json.dump(madeira, f, ensure_ascii=False)
    with open(f"{OUT_DIR}/tenders_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
