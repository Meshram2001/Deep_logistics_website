"""Generate a clean India network marketing SVG (map + pins).

- Uses the existing states SVG as the base map
- Adds pins based on video_pipeline/locations_geocoded.json
- Outputs to main/static/main/images/network_map.svg

This is intended for marketing materials and as a static fallback image.

Note: Pin placement uses a simple lat/lon -> SVG viewBox transform, so it may need minor tuning.
"""

import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
SVG_IN = ROOT / "assets" / "india_states.svg"
LOCATIONS = ROOT / "locations_geocoded.json"
SVG_OUT = ROOT.parent / "main" / "static" / "main" / "images" / "network_map.svg"

# Approx India bounding box for projection
LAT_MIN, LAT_MAX = 6.0, 37.5
LON_MIN, LON_MAX = 68.0, 97.5

VIEWBOX_SIZE = 1000

# Visual styling
BG = "#f2efe5"  # soft beige
MAP_FILL = "#f8f8f8"
MAP_STROKE = "#c9c9c9"
PIN_FILL = "#111111"
PIN_STROKE = "#ffffff"
HUB_FILL = "#e74c3c"  # red

# Pick a few cities as "hubs" (red pins) for a nicer marketing look.
HUBS = {
    ("Maharashtra", "Mumbai"),
    ("Maharashtra", "Pune"),
    ("Delhi", "Kashmere Gate"),
    ("Chhattisgarh", "Raipur"),
    ("Gujarat", "Rajkot"),
    ("Punjab", "Ludhiana"),
    ("Uttar Pradesh", "Noida"),
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def project(lat: float, lon: float):
    # Map lon->x, lat->y into viewBox 0..1000; invert y.
    x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * VIEWBOX_SIZE
    y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * VIEWBOX_SIZE
    # Clamp
    x = max(0.0, min(float(VIEWBOX_SIZE), float(x)))
    y = max(0.0, min(float(VIEWBOX_SIZE), float(y)))
    return x, y


def main() -> int:
    if not SVG_IN.exists():
        raise SystemExit(f"Missing {SVG_IN}")
    if not LOCATIONS.exists():
        raise SystemExit(f"Missing {LOCATIONS}")

    base_svg = SVG_IN.read_text(encoding="utf-8")

    # Lightly restyle the base SVG: beige background + subtle map look.
    # We keep the paths as-is but override root fill/stroke.
    # (Simple string replacements to avoid full XML parsing.)
    base_svg = base_svg.replace('fill="#6f9c76"', f'fill="{MAP_FILL}"')
    base_svg = base_svg.replace('stroke="#ffffff"', f'stroke="{MAP_STROKE}"')
    base_svg = base_svg.replace('stroke-width=".5"', 'stroke-width="0.8"')

    # Insert background rect right after <svg ...>
    insert_at = base_svg.find('>') + 1
    bg_rect = f'\n  <rect x="0" y="0" width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" fill="{BG}" />\n'
    base_svg = base_svg[:insert_at] + bg_rect + base_svg[insert_at:]

    locations = load_json(LOCATIONS)

    pin_elems = [
        '\n  <g id="pins">',
        '    <style>',
        '      .pin { stroke: %s; stroke-width: 2; }' % PIN_STROKE,
        '      .pinShadow { fill: rgba(0,0,0,0.18); }',
        '      .label { font-family: Poppins, Arial, sans-serif; font-size: 18px; font-weight: 700; fill: #1f2a33; }',
        '    </style>',
    ]

    # Slight shadow + pin circles
    for state, entries in locations.items():
        for e in entries:
            lat = e.get("lat")
            lon = e.get("lon")
            city = e.get("city")
            if lat is None or lon is None:
                continue

            x, y = project(float(lat), float(lon))
            is_hub = (state, city) in HUBS
            fill = HUB_FILL if is_hub else PIN_FILL

            # shadow
            pin_elems.append(f'    <circle class="pinShadow" cx="{x:.2f}" cy="{(y+2.2):.2f}" r="6.3" />')
            # pin
            pin_elems.append(f'    <circle class="pin" cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{fill}" />')

    pin_elems.append('  </g>\n')

    # Add a simple title
    title = '  <text class="label" x="60" y="120">OUR NETWORK IN INDIA</text>\n'

    # Place title + pins just before closing </svg>
    out_svg = base_svg.replace('</svg>', '\n' + title + '\n'.join(pin_elems) + '\n</svg>')

    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(out_svg, encoding="utf-8")
    print(f"Wrote {SVG_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
