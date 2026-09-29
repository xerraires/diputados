#!/usr/bin/env python3
"""Descarga fichas de diputados y sus PDFs de Declaración de Bienes y Rentas."""
import json, os, re, sys, time
import requests

BASE = "https://www.congreso.es"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
# cookies recogidas con curl (GUEST_LANGUAGE_ID es suficiente)
COOKIES = {"GUEST_LANGUAGE_ID": "es_ES", "COOKIE_SUPPORT": "true"}

FICHA_URL = (BASE + "/es/busqueda-de-diputados?p_p_id=diputadomodule&p_p_lifecycle=0"
             "&p_p_state=normal&p_p_mode=view&_diputadomodule_mostrarFicha=true")

RE_BIENES = re.compile(r'href="(/docbienes/[^"]+\.pdf)"', re.I)


def sesion():
    s = requests.Session()
    s.headers.update(UA)
    s.cookies.update(COOKIES)
    return s


def ficha_bienes_url(s, cod, leg="XV"):
    r = s.get(FICHA_URL, params={"codParlamentario": cod, "idLegislatura": leg}, timeout=30)
    r.raise_for_status()
    m = RE_BIENES.search(r.text)
    return m.group(1) if m else None


def main():
    with open("diputados.json", encoding="utf-8") as f:
        diputados = json.load(f)["data"]
    s = sesion()
    falta = []
    for i, d in enumerate(diputados):
        cod = d["codParlamentario"]
        out_pdf = f"pdfs/{cod}.pdf"
        if os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 1000:
            continue
        path = None
        try:
            path = ficha_bienes_url(s, cod)
            if not path:
                falta.append({"cod": cod, "nombre": d["apellidosNombre"], "motivo": "sin PDF bienes"})
                d["pdf_bienes"] = None
                print(f"[{i+1}/{len(diputados)}] {cod} {d['apellidosNombre']}: SIN declaración")
            else:
                rr = s.get(BASE + path, timeout=60)
                rr.raise_for_status()
                with open(out_pdf, "wb") as fh:
                    fh.write(rr.content)
                d["pdf_bienes"] = path
                print(f"[{i+1}/{len(diputados)}] {cod} {d['apellidosNombre']}: OK {len(rr.content)} B")
        except Exception as e:
            falta.append({"cod": cod, "nombre": d["apellidosNombre"], "motivo": str(e)})
            print(f"[{i+1}/{len(diputados)}] {cod}: ERROR {e}")
            s = sesion()
        d["url_ficha_bienes"] = (BASE + path) if path else None
        time.sleep(0.25)
    with open("diputados.json", "w", encoding="utf-8") as f:
        json.dump(diputados, f, ensure_ascii=False, indent=1)
    with open("errores_descarga.json", "w", encoding="utf-8") as f:
        json.dump(falta, f, ensure_ascii=False, indent=1)
    print(f"\nTerminado. Sin PDF o errores: {len(falta)}")


if __name__ == "__main__":
    main()
