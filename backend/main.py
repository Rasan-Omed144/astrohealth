from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Iterator, Literal

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.research import initialize_research_schema

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(
    os.environ.get("ASTRO_DATABASE_PATH", PROJECT_ROOT / "data" / "astro_health.db")
)

BIOMARKER_TIMEPOINT_ORDER = """
CASE "Timepoint"
    WHEN 'L-92' THEN 1
    WHEN 'L-44' THEN 2
    WHEN 'L-3' THEN 3
    WHEN 'R+1' THEN 4
    WHEN 'R+45' THEN 5
    WHEN 'R+82' THEN 6
    WHEN 'R+194' THEN 7
    ELSE 8
END
"""

RESEARCH_TIMEPOINT_ORDER = """
CASE m.timepoint
    WHEN 'L-92' THEN 1
    WHEN 'L-44' THEN 2
    WHEN 'L-3' THEN 3
    WHEN 'R+1' THEN 4
    WHEN 'R+45' THEN 5
    WHEN 'R+82' THEN 6
    WHEN 'R+194' THEN 7
    ELSE 8
END
"""

MetricName = Literal[
    "resting_heart_rate",
    "blood_oxygen",
    "sleep_duration",
    "exercise_minutes",
    "heart_rate_variability",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "body_temperature",
    "hydration_liters",
    "stress_score",
    "bone_loading_minutes",
]

METRIC_INFO: dict[str, tuple[str, str, float, float]] = {
    "resting_heart_rate": ("Resting heart rate", "bpm", 62, 72),
    "blood_oxygen": ("Blood oxygen", "%", 96, 99),
    "sleep_duration": ("Sleep duration", "hrs", 7, 8),
    "exercise_minutes": ("Exercise", "min", 30, 60),
    "heart_rate_variability": ("Heart rate variability", "ms", 45, 65),
    "systolic_blood_pressure": ("Systolic blood pressure", "mmHg", 105, 125),
    "diastolic_blood_pressure": ("Diastolic blood pressure", "mmHg", 65, 82),
    "body_temperature": ("Body temperature", "°C", 36.2, 37.3),
    "hydration_liters": ("Hydration", "L", 2, 2.5),
    "stress_score": ("Stress check-in", "/ 5", 1, 3),
    "bone_loading_minutes": ("Bone-loading exercise", "min", 30, 60),
}

CREW_SEED = [
    ("jordan-miller", "Jordan Miller", "Commander", 92),
    ("amara-kim", "Amara Kim", "Flight engineer", 90),
    ("leo-santos", "Leo Santos", "Mission specialist", 74),
    ("maya-chen", "Maya Chen", "Payload specialist", 89),
    ("elias-okafor", "Elias Okafor", "Mission specialist", 91),
]

LATEST_VALUES = {
    "jordan-miller": [64, 99, 7.5, 48, 61, 116, 74, 36.6, 2.3, 1, 48],
    "amara-kim": [71, 98, 7.2, 38, 52, 120, 78, 36.7, 2.0, 2, 38],
    "leo-santos": [76, 97, 6.4, 31, 43, 122, 80, 36.9, 1.8, 3, 31],
    "maya-chen": [66, 98, 7.6, 45, 57, 114, 72, 36.5, 2.2, 2, 45],
    "elias-okafor": [69, 99, 7.3, 50, 59, 119, 77, 36.7, 2.4, 1, 50],
}

