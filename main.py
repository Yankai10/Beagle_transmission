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

    # Pacing parameters to match hardware sample rate
    chunk_bytes = 1048576      # 1 MiB per read
    sample_rate = 48e6         # 48 MB/s ADC throughput
    interval = chunk_bytes / sample_rate  # Time to produce 1 MiB (~0.0218 s)

    try:
        while True:
            # Exit when duration elapsed
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break

            # Read 1 MiB and measure time
            t0 = time.perf_counter()
            data = sensor.raw(1.625e9, 1)
            t1 = time.perf_counter()

            total_bytes += len(data)
            capture_count += 1

            # Sleep to avoid reading faster than hardware writes
            elapsed = t1 - t0
            to_sleep = interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

    except KeyboardInterrupt:
        print("Interrupted by user.")

    # Final statistics
    elapsed_total = time.time() - start_time
    mbps = total_bytes / elapsed_total / 1e6
    print(f"Finished data capture: {capture_count} chunks, "
          f"{total_bytes} bytes in {elapsed_total:.2f}s → {mbps:.1f} MB/s")

    sensor.close()


if __name__ == "__main__":
    main()

