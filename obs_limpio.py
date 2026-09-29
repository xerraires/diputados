#!/usr/bin/env python3
"""Reescritura limpia de las OBSERVACIONES enrevesadas (lista B).

Textos reconstruidos de ocr_tsv/{cod}-p4.tsv (palabras agrupadas por línea)
y verificados visualmente contra obs_png/{cod}_p4-4.png donde el TSV era dudoso
(378 y 132).

Idempotente: solo reescribe filas OBSERVACIONES cuyo descripcion difiera del
texto objetivo y no toca filas con _fuente ya asignada por otros rescates.
"""
import json, sys

D = {}

D['253'] = "Soy propietario de un garaje en una vivienda de Madrid, que no tiene valor catastral propio ni es una finca independiente en el Registro de la Propiedad."
D['254'] = ("Soy autónoma y colaboradora: las rentas que se obtienen de los rendimientos de mi trabajo "
            "van destinadas a la cuenta de la empresa en la que desarrollo el mismo. "
            "No dispongo de participación alguna en la empresa.")
D['256'] = ("Se han tomado como referencia los saldos y valores contables a 31 de diciembre de 2022 para "
            "los bienes y derechos. El saldo pendiente de las deudas y obligaciones patrimoniales es del "
            "31 de julio de 2023.")
D['264'] = ("El rendimiento inmobiliario 2022 sobre el inmueble vendido en mayo de 2023: por lo que ya no "
            "aparece como bien en propiedad.")
D['293'] = ("El declarante deja constancia de que lo presentado tanto en saldos como en saldos pendientes "
            "de las hipotecas es a fecha 13 de agosto de 2023.")
D['368'] = ("En el apartado de rentas percibidas del parlamentario, las percepciones netas consignadas "
            "corresponden a retribuciones salariales percibidas en el ejercicio 2023. "
            "La cantidad pagada por IRPF corresponde a la Declaración de IRPF de 2022.")
D['378'] = ("Renta: datos del ejercicio 2022 (declaración en 2023).\n"
            "Fondo y Valores (2023 herencia).")
D['55']  = ("El plan de pensiones de las Cortes Generales ha quedado en suspenso y la cantidad consignada "
            "en esta declaración es aproximada.")
D['150'] = ("Los vehículos 1556 HDZ (Mercedes 180 CDI) y 8638 HNL (BMW 118 d) son vehículos comprados "
            "por mí, cedidos a mis dos hijos.")
D['53']  = "Abreviaturas utilizadas: Pleno dominio: PD · Compraventa: CV · Herencia: H"
D['82']  = ("Régimen económico matrimonial de separación de bienes; escritura de capitulaciones "
            "matrimoniales otorgada ante notario en 1985.")
D['229'] = ("Todas las propiedades de bienes inmuebles, las rentas por arrendamiento y las cuentas "
            "bancarias están compartidas con mi cónyuge en régimen de gananciales.")
D['200'] = ("En el año fiscal de 2022 accedí a la herencia por fallecimiento de padre y madre, lo que ha "
            "supuesto un incremento patrimonial en las cuentas corrientes y en el fondo de inversión.")
D['132'] = "Solar adquirido en 2017. Vivienda de nueva construcción finalizada en 2019."
D['63']  = ("Vivienda: pleno dominio por compraventa en 2022 en Valladolid.\n"
            "Plaza de garaje: pleno dominio por compraventa en 2023 en Valladolid.")
D['42']  = ("Seguro de vida Colegio de Economistas: 19.437 € · Seguro de accidentes Colegio de "
            "Economistas: 16.759 € · Seguro de vida AXA: 120.000 € · Plan de pensiones Universidad de "
            "Vigo: 9.035 € (están rescatados como filas propias en «Otros bienes o derechos»).")
D['48']  = ("En cuanto a los depósitos en cuentas corrientes bancarias, una de las cuentas es de triple "
            "titularidad (con madre y hermana), por lo que se ha hecho constar solo un tercio del valor "
            "de dicha cuenta. El resto de cuentas bancarias son bienes gananciales y se ha hecho constar "
            "el valor nominal completo. En el apartado de vehículos también se dispone de un Audi Q2 en "
            "régimen de renting, si bien el contrato está próximo a vencimiento (septiembre 2023).")