HISTORY_VARIATION = {
    "resting_heart_rate": [2, 0, -1, 3, 1, -2, 2, 0, 1, -3, 2, -1, 1, 0],
    "blood_oxygen": [0, -1, 0, 1, 0, 0, -1, 0, 1, 0, -1, 0, 0, 0],
    "sleep_duration": [0.7, 0.3, -0.2, 0.5, -0.1, 0.2, -0.4, 0.1, -0.6, 0.3, -0.2, 0.4, -0.5, 0],
    "exercise_minutes": [-5, 4, 0, 8, -3, 5, 2, -4, 6, 0, 4, -2, 7, 0],
    "heart_rate_variability": [-3, 2, 0, 4, -1, 1, -2, 3, 0, -4, 2, -1, 1, 0],
    "systolic_blood_pressure": [-2, 1, 0, 3, -1, 2, 0, -2, 1, 0, 2, -1, 1, 0],
    "diastolic_blood_pressure": [-1, 0, 1, 2, -1, 1, 0, -2, 1, 0, 2, -1, 1, 0],
    "body_temperature": [-0.2, 0.1, 0, 0.2, -0.1, 0.1, 0, -0.2, 0.1, 0, 0.2, -0.1, 0.1, 0],
    "hydration_liters": [-0.2, 0.1, 0, 0.3, -0.1, 0.2, 0, -0.2, 0.1, 0, 0.2, -0.1, 0.1, 0],
    "stress_score": [0, 1, -1, 0, 1, 0, -1, 0, 1, -1, 0, 1, -1, 0],
    "bone_loading_minutes": [-5, 4, 0, 8, -3, 5, 2, -4, 6, 0, 4, -2, 7, 0],
}

HEART_RATE_HISTORY_VARIATION = (
    -2, 1, 0, 3, -1, 2, -3, 1, 0, 4,
    -2, 1, -1, 2, 0, -4, 2, 1, -2, 3,
    0, -1, 2, -3, 1, 0, 4, -2, 1, 0,
)

