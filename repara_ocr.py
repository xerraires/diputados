#!/usr/bin/env python3
"""Saneamiento verificado de bienes.json (corrección de errores de OCR).

Todas las correcciones están verificadas contra los TXT OCR (ocr_txt/) y, en los
casos más delicados (depósitos e inmuebles de 129 y 324, inmuebles de 12),
contra las imágenes del PDF oficial (obs_png/129_p2-2.png, obs_png/324_p2-2.png,
obs_png/12_p2chk-2.png).

Efectos:
 1. DEP_NINGUNO: elimina las 31 filas 'Ninguno/a' (marcadas 'nada que declarar'
    en el formulario). Sin descripción, fecha, derecho ni valor → no son bienes.
 2. DEP_MULTINUM: reparte saldos fusionados por el OCR entre sus filas reales
    (verificados línea a línea en el PDF).
 3. REC reclasifica 2 filas (324 y 12).
 4. FIX retoques menores de transcripción OCR (fechas, valores, ruido).

Idempotente: puede ejecutarse varias veces sin duplicar ni dañar.
"""
import json
import os
import re
import sys
import shutil
from datetime import date

D = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(D, 'bienes.json')

CODE = ' [CORREGIDO 29-09-2025] '

# ── 1) Filas 'Ninguno/a' a eliminar: (cod, seccion, descripcion_exacta) ──
DEP_NINGUNO = [
    ('10',  'Valores, acciones y deuda pública', 'Ninguna'),
    ('103', 'Valores, acciones y deuda pública', 'NINGUNO'),
    ('103', 'OBSERVACIONES', 'NINGUNA'),
    ('129', 'Valores, acciones y deuda pública', 'NINGUNA'),
    ('150', 'Inmueble rústico', 'NINGUNO'),
    ('150', 'Valores, acciones y deuda pública', 'NINGUNA'),
    ('150', 'Valores, acciones y deuda pública', '| NINGUNA'),
    ('159', 'Inmueble urbano', 'Ninguno'),
    ('159', 'Inmueble rústico', 'Ninguno'),
    ('159', 'Valores, acciones y deuda pública', 'Ninguno'),
    ('159', 'Valores, acciones y deuda pública', 'Ninguna'),
    ('159', 'OBSERVACIONES', 'Ninguna'),
    ('229', 'Inmueble urbano', 'Ninguno'),
    ('229', 'Inmueble rústico', 'Ninguno'),
    ('229', 'Valores, acciones y deuda pública', 'Ninguno'),
    ('231', 'Valores, acciones y deuda pública', 'NINGUNA'),
    ('232', 'Inmueble urbano', 'NINGUNO'),
    ('232', 'Inmueble rústico', 'NINGUNO'),
    ('232', 'Valores, acciones y deuda pública', 'NINGUNA'),
    ('406', 'Inmueble rústico', 'NINGUNO'),
    ('406', 'Valores, acciones y deuda pública', 'NINGUNO'),
    ('406', 'Valores, acciones y deuda pública', '| NINGUNO'),
    ('406', 'Valores, acciones y deuda pública', 'NINGUNA'),
    ('48',  'Inmueble urbano', 'NINGUNO'),
    ('48',  'Inmueble rústico', 'NINGUNO'),
    ('48',  'Valores, acciones y deuda pública', 'NINGUNO'),
    ('48',  'Valores, acciones y deuda pública', 'NINGUNA'),
    ('79',  'Inmueble urbano', 'Ninguno'),
    ('79',  'Inmueble rústico', 'Ninguno'),
    ('79',  'Valores, acciones y deuda pública', 'Ninguna'),
]
# además, este 'nada que declarar' lo pilló el OCR con ruido de casillas:
DEP_NINGUNO_LIKE = [  # (cod, seccion, prefijo descripcion) - suburbano pero real
    ('150', 'Inmueble de sociedad', '| minGuno'),
    ('150', 'Vehículo o embarcación', 'AAA A A A A AIM A ¿A QA'),
]

def match_dep(x, e):
    return (x['cod'] == e[0] and x['seccion'] == e[1]
            and (x.get('descripcion') or '').strip() == e[2]
            and not (x.get('titulo') or '').strip()
            and not (x.get('fecha') or '').strip()
            and not (x.get('derecho') or '').strip())

