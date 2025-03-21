# #!/usr/bin/env python3
# import argparse
# import socket
# import sys
# import time

# from receiver import RadioHoundSensorV3

# def parse_arguments():
#     parser = argparse.ArgumentParser(description="Single raw capture and TCP transmission of ADC data")
#     parser.add_argument(
#         "--freq", type=float, default=1e9,
#         help="Center frequency in Hz (default: 1.0e9)"
#     )
#     parser.add_argument(
#         "--gain", type=float, default=1,
#         help="Gain in dB (default: 1)"
#     )
#     parser.add_argument(
#         "--remote_host", type=str, required=True,
#         help="Remote host IP address for TCP transmission"
#     )
#     parser.add_argument(
#         "--remote_port", type=int, default=5001,
#         help="Remote host port (default: 5001)"
#     )
#     parser.add__argument(
#         "--duration', type=int, default=600,
#         help="total scanning time"
#     )
#     return parser.parse_args()

# def main():
#     args = parse_arguments()

#     print("Initializing hardware...")
#     try:
#         sensor = RadioHoundSensorV3()
#         print("Hardware initialization completed.")
#     except Exception as e:
#         print("Failed to initialize hardware:", e)
#         sys.exit(1)

#     print(f"Preparing to capture raw IQ data at frequency={args.freq} Hz, gain={args.gain} dB.")
#     try:
#         # Perform a single raw capture
#         data = sensor.raw(args.freq, args.gain)
#         print(f"Successfully captured {len(data)} bytes of raw data.")
#     except Exception as e:
#         print("Failed to capture raw data:", e)
#         sensor.close()
#         sys.exit(1)

#     print(f"Attempting to send data to {args.remote_host}:{args.remote_port}...")
#     try:
#         # Establish a TCP connection
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.connect((args.remote_host, args.remote_port))
#         print("TCP connection established.")

#         # Create a header to identify the frequency and gain
#         header_str = f"FREQ:{args.freq}-GAIN:{args.gain}|"
#         header_bytes = header_str.encode("utf-8")

#         payload = header_bytes + data
#         sock.sendall(payload)

#         print(f"Sent {len(payload)} bytes to {args.remote_host}:{args.remote_port}.")
#         sock.close()
#     except Exception as e:
#         print("Failed to send data over TCP:", e)

#     sensor.close()
#     print("All resources released. Program finished successfully.")

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
import argparse
import socket
import sys
import time

from receiver import RadioHoundSensorV3

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Repeated raw capture and TCP transmission of ADC data for a specified duration"
    )
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
    parser.add_argument(
        "--duration", type=int, default=600,
        help="Total scanning time in seconds (default: 600 seconds)"
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

    # Establish a persistent TCP connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.remote_host, args.remote_port))
        print(f"TCP connection established to {args.remote_host}:{args.remote_port}.")
    except Exception as e:
        print("Failed to connect to remote host:", e)
        sensor.close()
        sys.exit(1)

    print(f"Starting repeated raw capture for {args.duration} seconds.")
    print(f"Center frequency: {args.freq} Hz, Gain: {args.gain} dB.")

    start_time = time.time()
    elapsed = 0
    capture_count = 0

    try:
        while elapsed < args.duration:
            try:
                # Capture raw data
                raw_data = sensor.raw(args.freq, args.gain)
                capture_count += 1
                print(f"Capture #{capture_count}: Captured {len(raw_data)} bytes of raw data.")
            except Exception as e:
                print("Error capturing raw data:", e)
                break

            # Prepend a header to identify the capture
            header_str = f"RAW|FREQ:{args.freq}-GAIN:{args.gain}-CAP#{capture_count}|"
            header_bytes = header_str.encode("utf-8")
            payload = header_bytes + raw_data

            try:
                sock.sendall(payload)
                print(f"Sent {len(payload)} bytes for capture #{capture_count}.")
            except Exception as e:
                print("Error sending data over TCP:", e)
                break

            # Update elapsed time and sleep for a defined interval
            elapsed = time.time() - start_time
    except KeyboardInterrupt:
        print("User interrupted. Stopping captures.")
    finally:
        sensor.close()
        sock.close()
        print("Hardware and socket resources released. Program finished successfully.")

if __name__ == "__main__":
    main()