SPACECRAFT_VARIATION = {
    "carbon_dioxide_ppm": (0.0, 0.1, -0.1, 0.2, 0.0, -0.2, 0.1),
    "cabin_temperature_c": (0.0, 0.3, -0.2, 0.1, -0.1, 0.2, -0.3),
    "relative_humidity_pct": (0, 2, -1, 1, -2, 3, 0),
}


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def seed_demo_data(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM crew").fetchone()[0]:
        return

    now = datetime.now(UTC)
    connection.execute(
        """INSERT INTO missions (id, name, phase, mission_day, radiation_context)
           VALUES (?, ?, ?, ?, ?)""",
        ("artemis-iii", "Artemis III", "Transit", 42, "Elevated relative to demo baseline"),
    )
    for crew_id, name, role, score in CREW_SEED:
        connection.execute(
            """INSERT INTO crew (id, mission_id, full_name, role, health_score)
               VALUES (?, ?, ?, ?, ?)""",
            (crew_id, "artemis-iii", name, role, score),
        )
        values = LATEST_VALUES[crew_id]
        for day_offset in range(29, -1, -1):
            recorded_at = (now - timedelta(days=day_offset)).isoformat()
            for index, (metric, variation) in enumerate(HISTORY_VARIATION.items()):
                latest_value = values[index]
                day_index = 29 - day_offset
                day_variation = (
                    0
                    if day_index == 29
                    else variation[day_index % (len(variation) - 1)]
                )
                value = latest_value + day_variation
                connection.execute(
                    """INSERT INTO measurements
                       (crew_id, metric, value, unit, recorded_at, source)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        crew_id,
                        metric,
                        round(value, 2),
                        METRIC_INFO[metric][1],
                        recorded_at,
                        "demo",
                    ),
                )
        sleep_value = float(values[2])
        connection.execute(
            """INSERT INTO checkins
               (crew_id, energy, stress, mood, sleep_hours, recorded_at, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                crew_id,
                4 if crew_id != "leo-santos" else 3,
                int(values[9]),
                "Good" if crew_id != "leo-santos" else "Okay",
                sleep_value,
                now.isoformat(),
                "demo",
            ),
        )


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phase TEXT NOT NULL,
                mission_day INTEGER NOT NULL CHECK (mission_day >= 0),
                radiation_context TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS crew (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                health_score INTEGER NOT NULL CHECK (health_score BETWEEN 0 AND 100),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crew_id TEXT NOT NULL REFERENCES crew(id) ON DELETE CASCADE,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                CHECK (metric IN (
                    'resting_heart_rate', 'blood_oxygen', 'sleep_duration',
                    'exercise_minutes', 'heart_rate_variability',
                    'systolic_blood_pressure', 'diastolic_blood_pressure',
                    'body_temperature', 'hydration_liters', 'stress_score',
                    'bone_loading_minutes'
                ))
            );
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crew_id TEXT NOT NULL REFERENCES crew(id) ON DELETE CASCADE,
                energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 5),
                stress INTEGER NOT NULL CHECK (stress BETWEEN 1 AND 5),
                mood TEXT NOT NULL CHECK (mood IN ('Good', 'Okay', 'Low')),
                sleep_hours REAL NOT NULL CHECK (sleep_hours BETWEEN 0 AND 24),
                recorded_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual'
            );
            CREATE TABLE IF NOT EXISTS spacecraft_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL UNIQUE,
                carbon_dioxide_ppm REAL NOT NULL,
                cabin_temperature_c REAL NOT NULL,
                relative_humidity_pct REAL NOT NULL,
                accumulated_radiation_dose_msv REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS measurements_crew_metric_time
                ON measurements (crew_id, metric, recorded_at DESC);
            CREATE INDEX IF NOT EXISTS checkins_crew_time
                ON checkins (crew_id, recorded_at DESC);
            """
        )
        initialize_research_schema(connection)
        connection.execute("DELETE FROM crew WHERE id = 'pasha-ivanov'")
        seed_demo_data(connection)
        extend_demo_history(connection)
        refresh_demo_heart_rate_history(connection)
        ensure_daily_demo_samples(connection)
        # Older illustrative records used 2.x while the UI labelled them ppm.
        # This is a *demo* unit cleanup only; no live environmental data is converted.
        connection.execute("UPDATE spacecraft_readings SET carbon_dioxide_ppm = carbon_dioxide_ppm * 1000 WHERE carbon_dioxide_ppm BETWEEN 0 AND 100")


def ensure_daily_demo_samples(
    connection: sqlite3.Connection,
    today: date | None = None,
) -> None:
    current_day = today or datetime.now(UTC).date()
    first_day = current_day - timedelta(days=29)
    window_dates = [first_day + timedelta(days=offset) for offset in range(30)]

    for crew_id, _, _, _ in CREW_SEED:
        for metric_index, (metric, variation) in enumerate(HISTORY_VARIATION.items()):
            connection.execute(
                """DELETE FROM measurements
                   WHERE crew_id = ? AND metric = ? AND source = 'demo'
                     AND substr(recorded_at, 1, 10) < ?""",
                (crew_id, metric, first_day.isoformat()),
            )
            latest_value = LATEST_VALUES[crew_id][metric_index]
            for sample_day in window_dates:
                exists = connection.execute(
                    """SELECT 1 FROM measurements
                       WHERE crew_id = ? AND metric = ? AND source = 'demo'
                         AND substr(recorded_at, 1, 10) = ?
                       LIMIT 1""",
                    (crew_id, metric, sample_day.isoformat()),
                ).fetchone()
                if exists:
                    continue
                day_index = sample_day.toordinal()
                if metric == "resting_heart_rate":
                    offset = HEART_RATE_HISTORY_VARIATION[day_index % len(HEART_RATE_HISTORY_VARIATION)]
                else:
                    offset = variation[day_index % len(variation)]
                connection.execute(
                    """INSERT INTO measurements
                       (crew_id, metric, value, unit, recorded_at, source)
                       VALUES (?, ?, ?, ?, ?, 'demo')""",
                    (
                        crew_id,
                        metric,
                        round(latest_value + offset, 2),
                        METRIC_INFO[metric][1],
                        datetime.combine(sample_day, datetime.min.time(), UTC).isoformat(),
                    ),
                )

    connection.execute(
        "DELETE FROM spacecraft_readings WHERE substr(recorded_at, 1, 10) < ?",
        (first_day.isoformat(),),
    )
    existing_spacecraft_days = {
        row["recorded_at"][:10]: row
        for row in connection.execute(
            """SELECT recorded_at, accumulated_radiation_dose_msv
               FROM spacecraft_readings
               WHERE substr(recorded_at, 1, 10) BETWEEN ? AND ?
               ORDER BY recorded_at""",
            (first_day.isoformat(), current_day.isoformat()),
        ).fetchall()
    }
    previous_dose = None
    for sample_day in window_dates:
        day_string = sample_day.isoformat()
        if day_string in existing_spacecraft_days:
            previous_dose = existing_spacecraft_days[day_string]["accumulated_radiation_dose_msv"]
            continue
        day_index = sample_day.toordinal()
        co2_offset = SPACECRAFT_VARIATION["carbon_dioxide_ppm"][day_index % 7]
        temperature_offset = SPACECRAFT_VARIATION["cabin_temperature_c"][day_index % 7]
        humidity_offset = SPACECRAFT_VARIATION["relative_humidity_pct"][day_index % 7]
        if previous_dose is None:
            dose = max(0.1, 18.6 - (current_day - sample_day).days * 0.45)
        else:
            dose = previous_dose + 0.45
        connection.execute(
            """INSERT INTO spacecraft_readings
               (recorded_at, carbon_dioxide_ppm, cabin_temperature_c,
                relative_humidity_pct, accumulated_radiation_dose_msv)
               VALUES (?, ?, ?, ?, ?)""",
            (
                datetime.combine(sample_day, datetime.min.time(), UTC).isoformat(),
                round(2500 + co2_offset * 1000, 0),
                round(22 + temperature_offset, 1),
                round(45 + humidity_offset, 1),
                round(dose, 2),
            ),
        )
        previous_dose = dose


def refresh_daily_demo_samples_if_stale(connection: sqlite3.Connection) -> None:
    latest = connection.execute(
        """SELECT MAX(recorded_at) FROM measurements
           WHERE source = 'demo'"""
    ).fetchone()[0]
    if latest and latest[:10] < datetime.now(UTC).date().isoformat():
        ensure_daily_demo_samples(connection)


def extend_demo_history(connection: sqlite3.Connection) -> None:
    now = datetime.now(UTC)
    for crew_id, _, _, _ in CREW_SEED:
        for index, (metric, variation) in enumerate(HISTORY_VARIATION.items()):
            existing = connection.execute(
                """SELECT COUNT(*) AS count, MIN(recorded_at) AS oldest
                   FROM measurements
                   WHERE crew_id = ? AND metric = ? AND source = 'demo'""",
                (crew_id, metric),
            ).fetchone()
            missing = max(0, 30 - existing["count"])
            if not missing:
                continue
            oldest = (
                datetime.fromisoformat(existing["oldest"])
                if existing["oldest"]
                else now
            )
            latest_value = LATEST_VALUES[crew_id][index]
            measurements = []
            for days_before_oldest in range(missing, 0, -1):
                day_index = 29 - days_before_oldest
                day_variation = (
                    0
                    if day_index == 29
                    else variation[day_index % (len(variation) - 1)]
                )
                measurements.append(
                    (
                        crew_id,
                        metric,
                        round(latest_value + day_variation, 2),
                        METRIC_INFO[metric][1],
                        (
                            oldest - timedelta(days=days_before_oldest)
                        ).isoformat(),
                        "demo",
                    )
                )
            connection.executemany(
                """INSERT INTO measurements
                   (crew_id, metric, value, unit, recorded_at, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                measurements,
            )


