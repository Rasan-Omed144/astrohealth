import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main


class HealthGuardApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.database_patch = patch.object(main, "DATABASE_PATH", self.database_path)
        self.database_patch.start()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_seed_data_and_static_dashboard_are_available(self) -> None:
        self.assertEqual(self.client.get("/api/health").json(), {
            "status": "ok",
            "database": "connected",
        })
        crew = self.client.get("/api/crew").json()
        self.assertEqual(len(crew), 5)
        self.assertEqual(crew[0]["id"], "amara-kim")
        self.assertIn("resting_heart_rate", crew[0]["latest_measurements"])
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/backend/main.py").status_code, 404)

    def test_demo_measurement_history_covers_thirty_days_without_reseeding(self) -> None:
        with main.get_connection() as connection:
            count = connection.execute(
                """SELECT COUNT(*) FROM measurements
                   WHERE crew_id = 'jordan-miller'
                     AND metric = 'resting_heart_rate'
                     AND source = 'demo'"""
            ).fetchone()[0]
        self.assertEqual(count, 30)

        main.initialize_database()

        with main.get_connection() as connection:
            count_after_reinitialize = connection.execute(
                """SELECT COUNT(*) FROM measurements
                   WHERE crew_id = 'jordan-miller'
                     AND metric = 'resting_heart_rate'
                     AND source = 'demo'"""
            ).fetchone()[0]
        self.assertEqual(count_after_reinitialize, 30)
        history = self.client.get(
            "/api/crew/jordan-miller/measurements",
            params={"metric": "resting_heart_rate", "limit": 30},
        ).json()
        self.assertEqual(len(history), 30)
        self.assertNotEqual(history[0]["recorded_at"][:10], history[-1]["recorded_at"][:10])
        values = [record["value"] for record in reversed(history)]
        expected = [
            main.LATEST_VALUES["jordan-miller"][0] + offset
            for offset in main.HEART_RATE_HISTORY_VARIATION
        ]
        self.assertEqual(values, expected)
        self.assertGreaterEqual(len(set(values)), 8)

    def test_daily_demo_timeline_rolls_forward_and_spacecraft_has_thirty_days(self) -> None:
        spacecraft = self.client.get("/api/spacecraft/history").json()
        self.assertEqual(len(spacecraft["items"]), 30)
        spacecraft_days = [row["recorded_at"][:10] for row in spacecraft["items"]]
        self.assertEqual(len(set(spacecraft_days)), 30)
        self.assertEqual(spacecraft_days[-1], main.datetime.now(main.UTC).date().isoformat())
        self.assertGreater(len({
            row["carbon_dioxide_ppm"] for row in spacecraft["items"]
        }), 1)

        for value in (65, 66):
            self.assertEqual(
                self.client.post(
                    "/api/crew/jordan-miller/measurements",
                    json={"metric": "resting_heart_rate", "value": value},
                ).status_code,
                201,
            )
        daily_health = self.client.get(
            "/api/crew/jordan-miller/measurements",
            params={"metric": "resting_heart_rate", "limit": 30, "daily": "true"},
        ).json()
        self.assertEqual(len(daily_health), 30)
        self.assertEqual(len({record["recorded_at"][:10] for record in daily_health}), 30)
        self.assertEqual(daily_health[0]["value"], 66)

        current_dose = spacecraft["items"][-1]["accumulated_radiation_dose_msv"]
        tomorrow = main.datetime.now(main.UTC).date() + timedelta(days=1)
        with main.get_connection() as connection:
            main.ensure_daily_demo_samples(connection, tomorrow)

        next_day_spacecraft = self.client.get("/api/spacecraft/history").json()["items"]
        self.assertEqual(len(next_day_spacecraft), 30)
        self.assertEqual(next_day_spacecraft[-1]["recorded_at"][:10], tomorrow.isoformat())
        self.assertEqual(
            next_day_spacecraft[-1]["accumulated_radiation_dose_msv"],
            round(current_dose + 0.45, 2),
        )
        health_history = self.client.get(
            "/api/crew/jordan-miller/measurements",
            params={"metric": "resting_heart_rate", "limit": 30, "daily": "true"},
        ).json()
        self.assertEqual(len(health_history), 30)
        self.assertEqual(health_history[0]["recorded_at"][:10], tomorrow.isoformat())
        self.assertEqual(len({record["recorded_at"][:10] for record in health_history}), 30)

    def test_creates_persistent_checkin_and_sleep_measurement(self) -> None:
        response = self.client.post(
            "/api/crew/jordan-miller/checkins",
            json={"energy": 4, "stress": 2, "mood": "Good", "sleep_hours": 7.4},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["sleep_hours"], 7.4)

        checkins = self.client.get("/api/crew/jordan-miller/checkins").json()
        self.assertEqual(checkins[0]["mood"], "Good")
        self.assertEqual(checkins[0]["source"], "manual")

        measurements = self.client.get(
            "/api/crew/jordan-miller/measurements",
            params={"metric": "sleep_duration"},
        ).json()
        self.assertEqual(measurements[0]["value"], 7.4)
        self.assertEqual(measurements[0]["baseline_min"], 7)
        updated_crew = self.client.get("/api/crew/jordan-miller").json()
        self.assertEqual(updated_crew["latest_measurements"]["sleep_duration"]["value"], 7.4)
        self.assertEqual(updated_crew["latest_measurements"]["stress_score"]["value"], 2)

    def test_validation_and_missing_crew_errors(self) -> None:
        invalid_checkin = self.client.post(
            "/api/crew/jordan-miller/checkins",
            json={"energy": 6, "stress": 2, "mood": "Good", "sleep_hours": 7},
        )
        self.assertEqual(invalid_checkin.status_code, 422)
        self.assertEqual(self.client.get("/api/crew/unknown").status_code, 404)

    def test_creates_manual_measurement(self) -> None:
        response = self.client.post(
            "/api/crew/jordan-miller/measurements",
            json={"metric": "hydration_liters", "value": 2.4},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["unit"], "L")
        self.assertEqual(response.json()["source"], "manual")

        latest = self.client.get(
            "/api/crew/jordan-miller/measurements",
            params={"metric": "hydration_liters", "limit": 1},
        ).json()[0]
        self.assertEqual(latest["value"], 2.4)

    def test_removes_existing_pasha_profile_and_dependent_records(self) -> None:
        with main.get_connection() as connection:
            connection.execute(
                """INSERT INTO crew (id, mission_id, full_name, role, health_score)
                   VALUES ('pasha-ivanov', 'artemis-iii', 'Pasha Ivanov',
                           'Mission specialist', 87)"""
            )
            connection.execute(
                """INSERT INTO measurements
                   (crew_id, metric, value, unit, recorded_at)
                   VALUES ('pasha-ivanov', 'resting_heart_rate', 68, 'bpm', '2026-01-01')"""
            )
            connection.execute(
                """INSERT INTO checkins
                   (crew_id, energy, stress, mood, sleep_hours, recorded_at)
                   VALUES ('pasha-ivanov', 4, 2, 'Good', 7, '2026-01-01')"""
            )

        main.initialize_database()

        self.assertEqual(self.client.get("/api/crew/pasha-ivanov").status_code, 404)
        self.assertEqual(
            self.client.get("/api/crew/pasha-ivanov/checkins").status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/api/crew/pasha-ivanov/measurements").status_code,
            404,
        )
        crew = self.client.get("/api/crew").json()
        self.assertEqual(len(crew), 5)
        self.assertNotIn("Pasha Ivanov", [member["full_name"] for member in crew])

    def test_adds_crew_to_existing_mission(self) -> None:
        response = self.client.post(
            "/api/crew",
            json={
                "id": "test-astronaut",
                "full_name": "Test Astronaut",
                "role": "Payload specialist",
                "health_score": 88,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["full_name"], "Test Astronaut")
        self.assertEqual(len(self.client.get("/api/crew").json()), 6)


if __name__ == "__main__":
    unittest.main()
