import argparse
from pathlib import Path
import cv2

from src import CollarDetector
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

    print("Loading image...")
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Could not read: {input_path}")

    print("Detecting collar...")
    detector = CollarDetector()
    collar = detector.detect(img)
    print(f"  Cropped: {collar.cropped_image.shape[:2]} px")

    print("Looking up sheet in shapefile index...")
    index = ShapefileIndex(args.shapefile)
    sheet = index.lookup_by_filename(input_path.name)
    if sheet is None:
        print(f"  WARNING: No matching sheet found for '{input_path.name}'")
        print("  Falling back to OCR...")
        from src import CoordinateOCR

        ocr = CoordinateOCR()
        corners = ocr.extract_from_image(img, input_path.name)

        for name in ["top_left", "top_right", "bottom_left", "bottom_right"]:
            c = getattr(corners, name)
            if c:
                print(
                    f"  {name}: {c.lat_deg}°{c.lat_min:02d}' N, {c.lon_deg}°{c.lon_min:02d}' E"
                )
            else:
                print(f"  {name}: MISSING")

        h, w = collar.cropped_image.shape[:2]
        pixel_corners, geo_corners = corners.to_pixel_geo_pairs(w, h)

        print("Computing georeference...")
        georeferencer = Georeferencer()
        ref = georeferencer.georeference(pixel_corners, geo_corners, w, h)
    else:
        print(f"  Sheet: {sheet.label}")
        print(
            f"  Bounds: lon=[{sheet.west_long:.4f}, {sheet.east_long:.4f}], lat=[{sheet.south_lat:.4f}, {sheet.north_lat:.4f}]"
        )

        h, w = collar.cropped_image.shape[:2]
        geo_corners = [
            (sheet.west_long, sheet.north_lat),
            (sheet.east_long, sheet.north_lat),
            (sheet.west_long, sheet.south_lat),
            (sheet.east_long, sheet.south_lat),
        ]
        pixel_corners = [(0, 0), (w, 0), (0, h), (w, h)]

        print("Computing georeference...")
        georeferencer = Georeferencer()
        ref = georeferencer.georeference(pixel_corners, geo_corners, w, h)

    print(
        f"  Bounds: lon=[{ref.bounds[0]:.4f}, {ref.bounds[2]:.4f}], lat=[{ref.bounds[1]:.4f}, {ref.bounds[3]:.4f}]"
    )

    print("Exporting...")
    base = input_path.stem
    cropped_path = output_dir / f"{base}_cropped.tif"
    geotiff_path = output_dir / f"{base}_georef.tif"

    cv2.imwrite(str(cropped_path), collar.cropped_image)
    export_geotiff(cropped_path, geotiff_path, ref)
    export_world_file(geotiff_path, ref)

    print(f"Done: {geotiff_path}")
    print(f"      {geotiff_path.with_suffix('.tfw')}")


if __name__ == "__main__":
    main()
