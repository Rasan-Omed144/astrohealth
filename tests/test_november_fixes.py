"""Regression checks for NASA Research Data search and Daily Log persistence."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import shutil
from fastapi.testclient import TestClient
from backend import main


class TestNovemberFixes(TestCase):
    def setUp(self):
        self.workdir = TemporaryDirectory()
        self.dbpath = Path(self.workdir.name) / "astro_health_test.db"
        shutil.copyfile(main.PROJECT_ROOT / "data" / "astro_health.db", self.dbpath)
        self.patch = patch.object(main, "DATABASE_PATH", self.dbpath)
        self.patch.start()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.patch.stop()
        self.workdir.cleanup()

    def test_research_searches_full_dataset_and_respects_filters(self):
        first = self.client.get("/api/research/measurements", params={"dataset_id": "OSD-575", "limit": 1})
        self.assertEqual(first.status_code, 200)
        analyte = first.json()["items"][0]["analyte"]
        results = self.client.get("/api/research/measurements", params={"dataset_id": "OSD-575", "q": analyte[:5], "limit": 1})
        self.assertEqual(results.status_code, 200)
        self.assertGreaterEqual(results.json()["total"], 1)
        self.assertEqual(len(results.json()["items"]), 1)
        none = self.client.get("/api/research/measurements", params={"dataset_id": "OSD-575", "q": "__not_a_marker__"})
        self.assertEqual(none.status_code, 200)
        self.assertEqual(none.json()["total"], 0)
        # Treat LIKE wildcards as literal text, not match-all characters.
        escaped = self.client.get("/api/research/measurements", params={"dataset_id": "OSD-575", "q": "%"})
        self.assertEqual(escaped.status_code, 200)
        self.assertEqual(escaped.json()["total"], 0)

    def test_checkin_controls_payload_persists_to_sqlite(self):
        record = {"energy": 5, "stress": 1, "mood": "Low", "sleep_hours": 9.5}
        created = self.client.post("/api/crew/jordan-miller/checkins", json=record)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["sleep_hours"], 9.5)
        latest = self.client.get("/api/crew/jordan-miller/checkins", params={"limit": 1})
        self.assertEqual(latest.status_code, 200)
        for field, value in record.items():
            self.assertEqual(latest.json()[0][field], value)