def refresh_demo_heart_rate_history(connection: sqlite3.Connection) -> None:
    for crew_id, _, _, _ in CREW_SEED:
        rows = connection.execute(
            """SELECT id FROM measurements
               WHERE crew_id = ? AND metric = 'resting_heart_rate' AND source = 'demo'
               ORDER BY recorded_at DESC, id DESC
               LIMIT ?""",
            (crew_id, len(HEART_RATE_HISTORY_VARIATION)),
        ).fetchall()
        latest_value = LATEST_VALUES[crew_id][0]
        for day_index, row in enumerate(reversed(rows)):
            value = latest_value + HEART_RATE_HISTORY_VARIATION[day_index]
            connection.execute(
                "UPDATE measurements SET value = ? WHERE id = ?",
                (value, row["id"]),
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="ASTRO HealthGuard API",
    description="Local SQLite-backed API for the ASTRO HealthGuard demo.",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")


class CrewCreate(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    full_name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    health_score: int = Field(ge=0, le=100, default=100)
    mission_id: str = "artemis-iii"


class MeasurementCreate(BaseModel):
    metric: MetricName
    value: float = Field(ge=0, le=1000)
    recorded_at: datetime | None = None
    source: Literal["manual", "device", "demo"] = "manual"


class CheckinCreate(BaseModel):
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    mood: Literal["Good", "Okay", "Low"]
    sleep_hours: float = Field(ge=0, le=24)
    recorded_at: datetime | None = None


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crew_id: str
    metric: str
    value: float
    unit: str
    recorded_at: datetime
    source: str
    baseline_min: float
    baseline_max: float


class CheckinResponse(BaseModel):
    id: int
    crew_id: str
    energy: int
    stress: int
    mood: str
    sleep_hours: float
    recorded_at: datetime
    source: str


def ensure_crew(connection: sqlite3.Connection, crew_id: str) -> sqlite3.Row:
    crew = connection.execute(
        "SELECT * FROM crew WHERE id = ?", (crew_id,)
    ).fetchone()
    if crew is None:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return crew


def measurement_response(row: sqlite3.Row) -> dict[str, object]:
    _, _, baseline_min, baseline_max = METRIC_INFO[row["metric"]]
    return {
        **dict(row),
        "baseline_min": baseline_min,
        "baseline_max": baseline_max,
    }


def normalized_timestamp(value: datetime | None) -> str:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat()


def crew_response(connection: sqlite3.Connection, crew: sqlite3.Row) -> dict[str, object]:
    measurements = connection.execute(
        """SELECT m.* FROM measurements m
           JOIN (
             SELECT metric, MAX(recorded_at) AS latest_at
             FROM measurements WHERE crew_id = ? GROUP BY metric
           ) latest ON latest.metric = m.metric AND latest.latest_at = m.recorded_at
           WHERE m.crew_id = ? ORDER BY m.metric""",
        (crew["id"], crew["id"]),
    ).fetchall()
    latest_checkin = connection.execute(
        "SELECT * FROM checkins WHERE crew_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
        (crew["id"],),
    ).fetchone()
    return {
        **dict(crew),
        "latest_measurements": {
            row["metric"]: measurement_response(row) for row in measurements
        },
        "latest_checkin": dict(latest_checkin) if latest_checkin else None,
    }


@app.get("/api/health")
def health_check() -> dict[str, str]:
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "connected"}


@app.get("/api/biomarkers")
def get_all_biomarkers() -> list[dict[str, object]]:
    with get_connection() as connection:
        _ensure_research_dataset(connection, "OSD-575")
        return _legacy_biomarkers(connection)


@app.get("/api/biomarkers/participants")
def get_biomarker_participants() -> list[str]:
    with get_connection() as connection:
        _ensure_research_dataset(connection, "OSD-575")
        rows = connection.execute(
            """SELECT DISTINCT participant_id FROM research_measurements
               WHERE dataset_id = 'OSD-575' ORDER BY participant_id"""
        ).fetchall()
        return [row["participant_id"] for row in rows]


@app.get("/api/biomarkers/analytes")
def get_biomarker_analytes() -> list[str]:
    with get_connection() as connection:
        _ensure_research_dataset(connection, "OSD-575")
        rows = connection.execute(
            """SELECT DISTINCT analyte FROM research_measurements
               WHERE dataset_id = 'OSD-575' ORDER BY analyte"""
        ).fetchall()
        return [row["analyte"] for row in rows]


@app.get("/api/biomarkers/{participant_id}/{analyte}")
def get_biomarker_history(participant_id: str, analyte: str) -> list[dict[str, object]]:
    with get_connection() as connection:
        _ensure_research_dataset(connection, "OSD-575")
        rows = connection.execute(
            f"""SELECT "Analyte", "Concentration", "Timepoint", "ID",
                       "Unit", "Timepoint2", "Type", "Percent"
                FROM (
                    SELECT analyte AS "Analyte", value AS "Concentration",
                           timepoint AS "Timepoint", participant_id AS "ID",
                           unit AS "Unit", phase AS "Timepoint2",
                           assay_type AS "Type",
                           COALESCE(secondary_value, secondary_value_raw) AS "Percent"
                    FROM research_measurements
                    WHERE dataset_id = 'OSD-575'
                )
                WHERE "ID" = ? AND LOWER("Analyte") = LOWER(?)
                ORDER BY {BIOMARKER_TIMEPOINT_ORDER}, "Timepoint", "Timepoint2" """,
            (participant_id, analyte),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No measurements found")
    return [dict(row) for row in rows]


def _ensure_research_dataset(
    connection: sqlite3.Connection, dataset_id: str
) -> sqlite3.Row:
    dataset = connection.execute(
        """SELECT d.dataset_id FROM research_datasets d
           WHERE d.dataset_id = ?
             AND EXISTS (
                 SELECT 1 FROM research_measurements m
                 WHERE m.dataset_id = d.dataset_id
             )""",
        (dataset_id,),
    ).fetchone()
    if dataset is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{dataset_id} research data has not been imported. "
                "Run `python import_data.py`."
            ),
        )
    return dataset


