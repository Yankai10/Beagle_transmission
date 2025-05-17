# import time
# import argparse
# from datetime import datetime
# from receiver import RadioHoundSensorV3


# def main():
#     parser = argparse.ArgumentParser(description="RadioHound raw capture counter")
#     parser.add_argument(
#         "--duration",
#         type=float,
#         default=None,
#         help="Scanning time in seconds; infinite by default"
#     )
#     args = parser.parse_args()

#     sensor = RadioHoundSensorV3()
#     print("Starting raw capture…")
#     start_time = time.time()
#     total_bytes = 0
#     capture_count = 0

#     # Pacing parameters to match hardware sample rate
#     chunk_bytes = 1048576      # 1 MiB per read
#     sample_rate = 48e6         # 48 MB/s ADC throughput
#     interval = chunk_bytes / sample_rate  # Time to produce 1 MiB (~0.0218 s)

#     try:
#         while True:
#             # Exit when duration elapsed
#             if args.duration is not None and (time.time() - start_time) >= args.duration:
#                 break

#             # Read 1 MiB and measure time
#             t0 = time.perf_counter()
#             data = sensor.raw(1.625e9, 1)
#             t1 = time.perf_counter()

#             total_bytes += len(data)
#             capture_count += 1

#             # Sleep to avoid reading faster than hardware writes
#             elapsed = t1 - t0
#             to_sleep = interval - elapsed
#             if to_sleep > 0:
#                 time.sleep(to_sleep)

#     except KeyboardInterrupt:
#         print("Interrupted by user.")

#     # Final statistics
#     elapsed_total = time.time() - start_time
#     mbps = total_bytes / elapsed_total / 1e6
#     print(f"Finished data capture: {capture_count} chunks, "
#           f"{total_bytes} bytes in {elapsed_total:.2f}s → {mbps:.1f} MB/s")

#     sensor.close()


# if __name__ == "__main__":
#     main()



#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import argparse
import os
from receiver import RadioHoundSensorV3
import paho.mqtt.client as mqtt

# ─── MQTT 配置 ────────────────────────────────────────────────────────────
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TOPIC       = "radiohound/raw"

def main():
    parser = argparse.ArgumentParser(
        description="RadioHound raw capture + MQTT sender (no sleep)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="扫描持续时间（秒），默认无限"
    )
    args = parser.parse_args()

    sensor = RadioHoundSensorV3()

    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)

    print("Starting raw capture (no pacing)…")
    start_time   = time.time()
    total_bytes  = 0
    chunk_count  = 0

    try:
        while True:
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break

            data = sensor.raw(1.625e9, 1)
            if not data:
                continue

            # 累加统计
            total_bytes += len(data)
            chunk_count += 1

            # payload 转 bytes
            if isinstance(data, memoryview):
                payload = data.tobytes()
            elif isinstance(data, bytes):
                payload = data
            else:
                payload = bytearray(data)

            # 直接发布，不做任何 sleep
            client.publish(TOPIC, payload, qos=0)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    # 最终统计
    elapsed_total = time.time() - start_time
    mbps = total_bytes / elapsed_total / 1e6 if elapsed_total > 0 else 0
    print(
        f"Finished: {chunk_count} chunks, "
        f"{total_bytes} bytes in {elapsed_total:.2f}s → {mbps:.1f} MB/s"
    )

    sensor.close()
    client.disconnect()

if __name__ == "__main__":
    main()

