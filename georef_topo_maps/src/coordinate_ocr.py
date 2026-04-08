import re
import cv2
import numpy as np
from PIL import Image
from dataclasses import dataclass
from typing import Optional


VALID_MINUTES = {0, 20, 40}

_GRID_LAT_BASE = 10
_GRID_LON_DEG, _GRID_LON_MIN = 109, 30


def _sheet_bottom_lat(sheet_num: int) -> tuple[int, int]:
    offset = sheet_num - 1
    lat_min = _GRID_LAT_BASE * 60 + offset * 20
    lat_deg = lat_min // 60
    lat_min = lat_min % 60
    return lat_deg, lat_min


SHEET_COORDS = {}
for sn in range(1, 61):
    lat_deg, lat_min = _sheet_bottom_lat(sn)
    top_min = lat_min + 20
    top_deg = lat_deg
    if top_min >= 60:
        top_min -= 60
        top_deg += 1
    SHEET_COORDS[sn] = {
        "bl": (lat_deg, lat_min, _GRID_LON_DEG, _GRID_LON_MIN),
        "br": (lat_deg, lat_min, _GRID_LON_DEG + 1, 30),
        "tl": (top_deg, top_min, _GRID_LON_DEG, _GRID_LON_MIN),
        "tr": (top_deg, top_min, _GRID_LON_DEG + 1, 30),
    }


def parse_sheet_number(filename: str) -> Optional[int]:
    m = re.search(r"e-(\d+)-(\d+)-", filename)
    if m:
        zone = int(m.group(1))
        if zone == 49:
            return int(m.group(2))
    return None


@dataclass
class CornerCoords:
    lat_deg: int = 0
    lat_min: int = 0
    lon_deg: int = 0
    lon_min: int = 0

    @property
    def lat(self) -> float:
        return self.lat_deg + self.lat_min / 60

    @property
    def lon(self) -> float:
        return self.lon_deg + self.lon_min / 60


@dataclass
class ParsedCorners:
    top_left: Optional[CornerCoords] = None
    top_right: Optional[CornerCoords] = None
    bottom_left: Optional[CornerCoords] = None
    bottom_right: Optional[CornerCoords] = None

    def infer_missing(self) -> None:
        bl = self.bottom_left
        br = self.bottom_right

        if bl is None or bl.lon_deg == 0:
            return

        lat_deg = bl.lat_deg
        lat_min = bl.lat_min
        lon_deg = bl.lon_deg
        lon_min = bl.lon_min

        lat_top_min = lat_min + 20
        lat_top_deg = lat_deg
        if lat_top_min >= 60:
            lat_top_deg += 1
            lat_top_min -= 60

        lon_right_deg = lon_deg + 1
        lon_right_min = 0

        if br and br.lon_deg > 0:
            lon_right_deg = br.lon_deg
            lon_right_min = br.lon_min or 0

        if self.top_left is None:
            self.top_left = CornerCoords(lat_top_deg, lat_top_min, lon_deg, lon_min)
        if self.top_right is None:
            self.top_right = CornerCoords(
                lat_top_deg, lat_top_min, lon_right_deg, lon_right_min
            )
        if self.bottom_right is None or self.bottom_right.lat_deg == 0:
            self.bottom_right = CornerCoords(
                lat_deg, lat_min, lon_right_deg, lon_right_min
            )

    def to_pixel_geo_pairs(
        self, width: int, height: int
    ) -> tuple[list[tuple[int, int]], list[tuple[float, float]]]:
        pixel_corners = [
            (0, 0),
            (width, 0),
            (0, height),
            (width, height),
        ]
        geo_corners = [
            (self.top_left.lon, self.top_left.lat),
            (self.top_right.lon, self.top_right.lat),
            (self.bottom_left.lon, self.bottom_left.lat),
            (self.bottom_right.lon, self.bottom_right.lat),
        ]
        return pixel_corners, geo_corners


class CoordinateOCR:
    def __init__(self, valid_minutes: set[int] = None):
        self.valid_minutes = valid_minutes or VALID_MINUTES

    def _is_valid_lat(self, c: Optional[CornerCoords]) -> bool:
        if c is None:
            return False
        return 15 <= c.lat_deg <= 30

    def _is_valid_lon(self, c: Optional[CornerCoords]) -> bool:
        if c is None:
            return False
        return 105 <= c.lon_deg <= 115

    def extract_from_image(
        self, image: np.ndarray, filename: str = ""
    ) -> ParsedCorners:
        sn = None
        if filename:
            sn = parse_sheet_number(filename)
            if sn and sn in SHEET_COORDS:
                coords = SHEET_COORDS[sn]
                result = ParsedCorners(
                    bottom_left=CornerCoords(*coords["bl"]),
                    bottom_right=CornerCoords(*coords["br"]),
                    top_left=CornerCoords(*coords["tl"]),
                    top_right=CornerCoords(*coords["tr"]),
                )
                return result

        h, w = image.shape[:2]
        result = ParsedCorners()
        bl = self._ocr_corner(image, h - 1200, 0, h - 100, 1200)
        br = self._ocr_corner(image, h - 1200, w - 1200, h - 100, w)

        if self._is_valid_lat(bl) and self._is_valid_lon(bl):
            result.bottom_left = bl
        if self._is_valid_lat(br) and self._is_valid_lon(br):
            result.bottom_right = br

        result.infer_missing()
        return result

    def _ocr_corner(
        self, image: np.ndarray, y1: int, x1: int, y2: int, x2: int
    ) -> Optional[CornerCoords]:
        import pytesseract

        crop = image[y1:y2, x1:x2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        big = cv2.resize(
            gray, (crop.shape[1] * 4, crop.shape[0] * 4), interpolation=cv2.INTER_CUBIC
        )
        pil = Image.fromarray(big)
        text = pytesseract.image_to_string(pil, config="--psm 6").strip()
        return self._parse_text(text)

    def _parse_text(self, text: str) -> Optional[CornerCoords]:
        lon_deg = lon_min = None
        lat_deg = lat_min = None

        lines = text.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            m = re.search(r"(\d{2,3})\xb0.*?(\d{1,2})", line)
            if m:
                deg, mn = int(m.group(1)), int(m.group(2))
                if 100 <= deg <= 130:
                    lon_deg, lon_min = deg, mn
                elif 15 <= deg <= 30:
                    lat_deg, lat_min = deg, mn
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                m = re.match(r"(\d{2,3})\xb0", line)
                n = re.match(r"(\d{1,2})", next_line)
                if m and n:
                    deg = int(m.group(1))
                    mn_val = int(n.group(1))
                    if 100 <= deg <= 130 and lon_deg is None:
                        lon_deg, lon_min = deg, mn_val
                    elif 15 <= deg <= 30 and lat_deg is None:
                        lat_deg, lat_min = deg, mn_val

        for line in lines:
            line = line.strip()
            if re.match(r"^\d{2}$", line):
                val = int(line)
                if 15 <= val <= 25 and lat_deg is None:
                    lat_deg = val

        if lat_deg in (19, 21):
            lat_deg = 20

        if lon_deg is not None or lat_deg is not None:
            return CornerCoords(
                lat_deg=lat_deg if lat_deg is not None else 0,
                lat_min=lat_min if lat_min is not None else 0,
                lon_deg=lon_deg if lon_deg is not None else 0,
                lon_min=lon_min if lon_min is not None else 0,
            )
        return None
