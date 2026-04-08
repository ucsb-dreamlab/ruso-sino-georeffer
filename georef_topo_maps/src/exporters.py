import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
from .georeferencer import GeoReference


def export_geotiff(
    image_path: str | Path,
    output_path: str | Path,
    reference: GeoReference,
    compression: str = "lzw",
) -> None:
    with rasterio.open(image_path) as src:
        data = src.read()
        profile = src.profile

    if data.shape[0] == 3:
        # Convert BGR to RGB
        data = data[::-1, :, :]

    profile.update(
        transform=reference.affine_transform,
        crs=reference.crs,
        compress=compression,
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data)


def export_world_file(
    image_path: str | Path,
    reference: GeoReference,
) -> Path:
    image_path = Path(image_path)
    t = reference.affine_transform
    world_path = image_path.with_suffix(".tfw")

    lines = [
        f"{t.a:.10f}",
        f"{t.d:.10f}",
        f"{t.b:.10f}",
        f"{t.e:.10f}",
        f"{t.c + t.a / 2.0 + t.b / 2.0:.10f}",
        f"{t.f + t.d / 2.0 + t.e / 2.0:.10f}",
    ]

    world_path.write_text("\n".join(lines))
    return world_path