D['117'] = ("En virtud del régimen económico matrimonial de gananciales corresponde incluir el 50% del "
            "domicilio familiar, propiedad de mi esposa: bien inmueble de naturaleza urbana con dos "
            "plazas de garaje sito en la calle Blanquerías núm. 12 de la ciudad de Valencia.")
D['12']  = ("1- Agrícola Roga: accionista sin cargo de gestión. Objeto social: producción agrícola de "
            "frutas tropicales y hortalizas. La sociedad no contrata con el sector público; recibe "
            "subvenciones no regladas.\n"
            "2- Otros bienes de naturaleza urbana: piso (Madrid, 2019, C-V); piso (Madrid, 2021, C-V); "
            "piso-estudio (Madrid, 2021, C-V); piso-estudio (Madrid, 2021, C-V); piso-estudio (Madrid, "
            "2022, C-V).\n"
            "3- Otros bienes de naturaleza rústica: finca rústica en Granada, 2017 (herencia, propiedad "
            "compartida); finca rústica en Granada, 2017 (herencia, propiedad compartida).")

# ─── Filas rotas de la tabla de deudas (p4, mitad superior) ───────────────
# Reparaciones verificadas contra ocr_tsv + ocr_tsv_psm4 (y recortes de imagen
# con re-OCR psm7 para el dígito dudoso del 222).

# 161 Olano Vela: la fila rota no es basura: perdió la descripción.
#   'PISO MADRID ADJUDICADO CON UNA CARGA: ARRENDAMIENTO QUE DATA DE 1960'
REPARA_DEUDA = {
    '161': [
        {'match': {'fecha': '', 'derecho': 'DE 1960'},
         'set': {'descripcion': 'Piso Madrid adjudicado con una carga: arrendamiento que data de 1960'}},
        {'match': {'descripcion': 'PREÉSTAMO PERSONAL BANCO SANTANDER'},
         'set': {'descripcion': 'Préstamo personal Banco Santander'}},
    ],
    '8': [
        # fila basura de cabecera (tragó '114.000' y '7.27…') → fuera
        {'match': {'fecha': 'FECHA. CONCESIÓN'}, 'delete': True},
        # fila de fecha suelta: es la hipoteca Cajamar (psm4: 'Cajamar 15/07/2004 114.000 7.278,71€')
        {'match': {'fecha': '- 15/07/2004'},
         'set': {'descripcion': 'Hipoteca Cajamar', 'fecha': '15/07/2004',
                 'derecho': '114.000', 'titulo': '7.278,71'}},
        # limpieza de la fila Caixa
        {'match': {'descripcion': 'Cajamar Caixa', 'fecha': '13/12/2005'},
         'set': {'descripcion': 'Caixa', 'derecho': '205.195,67', 'titulo': '97.543,39 € (50%)'}},
    ],
    '17': [
        # fila basura de cabecera ('FECHA CONCESIÓN' + restos de '135.000') → fuera
        {'match': {'fecha': 'FECHA CONCESIÓN'}, 'delete': True},
        # la hipoteca cogió por error los importes del préstamo personal
        {'match': {'descripcion': 'PRÉSTAMO HIPOTECARIO', 'fecha': '17/07/2009'},
         'set': {'derecho': '135.000', 'titulo': '65.000'}},
    ],
    '40': [
        # la hipoteca cogió por error los importes del préstamo MBA
        {'match': {'descripcion': 'HIPOTECA VIVIENDA JAEN'},
         'set': {'derecho': '190.000 €', 'titulo': '167.190,05 €'}},
        # fila perdida (psm4: 'PRESTAMO MBA 17-10-2018 30.242,52€ 10.579,15€')
        {'add': {'descripcion': 'Préstamo MBA', 'fecha': '17-10-2018',
                 'derecho': '30.242,52 €', 'titulo': '10.579,15 €'}},
        # fila basura (fecha suelta del MBA ya recapturada) → fuera
        {'match': {'fecha': '17-10-2018', 'descripcion': ''}, 'delete': True},
        # saldo del coche con '05€' duplicado
        {'match': {'descripcion': 'COCHE'},
         'set': {'titulo': '26.837,05 €'}},
    ],
    '222': [
        # fila basura (fecha suelta) → fuera
        {'match': {'fecha': '18 abril 2019', 'descripcion': ''}, 'delete': True},
        # hipoteca: concedido correcto 220.231 (recorte psm7; psm6 decía 220251)
        {'match': {'descripcion': 'hipotecario', 'fecha': '19 junio 2009'},
         'set': {'descripcion': 'Préstamo hipotecario', 'derecho': '220.231', 'titulo': '70.458'}},
        # crédito ICO: fecha partida y resto de celdas sucias
        {'match': {'descripcion': 'Cuenta de crédito ICO'},
         'set': {'fecha': '21 febrero 2022', 'derecho': '25.000', 'titulo': '12.440'}},
    ],
}

