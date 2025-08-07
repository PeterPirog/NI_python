# test_measure_voltage.py

from instruments.fluke8508a import Fluke8508A
import time

dmm = Fluke8508A("GPIB::19")
dmm.function_ = "DCV"  # Select DC voltage function
dmm.autorange = True  # Use autoranging
dmm.resolution = 8  # 8.5‑digit resolution
dmm.fast_enabled = True  # Enable fast mode
print(dmm.reading)  # Take a single measurement
