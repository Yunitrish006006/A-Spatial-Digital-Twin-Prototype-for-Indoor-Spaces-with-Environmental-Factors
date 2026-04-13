import csv
import json
import os
from html import escape
from typing import Dict, List, Optional, Tuple

from digital_twin.core.entities import Device
from digital_twin.physics.model import FieldGrid


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


def export_svg_volume_heatmap(
    path: str,
    field: FieldGrid,
    metric: str,
    title: str,
    devices: Optional[List[Device]] = None,
) -> None:
    values = field.values[metric]
    minimum = min(values)
    maximum = max(values)
    width = 760
    height = 560
    legend_x = width - 86
    legend_y = 96
    legend_height = 330
    usable_width = width - 190
    usable_height = height - 140
    nx = field.resolution.nx
    ny = field.resolution.ny
    nz = field.resolution.nz
    x_step = min(usable_width / max(nx + ny + 2, 1), usable_height / max((nx + ny) * 0.55 + nz * 1.4, 1))
    y_step = x_step * 0.58
    z_step = x_step * 1.18
    left_bound = 42.0
    right_bound = legend_x - 48.0
    top_bound = 86.0
    bottom_bound = height - 58.0
    x_span = (nx + ny - 2) * x_step
    y_span = (nx + ny - 2) * y_step + (nz - 1) * z_step
    origin_x = left_bound + (ny - 1) * x_step + max(0.0, (right_bound - left_bound - x_span) / 2.0)
    origin_y = top_bound + (nz - 1) * z_step + max(0.0, (bottom_bound - top_bound - y_span) / 2.0)
    point_radius = max(4.0, min(10.0, x_step * 0.28))

    def project_index(ix: float, iy: float, iz: float) -> Tuple[float, float]:
        return (
            origin_x + (ix - iy) * x_step,
            origin_y + (ix + iy) * y_step - iz * z_step,
        )

    parts: List[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="560" viewBox="0 0 760 560">',
        '<rect width="100%" height="100%" fill="#fffdf7" />',
        f'<text x="34" y="34" font-size="21" font-family="Helvetica, Arial, sans-serif" fill="#17211b">{escape(title)}</text>',
        f'<text x="34" y="56" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="#69776e">3D sampled field, min={minimum:.2f}, max={maximum:.2f}</text>',
    ]

    parts.extend(_room_wireframe(project_index, nx, ny, nz))

    points = []
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                index = field.index(ix, iy, iz)
                screen_x, screen_y = project_index(ix, iy, iz)
                depth = ix + iy + iz * 0.8
                points.append((depth, screen_x, screen_y, values[index]))

    for _, screen_x, screen_y, value in sorted(points):
        color = _value_to_color(value, minimum, maximum)
        opacity = _value_to_opacity(value, minimum, maximum)
        parts.append(
            f'<circle cx="{screen_x:.2f}" cy="{screen_y:.2f}" r="{point_radius:.2f}" fill="{color}" fill-opacity="{opacity:.2f}" stroke="#20352b" stroke-opacity="0.22" stroke-width="0.7" />'
        )

    parts.extend(_device_marker_parts(project_index, field, devices or []))
    parts.extend(_legend_parts(legend_x, legend_y, legend_height, minimum, maximum))
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


def _value_to_opacity(value: float, minimum: float, maximum: float) -> float:
    if maximum - minimum <= 1e-9:
        return 0.78
    fraction = (value - minimum) / (maximum - minimum)
    return 0.48 + 0.44 * max(0.0, min(1.0, fraction))


def _device_marker_parts(project_index, field: FieldGrid, devices: List[Device]) -> List[str]:
    if not devices:
        return []

    parts = [
        '<g id="device-markers">',
        '<text x="34" y="78" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="#17211b">Appliance positions</text>',
    ]
    for device in devices:
        if device.kind in ("ac", "window"):
            parts.extend(_wall_surface_marker_parts(project_index, field, device))
            continue
        ix = _coordinate_to_grid_index(device.position.x, field.x_coords)
        iy = _coordinate_to_grid_index(device.position.y, field.y_coords)
        iz = _coordinate_to_grid_index(device.position.z, field.z_coords)
        screen_x, screen_y = project_index(ix, iy, iz)
        color = _device_color(device.kind)
        label = escape(f"{device.name} ({device.kind}, {device.activation:.0%})")
        parts.append(
            f'<line x1="{screen_x:.2f}" y1="{screen_y + 12:.2f}" x2="{screen_x:.2f}" y2="{screen_y - 12:.2f}" stroke="#17211b" stroke-width="1.2" stroke-opacity="0.55" />'
        )
        parts.append(
            f'<rect x="{screen_x - 8:.2f}" y="{screen_y - 8:.2f}" width="16" height="16" rx="3" fill="#fffdf7" stroke="#17211b" stroke-width="2.4" />'
        )
        parts.append(
            f'<rect x="{screen_x - 5:.2f}" y="{screen_y - 5:.2f}" width="10" height="10" rx="2" fill="{color}" stroke="#ffffff" stroke-width="1.1" />'
        )
        parts.append(
            f'<text x="{screen_x + 12:.2f}" y="{screen_y - 10:.2f}" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="#17211b" stroke="#fffdf7" stroke-width="3" paint-order="stroke">{label}</text>'
        )
    parts.append("</g>")
    return parts


