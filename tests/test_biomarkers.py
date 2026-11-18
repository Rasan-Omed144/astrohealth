import csv
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from backend import main
from import_data import DATASETS, import_data

SPREADSHEET_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOCUMENT_RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)


class ResearchDataImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_dir = self.root / "source"
        self.source_dir.mkdir()
        self.database_file = self.root / "data" / "astro_health.db"
        self.write_source_files()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_csv(
        self, file_name: str, columns: list[str], rows: list[dict[str, str]]
    ) -> None:
        with (self.source_dir / file_name).open(
            "w", encoding="utf-8", newline=""
        ) as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def write_xlsx(
        self, file_name: str, columns: list[str], rows: list[list[str]]
    ) -> None:
        ElementTree.register_namespace("", SPREADSHEET_NAMESPACE)
        ElementTree.register_namespace("r", DOCUMENT_RELATIONSHIPS_NAMESPACE)
        text_values = list(dict.fromkeys(
            [*columns, *(value for row in rows for value in row if not value.replace(".", "", 1).replace("-", "", 1).isdigit())]
        ))
        shared_indexes = {value: index for index, value in enumerate(text_values)}
        shared_root = ElementTree.Element(
            f"{{{SPREADSHEET_NAMESPACE}}}sst",
            {"count": str(len(text_values)), "uniqueCount": str(len(text_values))},
        )
        for value in text_values:
            item = ElementTree.SubElement(
                shared_root, f"{{{SPREADSHEET_NAMESPACE}}}si"
            )
            text = ElementTree.SubElement(item, f"{{{SPREADSHEET_NAMESPACE}}}t")
            text.text = value

        workbook_root = ElementTree.Element(
            f"{{{SPREADSHEET_NAMESPACE}}}workbook"
        )
        sheets = ElementTree.SubElement(
            workbook_root, f"{{{SPREADSHEET_NAMESPACE}}}sheets"
        )
        ElementTree.SubElement(
            sheets,
            f"{{{SPREADSHEET_NAMESPACE}}}sheet",
            {
                "name": "Sheet1",
                "sheetId": "1",
                f"{{{DOCUMENT_RELATIONSHIPS_NAMESPACE}}}id": "rId1",
            },
        )
        relationships_root = ElementTree.Element(
            f"{{{PACKAGE_RELATIONSHIPS_NAMESPACE}}}Relationships"
        )
        ElementTree.SubElement(
            relationships_root,
            f"{{{PACKAGE_RELATIONSHIPS_NAMESPACE}}}Relationship",
            {
                "Id": "rId1",
                "Type": (
                    "http://schemas.openxmlformats.org/officeDocument/2006/"
                    "relationships/worksheet"
                ),
                "Target": "worksheets/sheet1.xml",
            },
        )

        worksheet_root = ElementTree.Element(
            f"{{{SPREADSHEET_NAMESPACE}}}worksheet"
        )
        sheet_data = ElementTree.SubElement(
            worksheet_root, f"{{{SPREADSHEET_NAMESPACE}}}sheetData"
        )
        for row_number, values in enumerate([columns, *rows], start=1):
            row_element = ElementTree.SubElement(
                sheet_data,
                f"{{{SPREADSHEET_NAMESPACE}}}row",
                {"r": str(row_number)},
            )
            for column_index, value in enumerate(values):
                column_name = chr(ord("A") + column_index)
                is_number = value not in shared_indexes
                cell = ElementTree.SubElement(
                    row_element,
                    f"{{{SPREADSHEET_NAMESPACE}}}c",
                    {
                        "r": f"{column_name}{row_number}",
                        "t": "n" if is_number else "s",
                    },
                )
                cell_value = ElementTree.SubElement(
                    cell, f"{{{SPREADSHEET_NAMESPACE}}}v"
                )
                cell_value.text = (
                    value if is_number else str(shared_indexes[value])
                )

        with zipfile.ZipFile(
            self.source_dir / file_name, "w", zipfile.ZIP_DEFLATED
        ) as workbook:
            workbook.writestr(
                "xl/workbook.xml", ElementTree.tostring(workbook_root)
            )
            workbook.writestr(
                "xl/_rels/workbook.xml.rels",
                ElementTree.tostring(relationships_root),
            )
            workbook.writestr(
                "xl/sharedStrings.xml", ElementTree.tostring(shared_root)
            )
            workbook.writestr(
                "xl/worksheets/sheet1.xml",
                ElementTree.tostring(worksheet_root),
            )

    def write_source_files(self) -> None:
        serum = DATASETS[0]
        self.write_csv(
            serum.file_name,
            [
                "Analyte", "Concentration", "Timepoint", "ID", "Unit",
                "Timepoint2", "Type", "Percent",
            ],
            [{
                "Analyte": "CRP", "Concentration": "3.25", "Timepoint": "R+1",
                "ID": "C001", "Unit": "mg/L", "Timepoint2": "R+1",
                "Type": "HDCVD9", "Percent": "12.5",
            }],
        )
        cbc = DATASETS[1]
        self.write_csv(
            cbc.file_name,
            [
                "ANALYTE", "VALUE", "RANGE_MIN", "RANGE_MAX", "UNITS",
                "TEST_TYPE", "SUBJECT_ID", "SEX", "TEST_DATE",
            ],
            [{
                "ANALYTE": "HEMOGLOBIN", "VALUE": "14.1",
                "RANGE_MIN": "13.2", "RANGE_MAX": "17.1", "UNITS": "g/dL",
                "TEST_TYPE": "CBC", "SUBJECT_ID": "C001", "SEX": "M",
                "TEST_DATE": "L-92",
            }],
        )
        urine = DATASETS[2]
        self.write_xlsx(
            urine.file_name,
            [
                "Analyte", "Concentration", "Timepoint", "ID", "Unit",
                "Timepoint2", "Type", "Percent_normalized_value",
            ],
            [[
                "IL-6", "12.7", "L-92", "C001", "NPQ", "Preflight",
                "Alamar panel", "99.8",
            ], [
                "IL-6", "13.1", "L-44", "C002", "NPQ", "Preflight",
                "Alamar panel", "NA",
            ], [
                "IL-6", "13.4", "L-3", "C003", "NPQ", "Preflight",
                "Alamar panel", "Inf",
            ]],
        )

    def test_imports_all_sources_and_preserves_existing_tables(self) -> None:
        self.database_file.parent.mkdir(parents=True)
        with sqlite3.connect(self.database_file) as connection:
            connection.execute("CREATE TABLE existing_app_data (value TEXT)")
            connection.execute("INSERT INTO existing_app_data VALUES ('preserved')")

        counts = import_data(self.source_dir, self.database_file)
        self.assertEqual(counts, {"OSD-575": 1, "OSD-569": 1, "OSD-656": 3})
        self.assertEqual(import_data(self.source_dir, self.database_file), counts)

        with sqlite3.connect(self.database_file) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT value FROM existing_app_data"
                ).fetchone(),
                ("preserved",),
            )
            datasets = connection.execute(
                "SELECT dataset_id, mission FROM research_datasets ORDER BY dataset_id"
            ).fetchall()
            measurements = connection.execute(
                """SELECT dataset_id, participant_id, timepoint, analyte, value,
                          unit, secondary_value, secondary_value_raw,
                          reference_min, reference_max, sex, phase,
                          measurement_basis, secondary_value_basis
                   FROM research_measurements ORDER BY dataset_id"""
            ).fetchall()

        self.assertEqual(
            datasets,
            [
                ("OSD-569", "Inspiration4"),
                ("OSD-575", "Inspiration4"),
                ("OSD-656", "Inspiration4"),
            ],
        )
        self.assertEqual(measurements[0][0:6], (
            "OSD-569", "C001", "L-92", "HEMOGLOBIN", 14.1, "g/dL"
        ))
        self.assertEqual(measurements[0][7:12], (None, 13.2, 17.1, "M", None))
        self.assertEqual(measurements[0][12], "measured")
        self.assertIsNone(measurements[0][13])
        self.assertEqual(measurements[1][6], 12.5)
        self.assertEqual(measurements[2][6], 99.8)
        self.assertEqual(measurements[2][12:], ("measured", "derived"))
        self.assertEqual(measurements[3][6:8], (None, "NA"))
        self.assertEqual(measurements[4][6:8], (None, "Inf"))

    def test_invalid_input_does_not_replace_previously_imported_records(self) -> None:
        import_data(self.source_dir, self.database_file)
        cbc_file = self.source_dir / DATASETS[1].file_name
        contents = cbc_file.read_text(encoding="utf-8")
        cbc_file.write_text(contents.replace(",14.1,", ",not-a-number,"), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "VALUE must be numeric"):
            import_data(self.source_dir, self.database_file)

        with sqlite3.connect(self.database_file) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM research_measurements"
            ).fetchone()[0]
        self.assertEqual(count, 5)

    def test_research_api_filters_and_paginates_imported_records(self) -> None:
        import_data(self.source_dir, self.database_file)
        database_patch = patch.object(main, "DATABASE_PATH", self.database_file)
        database_patch.start()
        try:
            with TestClient(main.app) as client:
                datasets = client.get("/api/research/datasets").json()
                filters = client.get(
                    "/api/research/datasets/OSD-656/filters"
                ).json()
                response = client.get(
                    "/api/research/measurements",
                    params={
                        "dataset_id": "OSD-656",
                        "participant_id": "C001",
                        "limit": 1,
                    },
                )
                legacy = client.get("/api/biomarkers/C001/crp")
        finally:
            database_patch.stop()

        self.assertEqual(
            [(item["dataset_id"], item["measurement_count"]) for item in datasets],
            [("OSD-569", 1), ("OSD-575", 1), ("OSD-656", 3)],
        )
        self.assertEqual(filters["analyte"], ["IL-6"])
        self.assertEqual(filters["participant_id"], ["C001", "C002", "C003"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["unit"], "NPQ")
        self.assertEqual(response.json()["items"][0]["mission"], "Inspiration4")
        self.assertEqual(response.json()["items"][0]["measurement_basis"], "measured")
        self.assertEqual(response.json()["items"][0]["secondary_value_basis"], "derived")
        self.assertEqual(
            response.json()["items"][0]["source_file"], DATASETS[2].file_name
        )
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(legacy.json()[0]["Concentration"], 3.25)

    def test_unknown_research_dataset_is_reported(self) -> None:
        database_patch = patch.object(main, "DATABASE_PATH", self.database_file)
        database_patch.start()
        try:
            with TestClient(main.app) as client:
                response = client.get(
                    "/api/research/measurements",
                    params={"dataset_id": "OSD-999"},
                )
        finally:
            database_patch.stop()
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
