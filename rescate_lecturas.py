#!/usr/bin/env python3
"""Lecturas verificadas por el usuario (leyendo los PNG obs_png/ de los PDF).

Efectos sobre bienes.json (idempotente):
 - cod 43 : añade Piso Huelva 2001 · 8,33% (el de 2002 ya se rescató antes).
 - cod 149: parte 'Varias fincas rústicas' (5% y 25%) en 2 filas y añade las
            2 comunidades de bienes de las observaciones.
 - cod 311: recalifica el velero Bavaria 36 (propiedad de Carmola SL, 50%) y
            corrige su fecha ('12004' → 2004).
 - cod 118 y 10: reescritura del texto OCR de las observaciones, verificado
            por el usuario (sin bienes nuevos).
 - cod 235: verificado con el PDF — los 2 bienes de Las Palmas ya estaban en
            la tabla y el piso de Madrid ya se rescató. Sin cambios.
"""
import json
import os

D = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(D, 'bienes.json')


def meta(d0):
    return {k: d0[k] for k in ('nombre', 'partido', 'grupo', 'circunscripcion')}


def main():
    b = json.load(open(PATH, encoding='utf-8'))
    n0 = len(b)
    log = {}

    d0 = lambda cod: next(d for d in b if d['cod'] == cod)

    # ── 43 · Verano Domínguez ────────────────────────────────────────────────
    # obs (verificada en obs_png/43_p4-4.png):
    #   PISO - HUELVA - 2001 - 8,33% NUDA PROPIEDAD/HERENCIA
    #   PISO - HUELVA - 2002 - 16,66% NUDA PROPIEDAD/HERENCIA  (ya rescatado)
    nuevo = {'seccion': 'Inmueble urbano', 'descripcion': 'Piso',
             'situacion': 'HUELVA', 'fecha': '2001',
             'derecho': '8,33% nuda propiedad/herencia', 'titulo': '',
             '_fuente': 'obs', 'cod': '43'}
    ya = any(x['cod'] == '43' and x['seccion'] == 'Inmueble urbano'
             and (x.get('descripcion') or '').lower() == 'piso'
             and x.get('fecha') == '2001' for x in b)
    if not ya:
        b.append({**nuevo, **meta(d0('43'))})
        log['43_piso_2001'] = 'añadido'
    # limpia el pegote del OCR en la fila del garaje (texto real del PDF: '*sigue en observaciones')
    for x in b:
        if x['cod'] == '43' and (x.get('descripcion') or '').startswith('PLAZA DE GARAJE *sigue'):
            x['descripcion'] = 'Plaza de garaje (*sigue en observaciones)'
            log['43_garaje'] = 'texto limpiado'

    # ── 149 · Catalán Higueras ───────────────────────────────────────────────
    # 'Varias fincas rústicas' con 5% y 25% → 2 filas (indicación del usuario)
    for x in b:
        if x['cod'] == '149' and x['seccion'] == 'Inmueble rústico' \
           and (x.get('descripcion') or '').strip() == 'Varias fincas rústicas' \
           and x.get('_fuente') != 'partida':
            x['descripcion'] = 'Varias fincas rústicas (1)'
            x['derecho'] = '5% propiedad'
            x['_fuente'] = 'reclasificado'
            b.append({'seccion': 'Inmueble rústico', 'descripcion': 'Varias fincas rústicas (2)',
                      'situacion': '', 'fecha': x.get('fecha', ''),
                      'derecho': '25% propiedad', 'titulo': '',
                      '_fuente': 'reclasificado', 'cod': '149', **meta(d0('149'))})
            log['149_fincas'] = 'partida en 2'
            break
    # comunidades de bienes de las observaciones (verificadas en el PDF)
    nuevos_149 = [
        {'seccion': 'Inmueble rústico', 'descripcion': 'Comunidad de bienes: explotación de fincas rústicas',
         'situacion': '', 'fecha': '', 'derecho': '25% comunidad de bienes', 'titulo': ''},
        {'seccion': 'Otros bienes o derechos', 'descripcion': 'Comunidad de bienes: explotación de farmacia',
         'situacion': '', 'fecha': '', 'derecho': '8% comunidad de bienes', 'titulo': ''},
    ]
    for it in nuevos_149:
        ya = any(x['cod'] == '149' and x['seccion'] == it['seccion']
                 and (x.get('descripcion') or '') == it['descripcion'] for x in b)
        if not ya:
            b.append({**it, '_fuente': 'obs', 'cod': '149', **meta(d0('149'))})
            log['149_cb'] = 'añadidas'

    # ── 311 · Santos Maraver ────────────────────────────────────────────────
    for x in b:
        if x['cod'] == '311' and x['seccion'] == 'Vehículo o embarcación' \
           and 'velero' in (x.get('descripcion') or '').lower():
            x['descripcion'] = 'Velero Bavaria 36 (propiedad de la sociedad Carmola SL, participada en un 50%)'
            x['fecha'] = '2004'
            log['311_velero'] = 'recalificado + fecha'
    # (queda en 'Vehículo o embarcación': el propio formulario ordena declarar ahí
    #  los vehículos propiedad de sociedades participadas)

    # ── 118 · Bermúdez de Castro ────────────────────────────────────────────
    for x in b:
        if x['cod'] == '118' and x['seccion'] == 'OBSERVACIONES':
            x['descripcion'] = ('Heredo 1/4 de una finca rústica que posteriormente vendo por 243.241 €; '
                                'con parte de ese dinero compro y vendo otra finca rústica.')
            log['118_obs'] = 'reescrita (lectura verificada)'

    # ── 10 · Sahuquillo García ──────────────────────────────────────────────
    for x in b:
        if x['cod'] == '10' and x['seccion'] == 'OBSERVACIONES':
            x['descripcion'] = ('Plan de pensiones personal del Congreso de los Diputados '
                                '(aportación anual de 8.000 €). No se detalla por ser ajeno a los inmuebles.')
            log['10_obs'] = 'reescrita'

    # backup
    bak = PATH + '.prelecturas'
    if not os.path.exists(bak):
        import shutil
        shutil.copy(PATH, bak)

    with open(PATH, 'w', encoding='utf-8') as f:
        json.dump(b, f, ensure_ascii=False, indent=1)
    print('OK. Antes:', n0, 'Después:', len(b))
    for k, v in log.items():
        print(' ', k, '→', k, v)


if __name__ == '__main__':
    main()
