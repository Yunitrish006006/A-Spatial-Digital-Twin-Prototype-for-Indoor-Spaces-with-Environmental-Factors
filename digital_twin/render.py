import csv
import json
import os
from typing import Dict, List, Tuple

from .model import FieldGrid


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def export_json(path: str, payload: Dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def export_field_csv(path: str, field: FieldGrid) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x", "y", "z", "temperature", "humidity", "illuminance"])
        for iz in range(field.resolution.nz):
            for iy in range(field.resolution.ny):
                for ix in range(field.resolution.nx):
                    point = field.point(ix, iy, iz)
                    index = field.index(ix, iy, iz)
                    writer.writerow(
                        [
                            round(point.x, 4),
                            round(point.y, 4),
                            round(point.z, 4),
                            round(field.values["temperature"][index], 4),
                            round(field.values["humidity"][index], 4),
                            round(field.values["illuminance"][index], 4),
                        ]
                    )


def export_svg_heatmap(path: str, field: FieldGrid, metric: str, z_index: int, title: str) -> None:
    matrix = field.layer_matrix(metric, z_index)
    values = [value for row in matrix for value in row]
    minimum = min(values)
    maximum = max(values)
    width = 640
    height = 420
    margin_x = 40
    margin_y = 60
    cell_width = (width - 2 * margin_x) / float(field.resolution.nx)
    cell_height = (height - 2 * margin_y) / float(field.resolution.ny)

    parts: List[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{margin_x}" y="30" font-size="20" font-family="Helvetica, Arial, sans-serif">{title}</text>',
        f'<text x="{margin_x}" y="48" font-size="12" font-family="Helvetica, Arial, sans-serif">min={minimum:.2f}, max={maximum:.2f}</text>',
    ]

    for iy, row in enumerate(reversed(matrix)):
        for ix, value in enumerate(row):
            x = margin_x + ix * cell_width
            y = margin_y + iy * cell_height
            color = _value_to_color(value, minimum, maximum)
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_width:.2f}" height="{cell_height:.2f}" fill="{color}" stroke="#dddddd" stroke-width="0.5" />'
            )

    legend_x = width - 80
    legend_y = margin_y
    legend_height = height - 2 * margin_y
    for step in range(100):
        fraction = step / 99.0
        y = legend_y + (1.0 - fraction) * legend_height
        color = _value_to_color(minimum + fraction * (maximum - minimum), minimum, maximum)
        parts.append(
            f'<rect x="{legend_x}" y="{y:.2f}" width="18" height="{legend_height / 100.0 + 1:.2f}" fill="{color}" stroke="none" />'
        )
    parts.append(
        f'<text x="{legend_x + 24}" y="{legend_y + 10}" font-size="11" font-family="Helvetica, Arial, sans-serif">{maximum:.1f}</text>'
    )
    parts.append(
        f'<text x="{legend_x + 24}" y="{legend_y + legend_height}" font-size="11" font-family="Helvetica, Arial, sans-serif">{minimum:.1f}</text>'
    )
    parts.append("</svg>")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(parts))


def _value_to_color(value: float, minimum: float, maximum: float) -> str:
    if maximum - minimum <= 1e-9:
        return "#cccccc"

    fraction = (value - minimum) / (maximum - minimum)
    if fraction < 0.5:
        start = (49, 130, 189)
        end = (255, 244, 173)
        local = fraction / 0.5
    else:
        start = (255, 244, 173)
        end = (203, 24, 29)
        local = (fraction - 0.5) / 0.5
    red, green, blue = _interpolate_rgb(start, end, local)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _interpolate_rgb(start: Tuple[int, int, int], end: Tuple[int, int, int], fraction: float) -> Tuple[int, int, int]:
    fraction = max(0.0, min(1.0, fraction))
    red = round(start[0] + (end[0] - start[0]) * fraction)
    green = round(start[1] + (end[1] - start[1]) * fraction)
    blue = round(start[2] + (end[2] - start[2]) * fraction)
    return red, green, blue
