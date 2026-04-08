import argparse
from pathlib import Path
import cv2

from src import CollarDetector, SovietGridDecoder, CoordinateOCR
from src.georeferencer import Georeferencer, GeoReference
from src.exporters import export_geotiff, export_world_file
from src.shapefile_index import ShapefileIndex


DEFAULT_SHAPEFILE = "index_map/6840s_100_r8_INDEX.shp"


def main():
    parser = argparse.ArgumentParser(
        description="Georeference Soviet topographic maps of China"
    )
    parser.add_argument("input", help="Input TIFF file")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument(
        "--shapefile",
        default=DEFAULT_SHAPEFILE,
        help="Path to shapefile index (default: index_map/6840s_100_r8_INDEX.shp)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing: {input_path}")

    # 1. Try Soviet Grid Decoder
    print("Trying Soviet Grid Decoder...")
    decoder = SovietGridDecoder()
    grid_bounds = decoder.decode(input_path.name)

    ref = None
    h, w = 0, 0  # placeholder for cropped size

    print("Loading image...")
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Could not read: {input_path}")

    from src.neatline_finder import NeatlineFinder

    print("Detecting collar...")
    collar_detector = CollarDetector()
    collar = collar_detector.detect(img)

    print("Finding neatline...")
    neatline_finder = NeatlineFinder()
    neatline_result = neatline_finder.find(img, collar.outer_bbox)

    h, w = neatline_result.cropped_image.shape[:2]
    print(f"  Neatline size: {w}x{h} px")

    if grid_bounds:
        print(f"  Grid Decoder match: {grid_bounds.scale}")
        geo_corners = [
            (grid_bounds.west, grid_bounds.north),
            (grid_bounds.east, grid_bounds.north),
            (grid_bounds.west, grid_bounds.south),
            (grid_bounds.east, grid_bounds.south),
        ]
        pixel_corners = [(0, 0), (w, 0), (0, h), (w, h)]
        georeferencer = Georeferencer()
        ref = georeferencer.georeference(pixel_corners, geo_corners, w, h)
    else:
        # 2. Try Shapefile Index
        print("Looking up sheet in shapefile index...")
        index = ShapefileIndex(args.shapefile)
        sheet = index.lookup_by_filename(input_path.name)
        if sheet:
            print(f"  Sheet: {sheet.label}")
            geo_corners = [
                (sheet.west_long, sheet.north_lat),
                (sheet.east_long, sheet.north_lat),
                (sheet.west_long, sheet.south_lat),
                (sheet.east_long, sheet.south_lat),
            ]
            pixel_corners = [(0, 0), (w, 0), (0, h), (w, h)]
            georeferencer = Georeferencer()
            ref = georeferencer.georeference(pixel_corners, geo_corners, w, h)
        else:
            # 3. Fallback to OCR / Gemini
            print("  Falling back to OCR...")
            ocr = CoordinateOCR()
            corners = ocr.extract_from_image(img, input_path.name)

            if corners.is_complete():
                pixel_corners, geo_corners = corners.to_pixel_geo_pairs(w, h)
                georeferencer = Georeferencer()
                ref = georeferencer.georeference(pixel_corners, geo_corners, w, h)
            else:
                print("  FAILED: Could not extract coordinates via OCR or Gemini.")
                return

    print(
        f"  Bounds: lon=[{ref.bounds[0]:.4f}, {ref.bounds[2]:.4f}], lat=[{ref.bounds[1]:.4f}, {ref.bounds[3]:.4f}]"
    )

    print("Exporting...")
    base = input_path.stem
    cropped_path = output_dir / f"{base}_cropped.tif"
    geotiff_path = output_dir / f"{base}_georef.tif"

    cv2.imwrite(str(cropped_path), neatline_result.cropped_image)
    export_geotiff(cropped_path, geotiff_path, ref)
    export_world_file(geotiff_path, ref)

    print(f"Done: {geotiff_path}")
    print(f"      {geotiff_path.with_suffix('.tfw')}")


if __name__ == "__main__":
    main()
