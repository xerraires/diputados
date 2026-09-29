#!/usr/bin/env python3
"""Extrae bienes patrimoniales de los TSV OCR (páginas 2-4) por diputado.

Enfoque:
- Umbrales de sección desde rótulos de plantilla (palabras con x pequeña).
- Celdas por columna (rango x) con clustering vertical por columna.
- Cada celda "ancla" (descripción) capta las celdas más cercanas de otras
  columnas para formar la fila.
- Filtrado de frases de plantilla + ruido.
"""
import os, re, sys, unicodedata, csv, json

D = os.path.dirname(os.path.abspath(__file__))
W_REF = 2481.0


def norm(t):
    t = unicodedata.normalize('NFKD', t)
    return ''.join(c for c in t if not unicodedata.combining(c)).lower()


def read_words(path, fc_min=0.075):
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
            if not t or conf < 35:
                continue
            x, y, w, h = int(row['left']), int(row['top']), int(row['width']), int(row['height'])
            fc0, fc1 = x / W_REF, (x + w) / W_REF
            if fc1 < fc_min or fc0 > 0.995:
                continue
            out.append({'x': x, 'y': y, 'w': w, 'h': h,
                        'fc': (x + w / 2) / W_REF, 'fc0': fc0, 'fc1': fc1, 't': t})
    return out


def read_words_merged(path, fc_min=0.075):
    """psm4 como base + palabras de psm6 que no estén ya (por posición).
    El OCR psm6 pierde líneas (sobre todo tablas con celdas de distinta altura) que psm4 sí ve."""
    p4 = path.replace(f'{D}/ocr_tsv/', f'{D}/ocr_tsv_psm4/')
    w4 = read_words(p4, fc_min)
    w6 = read_words(path, fc_min)
    if not w4:
        return w6
    out = list(w4)
    for q in w6:
        if not any(abs(r['x'] - q['x']) < 28 and abs(r['y'] - q['y']) < 22 for r in w4):
            out.append(q)
    return out


def lines_from(words, ygap=18):
    ws = sorted(words, key=lambda q: (q['y'], q['x']))
    clusters = []
    for w_ in ws:
        c = None
        for cl in clusters:
            if not (w_['y'] > cl['y1'] + ygap or w_['y'] + w_['h'] < cl['y0'] - ygap):
                c = cl; break
        if c is None:
            clusters.append({'y0': w_['y'], 'y1': w_['y'] + w_['h'], 'ws': [w_]})
        else:
            c['ws'].append(w_)
            c['y0'] = min(c['y0'], w_['y']); c['y1'] = max(c['y1'], w_['y'] + w_['h'])
    for c in clusters:
        c['ws'].sort(key=lambda q: q['x'])
        c['text'] = re.sub(r'\s+', ' ', ' '.join(q['t'] for q in c['ws']))
        c['fc'] = min(q['fc0'] for q in c['ws'])
    clusters.sort(key=lambda c: c['y0'])
    return clusters


# -------------------------------- plantilla y ruido ------------------------------
TPL_P2 = [
    'bienes patrimoniales del parlamentario', 'clase y caracteristicas',
    'de adquisicion', 'situacion', 'titulo', 'derecho sobre el bien',
    'bienes inmuebles de naturaleza urbana', 'de naturaleza rústica',
    'bienes inmuebles de naturaleza', 'bienes inmuebles propiedad de una sociedad',
    'propiedad de una sociedad, comunidad o entidad que no cotiza',
    'en bolsa y de la que el declarante tiene acciones o participaciones',
    'depositos en cuentas corrientes o de ahorro',
    'cuentas financieras', 'otros tipos de imposiciones',
    'plaza aparcamiento local comercial',
    'nave industrial y las caracteristicas que procedan',
    'indicar provincia donde este situado el bien',
    'para bienes radicados en el extranjero, indicar el pais',
    'pleno dominio, nuda propiedad, usufructo, derecho',
    'de superficie, privativo, ganancial, en comunidad de bienes',
    'compraventa herencia donacion etc',
    'indicar la clase de deposito sin necesidad de senalar entidad bancaria',
    'deben declararse con el saldo',
    'de las posibilidades, debe aplicarse',
]
TPL_P3 = [
    'otros bienes o derechos', 'clase de bien o derecho',
    'descripcion del bien o derecho',
    'indicar sistema que se ha utilizado para su valoracion dineraria',
    'deuda publica, obligaciones, bonos, certificados', 'deposito, pagares',
    'y demas valores equivalentes', 'acciones y participaciones en todo tipo',
    'de sociedades, entidades con valor economico y cooperativas',
    'sociedades participadas en mas de un 5%', 'por otras sociedades o entidades',
    'que sean propiedad, en todo o en parte, del parlamentario declarante',
    'vehiculos, embarcaciones y aeronaves',
    'otros bienes, rentas o derechos', 'de contenido economico no',
    'declarados en apartados anteriores',
    'en mercados organizados debe reflejarse el valor de cotizacion',
    'no indicar matricula. incluir vehiculos',
    'embarcaciones o aeronaves propiedad de una sociedad que, no cotizando en bols',
    'de algun modo por el declarante, siempre que el parlamentario los utilice',
    'aunque sea ocasionalmente',
]
TPL_P4 = [
    'deudas y obligaciones patrimoniales', 'prestamos (descripcion y acreedor)',
    'concesion', 'concedido', 'importe', 'saldo', 'fecha.',
    'otras deudas y obligaciones derivadas de contratos, sentencias o cualquier',
    'otro titulo', 'observaciones',
    '(que el declarante hace constar para ampliar informacion que no le cupo',
    'esta declaracion y para dejar constancia de cuanto considere conveniente anadir',
    '14 a la fecha de 31 de diciembre del ejercicio anterior',
    'inmediatamente anterior a la fecha de la presente declaracion',
]
TPL_P4_OBS = TPL_P4 + [
    'deudas y obligaciones patrimoniales',
    'observaciones (que el declarante hace constar',
]


