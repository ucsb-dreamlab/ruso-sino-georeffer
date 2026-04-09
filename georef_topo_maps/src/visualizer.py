import cv2
import numpy as np
from pathlib import Path
import webbrowser
from .georeferencer import GeoReference


def generate_visual_report(
    original_image: np.ndarray,
    neatline_bbox: tuple[int, int, int, int],
    ref: GeoReference,
    output_dir: Path,
    map_name: str,
    crop_size: int = 512,
    open_browser: bool = False,
) -> None:
    """
    Generates an HTML report with corner crops and a Leaflet map.
    """
    report_dir = output_dir / f"report_{map_name}"
    report_dir.mkdir(parents=True, exist_ok=True)

    x, y, w, h = neatline_bbox
    corners = [
        (x, y),  # Top-left
        (x + w, y),  # Top-right
        (x, y + h),  # Bottom-left
        (x + w, y + h),  # Bottom-right
    ]
    corner_names = ["top_left", "top_right", "bottom_left", "bottom_right"]

    # 1. Generate corner crops
    for i, (cx, cy) in enumerate(corners):
        name = corner_names[i]

        # Calculate crop area
        x1 = max(0, cx - crop_size // 2)
        y1 = max(0, cy - crop_size // 2)
        x2 = min(original_image.shape[1], x1 + crop_size)
        y2 = min(original_image.shape[0], y1 + crop_size)

        # Ensure we don't go out of bounds if we hit edges
        x1 = max(0, x2 - crop_size)
        y1 = max(0, y2 - crop_size)

        crop = original_image[y1:y2, x1:x2].copy()

        # Draw red cross at (cx, cy) relative to crop
        rx, ry = cx - x1, cy - y1
        cross_size = 20
        color = (0, 0, 255)  # BGR Red
        thickness = 2
        cv2.line(crop, (rx - cross_size, ry), (rx + cross_size, ry), color, thickness)
        cv2.line(crop, (rx, ry - cross_size), (rx, ry + cross_size), color, thickness)

        cv2.imwrite(
            str(report_dir / f"corner_{name}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 90]
        )

    # 2. Generate low-res overview
    # Extract the neatline area first
    neatline_img = original_image[y : y + h, x : x + w]

    # Resize for web (max 2048px)
    max_dim = 2048
    scale = min(1.0, max_dim / max(w, h))
    if scale < 1.0:
        low_res = cv2.resize(
            neatline_img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA
        )
    else:
        low_res = neatline_img

    cv2.imwrite(
        str(report_dir / "overview.jpg"), low_res, [cv2.IMWRITE_JPEG_QUALITY, 80]
    )

    # 3. Generate HTML
    lon_min, lat_min, lon_max, lat_max = ref.bounds

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Georeferencing Report - {output_dir.name}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f0f0f0; }}
        .corners {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 20px; }}
        .corner-box {{ background: white; padding: 10px; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .corner-box img {{ width: 100%; height: auto; display: block; }}
        .corner-label {{ font-weight: bold; margin-bottom: 5px; text-transform: capitalize; }}
        #map {{ height: 600px; width: 100%; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        h1 {{ margin-top: 0; }}
    </style>
</head>
<body>
    <h1>Georeferencing Report</h1>
    <div class="corners">
        <div class="corner-box">
            <div class="corner-label">Top Left</div>
            <img src="corner_top_left.jpg" />
        </div>
        <div class="corner-box">
            <div class="corner-label">Top Right</div>
            <img src="corner_top_right.jpg" />
        </div>
        <div class="corner-box">
            <div class="corner-label">Bottom Left</div>
            <img src="corner_bottom_left.jpg" />
        </div>
        <div class="corner-box">
            <div class="corner-label">Bottom Right</div>
            <img src="corner_bottom_right.jpg" />
        </div>
    </div>
    
    <div id="map"></div>

    <script>
        var map = L.map('map');
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        var imageUrl = 'overview.jpg';
        var imageBounds = [[{lat_min}, {lon_min}], [{lat_max}, {lon_max}]];
        
        L.imageOverlay(imageUrl, imageBounds, {{
            opacity: 0.5
        }}).addTo(map);
        
        map.fitBounds(imageBounds);
    </script>
</body>
</html>
"""

    html_path = report_dir / "index.html"
    with open(html_path, "w") as f:
        f.write(html_content)

    print(f"Visualization report generated: {html_path}")
    if open_browser:
        webbrowser.open(f"file://{html_path.absolute()}")
