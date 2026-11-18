# AstroHealth — OUR original design + friend green palette + cinematic background

**This is the requested MIX:** our original six-page layout and crew functionality, with your friend's charcoal/lime colour palette and black-hole space background. This is **not** the full replacement with your friend's compact layout.

## Windows

1. Extract the entire ZIP (don't run files inside the ZIP preview).
2. Open the folder named `AstroHealth_Our_Layout_Friends_Green_Cinematic`.
3. Double-click `RUN_GREEN_VERSION_WINDOWS.bat`, OR open CMD in that folder and run:

   `py -V:3.14 -m uvicorn backend.main:app --reload --port 8001`

4. Open **http://127.0.0.1:8001** and press **Ctrl + Shift + R**.

We intentionally use **port 8001** so you don't accidentally see an older AstroHealth server running on port 8000. If you see the gold theme, you opened the old app, not this version.

If Python dependencies are missing, run:

   `py -V:3.14 -m pip install -r requirements.txt`

## What's included

- Our original six-page frontend, not the friend's compact layout
- Teammate-inspired charcoal/lime-green colours and cinematic black-hole background
- Original five fictional astronaut profiles, chart dropdowns, alerts and check-ins
- Original FastAPI backend, SQLite database, NASA research data and source files
- No AI assistant

All fictional astronaut measurements remain simulated and distinct from imported NASA research measurements.

## Fixed version highlights (Nov 15)

- Mission Control: the formerly blank panel below summary cards now displays the intended image with a live-from-local-data observation caption.
- Daily Log: adjust energy, stress, mood and sleep, then press **Save check-in**. The Save button displays progress and errors if the server is unavailable; Cancel/Close never save.
- Research Data: select a NASA dataset card to open the searchable table, expand a row's Details for source provenance, or use **Back to research library**.

If an older copy of AstroHealth is already running on port 8001, close its command window before launching this version. Refresh with Ctrl+Shift+R.
