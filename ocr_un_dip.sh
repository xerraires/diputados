#!/bin/zsh
# OCR (txt+tsv) de páginas 2-4 de la declaración de bienes de un diputado
D=$(dirname "$0")
DIP="$1"
mkdir -p "$D/ocr_txt" "$D/ocr_tsv"
pdf="$D/pdfs/$DIP.pdf"

for p in 1 2 3 4; do
  out_txt="$D/ocr_txt/${DIP}-p$p"
  out_tsv="$D/ocr_tsv/${DIP}-p$p"
  if [[ -s "$out_tsv.tsv" ]]; then continue; fi
  find "$D/ocr_png" -name "${DIP}_${p}*.png" -delete 2>/dev/null
  pdftoppm -r 300 -png -f $p -l $p "$pdf" "$D/ocr_png/${DIP}_${p}" 2>/dev/null
  png=$(find "$D/ocr_png" -name "${DIP}_${p}*.png" | head -1)
  [[ -z "$png" ]] && { echo "FAIL $DIP p$p: sin render"; continue; }
  tesseract "$png" "$out_txt" -l spa --psm 6 tsv txt 2>/dev/null
  mv "$out_txt.tsv" "$out_tsv.tsv" 2>/dev/null
done
echo "OK $DIP"
