import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_log, faasr_put_file
from matplotlib.axes import Axes


def get_input_data(
    folder_name: str,
    input_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Get the input data from the FaaSr bucket and return it as a pandas DataFrame.

    Args:
        folder_name: The name of the folder to get the input data from.
        input_name: The name of the input file to get the data from.

    Returns:
        A tuple containing the current year data and the previous years data.
    """
    faasr_get_file(
        local_file=f"current_year_{input_name}",
        remote_folder=folder_name,
        remote_file=f"current_year_{input_name}",
    )

    faasr_get_file(
        local_file=f"previous_years_{input_name}",
        remote_folder=folder_name,
        remote_file=f"previous_years_{input_name}",
    )

    current_year_data = pd.read_csv(f"current_year_{input_name}")
    previous_years_data = pd.read_csv(f"previous_years_{input_name}")

    return current_year_data, previous_years_data


def prepare_data(
    current_year_precip: pd.DataFrame,
    current_year_min_temp: pd.DataFrame,
    current_year_max_temp: pd.DataFrame,
    prev_years_precip: pd.DataFrame,
    prev_years_min_temp: pd.DataFrame,
    prev_years_max_temp: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare the data for plotting.

    Unlike GHCND station data, NASA POWER values are already in physical
    units (mm/day for precipitation, degrees Celsius for temperature), so no
    unit conversion is needed here.

    Args:
        current_year_precip: The current year precipitation data.
        current_year_min_temp: The current year minimum temperature data.
        current_year_max_temp: The current year maximum temperature data.
        prev_years_precip: The previous years precipitation data.
        prev_years_min_temp: The previous years minimum temperature data.
        prev_years_max_temp: The previous years maximum temperature data.

    Returns:
        A tuple containing the current year data and the previous years data.
    """

    # Merge the dataframes on the DAY column
    current_year = current_year_precip.merge(current_year_min_temp, on="DAY")
    current_year = current_year.merge(current_year_max_temp, on="DAY")
    prev_years = prev_years_precip.merge(prev_years_min_temp, on="DAY")
    prev_years = prev_years.merge(prev_years_max_temp, on="DAY")

    # Drop leap days
    current_year = current_year[current_year["DAY"] != "02-29"]
    prev_years = prev_years[prev_years["DAY"] != "02-29"]

    return current_year, prev_years


def plot_subplot(
    ax: Axes,
    x_data: pd.Series,
    y_data: pd.Series,
    prev_years_x_data: pd.Series,
    prev_years_y_data: pd.Series,
    title: str,
    ylabel: str,
) -> None:
    """
    Plot a subplot with the given data. Current year data is plotted with 100% opacity
    and previous years data is plotted with 30% opacity.

    Args:
        ax: The axes to plot the data on.
        x_data: The x-axis data.
        y_data: The y-axis data.
        prev_years_x_data: The x-axis data for the previous years.
        prev_years_y_data: The y-axis data for the previous years.
        title: The title of the subplot.
        ylabel: The label for the y-axis.
    """
    # Create the plot for the current year
    ax.plot(
        x_data,
        y_data,
        alpha=1.0,
        label="This year",
        linewidth=2,
    )

    # Create the plot for the previous years
    ax.plot(
        prev_years_x_data,
        prev_years_y_data,
        alpha=0.3,
        label="Last 10 years",
        linewidth=2,
        linestyle="--",
    )

    # Set the title and y-axis label
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Set the x-axis ticks to every 7th day
    tick_positions = prev_years_x_data[::7]
    ax.set_xticks(tick_positions)
    ax.tick_params(axis="x", rotation=45)


def plot_weather_comparison(
    folder_name: str,
    input_precip_name: str,
    input_min_temp_name: str,
    input_max_temp_name: str,
    location: str,
    output_name: str,
):
    """
    Create a combined plot with three subplots: precipitation, min temp, and max temp.

    Args:
        folder_name: The name of the folder to get the input data from.
        input_precip_name: The name of the input file to get the precipitation data from.
        input_min_temp_name: The name of the input file to get the minimum temperature data from.
        input_max_temp_name: The name of the input file to get the maximum temperature data from.
        location: The location of the weather data.
        output_name: The name of the output file to save the plot to.
    """

    # 1. Get the input data
    current_year_precip, prev_years_precip = get_input_data(
        folder_name,
        input_precip_name,
    )

    faasr_log(f"Loaded precipitation data from {folder_name}/{input_precip_name}")

    current_year_min_temp, prev_years_min_temp = get_input_data(
        folder_name,
        input_min_temp_name,
    )

    faasr_log(
        f"Loaded minimum temperature data from {folder_name}/{input_min_temp_name}"
    )

    current_year_max_temp, prev_years_max_temp = get_input_data(
        folder_name,
        input_max_temp_name,
    )

    faasr_log(
        f"Loaded maximum temperature data from {folder_name}/{input_max_temp_name}"
    )

    # 2. Prepare the data for plotting
    current_year, prev_years = prepare_data(
        current_year_precip,
        current_year_min_temp,
        current_year_max_temp,
        prev_years_precip,
        prev_years_min_temp,
        prev_years_max_temp,
    )

    faasr_log("Prepared data for plotting")

    # 3. Create the plot with three subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 14))
    fig.suptitle(
        f"NASA POWER Daily Climate Data for {location}\n"
        "(satellite-derived, this year vs. last 10 years)",
        fontsize=16,
        fontweight="bold",
    )

    plot_subplot(
        axes[0],
        current_year["DAY"],
        current_year["PRECTOTCORR"],
        prev_years["DAY"],
        prev_years["PRECTOTCORR"],
        "Precipitation (corrected)",
        "Precipitation (mm/day)",
    )

    plot_subplot(
        axes[1],
        current_year["DAY"],
        current_year["T2M_MIN"],
        prev_years["DAY"],
        prev_years["T2M_MIN"],
        "Minimum Temperature at 2m",
        "Temperature (\u00b0C)",
    )

    plot_subplot(
        axes[2],
        current_year["DAY"],
        current_year["T2M_MAX"],
        prev_years["DAY"],
        prev_years["T2M_MAX"],
        "Maximum Temperature at 2m",
        "Temperature (\u00b0C)",
    )

    plt.tight_layout()
    plt.savefig(output_name, dpi=150, bbox_inches="tight")
    plt.close()

    faasr_log("Created weather comparison plot")

    # 4. Upload the plot to the S3 bucket
    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )

    faasr_log(f"Uploaded plot to {folder_name}/{output_name}")
