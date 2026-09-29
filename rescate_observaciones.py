#!/usr/bin/env python3
"""Rescate de bienes ocultos en OBSERVACIONES de los diputados.

Los bienes se verificaron visualmente contra las páginas 4 de los PDF oficiales
(obs_png/*.png). Solo se añaden si NO están ya en la tabla (sin duplicados).

Efectos sobre bienes.json:
 1. Añade items con '_fuente': 'obs' (bienes que no cabían en la tabla).
2. Reclasifica items mal clasificados por el OCR (con '_fuente': 'reclasificado').
3. Elimina 2 artefactos de OCR (con informe).
Idempotente: puede ejecutarse varias veces sin duplicar.
"""
import json
import os

D = os.path.dirname(os.path.abspath(__file__))

# ── Bienes ocultos en OBSERVACIONES (verificados en el PDF original) ──
EXTRAS = {
    '43': [  # Verano Domínguez: "*Continuación bienes patrimoniales"
        # el piso de 2001 ya figura en la tabla (fila 'PLAZA DE GARAJE *sigue observaciones')
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso', 'situacion': 'HUELVA', 'fecha': '2002',
         'derecho': '16,66% nuda propiedad/herencia', 'titulo': ''},
    ],
    '12': [  # Rojas García: "2- OTROS BIENES DE NATURALEZA URBANA"
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso', 'situacion': 'MADRID', 'fecha': '2019', 'derecho': 'Compraventa (C-V)', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso', 'situacion': 'MADRID', 'fecha': '2021', 'derecho': 'Compraventa (C-V)', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso-estudio', 'situacion': 'MADRID', 'fecha': '2021', 'derecho': 'Compraventa (C-V)', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso-estudio', 'situacion': 'MADRID', 'fecha': '2021 (2º)', 'derecho': 'Compraventa (C-V)', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso-estudio', 'situacion': 'MADRID', 'fecha': '2022', 'derecho': 'Compraventa (C-V)', 'titulo': ''},
        # (las 2 fincas rústicas Granada 2017 ya están en la tabla)
    ],
    '281': [  # Sánchez Sierra: "Bienes inmuebles propiedad de una sociedad… CONTINUACION" (16 filas)
        # (Oficina 64 m2, Piso 63'77 y Nave 450 ya declarados)
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Nave Industrial 1.165,50 m2', 'situacion': 'A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Piso 81,40 m2', 'situacion': 'A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Local Comercial 115 m2', 'situacion': 'A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Local Comercial 113 m2', 'situacion': 'A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': '4 plazas de garaje', 'situacion': 'A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Plaza de garaje', 'situacion': 'A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Casa 217 m2', 'situacion': 'Cacabelos - León', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Almacén 312 m2', 'situacion': 'Cacabelos - León', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Terreno urbano 2.865 m2', 'situacion': 'Cacabelos - León', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': '8 Fincas rústicas', 'situacion': 'Laracha - A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Finca Rústica', 'situacion': 'Miño - A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': '2 Fincas urbanas', 'situacion': 'Cambre - A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Finca Rústica', 'situacion': 'Cambre - A Coruña', 'fecha': '30-12-2020', 'derecho': '25% Pleno Dominio. Pacto sucesorio de mejora', 'titulo': ''},
    ],
    '182': [  # Martínez Salmerón: inmuebles de sus sociedades + Range Rover Velar
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Oficina (propiedad de Martínez & Salmerón Abogados SLP)', 'situacion': 'MURCIA', 'fecha': '28/10/2022', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': '1 plaza de garaje (propiedad de Martínez & Salmerón Abogados SLP)', 'situacion': 'MURCIA', 'fecha': '30/11/2022', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': 'Oficina (propiedad de Martínez Salmerón Recupera SL)', 'situacion': 'MURCIA', 'fecha': '30/11/2020', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': '2 plazas de garaje (propiedad de Martínez Salmerón Recupera SL)', 'situacion': 'MURCIA', 'fecha': '17/05/2021', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
        {'seccion': 'Inmueble de sociedad', 'descripcion': '1 plaza de garaje (propiedad de Martínez Salmerón Recupera SL)', 'situacion': 'MURCIA', 'fecha': '03/12/2021', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
        {'seccion': 'Vehículo o embarcación', 'descripcion': 'Range Rover Velar (propiedad de Martínez & Salmerón Abogados)', 'situacion': '', 'fecha': '2020 (adquirido 30/06/23)', 'derecho': '', 'titulo': ''},
    ],
    '325': [  # Ortega Smith: 3 solares Castropol
        {'seccion': 'Inmueble urbano', 'descripcion': 'Solar', 'situacion': 'CASTROPOL (ASTURIAS)', 'fecha': 'DICIEMBRE 2019', 'derecho': '1,4% por herencia', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Solar', 'situacion': 'CASTROPOL (ASTURIAS)', 'fecha': 'JULIO 2000', 'derecho': '8% por herencia', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Solar', 'situacion': 'CASTROPOL (ASTURIAS)', 'fecha': 'ENERO 2016', 'derecho': '50% por compraventa', 'titulo': ''},
    ],
    '277': [  # Herrero Bono: "AMPLIACION BIENES E INMUEBLES DE NATURALEZA RÚSTICA"
        {'seccion': 'Inmueble rústico', 'descripcion': 'Partida Viña Larga (Olivar regadio) 0,6542 ha', 'situacion': 'CALANDA (TERUEL)', 'fecha': '', 'derecho': 'Herencia 50% de la propiedad', 'titulo': ''},
        {'seccion': 'Inmueble rústico', 'descripcion': 'Partida Huerta Alta (Cereal regadio) 0,0581 ha', 'situacion': 'CALANDA (TERUEL)', 'fecha': '', 'derecho': 'Herencia 50% de la propiedad', 'titulo': ''},
    ],
    '197': [  # Quintana Carballo: 2 casas (las fincas 2018 ya están)
        {'seccion': 'Inmueble urbano', 'descripcion': 'Casa en lugar Pereiro de Alen', 'situacion': 'OURENSE', 'fecha': '2023', 'derecho': 'Comunidad de bienes. Compraventa 50% pleno dominio', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Casa en Pereiro de Aguiar', 'situacion': 'OURENSE', 'fecha': '2020', 'derecho': 'Comunidad de bienes. Adjudicación de herencia', 'titulo': ''},
    ],
    '235': [  # Delgado-Taramona: piso Madrid (los de Las Palmas 12/2020 ya están)
        {'seccion': 'Inmueble urbano', 'descripcion': 'Piso', 'situacion': 'MADRID', 'fecha': '04/2021', 'derecho': '50% pleno dominio. Compraventa', 'titulo': ''},
    ],
    '63': [  # Martínez Seijo: vivienda 2022 + plaza garaje 2023 Valladolid
        {'seccion': 'Inmueble urbano', 'descripcion': 'Vivienda', 'situacion': 'Valladolid', 'fecha': '2022', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
        {'seccion': 'Inmueble urbano', 'descripcion': 'Plaza de garaje', 'situacion': 'Valladolid', 'fecha': '2023', 'derecho': 'Pleno dominio. Compraventa', 'titulo': ''},
    ],
    '117': [  # Gil Lázaro: 50% del domicilio familiar (gananciales)
        {'seccion': 'Inmueble urbano', 'descripcion': '50% del domicilio familiar, bien inmueble urbano con dos plazas de garaje (calle Blanquerias 12)', 'situacion': 'VALENCIA', 'fecha': '', 'derecho': '50% ganancial (propiedad de la esposa)', 'titulo': ''},
    ],
    '42': [  # Garrido Valenzuela: seguros y plan de pensiones
        {'seccion': 'Otros bienes o derechos', 'descripcion': 'Seguro de vida Colegio de Economistas', 'situacion': '', 'fecha': '', 'derecho': '', 'titulo': '19.437 €'},
        {'seccion': 'Otros bienes o derechos', 'descripcion': 'Seguro de accidentes Colegio de Economistas', 'situacion': '', 'fecha': '', 'derecho': '', 'titulo': '16.759 €'},
        {'seccion': 'Otros bienes o derechos', 'descripcion': 'Seguro de vida AXA', 'situacion': '', 'fecha': '', 'derecho': '', 'titulo': '120.000 €'},
        {'seccion': 'Otros bienes o derechos', 'descripcion': 'Plan de pensiones Universidad de Vigo', 'situacion': '', 'fecha': '', 'derecho': '', 'titulo': '9.035 €'},
    ],
}

# ── Recalsificaciones verificadas (errores del parser OCR) ──
RECLASS = [
    # (cod, match seccion/desc actual, seccion destino)
    ('182', 'Inmueble rústico', 'APARTAMENTO DE LA SOCIEDAD', 'Inmueble de sociedad'),
]

# ── Artefactos de OCR a eliminar (sin contenido o duplicados verificados) ──
REMOVE = [
    ('182', 'Inmueble urbano', 'PATRIMONIALES BIENES'),  # fragmento del rótulo de la tabla
    # 281: la 'Oficina. 64 m2' del apartado sociedad fue emitida 2 veces por el
    # parser (una copia mal enrutada a rústicos). El PDF solo la lista una vez.
    ('281', 'Inmueble rústico', 'OFICINA. 64 M2'),
]


def key(x):
    return (x['cod'], x['seccion'], (x.get('descripcion') or '').strip().lower(),
            (x.get('situacion') or '').strip().lower(), (x.get('fecha') or '').strip(),
            (x.get('derecho') or '').strip().lower(), (x.get('titulo') or '').strip())


def main():
    path = f'{D}/bienes.json'
    b = json.load(open(path, encoding='utf-8'))

    # 1) recalsificaciones
    n_recl = 0
    for cod, sec_orig, prefijo, sec_dest in RECLASS:
        for x in b:
            if x['cod'] == cod and x['seccion'] == sec_orig and \
               (x.get('descripcion') or '').upper().startswith(prefijo):
                x['seccion'] = sec_dest
                x['_fuente'] = 'reclasificado'
                n_recl += 1
    print(f'recalsificados: {n_recl}')

    # 2) eliminación de artefactos OCR
    n_del = 0
    out = []
    for x in b:
        if any(x['cod'] == c and x['seccion'] == s and (x.get('descripcion') or '').upper().startswith(d)
               for c, s, d in REMOVE):
            n_del += 1
            continue
        out.append(x)
    b = out
    print(f'artefactos eliminados: {n_del}')

    # 3) dedupe SOLO de artefactos de OCR: filas idénticas en secciones NO inmobiliarias
    #    (los NINGUNA repetidos del formulario y celdas de depósitos duplicadas por el parser).
    #    NUNCA se deduplican inmuebles ni vehículos: pueden ser bienes reales distintos
    #    (verificado en los PDF: 177 tiene 2 plazas, 238 2 viviendas, 404 2 apartamentos).
    SAFE_SECTIONS = {'Valores, acciones y deuda pública', 'Depósito o cuenta',
                     'Otros bienes o derechos', 'Rentas', 'IRPF', 'OBSERVACIONES'}
    seen, dedup = set(), []
    n_ded = 0
    for x in b:
        k = key(x)
        if k in seen and x['seccion'] in SAFE_SECTIONS:
            n_ded += 1
            continue
        seen.add(k)
        dedup.append(x)
    b = dedup
    print(f'duplicados exactos eliminados (solo secciones no inmobiliarias): {n_ded}')

    # 4) extras de observaciones
    have = {key(x) for x in b}
    added = 0
    for cod, extras in EXTRAS.items():
        base = next((y for y in b if y['cod'] == cod), None)
        if base is None:
            print(f'  ! sin datos para {cod}')
            continue
        for it in extras:
            nuevo = {k: v for k, v in it.items()}
            item = {
                'seccion': it['seccion'],
                'descripcion': it['descripcion'],
                'situacion': it['situacion'],
                'fecha': it['fecha'],
                'derecho': it['derecho'],
                'titulo': it['titulo'],
                'cod': cod,
                'nombre': base['nombre'],
                'partido': base['partido'],
                'grupo': base['grupo'],
                'circunscripcion': base['circunscripcion'],
                '_fuente': 'obs',
            }
            if key(item) not in have:
                b.append(item)
                have.add(key(item))
                added += 1
    print(f'extras añadidos: {added}')

    json.dump(b, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_inm = sum(1 for x in b if x['seccion'].startswith('Inmueble') and (x['descripcion'] or x['titulo']))
    print(f'total items: {len(b)} · inmuebles: {n_inm}')


if __name__ == '__main__':
    main()
