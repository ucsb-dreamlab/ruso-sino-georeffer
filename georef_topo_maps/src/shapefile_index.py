import re
from pathlib import Path
from dataclasses import dataclass

from shapely.geometry import Polygon
import geopandas as gpd


@dataclass
class SheetInfo:
    cell_id: int
    label: str
    year: str
    polygon: Polygon
    west_long: float
    east_long: float
    south_lat: float
    north_lat: float


class ShapefileIndex:
    def __init__(self, shapefile_path: str | Path):
        self.shapefile_path = Path(shapefile_path)
        if not self.shapefile_path.exists():
            raise ValueError(f"Shapefile not found: {self.shapefile_path}")
        self.gdf = gpd.read_file(str(self.shapefile_path))
        self._label_to_row: dict[str, int] = {}
        for idx, row in self.gdf.iterrows():
            self._label_to_row[str(row["label"]).upper()] = int(idx)

    def lookup_by_filename(self, filename: str) -> SheetInfo | None:
        label = self._extract_label(filename)
        if label is None:
            return None
        return self.lookup_by_label(label)

    def lookup_by_label(self, label: str) -> SheetInfo | None:
        idx = self._label_to_row.get(label.upper())
        if idx is None:
            return None
        row = self.gdf.iloc[idx]
        return SheetInfo(
            cell_id=int(row["CELL_ID"]),
            label=row["label"],
            year=row["year"],
            polygon=row["geometry"],
            west_long=float(row["westLong"]),
            east_long=float(row["eastLong"]),
            south_lat=float(row["southLat"]),
            north_lat=float(row["northLat"]),
        )

    def _extract_label(self, filename: str) -> str | None:
        m = re.search(r"(e-\d+-\d+)", filename, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Look up sheet info from shapefile index"
    )
    parser.add_argument("filename", help="Map filename or sheet label (e.g. E-49-14)")
    parser.add_argument(
        "--shapefile",
        default="index_map/6840s_100_r8_INDEX.shp",
        help="Path to shapefile",
    )
    args = parser.parse_args()

    idx = ShapefileIndex(args.shapefile)
    info = idx.lookup_by_filename(args.filename)
    if info is None:
        info = idx.lookup_by_label(args.filename)

    if info is None:
        print(f"No match found for: {args.filename}")
    else:
        print(f"Label:      {info.label}")
        print(f"Cell ID:    {info.cell_id}")
        print(f"Year:       {info.year}")
        print(f"West Long:  {info.west_long:.6f}")
        print(f"East Long:  {info.east_long:.6f}")
        print(f"South Lat:  {info.south_lat:.6f}")
        print(f"North Lat:  {info.north_lat:.6f}")
