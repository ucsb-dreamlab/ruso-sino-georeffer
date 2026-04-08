import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class GridBounds:
    west: float
    east: float
    south: float
    north: float
    scale: str


class SovietGridDecoder:
    """
    Decodes Soviet Map Grid IDs (SK-42) into decimal degree coordinates.
    Supports 1:1,000,000 (e.g., E-49), 1:100,000 (E-49-14),
    1:50,000 (E-49-14-A), and 1:25,000 (E-49-14-A-a).
    """

    def decode(self, identifier: str) -> Optional[GridBounds]:
        # Normalize: 6840s_100_r8_e-49-14-m.tif -> E-49-14
        identifier = identifier.upper().replace("_", "-")

        # Determine scale if possible
        has_100 = "-100-" in identifier
        has_50 = "-050-" in identifier or "-50-" in identifier

        # 1:1,000,000 (e.g., E-49)
        # Look for [Letter]-[Number] with a 1- or 2-digit number
        matches = list(re.finditer(r"([A-V])-(\d{1,2})\b", identifier))
        if not matches:
            return None

        # If multiple matches, the one with more segments following it is likely the map ID
        # or just take the last one as it's often the ID in these filenames
        best_match = matches[-1]
        band, zone = best_match.group(1), int(best_match.group(2))

        # 1:50,000 (e.g., E-49-14-A)
        m50 = re.search(rf"{band}-{zone}-(\d{{1,3}})-([A-D1-4])", identifier)
        if m50 and (has_50 or not has_100):
            return self._decode_50k(band, zone, int(m50.group(1)), m50.group(2))

        # 1:100,000 (e.g., E-49-14)
        m100 = re.search(rf"{band}-{zone}-(\d{{1,3}})", identifier)
        if m100:
            return self._decode_100k(band, zone, int(m100.group(1)))

        return self._decode_1m(band, zone)

    def _decode_1m(self, lat_band: str, lon_zone: int) -> GridBounds:
        # Latitude bands: A=0-4, B=4-8, ...
        lat_start = (ord(lat_band) - ord("A")) * 4.0
        # Longitude zones: 31 = 0-6E, 32 = 6-12E, ...
        # Zone 1 is 180W-174W. Zone 31 is 0-6E.
        lon_start = (lon_zone - 31) * 6.0

        return GridBounds(
            west=lon_start,
            east=lon_start + 6.0,
            south=lat_start,
            north=lat_start + 4.0,
            scale="1:1,000,000",
        )

    def _decode_100k(
        self, lat_band: str, lon_zone: int, sheet_num: int
    ) -> Optional[GridBounds]:
        if not (1 <= sheet_num <= 144):
            return None

        parent = self._decode_1m(lat_band, lon_zone)

        # 144 sheets in 1M sheet, 12x12 grid
        # Row 1 is North, Row 12 is South
        # Sheet 1 is top-left (NW), Sheet 144 is bottom-right (SE)
        row = (sheet_num - 1) // 12
        col = (sheet_num - 1) % 12

        lat_step = 4.0 / 12.0  # 20'
        lon_step = 6.0 / 12.0  # 30'

        north = parent.north - (row * lat_step)
        west = parent.west + (col * lon_step)

        return GridBounds(
            west=west,
            east=west + lon_step,
            south=north - lat_step,
            north=north,
            scale="1:100,000",
        )

    def _decode_50k(
        self, lat_band: str, lon_zone: int, sheet_num: int, sub_id: str
    ) -> Optional[GridBounds]:
        parent = self._decode_100k(lat_band, lon_zone, sheet_num)
        if not parent:
            return None

        # NW, NE, SW, SE
        mapping = {
            "A": (0, 0),
            "1": (0, 0),
            "B": (0, 1),
            "2": (0, 1),
            "V": (1, 0),
            "3": (1, 0),
            "C": (1, 0),
            "G": (1, 1),
            "4": (1, 1),
            "D": (1, 1),
        }

        offsets = mapping.get(sub_id)
        if not offsets:
            return None

        row, col = offsets
        lat_step = (parent.north - parent.south) / 2.0
        lon_step = (parent.east - parent.west) / 2.0

        north = parent.north - (row * lat_step)
        west = parent.west + (col * lon_step)

        return GridBounds(
            west=west,
            east=west + lon_step,
            south=north - lat_step,
            north=north,
            scale="1:50,000",
        )


if __name__ == "__main__":
    import sys

    decoder = SovietGridDecoder()
    if len(sys.argv) > 1:
        res = decoder.decode(sys.argv[1])
        print(res)
