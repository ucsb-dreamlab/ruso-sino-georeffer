#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

TIFF_DIR = Path("tiffs")
OUTPUT_DIR = Path("output")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tiff_files = sorted(TIFF_DIR.glob("*.tif"))
    if not tiff_files:
        print(f"No .tif files found in {TIFF_DIR}")
        sys.exit(1)

    print(f"Found {len(tiff_files)} TIFF files")

    for i, tiff in enumerate(tiff_files, 1):
        print(f"\n[{i}/{len(tiff_files)}] Processing {tiff.name}...")
        result = subprocess.run(
            [sys.executable, "main.py", str(tiff), "-o", str(OUTPUT_DIR)],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"FAILED: {tiff.name}")


if __name__ == "__main__":
    main()
