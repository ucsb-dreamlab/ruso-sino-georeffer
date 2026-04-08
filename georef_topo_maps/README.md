# Georef Topo Maps

Georeference Soviet-era topographic maps of China. Converts scanned TIFFs with collars to georeferenced GeoTIFFs.

## Quick Start

```bash
pip install -r requirements.txt
# Tesseract OCR (English + Cyrillic):
sudo apt install tesseract-ocr
```

```bash
python main.py tiffs/6840s_100_r8_e-49-14-m.tif -o output/
```

Output:
- `*_cropped.tif` — collar removed
- `*_georef.tif` — georeferenced GeoTIFF
- `*_georef.tfw` — world file

## Verified Map Specs

From analysis of 16 sample tiles (`e-49-XX-m.tif`):

| Parameter | Value |
|-----------|-------|
| Image size | ~6600 × 5300 px |
| Collar | Near-white (~250+ brightness), full-width top border |
| Content starts | row ~461, col ~104 |
| Content extent | ~6438 × 4868 px |
| Neatline margin | ~130 px |
| Minute values | 0, 20, 40 (confirmed) |
| Sheet grid | 20' lat × 30' lon |

## Pipeline

1. **Collar detection** — brightness threshold (< 240) scans each edge to find content boundaries
2. **Corner OCR** — reads degree/minute values from bottom corners of original TIFF using Tesseract
3. **Inference** — infers top corners from bottom + 20' lat / 30' lon offset
4. **Affine transform** — maps pixel coords (col, row) → (lon, lat) via least-squares on 4 corners
5. **Export** — writes GeoTIFF + world file

## Coordinate Reference

Default output CRS: `EPSG:4326` (WGS84). For higher accuracy in China, consider:
- `EPSG:21453` — Gauss-Kruger zone 3 (central meridian 105°E, SK-42 datum)

## Troubleshooting

**OCR fails to detect coordinates**: Ensure Tesseract 5.x is installed. Try `--psm 6` mode. If Cyrillic degree symbols are misread, the parser corrects common OCR errors (e.g., 19° → 20° when minutes are 0/20/40).
