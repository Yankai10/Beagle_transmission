# #!/usr/bin/env python3
# import argparse
# import socket
# import sys
# import time

# # 从 receiver.py 中导入 RadioHoundSensorV3
# from receiver import RadioHoundSensorV3

# def parse_arguments():
#     parser = argparse.ArgumentParser(description="持续扫描并通过TCP传输原始ADC数据")
#     parser.add_argument(
#         '--freq_start', type=float, default=1615e6,
#         help="扫描起始频率(Hz)，默认1615e6"
#     )
#     parser.add_argument(
#         '--freq_end', type=float, default=1635e6,
#         help="扫描结束频率(Hz)，默认1635e6"
#     )
#     parser.add_argument(
#         '--gain', type=float, default=1,
#         help="增益(dB)，默认1"
#     )
    parser.add_argument(
        '--duration', type=int, default=600,
        help="持续扫描的总时长(秒)，默认600秒(10分钟)"
#     )
#     parser.add_argument(
#         '--remote_host', type=str, required=True,
#         help="目标主机IP地址(你的Mac的IP)"
#     )
#     parser.add_argument(
#         '--remote_port', type=int, default=5001,
#         help="目标主机端口，默认5001"
#     )
#     return parser.parse_args()

# def send_data_over_socket(sock, freq_lims, data):
#     """
#     使用持久的socket发送数据。
#     在数据前附加一个头部信息标明频率区间，方便远程端识别。
#     """
#     header = "FREQ:{}-{}|".format(freq_lims[0], freq_lims[1]).encode('utf-8')
#     payload = header + data
#     try:
#         sock.sendall(payload)
#         print("Sent {} bytes for frequency range {}-{}".format(len(payload), freq_lims[0], freq_lims[1]))
#     except Exception as e:
#         print("Error sending data over persistent socket:", e)

# def main():
#     args = parse_arguments()

#     sensor = RadioHoundSensorV3()
#     print("Initialization successfully")

#     freq_start = args.freq_start
#     freq_end = args.freq_end
#     gain = args.gain
#     duration = args.duration
#     host = args.remote_host
#     port = args.remote_port

#     # 建立一次持久TCP连接
#     try:
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.connect((host, port))
#         print("Connected to remote host {}:{}".format(host, port))
#     except Exception as e:
#         print("Failed to connect to remote host:", e)
#         sensor.close()
#         sys.exit(1)

#     print("开始持续扫描 {} ~ {} Hz, 增益 {} dB, 时长 {} 秒。".format(freq_start, freq_end, gain, duration))
#     start_time = time.time()
#     elapsed = 0

#     try:
#         while elapsed < duration:
#             # 调用 scan() 获取当前频率范围内的数据，显式传入 sample_rate 以避免 None 问题
#             scan_results = sensor.scan(
#                 frequency_start=freq_start,
#                 frequency_end=freq_end,
#                 gain=gain,
#                 rbw=23437.5,
#                 sample_rate=48e6,
#                 debug=0
#             )

#             if scan_results is not None:
#                 print("Get data :)")
#                 for (f_lims, data) in scan_results:
#                     # 使用持久连接发送数据
#                     send_data_over_socket(sock, f_lims, data)
#             else:
#                 print("Failed to get data")
            
#             elapsed = time.time() - start_time
#         print("持续扫描结束, 总时长约 {} 秒".format(duration))
#     except KeyboardInterrupt:
#         print("用户中断，停止扫描。")
#     except Exception as e:
#         print("出现异常，停止扫描:", e)
#     finally:
#         sensor.close()
#         sock.close()
#         print("硬件和socket资源均已释放，程序退出。")

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
import argparse
import socket
import sys
import time

from receiver import RadioHoundSensorV3

def parse_arguments():
    parser = argparse.ArgumentParser(description="Single raw capture and TCP transmission of ADC data")
    parser.add_argument(
        "--freq", type=float, default=1e9,
        help="Center frequency in Hz (default: 1.0e9)"
    )
    parser.add_argument(
        "--gain", type=float, default=1,
        help="Gain in dB (default: 1)"
    )
    parser.add_argument(
        "--remote_host", type=str, required=True,
        help="Remote host IP address for TCP transmission"
    )
    parser.add_argument(
        "--remote_port", type=int, default=5001,
        help="Remote host port (default: 5001)"
    )
    parser.add__argument(
        "--duration', type=int, default=600,
        help="total scanning time"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    print("Initializing hardware...")
    try:
        sensor = RadioHoundSensorV3()
        print("Hardware initialization completed.")
    except Exception as e:
        print("Failed to initialize hardware:", e)
        sys.exit(1)

    print(f"Preparing to capture raw IQ data at frequency={args.freq} Hz, gain={args.gain} dB.")
    try:
        # Perform a single raw capture
        data = sensor.raw(args.freq, args.gain)
        print(f"Successfully captured {len(data)} bytes of raw data.")
    except Exception as e:
        print("Failed to capture raw data:", e)
        sensor.close()
        sys.exit(1)

    print(f"Attempting to send data to {args.remote_host}:{args.remote_port}...")
    try:
        # Establish a TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.remote_host, args.remote_port))
        print("TCP connection established.")

        # Create a header to identify the frequency and gain
        header_str = f"FREQ:{args.freq}-GAIN:{args.gain}|"
        header_bytes = header_str.encode("utf-8")

        payload = header_bytes + data
        sock.sendall(payload)

        print(f"Sent {len(payload)} bytes to {args.remote_host}:{args.remote_port}.")
        sock.close()
    except Exception as e:
        print("Failed to send data over TCP:", e)

    sensor.close()
    print("All resources released. Program finished successfully.")

if __name__ == "__main__":
    main()

