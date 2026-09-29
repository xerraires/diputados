#!/usr/bin/env python3
"""Construye bienes_patrimoniales.xlsx con los bienes extraídos por diputado."""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

D = os.path.dirname(os.path.abspath(__file__))

bienes = json.load(open(f'{D}/bienes.json', encoding='utf-8'))
diputados = json.load(open(f'{D}/diputados.json', encoding='utf-8'))
if isinstance(diputados, dict):
    diputados = diputados['data']
mapa = {str(d['codParlamentario']): d for d in diputados}

PARTIDOS_ORDEN = ['PP', 'PSOE', 'PSC-PSOE', 'SUMAR', 'VOX', 'PsdeG-PSOE', 'PSE-EE (PSOE)',
                  'EAJ-PNV', 'ERC', 'JxCAT-JUNTS', 'EH Bildu', 'BNG', 'PSN-PSOE', 'PSIB-PSOE', 'UPN']

def part_key(p):
    return PARTIDOS_ORDEN.index(p) if p in PARTIDOS_ORDEN else 99

# índice de diputados por cod con datos generalizados = consolidado
por_cod = {}
for b in bienes:
    cod = str(b['cod'])
    if cod not in por_cod:
        d = mapa[cod]
        por_cod[cod] = {'diputado': d['apellidosNombre'], 'partido': b['partido'],
                        'grupo': b['grupo'], 'circunscripcion': b['circunscripcion'],
                        'items': []}
    por_cod[cod]['items'].append(b)

grupos = {}
for cod, info in por_cod.items():
    grupos.setdefault(info['partido'], {'diputados': set(), 'items': []})
    grupos[info['partido']]['diputados'].add(cod)
    grupos[info['partido']]['items'].extend(info['items'])

CATS = ['Inmueble urbano', 'Inmueble rústico', 'Inmueble de sociedad', 'Depósito o cuenta',
        'Valores, acciones y deuda pública', 'Vehículo o embarcación', 'Otros bienes o derechos',
        'Deuda o crédito', 'OBSERVACIONES']

def toks_count(it, cat):
    return sum(1 for i in it['items'] if i['seccion'] == cat)

def attrs_of(p):
    d = grupos[p]['diputados']
    its = grupos[p]['items']
    return len(d), len([i for i in its if i['seccion'] in CATS[:3]]), \
           len([i for i in its if i['seccion'] == 'Depósito o cuenta']), \
           len([i for i in its if i['seccion'] in CATS[4:7]]), \
           len([i for i in its if i['seccion'] == 'Deuda o crédito'])

HDR_FILL = PatternFill('solid', fgColor='0070C0')
TITLE_FONT = Font(bold=True, size=14)
HEAD_FONT = Font(bold=True, color='FFFFFF')
THIN = Side(style='thin', color='AAAACC')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

wb = wb_kwargs = None
wb = wb = None  # placeholder
wb = wb or None

from openpyxl import Workbook
wb = Workbook()

# ───────────── Hoja 1: Resumen por partido ─────────────
wsRes = wb.active
wsRes.title = 'Resumen por partido'
wsRes['A1'] = 'Bienes patrimoniales por partido — XV Legislatura (350 diputados)'
wsRes['A1'].font = TITLE_FONT
cols = ['Partido político', 'Diputados', 'Inmuebles urbanos', 'Inmuebles rústicos',
        '% diputados con más de 1 inmueble', 'Media de inmuebles por diputado',
        'Inmuebles de sociedad', 'Depósitos/cuentas', 'Valores/vehículos/otros', 'Deudas', 'Observaciones']
for j, h in enumerate(cols, 1):
    c = wsRes.cell(row=3, column=j, value=h)
    c.fill = HDR_FILL; c.font = HEAD_FONT; c.border = BORDER
    c.alignment = Alignment(horizontal='center', wrap_text=True)
wsRes.freeze_panes = 'A4'

cats3 = ([CATS[0], CATS[1], CATS[2], CATS[3], CATS[4], CATS[5], CATS[6]
          , CATS[7], CATS[8]])
r = 4
for p in sorted(grupos, key=part_key):
    an = grupos[p]['diputados']; its = grupos[p]['items']
    # inmuebles urbano+rústico+sociedad por diputado
    n_inm = {cod: sum(1 for i in por_cod[cod]['items']
                      if i['seccion'] in ('Inmueble urbano', 'Inmueble rústico', 'Inmueble de sociedad'))
             for cod in grupos[p]['diputados']}
    fila = [p, len(an)]
    for cat in [CATS[0], CATS[1], CATS[2], CATS[3], CATS[4], CATS[5], CATS[6], CATS[7]]:
        fila.append(sum(1 for i in its if i['seccion'] == cat))
    fila.insert(4, sum(1 for v in n_inm.values() if v > 1) / len(an))
    fila.insert(5, sum(n_inm.values()) / len(an))
    for j, v in enumerate(fila, 1):
        c = wsRes.cell(row=r, column=j, value=v); c.border = BORDER
        if j == 5:
            c.number_format = '0.0%'
        elif j == 6:
            c.number_format = '0.00'
    r += 1
