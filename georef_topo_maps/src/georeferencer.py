import numpy as np
from dataclasses import dataclass
from affine import Affine


@dataclass
class GeoReference:
    affine_transform: Affine
    crs: str
    bounds: tuple[float, float, float, float]


class Georeferencer:
    def __init__(self, crs: str = "EPSG:4326"):
        self.crs = crs

    def compute_affine(
        self,
        pixel_corners: list[tuple[int, int]],
        geo_corners: list[tuple[float, float]],
    ) -> Affine:
        if len(pixel_corners) != 4 or len(geo_corners) != 4:
            raise ValueError("Must provide exactly 4 corners")

        lon = np.array([g[0] for g in geo_corners], dtype=np.float64)
        lat = np.array([g[1] for g in geo_corners], dtype=np.float64)
        px = np.array(pixel_corners, dtype=np.float64)

        ones = np.ones((4, 1))
        A = np.hstack([px, ones])

        lon_coeffs = np.linalg.lstsq(A, lon, rcond=None)[0]
        lat_coeffs = np.linalg.lstsq(A, lat, rcond=None)[0]

        a, b, c = lon_coeffs[0], lon_coeffs[1], lon_coeffs[2]
        d, e, f = lat_coeffs[0], lat_coeffs[1], lat_coeffs[2]

        return Affine(a, b, c, d, e, f)

    def get_bounds(
        self, transform: Affine, width: int, height: int
    ) -> tuple[float, float, float, float]:
        left, top = transform * (0, 0)
        right, bottom = transform * (width, height)
        return (left, bottom, right, top)

    def georeference(
        self,
        pixel_corners: list[tuple[int, int]],
        geo_corners: list[tuple[float, float]],
        width: int,
        height: int,
    ) -> GeoReference:
        transform = self.compute_affine(pixel_corners, geo_corners)
        bounds = self.get_bounds(transform, width, height)
        return GeoReference(
            affine_transform=transform,
            crs=self.crs,
            bounds=bounds,
        )
