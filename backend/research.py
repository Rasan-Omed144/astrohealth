from __future__ import annotations

import sqlite3


def initialize_research_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS research_datasets (
            dataset_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            health_system TEXT NOT NULL,
            mission TEXT NOT NULL,
            source_file TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS research_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT NOT NULL
                REFERENCES research_datasets(dataset_id) ON DELETE CASCADE,
            source_row INTEGER NOT NULL,
            participant_id TEXT NOT NULL,
            timepoint TEXT NOT NULL,
            phase TEXT,
            analyte TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            secondary_value REAL,
            secondary_measure TEXT,
            secondary_value_raw TEXT,
            secondary_value_basis TEXT,
            reference_min REAL,
            reference_max REAL,
            assay_type TEXT,
            sex TEXT,
            measurement_basis TEXT NOT NULL DEFAULT 'measured',
            UNIQUE (dataset_id, source_row)
        );
        CREATE INDEX IF NOT EXISTS research_measurements_filters
            ON research_measurements
               (dataset_id, participant_id, timepoint, analyte);
        """
    )
    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(research_measurements)")
    }
    if "secondary_value_raw" not in existing_columns:
        connection.execute(
            "ALTER TABLE research_measurements ADD COLUMN secondary_value_raw TEXT"
        )
    if "secondary_value_basis" not in existing_columns:
        connection.execute(
            "ALTER TABLE research_measurements ADD COLUMN secondary_value_basis TEXT"
        )
    if "measurement_basis" not in existing_columns:
        connection.execute(
            """ALTER TABLE research_measurements
               ADD COLUMN measurement_basis TEXT NOT NULL DEFAULT 'measured'"""
        )