def _legacy_biomarkers(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        f"""SELECT analyte AS "Analyte", value AS "Concentration",
                   timepoint AS "Timepoint", participant_id AS "ID",
                   unit AS "Unit", phase AS "Timepoint2",
                   assay_type AS "Type",
                   COALESCE(secondary_value, secondary_value_raw) AS "Percent"
            FROM research_measurements
            WHERE dataset_id = 'OSD-575'
            ORDER BY participant_id, {BIOMARKER_TIMEPOINT_ORDER}, analyte"""
    ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/research/datasets")
def list_research_datasets() -> list[dict[str, object]]:
    with get_connection() as connection:
        rows = connection.execute(
            """SELECT d.dataset_id, d.title, d.health_system, d.mission,
                      d.source_file, COUNT(m.id) AS measurement_count,
                      COUNT(DISTINCT m.participant_id) AS participant_count,
                      COUNT(DISTINCT m.analyte) AS analyte_count,
                      COUNT(DISTINCT m.timepoint) AS timepoint_count
               FROM research_datasets d
               JOIN research_measurements m ON m.dataset_id = d.dataset_id
               GROUP BY d.dataset_id
               ORDER BY d.dataset_id"""
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/research/datasets/{dataset_id}/filters")
def get_research_filters(dataset_id: str) -> dict[str, list[str]]:
    with get_connection() as connection:
        _ensure_research_dataset(connection, dataset_id)
        filters: dict[str, list[str]] = {}
        for field in ("participant_id", "analyte", "timepoint"):
            rows = connection.execute(
                f"""SELECT DISTINCT {field} AS value
                    FROM research_measurements
                    WHERE dataset_id = ? ORDER BY {field}""",
                (dataset_id,),
            ).fetchall()
            filters[field] = [row["value"] for row in rows]
        return filters


@app.get("/api/research/measurements")
def list_research_measurements(
    dataset_id: Annotated[str, Query(min_length=7, max_length=7)],
    participant_id: Annotated[str | None, Query(max_length=80)] = None,
    analyte: Annotated[str | None, Query(max_length=200)] = None,
    timepoint: Annotated[str | None, Query(max_length=80)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> dict[str, object]:
    conditions = ["m.dataset_id = ?"]
    parameters: list[object] = [dataset_id]
    for field, value in (
        ("participant_id", participant_id),
        ("analyte", analyte),
        ("timepoint", timepoint),
    ):
        if value is not None:
            conditions.append(f"m.{field} = ?")
            parameters.append(value)
    if q and q.strip():
        # Search the entire selected dataset, not just the visible page.
        search = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(
            "(m.analyte LIKE ? ESCAPE '\\' OR m.participant_id LIKE ? ESCAPE '\\' "
            "OR m.timepoint LIKE ? ESCAPE '\\' OR m.phase LIKE ? ESCAPE '\\')"
        )
        parameters.extend([search] * 4)
    where_clause = " AND ".join(conditions)

    with get_connection() as connection:
        _ensure_research_dataset(connection, dataset_id)
        total = connection.execute(
            f"""SELECT COUNT(*) FROM research_measurements m
                WHERE {where_clause}""",
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""SELECT m.dataset_id, d.mission, d.source_file,
                       m.participant_id, m.timepoint, m.phase, m.analyte,
                       m.value, m.unit, m.measurement_basis,
                       m.secondary_value, m.secondary_measure,
                       m.secondary_value_raw, m.secondary_value_basis,
                       m.reference_min, m.reference_max, m.assay_type, m.sex,
                       m.source_row
                FROM research_measurements m
                JOIN research_datasets d ON d.dataset_id = m.dataset_id
                WHERE {where_clause}
                ORDER BY m.participant_id, {RESEARCH_TIMEPOINT_ORDER},
                         m.timepoint, m.analyte, m.source_row
                LIMIT ? OFFSET ?""",
            [*parameters, limit, offset],
        ).fetchall()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/mission")
def get_mission() -> dict[str, object]:
    with get_connection() as connection:
        mission = connection.execute(
            "SELECT * FROM missions ORDER BY id LIMIT 1"
        ).fetchone()
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return dict(mission)


@app.get("/api/crew")
def list_crew() -> list[dict[str, object]]:
    with get_connection() as connection:
        refresh_daily_demo_samples_if_stale(connection)
        crew_rows = connection.execute(
            "SELECT * FROM crew ORDER BY full_name"
        ).fetchall()
        return [crew_response(connection, crew) for crew in crew_rows]


@app.post("/api/crew", status_code=status.HTTP_201_CREATED)
def create_crew(payload: CrewCreate) -> dict[str, object]:
    with get_connection() as connection:
        if connection.execute(
            "SELECT 1 FROM missions WHERE id = ?", (payload.mission_id,)
        ).fetchone() is None:
            raise HTTPException(status_code=404, detail="Mission not found")
        try:
            cursor = connection.execute(
                """INSERT INTO crew (id, mission_id, full_name, role, health_score)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    payload.id,
                    payload.mission_id,
                    payload.full_name.strip(),
                    payload.role.strip(),
                    payload.health_score,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Crew member ID already exists") from error
        crew = connection.execute(
            "SELECT * FROM crew WHERE id = ?", (payload.id,)
        ).fetchone()
        return crew_response(connection, crew)


@app.get("/api/crew/{crew_id}")
def get_crew_member(crew_id: str) -> dict[str, object]:
    with get_connection() as connection:
        crew = ensure_crew(connection, crew_id)
        return crew_response(connection, crew)


@app.get("/api/crew/{crew_id}/measurements", response_model=list[MeasurementResponse])
def list_measurements(
    crew_id: str,
    metric: MetricName | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    daily: bool = False,
) -> list[dict[str, object]]:
    with get_connection() as connection:
        refresh_daily_demo_samples_if_stale(connection)
        ensure_crew(connection, crew_id)
        if metric is None:
            rows = connection.execute(
                """SELECT * FROM measurements WHERE crew_id = ?
                   ORDER BY recorded_at DESC, id DESC LIMIT ?""",
                (crew_id, limit),
            ).fetchall()
        elif daily:
            rows = connection.execute(
                """WITH daily_measurements AS (
                       SELECT measurements.*,
                              ROW_NUMBER() OVER (
                                  PARTITION BY substr(recorded_at, 1, 10)
                                  ORDER BY recorded_at DESC, id DESC
                              ) AS day_rank
                       FROM measurements
                       WHERE crew_id = ? AND metric = ?
                   )
                   SELECT * FROM daily_measurements
                   WHERE day_rank = 1
                   ORDER BY recorded_at DESC, id DESC
                   LIMIT ?""",
                (crew_id, metric, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT * FROM measurements WHERE crew_id = ? AND metric = ?
                   ORDER BY recorded_at DESC, id DESC LIMIT ?""",
                (crew_id, metric, limit),
            ).fetchall()
        return [measurement_response(row) for row in rows]


@app.get("/api/spacecraft/history")
def list_spacecraft_history(
    limit: Annotated[int, Query(ge=1, le=30)] = 30,
) -> dict[str, object]:
    with get_connection() as connection:
        refresh_daily_demo_samples_if_stale(connection)
        rows = connection.execute(
            """SELECT recorded_at, carbon_dioxide_ppm, cabin_temperature_c,
                      relative_humidity_pct, accumulated_radiation_dose_msv
               FROM spacecraft_readings
               ORDER BY recorded_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return {"items": [dict(row) for row in reversed(rows)], "total": len(rows)}


@app.post(
    "/api/crew/{crew_id}/measurements",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement(crew_id: str, payload: MeasurementCreate) -> dict[str, object]:
    with get_connection() as connection:
        ensure_crew(connection, crew_id)
        _, unit, _, _ = METRIC_INFO[payload.metric]
        recorded_at = normalized_timestamp(payload.recorded_at)
        cursor = connection.execute(
            """INSERT INTO measurements
               (crew_id, metric, value, unit, recorded_at, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (crew_id, payload.metric, payload.value, unit, recorded_at, payload.source),
        )
        row = connection.execute(
            "SELECT * FROM measurements WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return measurement_response(row)


@app.get("/api/crew/{crew_id}/checkins", response_model=list[CheckinResponse])
def list_checkins(
    crew_id: str,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict[str, object]]:
    with get_connection() as connection:
        ensure_crew(connection, crew_id)
        rows = connection.execute(
            """SELECT * FROM checkins WHERE crew_id = ?
               ORDER BY recorded_at DESC, id DESC LIMIT ?""",
            (crew_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


@app.post(
    "/api/crew/{crew_id}/checkins",
    response_model=CheckinResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkin(crew_id: str, payload: CheckinCreate) -> dict[str, object]:
    with get_connection() as connection:
        ensure_crew(connection, crew_id)
        recorded_at = normalized_timestamp(payload.recorded_at)
        cursor = connection.execute(
            """INSERT INTO checkins
               (crew_id, energy, stress, mood, sleep_hours, recorded_at, source)
               VALUES (?, ?, ?, ?, ?, ?, 'manual')""",
            (
                crew_id,
                payload.energy,
                payload.stress,
                payload.mood,
                payload.sleep_hours,
                recorded_at,
            ),
        )
        connection.execute(
            """INSERT INTO measurements
               (crew_id, metric, value, unit, recorded_at, source)
               VALUES (?, 'sleep_duration', ?, 'hrs', ?, 'manual')""",
            (crew_id, payload.sleep_hours, recorded_at),
        )
        connection.execute(
            """INSERT INTO measurements
               (crew_id, metric, value, unit, recorded_at, source)
               VALUES (?, 'stress_score', ?, '/ 5', ?, 'manual')""",
            (crew_id, payload.stress, recorded_at),
        )
        row = connection.execute(
            "SELECT * FROM checkins WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


@app.get("/", include_in_schema=False)
def serve_dashboard() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/styles.css", include_in_schema=False)
def serve_stylesheet() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def serve_script() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "app.js", media_type="text/javascript")


@app.get("/astro-theme.css", include_in_schema=False)
def serve_premium_styles() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "astro-theme.css", media_type="text/css")


@app.get("/cinematic.css", include_in_schema=False)
def serve_cinematic_styles() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "cinematic.css", media_type="text/css")


@app.get("/friends-green-cinematic.css", include_in_schema=False)
def serve_friends_green_cinematic_styles() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "friends-green-cinematic.css", media_type="text/css")

@app.get("/aftertrace.css", include_in_schema=False)
def serve_aftertrace_styles() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "aftertrace.css", media_type="text/css")
