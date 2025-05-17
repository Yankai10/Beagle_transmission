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
        description="RadioHound raw capture + MQTT sender"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="扫描持续时间（秒），默认无限"
    )
    args = parser.parse_args()

    # 实例化传感器
    sensor = RadioHoundSensorV3()

    # 初始化并连接 MQTT
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)

    print("Starting raw capture…")
    start_time   = time.time()
    total_bytes  = 0
    chunk_count  = 0

    # 控速参数：1 MiB / 48 MiB/s ≈ 0.0218 s
    chunk_bytes = 1 * 1024 * 1024
    sample_rate = 48e6
    interval    = chunk_bytes / sample_rate

    try:
        while True:
            # 持续时长到达则退出
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break

            t0 = time.perf_counter()
            data = sensor.raw(1.625e9, 1)
            t1 = time.perf_counter()

            if not data:
                continue

            # 累加统计
            total_bytes += len(data)
            chunk_count += 1

            # —— 类型转换：memoryview → bytes/bytearray
            if isinstance(data, memoryview):
                payload = data.tobytes()
            elif isinstance(data, bytes):
                payload = data
            else:
                # 保险起见：其他可缓冲类型
                payload = bytearray(data)

            # 发布到 MQTT
            client.publish(TOPIC, payload, qos=0)

            # 简单限速，避免推过快
            elapsed = t1 - t0
            to_sleep = interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    # 打印最终速率
    elapsed_total = time.time() - start_time
    mbps = total_bytes / elapsed_total / 1e6
    print(
        f"Finished: {chunk_count} chunks, "
        f"{total_bytes} bytes in {elapsed_total:.2f}s → {mbps:.1f} MB/s"
    )

    # 清理
    sensor.close()
    client.disconnect()

if __name__ == "__main__":
    main()
