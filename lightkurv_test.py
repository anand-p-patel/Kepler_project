import lightkurve as lk

def fetch_light_curve_data(target_id: str):
    """
    Phase 1: Data Ingestion
    Connects to the MAST archive and downloads light curve data.
    """
    print(f"Searching for target: {target_id}...")
    
    # 1. Search for available light curve files for the target star
    search_result = lk.search_lightcurve(target_id, mission="Kepler")
    
    # For our simple MVP, let's just grab the first available quarter of data
    if len(search_result) == 0:
        print(f"Error: No data found for {target_id}")
        return None
        
    print(f"Found {len(search_result)} data segments. Downloading the first one...")
    
    # 2. Download the data file (downloads a FITS file behind the scenes)
    lc_file = search_result[0].download()
    
    # 3. Extract the core mathematical arrays: Time and Flux
    # We use .value to get clean NumPy arrays out of the specialized AstroPy objects
    time_array = lc_file.time.value
    flux_array = lc_file.flux.value
    
    return time_array, flux_array

# --- Quick Test ---
if __name__ == "__main__":
    # Let's test it with Kepler-8, a star known to have a massive gas giant planet
    time, flux = fetch_light_curve_data("Kepler-8")
    
    if time is not None:
        print("\n--- Download Successful ---")
        print(f"Time array shape (number of data points): {time.shape}")
        print(f"Flux array shape (brightness readings):  {flux.shape}")
        print(f"First 5 timestamps: {time[:5]}")
        print(f"First 5 flux measurements: {flux[:5]}")