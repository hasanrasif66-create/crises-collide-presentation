"""
========================================================================
ERA5-LAND VIDEO DEMO — "paste the key, get a country's climate panel"
========================================================================
Built for a 60-second screen recording of the data-retrieval pipeline.

WHAT THE VIDEO SHOWS (suggested shots):
  1. Browser: https://cds.climate.copernicus.eu -> sign in -> copy your
     Personal Access Token from your profile page.
     (While you are there: open the dataset page
      "ERA5-Land monthly averaged data from 1950 to present" and click
      "Accept terms" once — required before the API will serve data.)
  2. This notebook: paste the token below, run all cells.
  3. Watch the request go to Copernicus, the NetCDF download start
     automatically, and a clean CSV appear at the end.

RUNS IN GOOGLE COLAB (recommended for the video) OR LOCALLY.
Only change you MUST make: paste your key in the CONFIG block.
"""

# ---------------------------------------------------------------------
# CELL 1 — install (Colab). Locally: pip install cdsapi xarray netCDF4 pandas
# ---------------------------------------------------------------------
# !pip install -q cdsapi xarray netCDF4 pandas

# ---------------------------------------------------------------------
# CELL 2 — CONFIG: paste your CDS Personal Access Token here
# ---------------------------------------------------------------------
CDS_API_KEY = "PASTE_YOUR_CDS_API_KEY_HERE"   # <-- the ONLY edit you need

COUNTRY = "random"   # "random" or pin one, e.g. "Bangladesh"
START_YEAR, END_YEAR = 2015, 2024   # 10 years downloads fast on camera.
                                    # Use 1998–2026 to rebuild the paper's full panel.

# ---------------------------------------------------------------------
# A small atlas of country bounding boxes: [North, West, South, East]
# ---------------------------------------------------------------------
BBOX = {
    "Bangladesh": [26.63, 88.01, 20.74, 92.67],
    "India":      [35.50, 68.10,  6.70, 97.40],
    "Pakistan":   [37.10, 60.90, 23.70, 77.80],
    "Sri Lanka":  [ 9.90, 79.60,  5.90, 81.90],
    "Nepal":      [30.40, 80.00, 26.40, 88.20],
    "Brazil":     [ 5.30,-73.90,-33.70,-34.80],
    "Kenya":      [ 5.00, 33.90, -4.70, 41.90],
    "Nigeria":    [13.90,  2.70,  4.30, 14.70],
    "Egypt":      [31.70, 24.70, 22.00, 36.90],
    "Indonesia":  [ 6.10, 95.00,-11.00,141.00],
    "Turkey":     [42.10, 25.70, 35.80, 44.80],
    "Argentina":  [-21.80,-73.60,-55.10,-53.60],
}

import os, random
import numpy as np
import pandas as pd
import xarray as xr

def pick_country(choice):
    if choice == "random":
        choice = random.choice(list(BBOX))
    if choice not in BBOX:
        raise ValueError(f"Unknown country '{choice}'. Options: {list(BBOX)}")
    return choice

def write_cdsrc(key):
    """Write ~/.cdsapirc so the cdsapi client can authenticate."""
    with open(os.path.expanduser("~/.cdsapirc"), "w") as f:
        f.write("url: https://cds.climate.copernicus.eu/api\n")
        f.write(f"key: {key}\n")
    print("✓ CDS credentials configured.")

def download_era5_land(country, bbox, years, out_nc):
    """Request monthly ERA5-Land fields; the .nc downloads automatically."""
    import cdsapi
    c = cdsapi.Client()
    print(f"→ Requesting ERA5-Land monthly means for {country} {years[0]}–{years[1]} …")
    print("  (the server queues the request, then the file downloads automatically)")
    c.retrieve(
        "reanalysis-era5-land-monthly-means",
        {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["2m_temperature", "total_precipitation",
                         "volumetric_soil_water_layer_1"],
            "year":  [str(y) for y in range(years[0], years[1] + 1)],
            "month": [f"{m:02d}" for m in range(1, 13)],
            "time":  ["00:00"],
            "area":  bbox,                 # [North, West, South, East]
            "data_format": "netcdf",
        },
        out_nc,
    )
    print(f"✓ Download finished: {out_nc}")

def grid_to_csv(nc_path, csv_path):
    """Collapse the lat–lon grid to one national mean per month; fix units."""
    ds = xr.open_dataset(nc_path)
    tkey = "valid_time" if "valid_time" in ds.coords else "time"
    flat = ds.mean(dim=["latitude", "longitude"]).to_dataframe().reset_index()
    df = pd.DataFrame({"date": pd.to_datetime(flat[tkey])})
    df["temp_c"] = flat["t2m"] - 273.15                          # Kelvin → °C
    df["precip_mm"] = flat["tp"] * 1000 * df["date"].dt.days_in_month  # m/day → mm/month
    df["soil_moisture_m3m3"] = flat["swvl1"]
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.to_csv(csv_path, index=False)
    return df

# ---------------------------------------------------------------------
# CELL 3 — run the pipeline
# ---------------------------------------------------------------------
if __name__ == "__main__" or True:      # 'or True' so it also runs as a Colab cell
    assert "PASTE_" not in CDS_API_KEY, "Please paste your CDS API key in the CONFIG block."

    country = pick_country(COUNTRY)
    print(f"🎲 Country selected: {country}  bbox={BBOX[country]}")

    nc_file  = f"{country.lower().replace(' ', '_')}_era5land_raw.nc"
    csv_file = f"{country.lower().replace(' ', '_')}_climate_panel.csv"

    write_cdsrc(CDS_API_KEY)
    download_era5_land(country, BBOX[country], (START_YEAR, END_YEAR), nc_file)
    panel = grid_to_csv(nc_file, csv_file)

    print(f"\n✓ Clean panel written: {csv_file}  ({len(panel)} monthly rows)\n")
    print(panel.head(12).to_string(index=False))     # the on-camera 'glimpse'

    # In Colab this triggers the browser download automatically:
    try:
        from google.colab import files  # type: ignore
        files.download(csv_file)
    except Exception:
        print(f"\n(Local run — your file is at ./{csv_file})")
