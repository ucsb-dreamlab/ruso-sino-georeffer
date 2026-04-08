import numpy as np
import cv2
from dataclasses import dataclass


@dataclass
class NeatlineResult:
    cropped_image: np.ndarray
    neatline_bbox: tuple[int, int, int, int]


class NeatlineFinder:
    def __init__(self, content_margin: int = 130):
        self.content_margin = content_margin

    def find(
        self, image: np.ndarray, content_bbox: tuple[int, int, int, int] = None
    ) -> NeatlineResult:
        h, w = image.shape[:2]

        if content_bbox is None:
            x, y, bw, bh = 0, 0, w, h
        else:
            x, y, bw, bh = content_bbox

        inner_x1 = x + self.content_margin
        inner_y1 = y + self.content_margin
        inner_x2 = x + bw - self.content_margin
        inner_y2 = y + bh - self.content_margin

        inner_x2 = min(inner_x2, w)
        inner_y2 = min(inner_y2, h)

        cropped = image[inner_y1:inner_y2, inner_x1:inner_x2]
        return NeatlineResult(
            cropped_image=cropped,
            neatline_bbox=(
                inner_x1,
                inner_y1,
                inner_x2 - inner_x1,
                inner_y2 - inner_y1,
            ),
        )
