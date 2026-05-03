"""Loads Austin route polygons (austin_routes_2015.xlsx),
computes centroids, clusters into 10 districts, and exposes lookups."""
import os
import json
from functools import lru_cache
from typing import Optional

import pandas as pd
from shapely import wkt
from sklearn.cluster import KMeans

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
XLSX_PATH = os.path.join(DATA_DIR, "austin_routes_2015.xlsx")
GEOJSON_OUT = os.path.join(DATA_DIR, "austin_route_polygons.geojson")
NUM_DISTRICTS = 10
DEPOT_FALLBACK = (30.2672, -97.7431)


@lru_cache(maxsize=1)
def _load_routes_df() -> pd.DataFrame:
    """Returns DataFrame with one row per route: GARB_RT, GARB_DAY, OP_TYPE, GARB_SUP, SUPER_NUM, lat, lng, geom."""
    if not os.path.exists(XLSX_PATH):
        return pd.DataFrame()
    df = pd.read_excel(XLSX_PATH)
    df = df.dropna(subset=['GARB_RT', 'the_geom']).copy()
    df['GARB_RT'] = df['GARB_RT'].astype(str).str.strip()

    geoms = []
    lats, lngs = [], []
    for wkt_str in df['the_geom']:
        try:
            g = wkt.loads(wkt_str)
            c = g.centroid
            geoms.append(g)
            lats.append(float(c.y))
            lngs.append(float(c.x))
        except Exception:
            geoms.append(None)
            lats.append(None)
            lngs.append(None)
    df['geom'] = geoms
    df['lat'] = lats
    df['lng'] = lngs
    df = df.dropna(subset=['lat', 'lng']).reset_index(drop=True)
    return df


@lru_cache(maxsize=1)
def _cluster_districts():
    """KMeans cluster centroids into NUM_DISTRICTS. Returns (route_to_district, district_centroids)."""
    df = _load_routes_df()
    if df.empty:
        return {}, {}

    coords = df[['lat', 'lng']].values
    k = min(NUM_DISTRICTS, len(df))
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(coords)
    labels = km.labels_

    route_to_district = {}
    for i, route_id in enumerate(df['GARB_RT']):
        route_to_district[route_id] = f"District {int(labels[i]) + 1}"

    district_centroids = {}
    for cluster_id, (lat, lng) in enumerate(km.cluster_centers_):
        district_centroids[f"District {cluster_id + 1}"] = (float(lat), float(lng))

    return route_to_district, district_centroids


def district_for_route(route_id: str) -> Optional[str]:
    """Return real-geography district for a route, or None if unknown."""
    if not route_id:
        return None
    rmap, _ = _cluster_districts()
    return rmap.get(str(route_id).strip())


def district_centroid(district_name: str):
    _, dmap = _cluster_districts()
    return dmap.get(district_name, DEPOT_FALLBACK)


def all_district_centroids() -> dict:
    _, dmap = _cluster_districts()
    return dict(dmap)


def routes_dataframe() -> pd.DataFrame:
    return _load_routes_df().copy()


def export_geojson(force: bool = False) -> Optional[str]:
    """Materialize a GeoJSON FeatureCollection. Returns the path."""
    if os.path.exists(GEOJSON_OUT) and not force:
        return GEOJSON_OUT
    df = _load_routes_df()
    if df.empty:
        return None
    rmap, _ = _cluster_districts()

    features = []
    for _, row in df.iterrows():
        geom = row['geom']
        if geom is None:
            continue
        # Convert shapely → __geo_interface__ → dict
        try:
            geom_dict = json.loads(json.dumps(geom.__geo_interface__))
        except Exception:
            continue
        district = rmap.get(row['GARB_RT'], None)
        features.append({
            "type": "Feature",
            "geometry": geom_dict,
            "properties": {
                "route_id": row['GARB_RT'],
                "district": district,
                "garb_day": str(row.get('GARB_DAY', '')),
                "op_type": str(row.get('OP_TYPE', '')),
                "supervisor": str(row.get('GARB_SUP', '')),
                "super_num": int(row['SUPER_NUM']) if pd.notnull(row.get('SUPER_NUM')) else None,
                "centroid_lat": row['lat'],
                "centroid_lng": row['lng'],
            },
        })

    fc = {"type": "FeatureCollection", "features": features}
    os.makedirs(os.path.dirname(GEOJSON_OUT), exist_ok=True)
    with open(GEOJSON_OUT, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    return GEOJSON_OUT


# Pre-build on import so endpoints can serve immediately
try:
    export_geojson(force=True)
except Exception as e:
    print(f"[route_geometry] Failed to export geojson on import: {e}")
