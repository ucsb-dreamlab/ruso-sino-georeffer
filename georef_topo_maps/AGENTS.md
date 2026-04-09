# AGENTS.md — georef_topo_maps

## Project Overview
This repository provides a Python-based CLI pipeline for georeferencing Soviet-era topographic map scans of China. The goal is to convert raw TIFF scans into georeferenced GeoTIFFs with minimal human intervention. A web-based review tool is included for quality control.

## Core Pipeline Architecture
The system uses a tiered approach to determine geographic coordinates for map corners. Each tier is tried in sequence until a match is found:
1. **Soviet Grid Decoder:** Parses the sheet nomenclature (e.g., `J-44-119-M`) from the filename to compute bounds based on the Soviet grid system. This is the fastest and most reliable method when filenames are correct.
2. **Shapefile Index:** Looks up the sheet in a reference shapefile (`index_map/6840s_100_r8_INDEX.shp`). Useful when the filename contains a sheet ID that doesn't follow the standard Soviet nomenclature but exists in the index.
3. **Coordinate OCR (Fallback):** Crops map corners and uses Tesseract or Gemini Vision API to extract lat/lon text directly from the map imagery. This is the slowest method but works for maps with non-standard naming.

### Detailed Processing Steps:
- **Collar Detection:** Identify and remove the white/gray border of the scan (`CollarDetector`). Uses average pixel values on edges to find where the paper ends and the map begins. It handles variable collar widths and slight rotations.
- **Neatline Finding:** Locate the actual map content boundary (the "neatline") inside the collar (`NeatlineFinder`). The neatline is the inner rectangle that contains all map data, excluding the labels in the margins. This step is crucial for accurate georeferencing as corner coordinates refer to this line.
- **Georeferencing:** Compute an affine transformation using corner coordinates (`Georeferencer`). Maps pixel coordinates `(x, y)` to geographic coordinates `(lon, lat)` using a least-squares fit. This handles slight distortions in the scan.
- **Export:** Write out a GeoTIFF and a World File (`.tfw`) using `rasterio` (`Exporters`). This ensures the map can be opened in GIS software like QGIS or ArcGIS. The world file provides compatibility with older software.
- **Visual Report:** Generate an HTML summary with crops of the corners for manual verification (`Visualizer`). This is critical for assessing the quality of the OCR fallback and identifying maps that need manual correction.
- **Review Server:** A Flask app (`server.py`) that serves the reports and collects quality feedback (crop accuracy, corner selection). Feedback is stored in `output/feedback.json`.

## Command Reference

### Environment Setup
The project uses `pixi` for environment management, but can also be installed via `pip`.
```bash
# Using pip
pip install -r requirements.txt
pip install -e .

# Using pixi
pixi install

# External Dependencies (Required for OCR)
sudo apt install tesseract-ocr
export GOOGLE_API_KEY="your-key-here"  # For Gemini Vision fallback
```

### Execution
```bash
# Process a single map
python main.py tiffs/input.tif -o output/

# Batch process all TIFFs in a directory (defaulting to tiffs/)
python batch_process.py --input tiffs/ --output output/

# Start the interactive review web server
python server.py --port 5000

# Standalone collar detection
python src/collar_detector.py tiffs/in.tif -o out.tif
```

### Linting & Formatting
We use `ruff` for all code quality checks.
```bash
ruff check .          # Linting
ruff check --fix .    # Linting + auto-fix
ruff format .         # Formatting (auto-fixes)
ruff format --check . # Verify formatting
```

### Testing
Tests are located in the `tests/` directory (using `pytest`). No tests exist yet as of April 2026, so adding them is a priority.
```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_georeferencer.py

# Run a specific test function
pytest tests/test_georeferencer.py -k "test_compute_affine"

# Run with verbose output
pytest -v
```

## Code Style & Conventions

