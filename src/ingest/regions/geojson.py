"""전국 시도 GeoJSON을 카카오맵용으로 단순화한다."""

from __future__ import annotations

import json
from pathlib import Path

from src.ingest.config import settings
from src.ingest.regions.codes import CODE_TO_NAME, NAME_TO_CODE

TOLERANCE = 0.004
MIN_RING_AREA = 0.0008


def _distance(point, start, end) -> float:
    (x, y), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def simplify(points: list, tolerance: float = TOLERANCE) -> list:
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        worst, at = 0.0, None
        for index in range(first + 1, last):
            distance = _distance(points[index], points[first], points[last])
            if distance > worst:
                worst, at = distance, index
        if at is not None and worst > tolerance:
            keep[at] = True
            stack.extend(((first, at), (at, last)))
    return [point for point, selected in zip(points, keep) if selected]


def _area(ring: list) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


def _geometry(value: dict) -> dict | None:
    polygons = [value["coordinates"]] if value["type"] == "Polygon" else value["coordinates"]
    cleaned = []
    for rings in polygons:
        ring = simplify(rings[0])
        if len(ring) < 4:
            continue
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        cleaned.append((_area(rings[0]), [ring]))
    if not cleaned:
        return None
    cleaned.sort(key=lambda item: -item[0])
    kept = [cleaned[0][1], *[polygon for area, polygon in cleaned[1:] if area >= MIN_RING_AREA]]
    return {"type": "MultiPolygon", "coordinates": kept}


def simplify_geojson(source: Path | None = None, target: Path | None = None) -> dict:
    source = source or settings.provinces_path.with_name("skorea-provinces.geojson")
    target = target or settings.provinces_path
    raw = json.loads(source.read_text(encoding="utf-8"))
    features = []
    for feature in raw["features"]:
        source_name = feature["properties"]["name"]
        code = NAME_TO_CODE.get(source_name)
        geometry = _geometry(feature["geometry"])
        if code and geometry:
            features.append({
                "type": "Feature",
                "properties": {"code": code, "name": CODE_TO_NAME[code], "source": source_name},
                "geometry": geometry,
            })
    result = {"type": "FeatureCollection", "features": features}
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return result


def main() -> None:
    result = simplify_geojson()
    print(f"GeoJSON 단순화 완료: {len(result['features'])}개 경계 → {settings.provinces_path}")


if __name__ == "__main__":
    main()