def strip_tpl(text, tpls):
    t = norm(text)
    # localiza y elimina las frases de plantilla reconocidas
    for ph in tpls:
        ln = ph.replace(' ', r'\W{0,4}')
        t = re.sub(rf'(^|\s){ln}(\W|$)', ' ', t)
    t = re.sub(r'\b(?:14|6|7|8|12|13)\b', ' ', t)
    t = re.sub(r'[^a-z0-9 €.,;%()/\'-]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' ,.-|')
    return t


ANCHOR_TPL = {
    2: ['bienes patrimoniales', 'del parlamentario', 'clase y caracteristicas',
        'clase y', 'caracteristicas', 'situacion', 'fecha de', 'adquisicion',
        'derecho sobre', 'titulo de', 'titulo',
        'deposito en cuenta', 'saldo de todos', 'indicar la clase',
        'depositos en cuentas', 'otros tipos de imposiciones',
        'plaza aparcamiento', 'indicar provincia', 'indicar si es piso',
        'pleno dominio nuda', 'compraventa herencia donacion'],
    3: ['otros bienes o derechos', 'descripcion', 'valor', 'clase de bien o derecho',
        'fecha de adquisicion', 'rentas', 'declarados', 'contenido'],
    4: ['prestamos (descripcion y acreedor)', 'otras deudas y obligaciones derivadas',
        'observaciones', 'sentencias o cualquier otro', 'obligaciones derivadas',
        'título.', 'y acreedor', 'titulo', 'descripcion y acreedor',
        '(descripcion', 'acreedor)'],
}

NOISE_WORDS = set("""
(nn) (n) xx 00 o a h sn no mm s an ss on => aa a0 po pa ig tai oi tf 4c 11 "
. , ; : - ' + * = # $ & % / \\ ) ( € ""
""".split())


def clean_join(words):
    # orden lectura: por línea (y) y dentro de línea por x
    ws = sorted(words, key=lambda q: (round(q['y'] / 22), q['x']))
    txt = re.sub(r'\s+', ' ', ' '.join(q['t'] for q in ws)).strip()
    return re.sub(r'\s*([.,;:€])\s*', r'\1 ', txt).strip()


def col_cells(words, fc_min, fc_max, gap):
    sel = sorted([q for q in words if fc_min <= q['fc'] <= fc_max], key=lambda q: q['y'])
    cells = []
    for w_ in sel:
        cur = cells[-1] if cells else None
        if cur is not None and not (w_['y'] > cur['y1'] + gap or w_['y'] + w_['h'] < cur['y0'] - gap):
            cur['ws'].append(w_)
            cur['y0'] = min(cur['y0'], w_['y']); cur['y1'] = max(cur['y1'], w_['y'] + w_['h'])
        else:
            cells.append({'y0': w_['y'], 'y1': w_['y'] + w_['h'], 'ws': [w_]})
    for c in cells:
        c['ws'].sort(key=lambda q: (q['y'], q['x']))
        c['text'] = clean_join(c['ws'])
        c['ycin'] = (c['y0'] + c['y1']) / 2
    return cells


def split_vertical_words(words, ysep=48):
    """Divide las celdas que mezclan 2+ líneas reales del formulario.
    Agrupa por líneas (like lines_from) y devuelve una lista de sub-celdas.
    Solo se aplica si la celda contiene saltos de línea reales (huecos y > ysep)."""
    if not words:
        return []
    if isinstance(words, dict):  # ya es una celda
        return [words]
    ys = sorted(set(w['y'] for w in words))
    # detectar huecos entre "líneas"
    groups = [[words[0]]]
    for w in sorted(words, key=lambda q: q['y'])[1:]:
        # línea nueva si la y está lejos de todas las y del grupo actual
        if all(abs(w['y'] - w2['y']) > ysep for w2 in groups[-1]):
            groups.append([w])
        else:
            groups[-1].append(w)
    if len(groups) <= 1:
        return [{'y0': min(w['y'] for w in words), 'y1': max(w['y']+w['h'] for w in words),
                 'ws': words, 'text': clean_join(words),
                 'ycin': (min(w['y'] for w in words) + max(w['y']+w['h'] for w in words)) / 2}]
    out = []
    for g in groups:
        g = sorted(g, key=lambda q: q['x'])
        y0 = min(w['y'] for w in g); y1 = max(w['y'] + w['h'] for w in g)
        out.append({'y0': y0, 'y1': y1, 'ws': g,
                    'text': clean_join(g), 'ycin': (y0+y1)/2})
    return out


def is_noise_cell(text):
    t = re.sub(r'\s+', ' ', norm(text)).strip(' .,;:()|-')
    if not re.search(r'[a-z]{3,}', t) and not re.search(r'\d{3,}', t):
        return True
    # artefactos de casillas marcadas / sellos: AAA, ATA, OOOO, SETE, A eee al, AAA OO...
    letters = re.sub(r'[^a-z]', '', t)
    if letters and len(set(letters)) <= 3 and len(letters) <= 7 and not re.search(r'\d{2,}', t):
        return True
    if re.fullmatch(r'(?:[aeo]{1,3}[\s.]*){1,6}', t):
        return True
    if re.fullmatch(r'(?:[ao]\s*){1,8}(?:\d{1,3}\s*){0,3}', t) and not re.search(r'\d{3,}', t):
        return True
    if re.fullmatch(r'(?:a\s+){0,3}e{2,4}\s*(?:al|a)?', t):
        return True
    ws = [norm(re.sub(r'[^\w]+', '', q)) for q in t.split()]
    ws = [w for w in ws if w]
    return not ws or all(w in NOISE_WORDS for w in ws)


def is_tpl_cell(text, tpls):
    t = norm(text)
    if len(t) < 2:
        return True
    t_sn = re.sub(r'[^a-z0-9]', '', t)
    for ph in tpls:
        if ph in t or re.sub(r'[^a-z0-9]', '', ph) in t_sn:
            return True
    if not re.search(r'[a-z0-9]', t):
        return True
    return False


def find_y(lines, *kws):
    for c in lines:
        t = norm(c['text'])
        if any(kw in t for kw in kws):
            return c['y0']
    return None



def unclaimed_rows(anchored_rows, others):
    used = {i: (r['cells'][k]) for r in anchored_rows for k, i in list((col, id(c)) for col, c in r['cells'].items())}
    used_ids = {id(c) for r in anchored_rows for c in r['cells'].values()}
    out = []
    for col, cs in others.items():
        for c in cs:
            if id(c) not in used_ids:
                out.append((col, c))
    return out

def rows_anchored(anchors, others, ytol=32):
    """anchors: dict col→celda; asigna de otros cols la celda más cercana."""
    rows = []
    for anc in anchors:
        row = {'anc': anc, 'cells': {anc['col']: anc}}
        for col, cs in others.items():
            best, dy = None, 1e9
            for c in cs:
                d = abs(c['ycin'] - anc['ycin'])
                if d < dy and d <= ytol + (anc['y1'] - anc['y0']):
                    best, dy = c, d
            if best:
                row['cells'][col] = best
        rows.append(row)
    return rows


def parse_page2(cod):
    raw = read_words_merged(f'{D}/ocr_tsv/{cod}-p2.tsv')
    data = read_words_merged(f'{D}/ocr_tsv/{cod}-p2.tsv', fc_min=0.08)
    if not raw: return []
    lines_all = lines_from(raw)
    y_rust = find_y(lines_all, 'rustica') or 1614
    y_soc = find_y(lines_all, 'sociedad, comunidad o entidad', 'propiedad de una sociedad') or 1897
    y_dep = find_y(lines_all, 'depositos en cuentas', 'salto de tod') or 2531
    if y_rust < 1000: y_rust = 1614
    if y_soc < 1500: y_soc = 1897
    if not (2200 < y_dep < 3000): y_dep = 2553
    y_foot = find_y(lines_all, 'indicar si es piso', 'aparcamiento') or 3035
    if y_foot < y_dep + 100: y_foot = 3037
    y_hdr = find_y(lines_all, 'clase y caracteristicas', 'caracteristicas de adquisicion') or 250
    datos = []
    # --- inmuebles
    anchors = []
    for c in col_cells(data, 0.23, 0.50, 45):
        if is_tpl_cell(c['text'], ANCHOR_TPL[2]) or is_noise_cell(c['text']): continue
        if c['y0'] >= y_dep or c['y1'] > y_foot - 30 or c['y0'] < y_hdr + 40: continue
        c['col'] = 'desc'; anchors.append(c)
    others = {}
    # excluye la cabecera de la tabla para que no contamine las celdas de la derecha
    # (la 2a línea de la cabecera, 'de adquisición', queda bajo y 400)
    data_body = [q for q in data if q['y'] > 450 and not (q['y'] < 450 and q['x'] > 1900)]
    for col, (a, b) in {'situ': (0.50, 0.66), 'fecha': (0.66, 0.79), 'der_tit': (0.79, 1.0)}.items():
        others[col] = [c for c in col_cells(data_body, a, b, 40)
                       if not is_tpl_cell(c['text'], TPL_P2) and c['y0'] < min(y_dep, y_foot) and not is_noise_cell(c['text'])]
        for c in others[col]: c['col'] = col
    for r in rows_anchored(anchors, others):
        def g(k):
            c = r['cells'].get(k)
            return c['text'] if c else ''
        y0 = r['anc']['y0']
        sec = ('Inmueble urbano' if not y_rust or y0 < y_rust
               else 'Inmueble rústico' if not y_soc or y0 < y_soc
               else 'Inmueble de sociedad')
        datos.append({'seccion': sec, 'descripcion': g('desc'),
                      'situacion': g('situ'), 'fecha': g('fecha'),
                      'derecho': g('der_tit'), 'titulo': ''})
    # --- depósitos
    a_dep = []
    for c in col_cells(data, 0.08, 0.68, 14):
        if is_tpl_cell(c['text'], TPL_P2) or is_noise_cell(c['text']): continue
        if c['y0'] < y_dep + 120 or c['y1'] > y_foot - 30: continue
        c['col'] = 'desc'; a_dep.append(c)
    o_dep = {}
    for col, (a, b) in {'saldo': (0.68, 0.94)}.items():
        o_dep[col] = []
        for c0 in col_cells(data, a, b, 40):
            for c in split_vertical_words(c0['ws']):
                if is_tpl_cell(c['text'], TPL_P2):
                    # puede ser el rótulo pegado al valor: separar
                    txt = re.sub(r'SALDO\W*\d*\W+de\W+TODOS\W+los\W+DEPOSITOS\W*\(\W*€\W*\)?', ' ', c['text'], flags=re.I)
                    txt = txt.strip(' .,;:|-')
                    if not txt or is_noise_cell(txt) or not re.search(r'\d{2,}', txt):
                        continue
                    if not (c['y0'] > y_dep + 60 and c['y1'] < y_foot - 30):
                        continue
                    c2 = dict(c); c2['text'] = txt
                    o_dep[col].append(dict(c2, col=col))
                    continue
                if c['y0'] > y_dep + 60 and c['y1'] < y_foot - 30 and not is_noise_cell(c['text']):
                    o_dep[col].append(dict(c, col=col))
    dep_rows = rows_anchored(a_dep, o_dep)
    for r in dep_rows:
        def g(k):
            c = r['cells'].get(k)
            return c['text'] if c else ''
        datos.append({'seccion': 'Depósito o cuenta', 'descripcion': g('desc'),
                      'situacion': '', 'fecha': '', 'derecho': '', 'titulo': g('saldo')})
    orf = {}
    for col, c in unclaimed_rows(dep_rows, o_dep):
        placed = False
        for ykey in list(orf):
            if abs(ykey - c['y0']) <= 55:
                if col == 'saldo': orf[ykey]['saldo'] = c['text']
                placed = True; break
        if not placed and col == 'saldo':
            orf[c['y0']] = {'saldo': c['text']}
    for ykey in sorted(orf):
        datos.append({'seccion': 'Depósito o cuenta', 'descripcion': '',
                      'situacion': '', 'fecha': '', 'derecho': '',
                      'titulo': orf[ykey].get('saldo', '')})
    return datos


def parse_page3(cod):
    raw = read_words_merged(f'{D}/ocr_tsv/{cod}-p3.tsv')
    data = read_words_merged(f'{D}/ocr_tsv/{cod}-p3.tsv', fc_min=0.08)
    if not raw: return []
    lines_all = lines_from(raw)
    y_veh = find_y(lines_all, 'vehiculos, embarcaciones', 'embarcaciones y aeronaves') or 1966
    y_otros = find_y(lines_all, 'apartados anteriores', 'declarados en apartados', 'rentas o derechos') or 2478
    if not (1500 < y_veh < 2600): y_veh = 1966
    if not (2000 < y_otros < 3200): y_otros = 2478
    if y_otros < y_veh: y_otros = 99999
    y_foot3 = find_y(lines_all, 'contable', 'elegida', 'matricula') or 3035
    y_hdr3 = find_y(lines_all, 'indicar sistema', 'valoracion dineraria') or 480
    if y_foot3 < y_otros + 100: y_foot3 = 3035
    if not (300 < y_hdr3 < 700): y_hdr3 = 480
    cap_val = min(y_veh, y_foot3)
    a_val = []
    for c in col_cells(data, 0.33, 0.84, 14):
        if c['y0'] >= cap_val or c['y0'] < y_hdr3 + 40: continue
        if is_tpl_cell(c['text'], ANCHOR_TPL[3]) or is_noise_cell(c['text']): continue
        c['col'] = 'desc'; a_val.append(c)
    o_val = {'valor': [dict(c, col='valor') for c in col_cells(data, 0.84, 0.99, 40)
                       if not is_noise_cell(c['text']) and c['y0'] < cap_val and c['y1'] > y_hdr3 + 20]}
    for r in rows_anchored(a_val, o_val):
        def g(k):
            c = r['cells'].get(k)
            return c['text'] if c else ''
        datos = []
        datos.append({'seccion': 'Valores, acciones y deuda pública',
                      'descripcion': g('desc'), 'situacion': '', 'fecha': '',
                      'derecho': '', 'titulo': g('valor')})
    # --- vehículos
    a_veh = []
    for c in col_cells(data, 0.28, 1.0, 14):
        t = c['text']
        if is_tpl_cell(t, ANCHOR_TPL[3]) or is_noise_cell(t): continue
        if not (y_veh + 40 <= c['y0'] < min(y_otros, y_foot3 - 30)): continue
        # desc tiene que empezar a la derecha de la fecha; la fecha va a su x
        c['col'] = 'desc'; a_veh.append(c)
    o_veh = {'fecha': [dict(c, col='fecha') for c in col_cells(data, 0.08, 0.28, 14)
                       if not is_tpl_cell(c['text'], TPL_P3) and y_veh + 40 <= c['y0'] < min(y_otros, y_foot3 - 30)]}
    out_veh = 0
    # --- otros bienes
    a_otr = []
    for c in col_cells(data, 0.23, 0.83, 14):
        if is_tpl_cell(c['text'], ANCHOR_TPL[3]) or is_noise_cell(c['text']): continue
        if not (c['y0'] >= y_otros + 50 and c['y1'] < y_foot3 - 30): continue
        c['col'] = 'desc'; a_otr.append(c)
    o_otr = {'valor': [dict(c, col='valor') for c in col_cells(data, 0.83, 0.99, 40)
                       if not is_tpl_cell(c['text'], TPL_P3) and c['y0'] >= y_otros + 50 and c['y1'] < y_foot3 - 30]}
    datos = []
    append = datos.extend
    for r in rows_anchored(a_val, o_val):
        append([{'seccion': 'Valores, acciones y deuda pública',
                 'descripcion': r['cells']['desc']['text'],
                 'situacion': '', 'fecha': '',
                 'derecho': '', 'titulo': (r['cells'].get('valor', {}).get('text') or '')}])
    for r in rows_anchored(a_veh, o_veh):
        f = r['cells'].get('fecha', {}).get('text') or ''
        d = r['cells']['desc']['text']
        if not (f or d):
            continue
        append([{'seccion': 'Vehículo o embarcación', 'descripcion': d,
                 'situacion': '', 'fecha': f, 'derecho': '', 'titulo': ''}])
    for r in rows_anchored(a_otr, o_otr):
        append([{'seccion': 'Otros bienes o derechos', 'descripcion': r['cells']['desc']['text'],
                 'situacion': '', 'fecha': '', 'derecho': '',
                 'titulo': (r['cells'].get('valor', {}).get('text') or '')}])
    return datos


def parse_page4(cod):
    raw = read_words_merged(f'{D}/ocr_tsv/{cod}-p4.tsv')
    data = read_words_merged(f'{D}/ocr_tsv/{cod}-p4.tsv', fc_min=0.08)
    if not raw: return [], ''
    lines_all = lines_from(raw)
    y_obs = find_y(lines_all, 'observaciones') or 1612
    y_lo4 = max(find_y(lines_all, 'otras deudas y obligaciones derivadas') or 877,
                find_y(lines_all, 'prestamos (descripcion') or 877)
    y_deu = find_y(lines_all, 'prestamos (descripcion y acreedor)', 'prestamos (descripcion',
                   'prestamos descripcion', 'descripcion y acreedor', '(descripcion y acreedor)')
    if y_deu is None:
        # el rótulo se puede partir en dos líneas ('DEUDAS Y OBLIGACIONES PATRIMONIALES' / 'PRESTAMOS...')
        # usar el rótulo superior como referencia y sumar ~80 px
        y2 = find_y(lines_all, 'deudas y obligaciones patrimoniales')
        if y2 is None:
            # o venir todo en la 1ª línea con datos ('PRESTAMO a HIPOTECARIO PRESTAMOS BBK (DESCRIPCIÓN...')
            for c in lines_all[:3]:
                tn = norm(c['text'])
                if ('prestamo' in tn or 'credito' in tn) and 'acreedor' in tn:
                    y2 = c['y0']; break
        y_deu = (y2 + 80) if y2 and 250 < y2 < 1000 else 503
    if not (250 < y_deu < 1400): y_deu = 503
    if not (700 < y_obs < 3200): y_obs = 1612
    a_deu = []
    for c0 in col_cells(data, 0.06, 0.62, 45):
      for c in split_vertical_words(c0['ws']):
        # separa el rótulo de plantilla si se pegó a la 1ª fila real (misma celda OCR)
        txt = c['text']
        txt = re.sub(r'(?i)^\W*[AOo0]{2,}\W*(?=\w)', ' ', txt)  # 'OOOO] Hyundai...' → 'Hyundai...'
        txt = re.sub(r'PRESTAMOS?\W*\(\s*DESCRIPCI\w*\W*(?:DEUDAS\W+Y\W+OBLIGACIONES\W+)?Y\W*ACREEDOR\s*\)', ' ', txt, flags=re.I)
        txt = re.sub(r'PRESTAMOS?\W*\(\s*DESCRIPCI\w*\W*(?:[A-Za-z]{1,3}\s*)?Y\W*ACREEDOR\s*\)', ' ', txt, flags=re.I)  # variante con 'p' suelta
        txt = re.sub(r'PRESTAMOS?\W*\(\s*DESCRIPCI\w*\W*[^)]{0,12}\)', ' ', txt, flags=re.I)  # variante truncada
        txt = re.sub(r'\(?\s*DESCRIPCI\w*\s*(?:\w{1,3}\s*)?ACREEDOR\s*\)?', ' ', txt, flags=re.I)  # resto de rotulo
        txt = re.sub(r'(?:DEUDAS?\W+Y\W+OBLIGACIONES|OBLIGACIONES\W+DEUDAS?|PRESTAMOS?|Y)\s*', ' ', txt, flags=re.I)  # restos
        txt = re.sub(r'otras?\W+deudas\W+y\W+obligaciones\W+derivadas?\W+de?\W*contratos?\W*,?\W*sentencias?\W+(?:o\W+)?cualquier\W+otro\W+t[ií]tulo\.?', ' ', txt, flags=re.I)
        txt = re.sub(r'\W*sentencias?\W+cualquier\W+otro\W*(?:t[ií]tulo\.?)?', ' ', txt, flags=re.I)
        txt = re.sub(r'otras?\W+(?:deudas\W+y\W+)?obligaciones\W+derivadas?\W*(?:de\W+)?(?:contratos?\W*,?\W*o?)?', ' ', txt, flags=re.I)
        txt = re.sub(r'(?:de\W+)?contratos?\W*,?\W*(?:sentencias?\W+)?(?:o\W+)?cualquier\W+otro\W*(?:t[ií]tulo\.?)?', ' ', txt, flags=re.I)
        txt = re.sub(r'otras?\W+(?:derivadas?\W*)?(?:de\W+)?(?:contratos?\W*(?:o)?)?', ' ', txt, flags=re.I)
        txt = re.sub(r'otras?\W+deudas\W+y\W+obligaciones\W+derivadas?', ' ', txt, flags=re.I)
        txt = re.sub(r'(?:de\W+)?contratos?\W*,?\W*sentencias?\W+(?:o\W+)?cualquier\W+otro\W+t[ií]tulo\.?', ' ', txt, flags=re.I)
        txt = txt.strip(' .,;:|-')
        if not txt or is_tpl_cell(txt, ANCHOR_TPL[4]) or is_noise_cell(txt): continue
        if c['y0'] >= y_obs or c['y1'] < y_deu + 40: continue
        c2 = dict(c); c2['text'] = txt
        c2['col'] = 'desc'; a_deu.append(c2)
    o_deu = {}
    for col, (a, b) in {'fecha': (0.62, 0.72), 'importe': (0.72, 0.845), 'saldo': (0.845, 1.0)}.items():
        o_deu[col] = []
        for c0 in col_cells(data, a, b, 40):
            if is_tpl_cell(c0['text'], ANCHOR_TPL[4]):
                continue
            for c in split_vertical_words(c0['ws']):
                if y_deu + 40 <= c['y0'] < y_obs:
                    o_deu[col].append(dict(c, col=col))
    deu = []
    deu_rows = rows_anchored(a_deu, o_deu, ytol=90)
    for r in deu_rows:
        def g(k):
            c = r['cells'].get(k)
            return c['text'] if c else ''
        d = r['cells']['desc']['text']
        if not d or is_tpl_cell(d, TPL_P4):
            continue
        f, im, sa = g('fecha'), g('importe'), g('saldo')
        # desc con solo resto de plantilla + filas con solo rótulos de la cabecera → descartar
        dn = norm(d)
        if re.fullmatch(r'(?:otras?|de|sentencias|cualquier|otro|derivadas|contratos|obligaciones|titulo|\s|,|\.)*', dn or ' '):
            continue
        fu = f.upper()
        if ('CONCES' in fu and not re.search(r'\d', f)) or ('IMPORTE' in im.upper() and not re.search(r'\d', im)) or ('SALDO PEND' in sa.upper() and not re.search(r'\d', sa)):
            continue
        deu.append({'seccion': 'Deuda o crédito', 'descripcion': d, 'situacion': '',
                    'fecha': f, 'derecho': im, 'titulo': sa})
    orf = {}
    for col, c in unclaimed_rows(deu_rows, o_deu):
        placed = False
        for ykey in list(orf):
            if abs(ykey - c['y0']) <= 60:
                orf[ykey][col] = c['text']; placed = True; break
        if not placed:
            orf[c['y0']] = {col: c['text']}
    for ykey in sorted(orf):
        m = orf[ykey]
        f, im, sa = m.get('fecha', ''), m.get('importe', ''), m.get('saldo', '')
        # descartar rótulos de la cabecera sin datos reales
        fu, iu, su = f.upper(), im.upper(), sa.upper()
        if ('CONCES' in fu and not re.search(r'\d', f)) and not re.search(r'\d', im + sa):
            continue
        if 'IMPORTE' in iu and 'CONCED' in iu and not re.search(r'\d', im):
            if 'SALDO PEND' in su and not re.search(r'\d', sa):
                continue
        if 'FECHA' in fu and 'CONCES' in fu and not re.search(r'\d', f) and not re.search(r'\d', im + sa):
            continue
        if re.search(r'\d', im + sa):
            pass  # hay importe o saldo real
        elif not re.search(r'\d', f):
            continue
        deu.append({'seccion': 'Deuda o crédito', 'descripcion': '', 'situacion': '',
                    'fecha': f, 'derecho': im, 'titulo': sa})
    obs_words = sorted([q for q in data if q['y'] + q['h'] / 2 > (y_obs if y_obs else 1e9)],
                       key=lambda q: (q['y'], q['x']))
    obs_txt = strip_tpl_obs_lines(obs_words) if obs_words else ''
    return deu, obs_txt


OBS_VOCAB = {
    'observaciones', 'declaracion', 'declarante', 'hace', 'constar', 'ampliar',
    'informacion', 'cupo', 'otros', 'apartados', 'esta', 'dejar', 'constancia',
    'cuanto', 'considera', 'conveniente', 'anadir', 'considere', 'que', 'el',
    'en', 'de', 'la', 'los', 'que', 'para', 'y', 'no', 'le', 'a', 'o', 'del',
    'fecha', 'dia', 'presente', 'anterior', 'diciembre', 'ejercicio', 'mes',
    'cualquier', 'inmediatamente', 'ala', 'laa', 'enl', 'para',
}


def strip_tpl_obs_lines(words):
    import re as _re
    lines = lines_from(sorted(words, key=lambda q: q['y']), ygap=20)
    out = []
    for ln in lines:
        t = re.sub(r'\s+', ' ', norm(ln['text'])).strip()
        if is_noise_cell(ln['text']):
            continue
        toks = [w.strip(' .,;:()12-') for w in t.split()]
        toks = [w for w in toks if w]
        toks3 = [w for w in re.sub(r'[^a-z0-9]+', ' ', t).split()]
        if toks3 and sum(w in OBS_VOCAB or w.isdigit() for w in toks3) / len(toks3) >= 0.8:
            continue
        out.append(ln['text'])
    return ' '.join(out)


def strip_tpl_obs(txt):
    t = ' ' + norm(txt).strip() + ' '
    tpls = [
        'observaciones', '(que el declarante hace constar para ampliar informacion que no le cupo',
        'en otros apartados de esta declaracion y para dejar constancia de cuanto considere conveniente anadir',
        'que el declarante hace constar para ampliar informacion que no le cupo en otros apartados de esta',
        'declaracion y para dejar constancia de cuanto considere conveniente anadir',
        'hace constar para ampliar informacion', 'en otros apartados de esta declaracion y para dejar',
        'constancia de cuanto considere conveniente anadir', 'que no le cupo en otros apartados de esta',
        '14 a la fecha de 31 de diciembre del ejercicio anterior a la declaracion o cualquier dia del',
        'mes inmediatamente anterior a la fecha de la presente declaracion',
        'deudas y obligaciones patrimoniales',
    ]
    for ph in tpls:
        ph = re.escape(ph).replace(r'\ ', r'(?:\W{0,2}|\s){1,2}').replace(r"\(", r"\W{0,3}").replace(r"\)", r"\W{0,3}")
        t = re.sub(rf'(^|\W){ph}(\W|$)', ' ', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'[^a-z0-9 €.,;()%/\']', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def limpiar_bienes(bienes):
    """Limpieza final: rótulos pegados, ruido de casillas y filas sin contenido real."""
    out = []
    for x in bienes:
        d = (x.get('descripcion') or '').strip()
        v = (x.get('titulo') or '').strip()
        f = (x.get('fecha') or '').strip()
        sec = x.get('seccion', '')
        drop = None
        if re.search(r'(?i)saldo\W*de\W*todos\W*los\W*deposit', v) and not re.search(r'\d[\d.,]*\s*(?:€|euros|eur\b)', v, re.I) and not re.search(r'\d{2}[.,]\d{2}', v):
            drop = 'orf rotulo saldo'
        elif re.search(r'(?i)veh[íi]culos\W*,?\W*embarcaciones\W+y\W+aeronaves', d) and len(d) < 60:
            drop = 'rotulo vehículos'
        elif re.fullmatch(r'(?i)aaa\s+ningun[oa]', d):
            drop = 'AAA NINGUNA'
        elif re.fullmatch(r'(?i)ningun[oa]?', d) and sec in ('Deuda o crédito', 'Vehículo o embarcación'):
            drop = 'NINGUNO en deuda/vehículo'
        elif re.fullmatch(r'(?i)descr\w{0,4}', d) and sec == 'Vehículo o embarcación':
            drop = 'DESCR'
        elif sec == 'OBSERVACIONES':
            dn = re.sub(r'[^a-záéíóúñ ]', ' ', d.lower())
            dn = re.sub(r'\s+', ' ', dn).strip()
            toks = dn.split()
            vocab = {'clase','situacion','fecha','derecho','de','y','caracteristicas','declarante','bienes','inmuebles','tiene','acciones','otros','participaciones','bien','naturaleza','que','el','la','los','en'}
            if toks and sum(t in vocab for t in toks) / len(toks) >= 0.8 and not re.search(r'\d{2,}', d):
                drop = 'observaciones=rotulo'
        if drop:
            continue
        out.append(x)
    return out


def parse_diputado(cod):
    bienes = parse_page2(cod) + parse_page3(cod)
    deu, obs_txt = parse_page4(cod)
    bienes += deu
    if obs_txt:
        bienes.append({'seccion': 'OBSERVACIONES', 'descripcion': obs_txt,
                       'situacion': '', 'fecha': '', 'derecho': '', 'titulo': ''})
    return limpiar_bienes(bienes)


def main(cods=None):
    with open(f'{D}/diputados.json', encoding='utf-8') as f:
        diputados = json.load(f)
    if isinstance(diputados, dict):
        diputados = diputados['data']
    mapa = {d['codParlamentario']: d for d in diputados}
    if not cods:
        cods = [l.strip() for l in open(f'{D}/lista_codigos.txt') if l.strip()]
    bienes = []
    for cod in cods:
        d = mapa[int(cod)]
        if not d.get('pdf_bienes'):
            continue
        try:
            lineas = parse_diputado(cod)
        except Exception as e:
            print(f'  ERROR {cod}: {e}'); lineas = []
        for ln in lineas:
            ln.update({'cod': cod, 'nombre': d['apellidosNombre'],
                       'partido': d['formacion'], 'grupo': d['grupo'],
                       'circunscripcion': d['nombreCircunscripcion']})
            bienes.append(ln)
        if not lineas:
            print(f'  {cod} {d["apellidosNombre"]}: sin bienes detectados (¿decl. en blanco?)')
    with open(f'{D}/bienes.json', 'w', encoding='utf-8') as f:
        json.dump(bienes, f, ensure_ascii=False, indent=1)
    print(f'Total entradas: {len(bienes)} sobre {len(cods)} diputados')


if __name__ == '__main__':
    main()
