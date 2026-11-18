from __future__ import annotations

import argparse
import csv
import math
import re
import sqlite3
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from xml.etree import ElementTree

from backend.research import initialize_research_schema

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "data" / "source"
DATABASE_FILE = BASE_DIR / "data" / "astro_health.db"

SPREADSHEET_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOCUMENT_RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)


@dataclass(frozen=True)
class Dataset:
    dataset_id: str
    title: str
    health_system: str
    mission: str
    file_name: str
    file_format: str
    analyte_column: str
    value_column: str
    timepoint_column: str
    participant_column: str
    unit_column: str
    phase_column: str | None
    assay_column: str
    secondary_column: str | None = None
    range_min_column: str | None = None
    range_max_column: str | None = None
    sex_column: str | None = None

    @property
    def required_columns(self) -> tuple[str, ...]:
        optional_names = (
            self.secondary_column,
            self.range_min_column,
            self.range_max_column,
            self.sex_column,
        )
        return tuple(
            column
            for column in (
                self.analyte_column,
                self.value_column,
                self.timepoint_column,
                self.participant_column,
                self.unit_column,
                self.phase_column,
                self.assay_column,
                *optional_names,
            )
            if column is not None
        )


DATASETS = (
    Dataset(
        dataset_id="OSD-575",
        title="Serum cardiovascular biomarkers",
        health_system="Cardiovascular",
        mission="Inspiration4",
        file_name="LSDS-8_Multiplex_serum.cardiovascular.EvePanel_SUBMITTED.csv",
        file_format="csv",
        analyte_column="Analyte",
        value_column="Concentration",
        timepoint_column="Timepoint",
        participant_column="ID",
        unit_column="Unit",
        phase_column="Timepoint2",
        assay_column="Type",
        secondary_column="Percent",
    ),
    Dataset(
        dataset_id="OSD-569",
        title="Whole-blood complete blood count",
        health_system="Blood composition",
        mission="Inspiration4",
        file_name="LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv",
        file_format="csv",
        analyte_column="ANALYTE",
        value_column="VALUE",
        timepoint_column="TEST_DATE",
        participant_column="SUBJECT_ID",
        unit_column="UNITS",
        phase_column=None,
        assay_column="TEST_TYPE",
        range_min_column="RANGE_MIN",
        range_max_column="RANGE_MAX",
        sex_column="SEX",
    ),
    Dataset(
        dataset_id="OSD-656",
        title="Urine immune and inflammation panel",
        health_system="Immune / inflammation",
        mission="Inspiration4",
        file_name="LSDS-64_Multiplex_urine.immune.AlamarPanel_SUBMITTED.xlsx",
        file_format="xlsx",
        analyte_column="Analyte",
        value_column="Concentration",
        timepoint_column="Timepoint",
        participant_column="ID",
        unit_column="Unit",
        phase_column="Timepoint2",
        assay_column="Type",
        secondary_column="Percent_normalized_value",
    ),
)


