"""Regression checks for the approved six-view, no-AI student prototype."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main

class CinematicNoAiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch=patch.object(main,'DATABASE_PATH',Path(self.temp.name)/'demo.sqlite')
        self.db_patch.start()
        self.context=TestClient(main.app)
        self.client=self.context.__enter__()
    def tearDown(self):
        self.context.__exit__(None,None,None)
        self.db_patch.stop()
        self.temp.cleanup()

    def test_all_six_pages_present_and_ai_absent(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        content=response.text
        for view in ('astronaut','control','timeline','spacecraft','research','alerts'):
            self.assertIn(f'id="{view}-view"',content)
        self.assertIn('id="crew-roster"',content)
        self.assertIn('id="portrait-full-report"',content)
        self.assertNotIn('astro-ai-open',content)
        self.assertNotIn('Help &amp; Support',content)
        self.assertEqual(self.client.get('/api/assistant/status').status_code,404)
        self.assertEqual(self.client.post('/api/assistant',json={'question':'test'}).status_code,404)

    def test_images_css_and_js_served(self):
        for path in ('/app.js','/styles.css','/astro-theme.css','/cinematic.css',
                     '/assets/earth-hero.jpg','/assets/control-hero.jpg',
                     '/assets/astronaut-reference-portrait.jpg','/assets/nasa-reference-logo.png'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code,200)

    def test_separate_crew_and_nasa_source_endpoints(self):
        crew=self.client.get('/api/crew').json()
        self.assertEqual(len(crew),5)
        member=self.client.get('/api/crew/'+crew[0]['id']).json()
        self.assertIn('latest_measurements',member)
        self.assertIn('sleep_duration',member['latest_measurements'])
        self.assertEqual(len(self.client.get('/api/spacecraft/history').json()['items']),30)
        self.assertEqual(self.client.get('/api/research/datasets').status_code,200)

if __name__=='__main__':unittest.main()
