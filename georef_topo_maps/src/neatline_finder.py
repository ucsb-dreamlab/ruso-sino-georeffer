import numpy as np
import cv2
from dataclasses import dataclass


@dataclass
class NeatlineResult:
    cropped_image: np.ndarray
    neatline_bbox: tuple[int, int, int, int]


class NeatlineFinder:
    def __init__(self, min_line_length_ratio: float = 0.5):
        self.min_line_length_ratio = min_line_length_ratio

    def find(
        self, image: np.ndarray, outer_bbox: tuple[int, int, int, int]
    ) -> NeatlineResult:
        x, y, w, h = outer_bbox
        # Crop to the outer bbox to reduce noise
        roi = image[y : y + h, x : x + w]
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi

        # Adaptive thresholding to find the lines
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # We are looking for a large rectangle (the neatline)
        # It should be at least 40% of the ROI width and height
        min_area = w * h * 0.4
        rect_candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            # Approximate the contour to a polygon
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                rect_candidates.append((area, approx))

        if rect_candidates:
            # Sort by area descending
            rect_candidates.sort(key=lambda x: x[0], reverse=True)
            # Most Soviet maps have an outer frame and an inner neatline.
            # If we find both, the second largest is likely the neatline.
            # If we find only one large one, it's either the neatline or the frame.
            if len(rect_candidates) >= 2:
                area1, approx1 = rect_candidates[0]
                # If the largest is almost the size of the whole area, it's probably the outer frame.
                if area1 > w * h * 0.95:
                    _, best_rect = rect_candidates[1]
                else:
                    _, best_rect = rect_candidates[0]
            else:
                _, best_rect = rect_candidates[0]

            # Sort the points of the rectangle
            pts = best_rect.reshape(4, 2)
            # Find the bounding box of the points
            nx, ny, nw, nh = cv2.boundingRect(pts)

            # Crop to this bounding box
            cropped = roi[ny : ny + nh, nx : nx + nw]
            return NeatlineResult(
                cropped_image=cropped,
                neatline_bbox=(x + nx, y + ny, nw, nh),
            )

        # Fallback to fixed margin if no rectangle found
        margin = 130
        cropped = roi[margin:-margin, margin:-margin]
        return NeatlineResult(
            cropped_image=cropped,
            neatline_bbox=(x + margin, y + margin, w - 2 * margin, h - 2 * margin),
        )