def _column_index(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    if match is None:
        raise ValueError(f"Invalid spreadsheet cell reference: {reference!r}.")
    index = 0
    for character in match.group():
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _xlsx_rows(source: Path) -> list[tuple[int, dict[str, str]]]:
    try:
        workbook = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError(f"Could not open Excel workbook {source.name}: {error}") from error

    with workbook:
        try:
            workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
            relationships_root = ElementTree.fromstring(
                workbook.read("xl/_rels/workbook.xml.rels")
            )
            relationship_map = {
                relation.attrib["Id"]: relation.attrib["Target"]
                for relation in relationships_root.findall(
                    f"{{{PACKAGE_RELATIONSHIPS_NAMESPACE}}}Relationship"
                )
            }
            sheet = workbook_root.find(
                f".//{{{SPREADSHEET_NAMESPACE}}}sheet"
            )
            if sheet is None:
                raise ValueError("The Excel workbook does not contain a worksheet.")
            relationship_id = sheet.attrib[
                f"{{{DOCUMENT_RELATIONSHIPS_NAMESPACE}}}id"
            ]
            target = relationship_map[relationship_id].lstrip("/")
            worksheet_path = target if target.startswith("xl/") else f"xl/{target}"
            worksheet_root = ElementTree.fromstring(workbook.read(worksheet_path))
        except (KeyError, ElementTree.ParseError, OSError) as error:
            raise ValueError(
                f"Could not read the first worksheet in {source.name}: {error}"
            ) from error

        try:
            shared_root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(text.text or "" for text in item.findall(f".//{{{SPREADSHEET_NAMESPACE}}}t"))
                for item in shared_root.findall(f"{{{SPREADSHEET_NAMESPACE}}}si")
            ]
        except KeyError:
            shared_strings = []
        except ElementTree.ParseError as error:
            raise ValueError(
                f"Could not read shared strings in {source.name}: {error}"
            ) from error

        rows: list[tuple[int, dict[str, str]]] = []
        sheet_data = worksheet_root.find(
            f".//{{{SPREADSHEET_NAMESPACE}}}sheetData"
        )
        if sheet_data is None:
            raise ValueError(f"The first worksheet in {source.name} is empty.")
        for row in sheet_data.findall(f"{{{SPREADSHEET_NAMESPACE}}}row"):
            cells: list[str] = []
            for cell in row.findall(f"{{{SPREADSHEET_NAMESPACE}}}c"):
                index = _column_index(cell.attrib["r"])
                if index >= 10000:
                    raise ValueError(f"{source.name} contains an invalid wide row.")
                if len(cells) <= index:
                    cells.extend([""] * (index + 1 - len(cells)))
                value = cell.find(f"{{{SPREADSHEET_NAMESPACE}}}v")
                cell_value = value.text or "" if value is not None else ""
                if cell.attrib.get("t") == "s" and cell_value:
                    try:
                        cell_value = shared_strings[int(cell_value)]
                    except (IndexError, ValueError) as error:
                        raise ValueError(
                            f"{source.name} contains an invalid shared-string reference."
                        ) from error
                elif cell.attrib.get("t") == "inlineStr":
                    cell_value = "".join(
                        text.text or ""
                        for text in cell.findall(
                            f".//{{{SPREADSHEET_NAMESPACE}}}t"
                        )
                    )
                cells[index] = cell_value
            if any(value.strip() for value in cells):
                rows.append((int(row.attrib["r"]), {str(i): value for i, value in enumerate(cells)}))

    if not rows:
        raise ValueError(f"The first worksheet in {source.name} has no data.")
    headers = [value.strip() for _, value in sorted(rows[0][1].items(), key=lambda item: int(item[0]))]
    if not headers or any(not name for name in headers) or len(headers) != len(set(headers)):
        raise ValueError(f"{source.name} has blank or duplicate column names.")
    return [
        (
            row_number,
            {
                headers[int(index)]: value
                for index, value in row.items()
                if int(index) < len(headers)
            },
        )
        for row_number, row in rows[1:]
    ]


def _read_dataset_rows(dataset: Dataset, source: Path) -> list[tuple[int, dict[str, str]]]:
    if dataset.file_format == "xlsx":
        rows = _xlsx_rows(source)
    else:
        try:
            with source.open("r", encoding="utf-8-sig", newline="") as stream:
                reader: csv.DictReader[str] = csv.DictReader(stream)
                headers = reader.fieldnames or []
                if len(headers) != len(set(headers)):
                    raise ValueError(f"{source.name} has duplicate column names.")
                rows = []
                for line_number, row in enumerate(reader, start=2):
                    if None in row:
                        raise ValueError(
                            f"{source.name} line {line_number} has more fields than the header."
                        )
                    rows.append(
                        (
                            line_number,
                            {
                                key: value or ""
                                for key, value in row.items()
                                if key is not None
                            },
                        )
                    )
        except UnicodeDecodeError as error:
            raise ValueError(f"{source.name} is not valid UTF-8 text.") from error

    if not rows:
        raise ValueError(f"{source.name} contains no measurement rows.")
    headers = set(rows[0][1])
    missing = [column for column in dataset.required_columns if column not in headers]
    if missing:
        raise ValueError(
            f"{source.name} is missing required columns: {', '.join(missing)}."
        )
    return rows


def _required_text(
    row: dict[str, str], column: str, dataset: Dataset, row_number: int
) -> str:
    value = row.get(column, "").strip()
    if not value:
        raise ValueError(
            f"{dataset.file_name} row {row_number}: {column} must not be empty."
        )
    return value


def _optional_number(
    row: dict[str, str],
    column: str | None,
    dataset: Dataset,
    row_number: int,
    allow_source_missing: bool = False,
) -> float | None:
    if column is None or not row.get(column, "").strip():
        return None
    value = row[column].strip()
    if allow_source_missing and value.casefold() in {
        "na", "n/a", "nan", "inf", "+inf", "-inf", "infinity",
    }:
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(
            f"{dataset.file_name} row {row_number}: {column} must be numeric or empty; "
            f"got {value!r}."
        ) from error
    if not math.isfinite(number):
        raise ValueError(
            f"{dataset.file_name} row {row_number}: {column} must be a finite number."
        )
    return number


