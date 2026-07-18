# Kepler Transit Analytics Engine

An end-to-end pipeline that ingests Kepler space telescope photometry,
isolates exoplanet transit signals from instrument drift, measures the
planet-to-star radius ratio from first principles, and serves the
results through an interactive dashboard.

The physics: when a planet crosses its star, the fractional drop in
light obeys the geometry of two intersecting discs,

    Delta F = (Rp / R*)^2

so a careful measurement of transit depth is a direct measurement of
planetary size. Every number and image in the dashboard is derived
from that relation applied to real (or synthetic ground-truth)
photometry.

## Architecture

    [ Phase 1: Ingestion ] -> [ Phase 2: ETL ] -> [ Phase 3: BLS baseline ]
                                                       |
                              [ SQLite results ] <-----+----> [ Phase 4: PINN (in progress) ]
                                      |
                              [ Streamlit dashboard ]

- `pipeline/ingest.py` — downloads light curves from the MAST archive
  (lightkurve), mission-parameterised for future TESS support, and
  extracts the host star's Teff and radius from the FITS header
  (Kepler Input Catalog values).
- `pipeline/transform.py` — Savitzky-Golay detrending, with a
  documented guard against the filter biasing transit depth.
- `pipeline/analyze.py` — Box Least Squares period search: the
  classical baseline the mission itself used, and the falsifiability
  standard the Phase 4 PINN must beat.
- `pipeline/pinn.py` — Physics-Informed Neural Network (in progress):
  transit geometry encoded in the loss function.
- `pipeline/synthetic.py` — two ground-truth demo targets (a Sun-like
  G star and a K dwarf) so the pipeline, star rendering, and compare
  mode all run offline. Validation: injected P = 3.5000 d recovered at
  3.4992 d (0.02% error); both targets show the same ~2% depth
  underestimate — a systematic detrending effect, documented and
  scheduled for the Phase 4 transit-masking fix.
- `db/storage.py` — SQLite metadata + results; bulk arrays stored as
  compressed .npz with paths in the DB. A `method` column lets PINN
  results land beside BLS with zero schema changes; stellar columns
  are added via lightweight in-place migration.
- `viz/plots.py` — light curves, phase-folded transits, folded
  comparison overlays, and simulated star imagery: each host star's
  colour is computed from Planck's law at its catalogued Teff (via
  the CIE colour-matching fits of Wyman, Sloan & Shirley 2013),
  with temperature-dependent limb darkening, and the planet
  silhouette drawn to scale from the measured Rp/R* — the image is
  the measurement.
- `app.py` — Streamlit dashboard with two modes: single-target
  diagnostics (metrics, plots, simulated host-star portrait, transit
  scene, random-target exploration) and multi-target comparison
  (parameter table, star gallery at relative physical scale, overlaid
  folded transits). A model-comparison panel awaits the PINN.

## Quick start

    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

    # Offline demo (two ground-truth stars, no internet needed):
    python run_pipeline.py --synthetic

    # Real targets (downloads from MAST):
    python run_pipeline.py --targets Kepler-8 Kepler-10 Kepler-17
    python run_pipeline.py --range Kepler 8 12    # Kepler-8 .. Kepler-12

    streamlit run app.py

## Roadmap

- [x] Phase 1–2: ingestion + ETL (validated against synthetic ground truth)
- [x] Phase 3: BLS baseline analysis
- [x] Phase 5: batch CLI over user-supplied targets and ranges
- [x] Phase 8: SQLite persistence with stellar characterisation
- [x] Phase 9: Streamlit dashboard — single-target and comparison
      modes, physics-simulated star imagery
- [ ] Phase 4: PINN — transit geometry in the loss function; validate
      against BLS and the NASA Exoplanet Archive
- [ ] Phase 5b: multi-quarter stitching for more transits per target
- [ ] Phase 6: TESS adapter (mission parameter already threaded through)
- [ ] Phase 7: Wolf-Rayet variability mode (separate physics loss)
- [ ] Deployment: Streamlit Community Cloud

Built with [lightkurve](https://lightkurve.github.io/lightkurve/),
NumPy, Matplotlib, SQLite, and Streamlit.