r += 1
fila_tot = r - 2
wsRes.cell(row=r, column=1, value='TOTALES').font = Font(bold=True)
wsRes.cell(row=r, column=2, value=len(por_cod)).font = Font(bold=True)
for j in range(3, 12):
    cl = get_column_letter(j)
    if j in (5, 6):
        f = f'=SUMPRODUCT($B4:$B{fila_tot},{cl}4:{cl}{fila_tot})/SUM($B4:$B{fila_tot})'
    else:
        f = f'=SUM({cl}4:{cl}{fila_tot})'
    c = wsRes.cell(row=r, column=j, value=f)
    c.font = Font(bold=True)
    if j == 5:
        c.number_format = '0.0%'
    elif j == 6:
        c.number_format = '0.00'

for j, w in enumerate([30, 12, 16, 16, 15, 15, 18, 18, 22, 10, 16], 1):
    wsRes.column_dimensions[get_column_letter(j)].width = w

# ───────────── Hoja 2: Bienes por diputado y partido ─────────────
wsB = wb.create_sheet('Bienes por diputado')
wsB['A1'] = 'Detalle de bienes patrimoniales por diputado y partido'
wsB['A1'].font = TITLE_FONT
hdr = ['Partido', 'Diputado', 'Circunscripción', 'Cod. parl.', 'Categoría',
       'Tipología', 'Situación / lugar', 'Fecha adquisición', 'Derecho sobre el bien',
       'Título / valor (€)']
for j, h in enumerate(hdr, 1):
    c = wsB.cell(row=3, column=j, value=h)
    c.fill = HDR_FILL; c.font = HEAD_FONT; c.border = BORDER
    c.alignment = Alignment(horizontal='center', wrap_text=True)
wsB.freeze_panes = 'C4'
wsB.auto_filter.ref = f'A3:J{3 + sum(len(i["items"]) for i in por_cod.values())}'

r = 4
for p in sorted(grupos, key=part_key):
    for cod in sorted(grupos[p]['diputados']):
        info = por_cod[cod]
        for it in sorted(info['items'], key=lambda x: CATS.index(x['seccion'])):
            vals = [p, info['diputado'], info['circunscripcion'], cod, it['seccion'] if False else it.get('seccion', ''),
                    it.get('descripcion', ''), it.get('situacion', ''),
                    it.get('fecha', ''), it.get('derecho', ''), it.get('titulo', '')]
            for j, v in enumerate(vals, 1):
                c = wsB.cell(row=r, column=j, value=str(v) if isinstance(v, int) else v)
                c.border = BORDER
            r += 1

widths = [18, 32, 16, 10, 22, 46, 18, 16, 30, 24]
for j, w in enumerate(widths, 1):
    wsB.column_dimensions[get_column_letter(j)].width = w

# ───────────── Hoja 3: Diputados sin declaración ─────────────
wsN = wb.create_sheet('Sin declaración')
wsN['A1'] = 'Diputados sin Declaración de Bienes y Rentas publicada'
wsN['A1'].font = TITLE_FONT
for j, h in enumerate(['Diputado', 'Partido', 'Motivo'], 1):
    c = wsN.cell(row=3, column=j, value=h)
    c.fill = HDR_FILL; c.font = HEAD_FONT; c.border = BORDER
wsN.column_dimensions['A'].width = 34
wsN.column_dimensions['B'].width = 14
wsN.column_dimensions['C'].width = 46
r = 4
for d in diputados:
    cod = str(d['codParlamentario'])
    if cod not in por_cod:
        vals = [d['apellidosNombre'], d['formacion'],
                'Sin bienes declarados' if d.get('pdf_bienes') else 'Declaración aún no publicada (diputación de nueva entrada)']
        for j, v in enumerate(vals, 1):
            wsN.cell(row=r, column=j, value=v).border = BORDER
        r += 1

for s in wb.worksheets:
    s.sheet_view.zoomScale = 90

wb.save(f'{D}/bienes_patrimoniales.xlsx')
print('Excel generado:', f'{D}/bienes_patrimoniales.xlsx')
