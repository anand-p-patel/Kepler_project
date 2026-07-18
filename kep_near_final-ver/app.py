"""
Kepler PINN — public dashboard (Phase 9).

Run with:  streamlit run app.py

Two view modes:
  - Single target: full diagnostics for one star, including a
    simulated portrait of the host star itself.
  - Compare targets: any user-selected set of processed stars side by
    side — parameter table, star gallery at relative physical scale,
    and overlaid folded transits.

Reads processed results from SQLite; never re-runs the heavy pipeline
on page load.
"""

import pandas as pd
import streamlit as st

from db import storage
from viz import plots

st.set_page_config(page_title="Kepler Transit Analytics",
                   page_icon="\U0001FA90", layout="wide")

storage.init_db()

st.sidebar.title("Kepler Transit Analytics")

targets = [row[0] for row in storage.list_targets()]

if not targets:
    st.title("No targets processed yet")
    st.markdown(
        "Populate the database first:\n\n"
        "```bash\n"
        "python run_pipeline.py --synthetic\n"
        "python run_pipeline.py --targets Kepler-8 Kepler-10\n"
        "python run_pipeline.py --range Kepler 8 12\n"
        "```"
    )
    st.stop()

mode = st.sidebar.radio("View mode", ["Single target", "Compare targets"])

# ======================================================================
# Single-target view
# ======================================================================
if mode == "Single target":
    if ("target_id" not in st.session_state
            or st.session_state.target_id not in targets):
        st.session_state.target_id = targets[0]

    st.sidebar.selectbox("Choose a target", targets, key="target_id")

    if st.sidebar.button("\U0001F3B2 Random target"):
        random_id = storage.get_random_target()
        if random_id:
            st.session_state.target_id = random_id
            st.rerun()

    st.sidebar.divider()
    st.sidebar.caption(
        "Process new targets from the command line:\n\n"
        "`python run_pipeline.py --targets Kepler-17`\n\n"
        "`python run_pipeline.py --range Kepler 8 12`"
    )

    data = storage.load_target(st.session_state.target_id)
    if data is None:
        st.error("Target not found in database.")
        st.stop()

    bls = data["results"].get("bls")
    pinn = data["results"].get("pinn")

    st.title(data["target_id"])
    star_bits = []
    if data["teff"] is not None:
        star_bits.append(f"{plots.spectral_class(data['teff'])}-type")
        star_bits.append(f"{data['teff']:.0f} K")
    if data["stellar_radius"] is not None:
        star_bits.append(f"{data['stellar_radius']:.2f} R\u2609")
    star_txt = " \u00b7 ".join(star_bits) if star_bits \
        else "stellar parameters unavailable"
    st.caption(
        f"Mission: {data['mission']} \u00b7 {star_txt} "
        f"\u00b7 {data['n_points']:,} data points "
        f"\u00b7 processed {data['processed_at']}"
    )

    if bls:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Period", f"{bls['period_days']:.4f} d")
        c2.metric("Transit depth", f"{bls['depth'] * 100:.3f} %")
        c3.metric("Rp / R\u2605", f"{bls['rp_over_rstar']:.4f}")
        c4.metric("Duration", f"{bls['duration_days'] * 24:.2f} h")

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Detrended light curve")
        st.pyplot(plots.plot_light_curve(data["time"], data["flux"]))

        if bls:
            st.subheader("Phase-folded transit")
            st.pyplot(plots.plot_folded(
                data["time"], data["flux"],
                period=bls["period_days"], t0=bls["t0"],
                duration=bls["duration_days"],
            ))

    with right:
        st.subheader("Host star (simulated)")
        st.pyplot(plots.render_star(
            data["teff"], data["stellar_radius"], name=data["target_id"],
        ))
        st.caption(
            "Simulated from catalogue physics: colour from Planck's law "
            "at the star's measured Teff, limb darkening varying with "
            "temperature. Not a stock image."
        )

        if bls:
            st.subheader("Transit scene (to scale)")
            st.pyplot(plots.render_transit_scene(
                bls["rp_over_rstar"], teff=data["teff"],
            ))
            st.caption(
                "Planet silhouette at the pipeline's own measured "
                "Rp/R\u2605 \u2014 the image is the measurement."
            )

        st.subheader("Model comparison")
        if pinn:
            st.metric(
                "PINN Rp / R\u2605", f"{pinn['rp_over_rstar']:.4f}",
                delta=(f"{pinn['rp_over_rstar'] - bls['rp_over_rstar']:+.4f}"
                       if bls else None),
            )
        else:
            st.info(
                "PINN predictions land here in Phase 4 \u2014 same "
                "results table, method='pinn' \u2014 and will be compared "
                "directly against the classical BLS baseline above."
            )

    with st.expander("ETL before / after (Phase 2 detrending)"):
        st.pyplot(plots.plot_raw_vs_flat(
            data["raw_time"], data["raw_flux"], data["time"], data["flux"],
        ))

# ======================================================================
# Compare view
# ======================================================================
else:
    default_sel = targets[: min(3, len(targets))]
    sel = st.sidebar.multiselect("Choose targets to compare", targets,
                                 default=default_sel)

    st.title("Target comparison")
    if not sel:
        st.info("Pick one or more targets in the sidebar.")
        st.stop()

    loaded = [d for d in (storage.load_target(t) for t in sel)
              if d is not None]

    rows = []
    for d in loaded:
        b = d["results"].get("bls") or {}
        rows.append({
            "Target": d["target_id"],
            "Class": plots.spectral_class(d["teff"]),
            "Teff (K)": (None if d["teff"] is None
                         else int(round(d["teff"]))),
            "R\u2605 (R\u2609)": (None if d["stellar_radius"] is None
                                  else round(d["stellar_radius"], 2)),
            "Period (d)": (None if b.get("period_days") is None
                           else round(b["period_days"], 4)),
            "Depth (%)": (None if b.get("depth") is None
                          else round(100 * b["depth"], 3)),
            "Rp/R\u2605": (None if b.get("rp_over_rstar") is None
                           else round(b["rp_over_rstar"], 4)),
            "Duration (h)": (None if b.get("duration_days") is None
                             else round(24 * b["duration_days"], 2)),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True,
                 hide_index=True)

    st.subheader("Host stars (simulated, sizes to relative scale)")
    radii = [d["stellar_radius"] if d["stellar_radius"] else 1.0
             for d in loaded]
    rmax = max(radii)
    cols = st.columns(len(loaded))
    for col, d, r in zip(cols, loaded, radii):
        scale = max(0.25, r / rmax)
        col.pyplot(plots.render_star(
            d["teff"], d["stellar_radius"],
            name=d["target_id"], scale=scale,
        ))

    entries = [
        {
            "label": d["target_id"],
            "time": d["time"], "flux": d["flux"],
            "period": b["period_days"], "t0": b["t0"],
            "duration": b["duration_days"],
        }
        for d in loaded
        if (b := d["results"].get("bls"))
    ]
    if len(entries) >= 2:
        st.subheader("Folded transit comparison")
        st.pyplot(plots.plot_folded_comparison(entries))
        st.caption(
            "Binned median transit profile for each star, folded at its "
            "own detected period. Depth differences are direct Rp/R\u2605 "
            "differences."
        )
