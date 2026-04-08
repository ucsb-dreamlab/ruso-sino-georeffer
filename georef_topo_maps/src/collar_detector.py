import numpy as np
import cv2
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CollarResult:
    cropped_image: np.ndarray
    outer_bbox: tuple[int, int, int, int]  # x, y, w, h
    content_bbox: tuple[int, int, int, int]  # x, y, w, h (inner neatline)


class CollarDetector:
    def __init__(
        self,
        brightness_threshold: int = 240,
        min_border_pixels: int = 50,
        content_margin: int = 130,
    ):
        self.brightness_threshold = brightness_threshold
        self.min_border_pixels = min_border_pixels
        self.content_margin = content_margin

    def detect(self, image: np.ndarray) -> CollarResult:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        top, bottom, left, right = self._find_content_bounds(gray)
        content_x1 = left + self.content_margin
        content_y1 = top + self.content_margin
        content_x2 = right - self.content_margin
        content_y2 = bottom - self.content_margin

        cropped = image[content_y1:content_y2, content_x1:content_x2]

        return CollarResult(
            cropped_image=cropped,
            outer_bbox=(left, top, right - left, bottom - top),
            content_bbox=(
                content_x1,
                content_y1,
                content_x2 - content_x1,
                content_y2 - content_y1,
            ),
        )

    def _find_content_bounds(self, gray: np.ndarray) -> tuple[int, int, int, int]:
        h, w = gray.shape

        def find_edge(profile: np.ndarray) -> int:
            for i in range(len(profile)):
                if profile[i] < self.brightness_threshold:
                    return i
            return len(profile) - 1

        def find_edge_rev(profile: np.ndarray) -> int:
            for i in range(len(profile) - 1, -1, -1):
                if profile[i] < self.brightness_threshold:
                    return i
            return 0

        top_row_means = gray.mean(axis=1)
        bottom_row_means = gray.mean(axis=1)[::-1]
        left_col_means = gray.mean(axis=0)
        right_col_means = gray.mean(axis=0)[::-1]

        top = find_edge(top_row_means)
        bottom = find_edge_rev(bottom_row_means)
        left = find_edge(left_col_means)
        right = find_edge_rev(right_col_means)

        top = max(top, self.min_border_pixels)
        bottom = min(bottom, h - self.min_border_pixels)
        left = max(left, self.min_border_pixels)
        right = min(right, w - self.min_border_pixels)

        return top, bottom, left, right

    def detect_from_file(self, path: str | Path) -> CollarResult:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image: {path}")
        return self.detect(image)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Detect and remove map collars")
    parser.add_argument("input", help="Input TIFF/PNG file")
    parser.add_argument("-o", "--output", help="Output cropped image path")
    args = parser.parse_args()

    detector = CollarDetector()
    result = detector.detect_from_file(args.input)

    print(f"Outer bbox: {result.outer_bbox}")
    print(f"Content bbox: {result.content_bbox}")
    print(f"Cropped size: {result.cropped_image.shape[:2]}")

    if args.output:
        cv2.imwrite(args.output, result.cropped_image)
        print(f"Saved to {args.output}")
