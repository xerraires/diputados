# Bienes patrimoniales de los diputados — XV Legislatura

Web estática e interactiva con los bienes declarados por los 350 diputados de la XV Legislatura
(declaraciones de bienes y rentas publicadas por el Congreso de los Diputados).

**No requiere servidor ni configuración**: abre `index.html` y listo. También funciona
descargando el repo y abriendo el archivo en el navegador.

## Archivos principales

| Archivo | Descripción |
|---|---|
| `index.html` | Web interactiva (una sola página, JS nativo) |
| `data.js` | Datos para la web (generado desde `bienes.json` + `diputados.json`) |
| `bienes.json` | Bienes extraídos (2433 bienes de 350 diputados) |
| `diputados.json` | Metadatos de los 350 diputados (nombre, partido, grupo, PDF) |
| `bienes_patrimoniales.xlsx` | Excel generado con los bienes por diputado |
| `build_web.py` | Regenera `data.js` y el Excel |
| `extract.py` | Pipeline OCR + extracción de las declaraciones |
| `scrape_fichas.py` | Descarga de fichas y PDFs del Congreso |

## Regenerar datos

```bash
python3 build_web.py     # regenera data.js
python3 build_excel.py   # regenera el Excel
```

## Fuentes

- Fichas de diputados: `https://www.congreso.es/es/busqueda-de-diputados`
- Declaraciones (PDF): `https://www.congreso.es/docbienes/...`

Los enlaces de la web apuntan a los PDFs originales del Congreso. El OCR se hizo con
`tesseract` sobre renders a 300 dpi (`pdftoppm`) y luego se depuró a mano.
