#!/usr/bin/env python3
"""Genera data.js para la web interactiva desde bienes.json + diputados.json."""
import json, os, re

D = os.path.dirname(os.path.abspath(__file__))

bienes = json.load(open(f'{D}/bienes.json', encoding='utf-8'))
diputados = json.load(open(f'{D}/diputados.json', encoding='utf-8'))
if isinstance(diputados, dict):
    diputados = diputados['data']

def clean(s):
    if not s:
        return ''
    s = re.sub(r'\s+', ' ', str(s)).strip()
    s = re.sub(r'^[|lL|:;,.\s-]+', '', s) if len(s) < 3 else s
    s = s.replace(' | ', ' ').replace('| ', ' ').replace(' |', ' ')
    s = re.sub(r'^|\|', '', s)
    s = re.sub(r'\|', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -,;:.|')
    return norm_num(s)

INMUEBLES = ('Inmueble urbano', 'Inmueble rústico', 'Inmueble de sociedad')
TODAS = ['Inmueble urbano', 'Inmueble rústico', 'Inmueble de sociedad', 'Depósito o cuenta',
         'Valores, acciones y deuda pública', 'Vehículo o embarcación', 'Otros bienes o derechos',
         'Deuda o crédito', 'OBSERVACIONES']

# ─── Normalización de números OCR: '13. 600' → '13.600', '11752, 31' → '11752,31' ───
def norm_num(s):
    for _ in range(3):
        s = re.sub(r'(\d)[.,]\s+(?=\d)', lambda m: m.group(1), s)
    return s

# ─── Clasificación de titularidad del inmueble: P plena / I indiviso / '' sin dato ───
KW_I = re.compile(r'nuda|usufruct|usufrut|multipropied|indiviso|comunidad de bienes|ganancial|'
                  r'compart|proindiviso|copropiet|\b1/\d|mitad|tercio|media\b|cuart|½|¾|en com[uú]n|'
                  r'(?:sexta|quinta|s[eé]ptima|octava|novena|d[eé]cima)\s+parte|al[íi]cuota', re.I)
KW_P = re.compile(r'pleno|privativo|propiedad|propietari', re.I)

def clasif_derecho(derecho):
    d = norm_num(str(derecho or ''))
    if not d.strip():
        return ''
    pcts = [int(p) for p in re.findall(r'(\d{1,3})\s*%', d)]
    kw_i = bool(KW_I.search(d))
    todo100 = bool(pcts) and all(p == 100 for p in pcts)
    if (kw_i or any(p < 100 for p in pcts)) and not (todo100 and not kw_i):
        return 'I'
    if KW_P.search(d) or todo100:
        return 'P'
    return ''

por_cod = {}
for d in diputados:
    cod = str(d['codParlamentario'])
    por_cod[cod] = {
        'cod': cod,
        'nombre': d['apellidosNombre'],
        'partido': d['formacion'],
        'grupo': d.get('grupo', ''),
        'circ': d['nombreCircunscripcion'],
        'pdf': d.get('url_ficha_bienes', ''),
        'items': [],
    }

for b in bienes:
    cod = str(b['cod'])
    if cod in por_cod:
        por_cod[cod]['items'].append({
            's': b['seccion'],
            'd': clean(b.get('descripcion', '')),
            'l': clean(b.get('situacion', '')),
            'f': clean(b.get('fecha', '')),
            'r': clean(b.get('derecho', '')),
            'v': clean(b.get('titulo', '')),
            'o': b.get('_fuente', ''),
            'pr': (b.get('_pr') or (clasif_derecho(b.get('derecho', '')) if b['seccion'] in INMUEBLES else '')) or '',
        })

out = list(por_cod.values())
out.sort(key=lambda x: (x['apellidos'] if False else x['nombre']))

data = 'const DIPUTADOS = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';'
with open(f'{D}/data.js', 'w', encoding='utf-8') as f:
    f.write(data)

n_items = sum(len(d['items']) for d in out)
n_inm = sum(1 for d in out if False)
n_inm = sum(len([i for i in d['items'] if i['s'] in INMUEBLES]) for d in out)
print(f'data.js generado: {len(out)} diputados, {n_items} bienes, {n_inm} inmuebles')
