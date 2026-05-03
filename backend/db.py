import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smartwaste.db")


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                predicted_tons REAL NOT NULL,
                fill_level INTEGER NOT NULL,
                status TEXT NOT NULL,
                predicted_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                actual_tons REAL NOT NULL,
                note TEXT,
                recorded_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS model_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                r2_score REAL NOT NULL,
                mae REAL,
                n_samples INTEGER,
                trained_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS route_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_km REAL NOT NULL,
                naive_km REAL NOT NULL,
                fuel_l REAL NOT NULL,
                naive_fuel_l REAL NOT NULL,
                run_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS dispatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                truck_id TEXT NOT NULL,
                truck_type TEXT,
                district TEXT,
                eta_minutes INTEGER,
                status TEXT DEFAULT 'dispatched',
                mode TEXT DEFAULT 'scheduled',
                dispatched_at TEXT NOT NULL
            )
        """)
        # Migration: add mode column to existing rows if it's missing
        cols = [r[1] for r in c.execute("PRAGMA table_info(dispatches)").fetchall()]
        if 'mode' not in cols:
            c.execute("ALTER TABLE dispatches ADD COLUMN mode TEXT DEFAULT 'scheduled'")
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def log_prediction(district: str, predicted_tons: float, fill_level: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO predictions (district, predicted_tons, fill_level, status, predicted_at) VALUES (?, ?, ?, ?, ?)",
            (district, predicted_tons, fill_level, status, now_iso()),
        )
        conn.commit()


def log_feedback(district: str, actual_tons: float, note: Optional[str] = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO feedback (district, actual_tons, note, recorded_at) VALUES (?, ?, ?, ?)",
            (district, actual_tons, note, now_iso()),
        )
        conn.commit()


def list_feedback(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, district, actual_tons, note, recorded_at FROM feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def log_model_meta(r2: float, mae: Optional[float], n_samples: Optional[int]):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO model_meta (r2_score, mae, n_samples, trained_at) VALUES (?, ?, ?, ?)",
            (r2, mae, n_samples, now_iso()),
        )
        conn.commit()


def latest_model_meta() -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT r2_score, mae, n_samples, trained_at FROM model_meta ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def log_route_run(total_km: float, naive_km: float, fuel_l: float, naive_fuel_l: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO route_runs (total_km, naive_km, fuel_l, naive_fuel_l, run_at) VALUES (?, ?, ?, ?, ?)",
            (total_km, naive_km, fuel_l, naive_fuel_l, now_iso()),
        )
        conn.commit()


def list_route_runs(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT total_km, naive_km, fuel_l, naive_fuel_l, run_at FROM route_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_predictions_by_district(district: str, limit: int = 30):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT predicted_tons, fill_level, status, predicted_at FROM predictions WHERE district = ? ORDER BY id DESC LIMIT ?",
            (district, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def log_dispatch(zone_id: str, zone_name: str, truck_id: str, truck_type: Optional[str],
                 district: Optional[str], eta_minutes: Optional[int], mode: str = 'scheduled') -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO dispatches (zone_id, zone_name, truck_id, truck_type, district, eta_minutes, mode, dispatched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (zone_id, zone_name, truck_id, truck_type, district, eta_minutes, mode, now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_dispatches_today() -> list:
    today_prefix = now_iso()[:10]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, zone_id, zone_name, truck_id, truck_type, district, eta_minutes, status, mode, dispatched_at "
            "FROM dispatches WHERE dispatched_at LIKE ? ORDER BY id DESC",
            (f"{today_prefix}%",),
        ).fetchall()
        return [dict(r) for r in rows]


def truck_already_dispatched_today(truck_id: str) -> bool:
    today_prefix = now_iso()[:10]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM dispatches WHERE truck_id = ? AND dispatched_at LIKE ? LIMIT 1",
            (truck_id, f"{today_prefix}%"),
        ).fetchone()
        return row is not None


init_db()