# ── 2) Depósitos fusionados: reconstrucción fiel al PDF ──────────────────────
# Cada entrada sustituye TODAS las filas Depósito o cuenta de ese cod por la
# lista correcta (leída del PDF original).
DEP_MULTINUM = {
    # Asón Escalante (Verificado: obs_png/129_p2-2.png). El '450.000' de la
    # ahorro estaba desplazado a la fila de la cuenta corriente.
    '129': [
        'CUENTA DE AHORRO ABANCA|450.000',
        'CUENTA CORRIENTE ABANCA|2.000',
    ],
    # Argota Castro: 4 cuentas (3 con saldo) + PLAN DE PENSIONES sin saldo
    '103': [
        'PLAN DE PENSIONES LA CAIXA|11.752,31',
        'CUENTA CORRIENTE|5.153,92',
        'CUENTA CORRIENTE COMPARTIDA CON MI HERMANA|11.768,43',
        'CUENTA CORRIENTE|36,80',
    ],
    # Giménez Rahola (+ presupuesto transfugas S.A.): 3 depósitos + 1 fondo
    '107': [
        'CUENTAS AHORRO|9.786,85',
        'CUENTAS GESTIONADAS POR BBVA Y ATL CAPITAL|734.869,65',
        'PRESUPUESTO TRANSFUGAS S.A.|18.901,17',
        'FONDO DE INVERSIÓN|',
    ],
    # Falces Gabilondo: 3 cuentas (2 con saldo)
    '189': [
        '2 CUENTAS CORRIENTES|19.208,79',
        '1 PLAN DE PENSIONES|105.378,10',
        '1 FONDO DE INVERSIÓN|81.449,20',
    ],
    # Casares Vidal: 3 cuentas (2 con saldo)
    '221': [
        'Cuentas corrientes|9.300,00',
        'Plan de previsión|4.890,75',
        'Plan de ahorro|21.072,59',
    ],
    # Villagrasa Royo: 4 depósitos
    '245': [
        'depósito (50%)|2.307,15',
        'depósito (100%)|16.017,81',
        'depósito (100%)|2.420,22',
        'depósito (50%)|4.460,29',
    ],
    # Sanjurjo Río: 3 depósitos
    '253': [
        'DEPÓSITOS EN CUENTAS CORRIENTES|67.851,83 €',
        'FONDOS DE INVERSIÓN|60.613,97 €',
        'PLAN DE PENSIONES DE EMPLEO|84.406,64 €',
    ],
    # Ortiz Vargas: 3 depósitos
    '320': [
        'CUENTAS CORRIENTES Y DE AHORRO (PARTE GANANCIAL)|28.475,21 €',
        'PLANES DE PENSIONES|113.481 €',
        'FONDOS DE INVERSION (PARTE GANANCIAL)|33.623 €',
    ],
    # Pradas Banks: 3 cuentas
    '328': [
        'Cuenta Corriente|56.604,87',
        'Cuenta Corriente|1.525,90',
        'Cuenta a plazo|10.000',
    ],
    # Gutiérrez Vicén: 3 cuentas
    '331': [
        'Cuentas corrientes|45.302,72 €',
        'Plan de pensiones|45.514,96 €',
        'Seguro Universal vida y pensión|27.259,88 €',
    ],
    # Rozalén Orza: 4 depósitos
    '399': [
        'SALDO MEDIO|25.161',
        'PLANES PENSIONES|20.700',
        'SEGUROS AHORRO|8.656',
        'AHORRO PLAZO|2.300',
    ],
    # Puig Doria: 4 depósitos
    '59': [
        'Cuentas corrientes en diversas entidades financieras (31/07/2023)|67.656',
        'Planes pensiones privados|101.841',
        'Fondos de inversión|40.435',
        'Planes de previsión social empresarial (Cortes Generales)|5.651,60',
    ],
    # Crabiffosse Coman: 4 depósitos
    '69': [
        'CAIXAFUTURO|17.242,96 €',
        'VALOR FUTURO 10 UL|5.183,32 €',
        'CUENTA CORRIENTE|4.000,00 €',
        'CUENTA DE AHORRO COMÚN|9.519,59 €',
    ],
    # Otxoa Oficialdegui: 2 cuentas
    '150': [
        'CUENTA CORRIENTE|120.924,96',
        'CUENTA CORRIENTE|5.107,13',
    ],
}

# (reclasificaciones puntuales van en FIX)

# ── 5) Parches individuales (cod, seccion, desc_exacta) → campo/valor ──────
FIX = [
    # cod 12 imprimió '1006' (el PDF pone 1996)
    ('12', 'Inmueble urbano', 'COCHERA', [('fecha', '1996')]),
]

