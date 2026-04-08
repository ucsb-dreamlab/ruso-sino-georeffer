import re
import cv2
import numpy as np
import os
import json
from PIL import Image
from dataclasses import dataclass
from typing import Optional


VALID_MINUTES = {0, 20, 40}


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

    def is_complete(self) -> bool:
        return all([self.top_left, self.top_right, self.bottom_left, self.bottom_right])

    def infer_missing(self) -> None:
        bl = self.bottom_left
        br = self.bottom_right

        if bl is None or bl.lon_deg == 0:
            return

        lat_deg = bl.lat_deg
        lat_min = bl.lat_min
        lon_deg = bl.lon_deg
        lon_min = bl.lon_min

        # Soviet 1:100k maps are 20' lat by 30' lon
        lat_top_min = lat_min + 20
        lat_top_deg = lat_deg
        if lat_top_min >= 60:
            lat_top_deg += 1
            lat_top_min -= 60

        lon_right_deg = lon_deg
        lon_right_min = lon_min + 30
        if lon_right_min >= 60:
            lon_right_deg += 1
            lon_right_min -= 60

        if br and br.lon_deg > 0:
            lon_right_deg = br.lon_deg
            lon_right_min = br.lon_min

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
        if not self.is_complete():
            raise ValueError(
                "ParsedCorners is not complete. Cannot generate geo pairs."
            )

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


class GeminiOCR:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model = None
        if self.api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            except ImportError:
                pass

    def extract_from_image(self, image: np.ndarray) -> Optional[ParsedCorners]:
        if not self.model:
            return None

        h, w = image.shape[:2]
        # Crop corners (bottom left and bottom right are most important)
        bl_crop = image[h - 1000 :, :1000]
        br_crop = image[h - 1000 :, w - 1000 :]

        # Combine crops for a single request
        combined = np.hstack([bl_crop, br_crop])
        pil_img = Image.fromarray(cv2.cvtColor(combined, cv2.COLOR_BGR2RGB))

        prompt = """
        This is a scan of a Soviet topographic map. I need the geographic coordinates 
        from the bottom-left and bottom-right corners. 
        Look for numbers like 39°40' or 110°30'.
        Return ONLY a JSON object with this structure:
        {
            "bottom_left": {"lat_deg": 39, "lat_min": 20, "lon_deg": 110, "lon_min": 0},
            "bottom_right": {"lat_deg": 39, "lat_min": 20, "lon_deg": 110, "lon_min": 30}
        }
        """

        try:
            response = self.model.generate_content([prompt, pil_img])
            text = response.text
            # Clean up JSON if model adds markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            data = json.loads(text)

            result = ParsedCorners()
            if "bottom_left" in data:
                result.bottom_left = CornerCoords(**data["bottom_left"])
            if "bottom_right" in data:
                result.bottom_right = CornerCoords(**data["bottom_right"])

            result.infer_missing()
            return result
        except Exception as e:
            print(f"Gemini OCR failed: {e}")
            return None


class CoordinateOCR:
    def __init__(self, valid_minutes: Optional[set[int]] = None):
        self.valid_minutes = valid_minutes or VALID_MINUTES
        self.gemini = GeminiOCR()

    def _is_valid(self, c: Optional[CornerCoords]) -> bool:
        if c is None:
            return False
        # Geographic common sense for the targeted China region
        valid_lat = 15 <= c.lat_deg <= 55
        valid_lon = 70 <= c.lon_deg <= 140
        valid_min = c.lat_min in self.valid_minutes and c.lon_min in self.valid_minutes
        return valid_lat and valid_lon and valid_min

    def extract_from_image(
        self, image: np.ndarray, filename: str = ""
    ) -> ParsedCorners:
        h, w = image.shape[:2]
        result = ParsedCorners()

        # Try Tesseract first
        print("  Trying Tesseract...")
        bl = self._ocr_corner(image, h - 1200, 0, h - 100, 1200)
        br = self._ocr_corner(image, h - 1200, w - 1200, h - 100, w)

        if self._is_valid(bl):
            result.bottom_left = bl
        if self._is_valid(br):
            result.bottom_right = br

        result.infer_missing()

        # If Tesseract failed or gave invalid results, try Gemini
        if not self._is_valid(result.bottom_left) or not self._is_valid(
            result.bottom_right
        ):
            print("  Tesseract failed or invalid. Trying Gemini Vision...")
            gemini_result = self.gemini.extract_from_image(image)
            if gemini_result:
                # Merge or replace
                if self._is_valid(gemini_result.bottom_left):
                    result.bottom_left = gemini_result.bottom_left
                if self._is_valid(gemini_result.bottom_right):
                    result.bottom_right = gemini_result.bottom_right
                result.infer_missing()

        return result

    def _ocr_corner(
        self, image: np.ndarray, y1: int, x1: int, y2: int, x2: int
    ) -> Optional[CornerCoords]:
        try:
            import pytesseract
        except ImportError:
            return None

        crop = image[y1:y2, x1:x2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        # Binarize for better OCR
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        big = cv2.resize(
            binary,
            (binary.shape[1] * 2, binary.shape[0] * 2),
            interpolation=cv2.INTER_CUBIC,
        )
        pil = Image.fromarray(big)
        text = pytesseract.image_to_string(pil, config="--psm 6").strip()
        return self._parse_text(text)

    def _parse_text(self, text: str) -> Optional[CornerCoords]:
        lon_deg = lon_min = None
        lat_deg = lat_min = None

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # Look for degrees and minutes
            # Matches "39°20'" or "39 20" or "39.20"
            m = re.search(r"(\d{2,3})[^\d]{1,3}(\d{1,2})", line)
            if m:
                deg, mn = int(m.group(1)), int(m.group(2))
                if 70 <= deg <= 140:
                    lon_deg, lon_min = deg, mn
                elif 15 <= deg <= 55:
                    lat_deg, lat_min = deg, mn

        if lon_deg is not None or lat_deg is not None:
            return CornerCoords(
                lat_deg=lat_deg or 0,
                lat_min=lat_min or 0,
                lon_deg=lon_deg or 0,
                lon_min=lon_min or 0,
            )
        return None
