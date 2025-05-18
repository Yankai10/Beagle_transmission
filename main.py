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
            # Exit when duration elapsed
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break

            # Read 1 MiB without pacing delay for max throughput
            data = sensor.raw(1.625e9, 1)
            total_bytes += len(data)
            capture_count += 1

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


# import os
# import time
# import argparse
# from datetime import datetime
# from receiver import RadioHoundSensorV3

# def main():
#     parser = argparse.ArgumentParser(description="RadioHound max-throughput USB write test")
#     parser.add_argument(
#         "--duration",
#         type=float,
#         default=None,
#         help="Scanning time in seconds; infinite by default"
#     )
#     parser.add_argument(
#         "--out",
#         type=str,
#         default="/mnt/usb/raw_capture.bin",
#         help="Path to USB-mounted output file"
#     )
#     args = parser.parse_args()

#     sensor = RadioHoundSensorV3()
#     print("Starting raw capture…", datetime.now().isoformat())

#     # 打开 USB 
#     f = open(args.out, "wb", buffering=0)
#     write_func = f.write

#     start_time = time.time()
#     total_bytes   = 0
#     capture_count = 0

#     # 用于统计读和写耗时
#     read_time  = 0.0
#     write_time = 0.0

#     try:
#         while True:
#             if args.duration is not None and (time.time() - start_time) >= args.duration:
#                 break

#             # —— 1）读样本 —— 
#             t0 = time.perf_counter()
#             data = sensor.raw(1.625e9, 1)
#             t1 = time.perf_counter()
#             read_time += (t1 - t0)

#             # —— 2）写入 USB —— 
#             w0 = time.perf_counter()
#             write_func(data)
#             w1 = time.perf_counter()
#             write_time += (w1 - w0)

#             # 统计总量
#             total_bytes   += len(data)
#             capture_count += 1

#     except KeyboardInterrupt:
#         print("Interrupted by user.")

#     finally:
#         f.close()
#         sensor.close()

#     # —— 结果输出 —— 
#     elapsed_total = time.time() - start_time
#     total_mbps    = total_bytes / elapsed_total / 1e6 if elapsed_total > 0 else 0
#     read_mbps     = total_bytes / read_time      / 1e6 if read_time  > 0 else 0
#     write_mbps    = total_bytes / write_time     / 1e6 if write_time > 0 else 0

#     print("\n==== Throughput Results ====")
#     print(f"Total loop rate : {total_mbps:5.1f} MB/s "
#           f"({capture_count} chunks, {total_bytes} bytes in {elapsed_total:.2f}s)")
#     print(f"Read-only rate : {read_mbps:5.1f} MB/s over {read_time:.2f}s")
#     print(f"Write-only rate: {write_mbps:5.1f} MB/s over {write_time:.2f}s")

# if __name__ == "__main__":
#     main()