### Imports
- **Order:** Standard Library → Third-party → Local (`src.*`).
- Separate each group with a blank line.
- **Lazy Imports:** Import heavy dependencies (`pytesseract`, `google.generativeai`) inside the methods where they are used to keep CLI startup fast and avoid unnecessary dependency loads.
- **Public API:** Use `from src import ClassName` for public classes defined in `src/__init__.py`.

### Formatting
- **Indentation:** 4-space (PEP 8).
- **Strings:** Double quotes (`"`) preferred.
- **Line Length:** Maximum 100 characters.
- **Trailing Commas:** Required in multiline structures (lists, dicts, function calls) for better git diffs.

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `CollarDetector`, `GeoReference`).
- **Functions & Methods:** `snake_case` (e.g., `detect_neatline`, `compute_affine`).
- **Variables:** `snake_case` (e.g., `input_path`, `pixel_coords`).
- **Private Members:** `_leading_underscore` (e.g., `self._ocr_corner`).
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `VALID_MINUTES`, `EPSG_4326`).

### Type Hinting
Modern Python 3.10+ typing is mandatory for all new code.
- **Functions:** Annotate all arguments and return types.
- **Unions:** Use `str | Path` instead of `Union[str, Path]`.
- **Generics:** Use built-in types like `list[int]`, `dict[str, float]` (no `List` or `Dict`).
- **Nullable:** Use `T | None` for optional returns (preferred over `Optional[T]`).

### Error Handling
- **Core Logic:** Raise `ValueError` or `FileNotFoundError` for invalid inputs. Let exceptions propagate to the caller; avoid silent failures in the `src/` library.
- **CLI Scripts:** Use `sys.exit(1)` for fatal user-facing errors after printing a clear message.
- **OCR Failures:** If OCR fails, return `None` or an empty result object rather than crashing, to allow the pipeline to proceed or try another fallback.

### Documentation
- **Docstrings:** Use Google-style docstrings for public classes and methods.
- **Comments:** Focus on "Why" rather than "What". Keep them concise and meaningful.

### Data Modeling
- **Dataclasses:** Use `@dataclass` for structured data containers instead of dictionaries or raw tuples.
- **Immutability:** Prefer immutable data structures where possible.

## Development Patterns
- **Pathlib:** Always use `pathlib.Path` for file system operations instead of `os.path` or raw strings.
- **NumPy/OpenCV:** Use `np.ndarray` for image data. Handle image coordinates as `(x, y)` tuples and pixel arrays as `(height, width, channels)`.
- **Rasterio:** Use `rasterio` for all GeoTIFF writing and CRS handling to ensure metadata consistency.
- **Fallback Chain:** When adding a new coordinate source, integrate it into the `main.py` fallback chain rather than replacing existing logic.
- **Main Blocks:** All runnable modules should have `if __name__ == "__main__":` blocks for CLI execution.

## Project Structure
- `src/`: Core library and processing logic.
- `index_map/`: Reference shapefiles for sheet lookups.
- `tiffs/`: Default directory for input map scans.
- `output/`: Default directory for georeferenced results.
- `tests/`: Project unit and integration tests.
- `notebooks/`: Research and development notebooks.
- `configs/`: (Future) Directory for map-series-specific configuration files.

## Troubleshooting
- **OCR Issues:** Ensure `tesseract-ocr` is installed and in your PATH. If Gemini Vision fails, check your `GOOGLE_API_KEY`.
- **GDAL/Rasterio:** On some systems, `rasterio` may require external GDAL libraries. Use `pixi` or `conda` to manage these complex dependencies easily.
- **No Coordinate Match:** If a map cannot be georeferenced, it's usually because the filename doesn't match the Soviet grid pattern and OCR failed. Check the visual report in `output/` for clues.

## Contributing
1. Always run `ruff check .` and `ruff format .` before committing.
2. Ensure any new logic is added as a module in `src/` and exposed in `src/__init__.py`.
3. If adding a new coordinate source, update the fallback chain in `main.py`.
4. Add unit tests in `tests/` for any new core logic.
5. Use `pathlib.Path` for all file operations.
