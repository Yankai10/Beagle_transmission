import time
import argparse
from datetime import datetime
from receiver import RadioHoundSensorV3

def main():
    parser = argparse.ArgumentParser(description="RadioHound raw capture counter")
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Scanning time in seconds; infinite by default"
    )
    args = parser.parse_args()

    sensor = RadioHoundSensorV3()
    print("Starting raw capture…")
    start_time = time.time()
    total_bytes = 0
    capture_count = 0

    try:
        while True:
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break

            data = sensor.raw(1.625e9, 1)  # 1 second at 1.625 GHz center, unit=1?
            total_bytes += len(data)
            capture_count += 1

    except KeyboardInterrupt:
        print("Interrupted by user.")

    elapsed = time.time() - start_time
    mbps = total_bytes / elapsed / 1e6

    print(f"Finished data capture: {capture_count} chunks, "
          f"{total_bytes} bytes in {elapsed:.2f}s → {mbps:.1f} MB/s")

    sensor.close()

if __name__ == "__main__":
    main()
