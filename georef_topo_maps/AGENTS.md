# AGENTS.md — georef_topo_maps

## Project Overview
Python CLI for georeferencing Soviet-era topographic map scans. Pipeline: detect/remove collar → OCR corner coordinates → compute affine transform → export GeoTIFF + world file.

## Commands

### Setup
```bash
pip install -r requirements.txt        # or: pip install -e .
sudo apt install tesseract-ocr          # external OCR dependency
```

### Run
```bash
python main.py <input.tif> -o output/   # single file
python batch_process.py                  # process all TIFFs in tiffs/
python src/collar_detector.py in.tif -o out.tif  # standalone collar removal
```

### Lint & Format (Ruff — no config file, uses defaults)
```bash
ruff check .          # lint
ruff check --fix .    # lint + auto-fix
ruff format .         # format
ruff format --check . # check formatting only
```

### Tests
No tests exist yet. The `tests/` directory is empty. When adding tests:
```bash
pip install pytest
pytest                          # run all tests
pytest tests/test_file.py       # run single test file
pytest tests/test_file.py -k name  # run tests matching name
pytest -v                       # verbose output
```

## Code Style

### Imports
- Standard library → third-party → local (`src.*`), separated by blank lines.
- Import pytesseract lazily inside functions (heavy dependency).
- Use `from src import ClassName` for public classes (see `src/__init__.py`).

### Formatting
- 4-space indentation (PEP 8).
- Double quotes for strings.
- Max line length ~100 chars.
- Trailing commas in multiline structures.

### Naming
- Classes: `PascalCase` (`CollarDetector`, `GeoReference`)
- Functions/methods: `snake_case` (`detect`, `compute_affine`)
- Private methods: `_leading_underscore` (`_ocr_corner`, `_parse_text`)
- Constants: `UPPER_SNAKE_CASE` (`VALID_MINUTES`, `SHEET_COORDS`)
- Variables: `snake_case` (`input_path`, `output_dir`)

### Types
- Type hints required on all function signatures and return types.
- Use modern union syntax: `str | Path` (not `Union[str, Path]`).
- Use built-in generics: `list[int]`, `tuple[float, ...]` (not `List`, `Tuple`).
- `@dataclass` for structured data containers.
- `Optional[T]` acceptable for nullable returns; `T | None` preferred.

### Error Handling
- Raise `ValueError` for invalid inputs and file read failures.
- Use `sys.exit(1)` in CLI scripts for fatal errors.
- No try/except in core library — let errors propagate.
- OCR failures return `None` or defaults silently (no exceptions).
- No custom exception classes currently.

### Docstrings
- None exist yet. Add Google-style docstrings for new public functions.

### General Patterns
- `if __name__ == "__main__":` blocks for runnable modules.
- NumPy for numerical work (`np.linalg.lstsq` for affine fitting).
- OpenCV (`cv2`) for image I/O and processing.
- Rasterio for GeoTIFF output.
- Dataclasses over dicts for structured data.
