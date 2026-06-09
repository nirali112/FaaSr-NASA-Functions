import requests
from FaaSr_py.client.py_client_stubs import faasr_log, faasr_put_file

# NASA POWER uses this sentinel value for missing/unprocessed days
NASA_FILL_VALUE = -999.0


def build_url(lat: str, lon: str, start: str, end: str) -> str:
    """
    Build the URL for the NASA POWER daily point endpoint.

    NASA POWER provides satellite-derived daily climate data for any
    coordinate worldwide. No API key or signup is required.

    Args:
        lat: The latitude coordinate.
        lon: The longitude coordinate.
        start: Start date in YYYYMMDD format (e.g., "20150101").
        end: End date in YYYYMMDD format (e.g., "20260515").

    Returns:
        The URL to download daily precipitation, minimum temperature, and
        maximum temperature data from, using the Agroclimatology community.
    """
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    return (
        f"{base_url}?parameters=PRECTOTCORR,T2M_MIN,T2M_MAX&community=AG"
        f"&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON"
    )


def download_data(url: str) -> dict:
    """
    Download data from the NASA POWER API and return the parsed JSON.

    Args:
        url: The URL to download the data from.

    Returns:
        The NASA POWER API response as a dictionary.
    """
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        faasr_log(f"Error downloading data from {url}: {e}")
        raise e


def convert_to_csv(nasa_data: dict, output_name: str) -> int:
    """
    Convert the NASA POWER JSON response to a GHCND-style CSV file.

    The NASA POWER API returns each parameter as a {date: value} map under
    properties.parameter. This function pivots them into rows of
    DATE,PRECTOTCORR,T2M_MIN,T2M_MAX with ISO dates (YYYY-MM-DD), so the
    downstream processing matches the WeatherVisualization workflow.
    Fill values (-999.0, meaning the satellite product is not yet available
    for that day) are written as empty cells.

    Args:
        nasa_data: The NASA POWER API response.
        output_name: The name of the CSV file to write.

    Returns:
        The number of data rows written.
    """
    parameters = nasa_data.get("properties", {}).get("parameter", {})
    fill_value = nasa_data.get("header", {}).get("fill_value", NASA_FILL_VALUE)

    precip = parameters.get("PRECTOTCORR", {})
    t_min = parameters.get("T2M_MIN", {})
    t_max = parameters.get("T2M_MAX", {})

    def fmt(value) -> str:
        if value is None or value == fill_value:
            return ""
        return str(value)

    num_rows = 0
    with open(output_name, "w") as f:
        f.write("DATE,PRECTOTCORR,T2M_MIN,T2M_MAX\n")
        for date_key in sorted(precip.keys()):
            iso_date = f"{date_key[0:4]}-{date_key[4:6]}-{date_key[6:8]}"
            row = (
                f"{iso_date},{fmt(precip.get(date_key))},"
                f"{fmt(t_min.get(date_key))},{fmt(t_max.get(date_key))}\n"
            )
            f.write(row)
            num_rows += 1

    return num_rows


def get_nasa_power_data(
    folder_name: str,
    output_name: str,
    lat: str,
    lon: str,
    start: str,
    end: str,
    location_name: str,
):
    """
    Download daily climate data (precipitation, min/max temperature) from the
    NASA POWER API for a coordinate, convert it to CSV, and upload it to an
    S3 bucket.

    Args:
        folder_name: The name of the folder to upload the data to.
        output_name: The name of the CSV file to upload the data to.
        lat: The latitude coordinate.
        lon: The longitude coordinate.
        start: Start date in YYYYMMDD format.
        end: End date in YYYYMMDD format.
        location_name: A descriptive name for the location (for logging).
    """

    # 1. Build the URL - note: no API key required
    url = build_url(lat, lon, start, end)
    faasr_log(
        f"Downloading NASA POWER data for {location_name} "
        f"(lat={lat}, lon={lon}, {start}-{end})"
    )

    # 2. Download the data and convert to CSV
    nasa_data = download_data(url)
    num_rows = convert_to_csv(nasa_data, output_name)
    faasr_log(f"Converted {num_rows} days of NASA POWER data to CSV")

    # 3. Upload the file to the S3 bucket
    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )

    faasr_log(f"Uploaded data to {folder_name}/{output_name}")
