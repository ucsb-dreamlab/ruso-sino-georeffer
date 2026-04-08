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

        # 1. Use a Sobel or Canny filter to find feature-rich areas
        # Map content is dense with lines and symbols, margins are sparse.
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edges = cv2.Canny(blurred, 30, 100)

        # 2. Compute density profiles (projection of edge pixels)
        # We look for the sharp transition from low-density (margin) to high-density (content)
        row_density = np.mean(edges, axis=1)
        col_density = np.mean(edges, axis=0)

        def find_transition(profile: np.ndarray, side: str, limit_size: int) -> int:
            # Neatline is usually between 100 and 450 pixels from the outer edge
            search_min = 80
            search_max = min(500, limit_size // 4)

            if side == "start":
                # Look for the first major jump in density
                window = 15
                diffs = []
                for i in range(search_min, search_max):
                    prev_avg = np.mean(profile[i - window : i])
                    curr_avg = np.mean(profile[i : i + window])
                    diffs.append(curr_avg - prev_avg)
                return int(search_min + np.argmax(diffs))
            else:  # side == "end"
                window = 15
                diffs = []
                for i in range(limit_size - search_max, limit_size - search_min):
                    prev_avg = np.mean(profile[i - window : i])
                    curr_avg = np.mean(profile[i : i + window])
                    diffs.append(prev_avg - curr_avg)
                return int((limit_size - search_max) + np.argmax(diffs))

        top_line = find_transition(row_density, "start", h)
        bottom_line = find_transition(row_density, "end", h)
        left_line = find_transition(col_density, "start", w)
        right_line = find_transition(col_density, "end", w)

        # 3. Refine with Hough Lines near the transition points
        # If we find a strong line near the density jump, snap to it.
        def refine_line(img_edges: np.ndarray, pos: int, horizontal: bool) -> int:
            search_range = 20
            if horizontal:
                roi_edges = img_edges[
                    max(0, pos - search_range) : min(h, pos + search_range), :
                ]
                lines = cv2.HoughLinesP(
                    roi_edges,
                    1,
                    np.pi / 180,
                    threshold=100,
                    minLineLength=w // 2,
                    maxLineGap=10,
                )
                if lines is not None:
                    # Find the line closest to the center of the search area
                    best_y = pos
                    min_dist = 999
                    for line in lines:
                        y_val = (line[0][1] + line[0][3]) // 2 + (pos - search_range)
                        if abs(y_val - pos) < min_dist:
                            min_dist = abs(y_val - pos)
                            best_y = y_val
                    return int(best_y)
            else:
                roi_edges = img_edges[
                    :, max(0, pos - search_range) : min(w, pos + search_range)
                ]
                lines = cv2.HoughLinesP(
                    roi_edges,
                    1,
                    np.pi / 180,
                    threshold=100,
                    minLineLength=h // 2,
                    maxLineGap=10,
                )
                if lines is not None:
                    best_x = pos
                    min_dist = 999
                    for line in lines:
                        x_val = (line[0][0] + line[0][2]) // 2 + (pos - search_range)
                        if abs(x_val - pos) < min_dist:
                            min_dist = abs(x_val - pos)
                            best_x = x_val
                    return int(best_x)
            return pos

        top_line = refine_line(edges, top_line, True)
        bottom_line = refine_line(edges, bottom_line, True)
        left_line = refine_line(edges, left_line, False)
        right_line = refine_line(edges, right_line, False)

        # Final crop
        cropped = roi[top_line:bottom_line, left_line:right_line]
        return NeatlineResult(
            cropped_image=cropped,
            neatline_bbox=(
                x + left_line,
                y + top_line,
                right_line - left_line,
                bottom_line - top_line,
            ),
        )
