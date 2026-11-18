# NASA research data

The three source exports are stored in `source/` and imported into
`astro_health.db` alongside (but separately from) the illustrative demo crew
tables. Run `python import_data.py` from the project root to import or refresh
the research records without replacing the existing demo data.

| Study ID | Source file | Data |
| --- | --- | --- |
| OSD-575 | `LSDS-8_Multiplex_serum.cardiovascular.EvePanel_SUBMITTED.csv` | Serum cardiovascular biomarkers |
| OSD-569 | `LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv` | Whole-blood complete blood count |
| OSD-656 | `LSDS-64_Multiplex_urine.immune.AlamarPanel_SUBMITTED.xlsx` | Urine immune and inflammation panel |

These study IDs and the Inspiration4 mission association come from the supplied
ASTRA HealthGuard instructions. The original filenames, participant codes,
timepoints, phases, units and available assay-specific context are retained.
Only columns needed to present and filter measurements are imported; the source
files remain unchanged for reference. Do not interpret these cohort-level
observations as live measurements or as a single astronaut's clinical history.
