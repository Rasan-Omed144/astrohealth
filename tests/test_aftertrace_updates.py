"""Aftertrace palette, accessible selectors, and 5 consistent crew photos."""
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from backend import main

ROOT=Path(__file__).resolve().parents[1]
class AftertraceUpdateTests(unittest.TestCase):
    def test_true_chart_dropdowns(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        script=(ROOT/"app.js").read_text(encoding="utf-8")
        self.assertIn('<select aria-label="Select chart metric"',html)
        self.assertIn('id="timeline-metric"></select>',html)
        self.assertIn('select.addEventListener("change"',script)
        self.assertIn('await loadMetricHistory(activeChartMetric)',script)
        self.assertNotIn('const next = options[(options.indexOf(current) + 1) % options.length]',script)

    def test_five_distinct_portraits(self):
        script=(ROOT/"app.js").read_text(encoding="utf-8")
        for crew_id, *_ in main.CREW_SEED:
            img=ROOT/"assets"/"crew"/(crew_id+".jpg")
            with self.subTest(crew_id=crew_id):
                self.assertIn('"'+crew_id+'": "assets/crew/'+crew_id+'.jpg"',script)
                self.assertTrue(img.is_file())
                self.assertGreater(img.stat().st_size,10_000)

    def test_palette_and_assets_available_over_fastapi(self):
        css=(ROOT/"aftertrace.css").read_text(encoding="utf-8")
        for code in ('#080C13','#101722','#151E2B','#EEF3F8','#9AA9BA','#283343','#E8BC77','#9CBCE4','#DE9D7F'):
            self.assertIn(code,css)
        with TestClient(main.app) as client:
            self.assertEqual(client.get('/aftertrace.css').status_code,200)
            for crew_id,*_ in main.CREW_SEED:
                self.assertEqual(client.get('/assets/crew/'+crew_id+'.jpg').status_code,200)
            self.assertIn('aftertrace.css',client.get('/').text)