# Dos filas reconstruidas desde cero (la del OCR fusiona descripciones y valores).
# Verificado contra el PDF p3 (ocr_txt/12-p3.txt): 389.012,40 (Roga) / 21.636,00 (Haza).
ADD = {
    '12': {
        'cod': '12',
        'remove_exact': [
            ('Valores, acciones y deuda pública',
             'Accionista con participación y sin cargo de gestión. Sociedad Roga S.L. (Herencia)'),
            ('Valores, acciones y deuda pública',
             'Accionista con participación y sin cargo de gestión. Jamones Haza de Lino S.L. (Herencia)'),
        ],
        'remove_prefix': ('Valores, acciones y deuda pública',
                          'Accionista participación sin de gestión Sociedad Roga'),
        'items': [
            {'seccion': 'Valores, acciones y deuda pública',
             'descripcion': 'Accionista con participación y sin cargo de gestión. Sociedad Roga S.L. (Herencia)',
             'titulo': '389.012,40 €'},
            {'seccion': 'Valores, acciones y deuda pública',
             'descripcion': 'Accionista con participación y sin cargo de gestión. Jamones Haza de Lino S.L. (Herencia)',
             'titulo': '21.636,00 €'},
        ],
    },
    # cod 12: fila BANKINTER fusionada (2.610 + 2.047) → 2 filas
    '12b': {
        'cod': '12',
        'remove_exact': [
            ('Valores, acciones y deuda pública', 'BANKINTER FONDOS (PLATEA Y MIXTO)'),
            ('Valores, acciones y deuda pública', 'SANTANDER FONDO EUROPA'),
        ],
        'remove_prefix': ('Valores, acciones y deuda pública',
                          'Y ) BANKINTER FONDOS (PLATEA MIXTO SANTANDER FONDO EUROPA'),
        'items': [
            {'seccion': 'Valores, acciones y deuda pública',
             'descripcion': 'BANKINTER FONDOS (PLATEA Y MIXTO)', 'titulo': '2.610 €'},
            {'seccion': 'Valores, acciones y deuda pública',
             'descripcion': 'SANTANDER FONDO EUROPA', 'titulo': '2.047 €'},
        ],
    },
}

# cod 12: la cochera está en 1996 (OCR puso 1006) — en FIX

def apply_fix(b):
    applied = 0
    for i, x in enumerate(b):
        for (cod, sec, desc, changes) in FIX:
            if changes and x['cod'] == cod and x['seccion'] == sec \
               and (x.get('descripcion') or '').strip() == desc:
                for k, v in changes:
                    if x.get(k) != v:
                        x[k] = v
                        applied += 1
    return applied


def split_multinum(b):
    """Elimina todas las filas Depósito de un cod y añade las correctas."""
    n_del, n_add = 0, 0
    nuevos = []
    for cod, filas in DEP_MULTINUM.items():
        keep = []
        for x in b:
            if x['cod'] == cod and x['seccion'] == 'Depósito o cuenta':
                n_del += 1
                continue
            keep.append(x)
        b = keep
        d0 = next((d for d in b if d['cod'] == cod), None)
        for fila in filas:
            desc, val = fila.split('|')
            b.append({'seccion': 'Depósito o cuenta', 'descripcion': desc,
                      'situacion': '', 'fecha': '', 'derecho': '', 'titulo': val,
                      'cod': cod,
                      'nombre': d0['nombre'] if d0 else '',
                      'partido': d0['partido'] if d0 else '',
                      'grupo': d0['grupo'] if d0 else '',
                      'circunscripcion': d0['circunscripcion'] if d0 else ''})
            n_add += 1
    return b, n_del, n_add


def main():
    b = json.load(open(PATH, encoding='utf-8'))
    n0 = len(b)
    counts = {}

    # 1) NINGUNOs
    keep = []
    for x in b:
        if any(match_dep(x, e) for e in DEP_NINGUNO) or \
           any(x['cod'] == c and x['seccion'] == s and (x.get('descripcion') or '').strip().startswith(p)
               for c, s, p in DEP_NINGUNO_LIKE):
            counts['ninguno_eliminados'] = counts.get('ninguno_eliminados', 0) + 1
            continue
        keep.append(x)
    b = keep

    # 2) multinum
    b, n_del, n_add = split_multinum(b)
    counts['multinum_eliminadas'] = n_del
    counts['multinum_regeneradas'] = n_add

    # 3) filas reconstruidas (ADD) — idempotente
    for key, spec in ADD.items():
        cod = spec['cod']
        sec_r, pre_r = spec['remove_prefix']
        exact = {(cod, s, d) for s, d in spec.get('remove_exact', [])}
        b = [x for x in b if not (
            (x['cod'] == cod and x['seccion'] == sec_r
             and (x.get('descripcion') or '').strip().startswith(pre_r))
            or ((x['cod'], x['seccion'], (x.get('descripcion') or '').strip()) in exact))
        ]
        d0 = next((d for d in b if d['cod'] == cod), None)
        for it in spec['items']:
            b.append(dict(it, situacion='', fecha='', derecho='', cod=cod,
                          nombre=d0['nombre'] if d0 else '',
                          partido=d0['partido'] if d0 else '',
                          grupo=d0['grupo'] if d0 else '',
                          circunscripcion=d0['circunscripcion'] if d0 else ''))
        counts['add_' + key] = len(spec['items'])

    # 4) correcciones puntuales (FIX)
    counts['fix'] = apply_fix(b)

    # marca global
    for x in b:
        x['_audit'] = 'v2-corrected-2025-09-29'

    # backup
    if not os.path.exists(PATH + '.preaudit'):
        shutil.copy(PATH, PATH + '.preaudit')

    with open(PATH, 'w', encoding='utf-8') as f:
        json.dump(b, f, ensure_ascii=False, indent=1)
    print('OK. Antes:', n0, 'Después:', len(b))
    print(counts)


if __name__ == '__main__':
    main()
