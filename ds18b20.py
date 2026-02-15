#!/usr/bin/env python3
"""DS18B20 temperature sensor reader via 1-Wire kernel interface on BCM GPIO 17 (physical pin 11)."""

import glob
import os
import subprocess
import sys
import time

W1_DEVICES_PATH = "/sys/bus/w1/devices/"
DS18B20_PREFIX = "28-"
GPIO_PIN = 17  # Physical pin 11 = BCM GPIO 17


def setup_kernel_modules():
    """Load w1-gpio and w1-therm kernel modules and enable the dtoverlay."""
    try:
        subprocess.run(
            ["sudo", "dtoverlay", "w1-gpio", f"gpiopin={GPIO_PIN}"],
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Warning: dtoverlay command failed. Ensure w1-gpio overlay is enabled in /boot/config.txt:")
        print(f"  dtoverlay=w1-gpio,gpiopin={GPIO_PIN}")

    for module in ("w1-gpio", "w1-therm"):
        subprocess.run(["sudo", "modprobe", module], check=True)

    # Give the kernel a moment to discover devices
    time.sleep(1)


def find_sensor():
    """Find the first DS18B20 device directory."""
    devices = glob.glob(os.path.join(W1_DEVICES_PATH, DS18B20_PREFIX + "*"))
    if not devices:
        return None
    return devices[0]


def read_temperature(device_path):
    """Read temperature in Celsius from the sensor's sysfs file.

    Returns the temperature as a float, or None on read failure.
    """
    slave_file = os.path.join(device_path, "w1_slave")
    with open(slave_file, "r") as f:
        lines = f.readlines()

    # First line ends with YES if the CRC check passed
    if len(lines) < 2 or "YES" not in lines[0]:
        return None

    # Second line contains t=<millidegrees>
    idx = lines[1].find("t=")
    if idx == -1:
        return None

    raw = int(lines[1][idx + 2:])
    return raw / 1000.0


def main():
    print(f"Setting up 1-Wire on BCM GPIO {GPIO_PIN}...")
    setup_kernel_modules()

    sensor = find_sensor()
    if sensor is None:
        print("No DS18B20 sensor found. Check wiring and ensure the data pin is on physical pin 11 (BCM 17) with a 4.7kΩ pull-up resistor.")
        sys.exit(1)

    sensor_id = os.path.basename(sensor)
    print(f"Found sensor: {sensor_id}")

    try:
        while True:
            temp = read_temperature(sensor)
            if temp is not None:
                print(f"{temp:.1f} °C  /  {temp * 9 / 5 + 32:.1f} °F")
            else:
                print("CRC error, retrying...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