def _wall_surface_marker_parts(project_index, field: FieldGrid, device: Device) -> List[str]:
    width = float(device.metadata.get("surface_width", 1.4))
    height = float(device.metadata.get("surface_height", 1.1))
    center = device.position
    color = _device_color(device.kind)
    y_min = max(field.y_coords[0], center.y - width / 2.0)
    y_max = min(field.y_coords[-1], center.y + width / 2.0)
    z_min = max(field.z_coords[0], center.z - height / 2.0)
    z_max = min(field.z_coords[-1], center.z + height / 2.0)
    corners = [
        (center.x, y_min, z_min),
        (center.x, y_max, z_min),
        (center.x, y_max, z_max),
        (center.x, y_min, z_max),
    ]
    projected = [
        project_index(
            _coordinate_to_grid_index(x, field.x_coords),
            _coordinate_to_grid_index(y, field.y_coords),
            _coordinate_to_grid_index(z, field.z_coords),
        )
        for x, y, z in corners
    ]
    polygon = " ".join(f"{x:.2f},{y:.2f}" for x, y in projected)
    label_x, label_y = project_index(
        _coordinate_to_grid_index(center.x, field.x_coords),
        _coordinate_to_grid_index(center.y, field.y_coords),
        _coordinate_to_grid_index(center.z, field.z_coords),
    )
    label = escape(f"{device.name} ({device.kind}, {device.activation:.0%})")
    return [
        f'<polygon points="{polygon}" fill="{color}" fill-opacity="0.22" stroke="{color}" stroke-width="3" />',
        f'<circle cx="{label_x:.2f}" cy="{label_y:.2f}" r="4.5" fill="{color}" stroke="#fffdf7" stroke-width="1.4" />',
        f'<text x="{label_x + 12:.2f}" y="{label_y - 10:.2f}" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="#17211b" stroke="#fffdf7" stroke-width="3" paint-order="stroke">{label}</text>',
    ]


def _coordinate_to_grid_index(value: float, coords: List[float]) -> float:
    if len(coords) <= 1 or abs(coords[-1] - coords[0]) <= 1e-9:
        return 0.0
    fraction = (value - coords[0]) / (coords[-1] - coords[0])
    fraction = max(0.0, min(1.0, fraction))
    return fraction * (len(coords) - 1)


def _device_color(kind: str) -> str:
    colors = {
        "ac": "#2b5c7c",
        "window": "#2f855a",
        "light": "#c58b2d",
    }
    return colors.get(kind, "#b4552b")


def _room_wireframe(project_index, nx: int, ny: int, nz: int) -> List[str]:
    corners = {
        "000": project_index(0, 0, 0),
        "x00": project_index(nx - 1, 0, 0),
        "0y0": project_index(0, ny - 1, 0),
        "xy0": project_index(nx - 1, ny - 1, 0),
        "00z": project_index(0, 0, nz - 1),
        "x0z": project_index(nx - 1, 0, nz - 1),
        "0yz": project_index(0, ny - 1, nz - 1),
        "xyz": project_index(nx - 1, ny - 1, nz - 1),
    }
    edges = [
        ("000", "x00"),
        ("000", "0y0"),
        ("x00", "xy0"),
        ("0y0", "xy0"),
        ("00z", "x0z"),
        ("00z", "0yz"),
        ("x0z", "xyz"),
        ("0yz", "xyz"),
        ("000", "00z"),
        ("x00", "x0z"),
        ("0y0", "0yz"),
        ("xy0", "xyz"),
    ]
    parts = []
    for start, end in edges:
        x1, y1 = corners[start]
        x2, y2 = corners[end]
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#6f7f72" stroke-width="1.1" stroke-opacity="0.58" />'
        )
    parts.append('<text x="34" y="530" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="#69776e">Each dot is one 3D grid sample. Labeled squares mark appliance positions.</text>')
    return parts


def _legend_parts(x: float, y: float, height: float, minimum: float, maximum: float) -> List[str]:
    parts: List[str] = [
        f'<text x="{x - 4:.2f}" y="{y - 18:.2f}" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="#69776e">Value</text>'
    ]
    for step in range(100):
        fraction = step / 99.0
        rect_y = y + (1.0 - fraction) * height
        color = _value_to_color(minimum + fraction * (maximum - minimum), minimum, maximum)
        parts.append(
            f'<rect x="{x:.2f}" y="{rect_y:.2f}" width="20" height="{height / 100.0 + 1:.2f}" fill="{color}" stroke="none" />'
        )
    parts.append(
        f'<text x="{x + 28:.2f}" y="{y + 10:.2f}" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="#17211b">{maximum:.1f}</text>'
    )
    parts.append(
        f'<text x="{x + 28:.2f}" y="{y + height:.2f}" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="#17211b">{minimum:.1f}</text>'
    )
    return parts


def _interpolate_rgb(start: Tuple[int, int, int], end: Tuple[int, int, int], fraction: float) -> Tuple[int, int, int]:
    fraction = max(0.0, min(1.0, fraction))
    red = round(start[0] + (end[0] - start[0]) * fraction)
    green = round(start[1] + (end[1] - start[1]) * fraction)
    blue = round(start[2] + (end[2] - start[2]) * fraction)
    return red, green, blue
