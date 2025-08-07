"""
Script to perform a series of DC voltage measurements using a Fluke 5522A
calibrator and a Fluke 8508A reference multimeter.  The calibrator
produces ten equally spaced voltage setpoints and the multimeter takes
five readings at each point.  The mean and standard deviation of the
readings are saved to a CSV file.

Prerequisites: both instruments must be connected via GPIB and the
corresponding instrument classes (Fluke5522A and Fluke8508A) must
already be available in ``instruments.fluke5522a`` and
``instruments.fluke8508a`` respectively.
"""

import time
import numpy as np
import pandas as pd

from instruments.fluke5522a import Fluke5522A
from instruments.fluke8508a import Fluke8508A


def main() -> None:
    """Run the measurement loop and save results to a CSV file."""
    # Instantiate the instruments
    calibrator = Fluke5522A("GPIB::5")
    print("Calibrator ID:", calibrator.id)
    multimeter = Fluke8508A("GPIB::19")
    print("Multimeter ID:", multimeter.id)

    # Configure the multimeter for DC voltage measurements
    multimeter.function_ = "DCV"
    multimeter.autorange = True
    multimeter.resolution = 5  # 8.5‑digit resolution
    multimeter.fast_enabled = True
    multimeter.filter_enabled = False
    multimeter.adapter.connection.timeout=10000

    # Define ten equally spaced voltage setpoints from –5 V to +5 V
    num_points = 10
    setpoints = np.linspace(-5.0, 5.0, num=num_points)
    means: list[float] = []
    stds: list[float] = []

    # Loop over each setpoint
    for v in setpoints:
        print(f"\nSetting calibrator output to {v:.3f} V")
        # Prepare calibrator, set the voltage and enable output
        calibrator.standby()
        calibrator.output_voltage(v)
        calibrator.operate()
        # Allow time for the calibrator to settle
        time.sleep(2.0)

        # Acquire five readings at this setpoint
        readings: list[float] = []
        for i in range(5):
            value = multimeter.reading
            print(f"  Reading {i+1}: {value:.9f} V")
            readings.append(value)
            # Wait briefly between readings
            time.sleep(1.0)

        # Compute statistics and store them
        mean_val = float(np.mean(readings))
        std_val = float(np.std(readings, ddof=1))
        print(f"  Mean: {mean_val:.9f} V, Std: {std_val:.9f} V")
        means.append(mean_val)
        stds.append(std_val)

        # Return calibrator to standby before moving to the next point
        calibrator.standby()
        time.sleep(1.0)

    # Save results to CSV
    df = pd.DataFrame({
        'Set Voltage (V)': setpoints,
        'Measured Voltage Mean (V)': means,
        'Measured Voltage Std (V)': stds,
    })
    output_file = 'dc_voltage_measurements.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")

    # Ensure calibrator output is disabled before exiting
    calibrator.standby()


if __name__ == '__main__':
    main()