# AstroHealth — Cinematic UI, No AI

This is the updated **runnable student prototype** based on the existing team's code and the six approved dashboard mockups in `design-references/`.

**Removed:** the ASTRO AI widget, assistant endpoints, external model integration and associated dependencies/configuration. There is no simulation engine beyond the pre-existing fictional demo measurements.

**Retained:** FastAPI/SQLite, NASA research import/browser, five fictional crew profiles, 30-day health history, six navigation views, per-person reports, daily check-ins, local calculated alerts, spacecraft demonstration history and emergency drill dialogue.

**Design:** identical sidebar across six pages, teammate charcoal/lime-green colors and black-hole space background, compact health priority cards, a data-backed trend chart, alert review, astronaut illustration and dedicated crew cards. The actual values shown come from the local database, **not from the numbers embedded in the original mockup images**.

For beginner-friendly Windows instructions, see **START_HERE.md**.

## Data provenance / limitations

Research records from OSD-569 (blood count), OSD-575 (serum biomarkers) and OSD-656 (urine immune panel) remain distinct from fictional crew readings. See `data/README.md` and `import_data.py` for source import details. Mission day, cabin metrics and mockup imagery are illustrative. This is not a clinical tool, official NASA product, validated physiological simulation or operational spacecraft dashboard.

**Verification:** Backend/unit tests and an isolated browser DOM interaction check passed. The project could not be tested end to end with live browser-to-local-server networking in the build environment; please verify the extracted project in Windows/Chrome. See `CHANGES_NOV15.md` for fixes and tests.

## Latest changes

The requested AFTERTRACE palette is applied through `aftertrace.css`. Both health metric selectors are native dropdowns with 10 available indicators; changing them reloads measurements for the selected demo astronaut. Each of the five fictional crew members now has a distinct AI-generated image in a white astronaut EVA suit, consistently reused across views. Portraits are illustrations, not documentary NASA photographs. NASA study records and fictional demo health data remain distinct.

## November 15 fixes

Mission Control photo panel restored with a crew observation summary; Daily Log form controls, Save and Cancel behaviors corrected; NASA Research Data reorganized as a three-dataset research library with search, filters and on-demand record tables. See `CHANGES_NOV15.md` for details.