def repara_deudas(b):
    """Aplica REPARA_DEUDA: filas rotas de la tabla de préstamos. Idempotente."""
    nuevos = []
    for x in b:
        if x['seccion'] != 'Deuda o crédito' or str(x['cod']) not in REPARA_DEUDA:
            nuevos.append(x)
            continue
        regs = REPARA_DEUDA[str(x['cod'])]
        for r in regs:
            if 'add' in r:
                continue
            m = r['match']
            if all((x.get(k) or '') == v for k, v in m.items()):
                if r.get('delete'):
                    print(f"  {x['cod']}: fila deuda basura eliminada ({m})")
                    x = None
                    break
                if all((x.get(k) or '') == v for k, v in r['set'].items()):
                    break  # ya aplicada (idempotencia)
                x.update(r['set'])
                print(f"  {x['cod']}: fila deuda reparada → {r['set']}")
                break
        if x is not None:
            nuevos.append(x)
    # añadir filas que faltaban
    for cod, regs in REPARA_DEUDA.items():
        for r in regs:
            if 'add' not in r:
                continue
            d = r['add']
            ya = any(str(y['cod']) == cod and y['seccion'] == 'Deuda o crédito'
                     and (y.get('descripcion') or '') == d['descripcion'] for y in nuevos)
            if not ya:
                # obtener nombre/partido de una fila existente del mismo cod
                ref = next(y for y in nuevos if str(y['cod']) == cod)
                fila = {'seccion': 'Deuda o crédito', 'descripcion': d['descripcion'],
                        'situacion': '', 'fecha': d['fecha'], 'derecho': d['derecho'],
                        'titulo': d['titulo'], 'cod': ref['cod'], 'nombre': ref['nombre'],
                        'partido': ref['partido'], 'grupo': ref['grupo'],
                        'circunscripcion': ref['circunscripcion'], '_fuente': 'reparada'}
                nuevos.append(fila)
                print(f"  {cod}: fila deuda añadida → {d['descripcion']}")
    return nuevos


def main():
    b = json.load(open('bienes.json'))
    cambiadas, sin_encontrar = 0, list(D)
    for x in b:
        if x['seccion'] != 'OBSERVACIONES':
            continue
        cod = str(x['cod'])
        if cod not in D:
            continue
        if x.get('_fuente'):  # ya reescrita/reescribiéndose por otro rescate
            continue
        nuevo = D[cod]
        if (x.get('descripcion') or '') != nuevo:
            x['descripcion'] = nuevo
            x['_fuente'] = 'obs-limpia'
            cambiadas += 1
            print(f"  {cod}: OBS reescrita")
        sin_encontrar.remove(cod)
    print(f"\nOBS cambiadas: {cambiadas}")
    if sin_encontrar:
        print("SIN ENCONTRAR (sin fila OBS activa o ya con _fuente):", ', '.join(sin_encontrar))
    b = repara_deudas(b)
    json.dump(b, open('bienes.json', 'w'), ensure_ascii=False)
    print(f"total bienes: {len(b)}")

if __name__ == '__main__':
    main()
