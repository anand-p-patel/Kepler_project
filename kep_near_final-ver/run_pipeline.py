"""
Batch pipeline runner (Phase 5 — user-supplied targets).

Usage
-----
Real targets (needs internet, hits the MAST archive):
    python run_pipeline.py --targets Kepler-8 Kepler-10 Kepler-17

A numeric range of targets:
    python run_pipeline.py --range Kepler 8 12     # Kepler-8 .. Kepler-12

Offline demo targets with known ground truth (no internet needed):
    python run_pipeline.py --synthetic
"""

import argparse
import sys

import numpy as np

from pipeline.ingest import fetch_light_curve, get_stellar_params
from pipeline.transform import flatten_light_curve
from pipeline.analyze import run_bls
from pipeline.synthetic import make_synthetic_light_curve, DEMO_TARGETS
from db import storage


def expand_range(prefix: str, start: int, end: int):
    """'Kepler', 8, 12 -> ['Kepler-8', ..., 'Kepler-12']"""
    if end < start:
        start, end = end, start
    return [f"{prefix}-{i}" for i in range(start, end + 1)]


def process_light_curve(target_id: str, mission: str, lc, window: int,
                        teff=None, stellar_radius=None):
    """Shared Phase 2 -> 3 -> storage path for real and synthetic data."""
    raw_time = np.asarray(lc.time.value, dtype=float)
    raw_flux = np.asarray(lc.flux.value, dtype=float)

    time, flux = flatten_light_curve(lc, window_length=window)
    result = run_bls(time, flux)

    storage.save_target(target_id, mission, raw_time, raw_flux, time, flux,
                        teff=teff, stellar_radius=stellar_radius)
    storage.save_result(target_id, result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Kepler PINN pipeline")
    parser.add_argument("--targets", nargs="*", default=[],
                        help="Target names, e.g. Kepler-8 Kepler-10")
    parser.add_argument("--range", nargs=3, metavar=("PREFIX", "START", "END"),
                        help="Numeric target range, e.g. --range Kepler 8 12")
    parser.add_argument("--mission", default="Kepler")
    parser.add_argument("--window", type=int, default=101,
                        help="flatten() window length in cadences")
    parser.add_argument("--synthetic", action="store_true",
                        help="Process the offline demo targets instead")
    args = parser.parse_args()

    storage.init_db()

    targets = list(args.targets)
    if args.range:
        prefix, start, end = args.range
        targets += expand_range(prefix, int(start), int(end))

    if not targets and not args.synthetic:
        parser.error("Provide --targets ..., --range ..., or --synthetic")

    summary = []

    if args.synthetic:
        for name, params in DEMO_TARGETS.items():
            print(f"Processing {name} (synthetic, ground truth known)...")
            lc = make_synthetic_light_curve(params)
            result = process_light_curve(
                name, "Synthetic", lc, args.window,
                teff=params["teff"],
                stellar_radius=params["stellar_radius"],
            )
            summary.append((name, result))
            print(f"  truth:     P={params['period_days']:.4f} d, "
                  f"depth={params['depth']:.5f}, "
                  f"Rp/R*={np.sqrt(params['depth']):.4f}")
            print(f"  recovered: P={result['period_days']:.4f} d, "
                  f"depth={result['depth']:.5f}, "
                  f"Rp/R*={result['rp_over_rstar']:.4f}")

    for target in targets:
        print(f"Processing {target} ({args.mission})...")
        try:
            lc = fetch_light_curve(target, mission=args.mission)
            if lc is None:
                print(f"  no light curve found for {target}, skipping")
                continue
            teff, radius = get_stellar_params(lc)
            result = process_light_curve(target, args.mission, lc,
                                         args.window, teff=teff,
                                         stellar_radius=radius)
            summary.append((target, result))
            star_txt = f", Teff={teff:.0f} K" if teff is not None else ""
            print(f"  P={result['period_days']:.4f} d, "
                  f"depth={result['depth']:.5f}, "
                  f"Rp/R*={result['rp_over_rstar']:.4f}{star_txt}")
        except Exception as exc:
            # One bad target must not kill the batch.
            print(f"  FAILED on {target}: {exc}", file=sys.stderr)

    print(f"\nDone. {len(summary)} target(s) processed and stored.")
    print("Launch the dashboard with:  streamlit run app.py")


if __name__ == "__main__":
    main()
