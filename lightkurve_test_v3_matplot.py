import numpy as np
import lightkurve as lk
import matplotlib.pyplot as plt

def fetch_light_curve_data(target_id: str):
    """Phase 1: Ingestion"""
    search_result = lk.search_lightcurve(target_id, mission="Kepler")
    if len(search_result) == 0:
        return None, None
    lc_file = search_result[0].download()
    return lc_file.time.value, lc_file.flux.value

def clean_and_normalize_data(raw_time, raw_flux):
    """Phase 2: Cleaning & Transformation"""
    nan_mask = ~np.isnan(raw_time) & ~np.isnan(raw_flux)
    clean_time = raw_time[nan_mask]
    clean_flux = raw_flux[nan_mask]
    
    flux_median = np.median(clean_flux)
    normalized_flux = clean_flux / flux_median
    return clean_time, normalized_flux


def plot_light_curve(time, flux, target_id: str):
    """
    Phase 2 Validation: Visual Verification
    Plots the normalized flux over time to expose planetary transits.
    """
    print("\nGenerating data visualization...")
    plt.figure(figsize=(12, 5))
    
    # Plot using small, clean markers to see individual observations clearly
    plt.plot(time, flux, 'k.', markersize=1, alpha=0.6)
    
    plt.title(f"Normalized Kepler Light Curve - {target_id}")
    plt.xlabel("Time (Kepler Barycentric Julian Date)")
    plt.ylabel("Normalized Flux (Relative Brightness)")
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Constrain the y-axis slightly so random outlier spikes 
    # don't crush our view of the 1.0 baseline
    plt.ylim(0.98, 1.02) 
    
    print("Displaying plot window...")
    plt.show()


if __name__ == "__main__":
    TARGET_KIC = "Kepler-8"
    
    # Run the pipeline layers
    raw_time, raw_flux = fetch_light_curve_data(TARGET_KIC)
    
    if raw_time is not None:
        clean_time, clean_flux = clean_and_normalize_data(raw_time, raw_flux)
        
        # Validate the pipeline output visually
        plot_light_curve(clean_time, clean_flux, TARGET_KIC)