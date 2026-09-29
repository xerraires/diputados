#!/usr/bin/env python3
"""Extrae los bienes patrimoniales de las declaraciones OCR (TSV con coordenadas).

Salidas:
  bienes.json   — lista de entradas por diputado
"""
import csv, json, os, re, unicodedata

W_REF = 2481.0  # ancho de imagen de referencia


def norm(t):
    t = unicodedata.normalize('NFKD', t)
    return ''.join(c for c in t if not unicodedata.combining(c)).lower()


# frases de la plantilla que no son datos
TEMPLATE_PHRASES = [
    'clase y caracteristicas', 'situacion', 'fecha de', 'adquisicion', 'derecho sobre',
    'el bien', 'titulo de', 'plen', 'comprav', 'bienes inmuebles', 'de naturaleza',
    'urbana', 'rustica', 'propiedad de una','sociedad', 'comunidad o', 'entidad que',
    'cotiza en bolsa', 'de la que el', 'declarante tiene', 'acciones o',
    'participacion', 'depositos en cuentas', 'cuentas corrientes', 'cuentas financieras',
    'otros tipos de imposiciones', 'saldo de todos los', 'depositos', ' klasa', 'clase de bien',
    'descripcion del', 'valor', 'indicar sistema', 'que se ha', 'utilizado para',
    'su valoracion dineraria', 'deuda publica', 'obligaciones', 'certificados de',
    'deposito, pagares', 'y demas', 'valores equivalentes', 'acciones y participacione',
    'en todo tipo de sociedades', 'entidades con valor economico', 'y cooperativas',
    'participadas en', 'por otras', 'sociedades o', 'que sean', 'propiedad,',
    'en todo', 'o en', 'parte, del', 'parlamentario declarante', 'otras observaciones',
]
TEMPLATE_SINGLE = set('(nn) xx 00 o | (n) a h sn no mm s an ss on => ¡0) aa aa a0 po pa ig tai oí'.split()) | {
    '.', ',', ';', ':', '-', '—', 'n', 'y', 'u', 'o', 'a', 'e', 'en', 'de', 'la', 'las', 'el', 'los',
    'que', 'para', 'por', 'con', 'del', 'al', 'un', 'una', 'su', 'sus', '(nn)', '(€)', '(€)?', '"',"'", ")
}


def read_words(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='ignore') as f:
        r = csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        for row in r:
            t = (row.get('text') or '').strip()
            try:
                conf = float(row.get('conf') or -1)
            except ValueError:
                conf = -1
            if not t or conf < 30:
                continue
            x, y, w, h = (int(row['left']), int(row['top']), int(row['width']), int(row['height']))
            if x / W_REF < 0.235 or x / W_REF > 0.995:  # columna izquierda de plantilla / borde
                continue
            out.append({'x': x, 'y': y, 'w': w, 'h': h, 't': t})
    return out


def lines_from(words, ygap=22):
    """Agrupa palabras en líneas (listas ordenadas por y)."""
    ws = sorted(words, key=lambda q: (q['y'], q['x']))
    lines = []
    for w_ in ws:
        placed = False
        for ln in lines:
            y0, y1 = ln['y0'], ln['y1']
            if not (w_['y'] > y1 + ygap or w_['y'] + w_['h'] < y0 - ygap):
                ln['words'].append(w_)
                ln['y0'] = min(ln['y0'], w_['y'])
                ln['y1'] = max(ln['y1'], w_['y'] + w_['h'])
                placed = True
                break
        if not placed:
            lines.append({'y0': w_['y'], 'y1': w_['y'] + w_['h'], 'words': [w_]})
    for ln in lines:
        ln['words'].sort(key=lambda q: q['x'])
        ln['text'] = ' '.join(q['t'] for q in ln['words'])
    lines.sort(key=lambda ln: ln['y0'])
    return lines


def is_template(text):
    t = norm(text)
    if len(t) < 3:
        return True
    words = [norm(x.strip('.,;:()')) for x in text.split()]
    if words and all(w in TEMPLATE_SINGLE for w in words):
        return True
    for ph in TEMPLATE_PHRASES:
        if ph in t:
            return True
    # líneas que son casi todo de plantilla conocido
    known = 0
    for w_ in words:
        if any(w_ == norm(p) for p in ('clase', 'situacion', 'fecha', 'derecho', 'titulo',
                                       'adquisicion', 'bien', 'pleno', 'dominio')) or w_ in TEMPLATE_SINGLE:
            known += 1
    return False