def _parse_rows(
    dataset: Dataset, source: Path
) -> list[tuple[object, ...]]:
    source_rows = _read_dataset_rows(dataset, source)
    parsed: list[tuple[object, ...]] = []
    for row_number, row in source_rows:
        analyte = _required_text(row, dataset.analyte_column, dataset, row_number)
        participant_id = _required_text(
            row, dataset.participant_column, dataset, row_number
        )
        timepoint = _required_text(
            row, dataset.timepoint_column, dataset, row_number
        )
        value = _optional_number(row, dataset.value_column, dataset, row_number)
        if value is None:
            raise ValueError(
                f"{dataset.file_name} row {row_number}: "
                f"{dataset.value_column} must be numeric and not empty."
            )
        secondary_text = (
            row.get(dataset.secondary_column, "").strip()
            if dataset.secondary_column is not None
            else ""
        )
        secondary_value = _optional_number(
            row,
            dataset.secondary_column,
            dataset,
            row_number,
            allow_source_missing=True,
        )
        parsed.append(
            (
                dataset.dataset_id,
                row_number,
                participant_id,
                timepoint,
                (
                    row.get(dataset.phase_column, "").strip() or None
                    if dataset.phase_column is not None
                    else None
                ),
                analyte,
                value,
                row.get(dataset.unit_column, "").strip() or None,
                secondary_value,
                dataset.secondary_column,
                secondary_text if secondary_text and secondary_value is None else None,
                "derived" if dataset.secondary_column is not None else None,
                _optional_number(
                    row, dataset.range_min_column, dataset, row_number
                ),
                _optional_number(
                    row, dataset.range_max_column, dataset, row_number
                ),
                row.get(dataset.assay_column, "").strip() or None,
                (
                    row.get(dataset.sex_column, "").strip() or None
                    if dataset.sex_column is not None
                    else None
                ),
                "measured",
            )
        )
    return parsed


def import_data(
    source_dir: Path = SOURCE_DIR,
    database_file: Path = DATABASE_FILE,
) -> dict[str, int]:
    dataset_rows: dict[str, list[tuple[object, ...]]] = {}
    for dataset in DATASETS:
        source = source_dir / dataset.file_name
        if not source.is_file():
            raise FileNotFoundError(
                f"Required dataset file not found: {source}. "
                "Place all three supplied files in data/source/."
            )
        dataset_rows[dataset.dataset_id] = _parse_rows(dataset, source)

    database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_file, timeout=10)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        initialize_research_schema(connection)
        with connection:
            connection.executemany(
                """INSERT INTO research_datasets
                   (dataset_id, title, health_system, mission, source_file)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(dataset_id) DO UPDATE SET
                       title = excluded.title,
                       health_system = excluded.health_system,
                       mission = excluded.mission,
                       source_file = excluded.source_file""",
                [
                    (
                        dataset.dataset_id,
                        dataset.title,
                        dataset.health_system,
                        dataset.mission,
                        dataset.file_name,
                    )
                    for dataset in DATASETS
                ],
            )
            for dataset in DATASETS:
                connection.execute(
                    "DELETE FROM research_measurements WHERE dataset_id = ?",
                    (dataset.dataset_id,),
                )
                connection.executemany(
                    """INSERT INTO research_measurements
                       (dataset_id, source_row, participant_id, timepoint, phase,
                        analyte, value, unit, secondary_value, secondary_measure,
                        secondary_value_raw, secondary_value_basis, reference_min,
                        reference_max, assay_type, sex, measurement_basis)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    dataset_rows[dataset.dataset_id],
                )
    finally:
        connection.close()
    return {dataset_id: len(rows) for dataset_id, rows in dataset_rows.items()}


def main(output: TextIO = sys.stdout, arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import the supplied NASA research exports into the app database."
    )
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--database", type=Path, default=DATABASE_FILE)
    options = parser.parse_args(arguments)

    counts = import_data(options.source_dir, options.database)
    print("NASA research datasets imported successfully.", file=output)
    for dataset in DATASETS:
        print(f"{dataset.dataset_id}: {counts[dataset.dataset_id]} measurements", file=output)
    print(f"Database location: {options.database}", file=output)
    return sum(counts.values())


if __name__ == "__main__":
    main()
