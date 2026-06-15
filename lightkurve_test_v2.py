import numpy as np
import lightkurve as lk

def fetch_light_curve_data(target_id: str):
    """Phase 1: Ingestion (Already working!)"""
    search_result = lk.search_lightcurve(target_id, mission="Kepler")
    if len(search_result) == 0:
        return None, None
    lc_file = search_result[0].download()
    return lc_file.time.value, lc_file.flux.value


def clean_and_normalize_data(raw_time, raw_flux):
    """
    Phase 2: Data Cleaning & Transformation (ETL)
    """
    print("\nStarting data cleaning layer...")
    
    # 1. Handle Missing Data (Remove NaN values)
    # create a mask that is True only where BOTH time and flux are valid numbers
    nan_mask = ~np.isnan(raw_time) & ~np.isnan(raw_flux)
    
    clean_time = raw_time[nan_mask]
    clean_flux = raw_flux[nan_mask]
    
    points_removed = len(raw_flux) - len(clean_flux)
    print(f"-> Removed {points_removed} invalid (NaN) data points.")
    
    # 2. Normalization
    # Divide by the median brightness so the star's baseline sits at 1.0
    flux_median = np.median(clean_flux)
    normalized_flux = clean_flux / flux_median
    
    return clean_time, normalized_flux


if __name__ == "__main__":
    TARGET_KIC = "Kepler-8"
    
    # Execute Phase 1
    raw_time, raw_flux = fetch_light_curve_data(TARGET_KIC)
    
    if raw_time is not None:
        # Execute Phase 2
        clean_time, clean_flux = clean_and_normalize_data(raw_time, raw_flux)
        
        print("\n--- Cleaning Complete ---")
        print(f"Cleaned Flux baseline (Median): {np.median(clean_flux)}")
        print(f"First 5 cleaned flux values:    {clean_flux[:5]}")