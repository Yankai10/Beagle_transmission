import paho.mqtt.client as mqtt
import time
import argparse
from datetime import datetime
from receiver import RadioHoundSensorV3

BROKER_HOST = "127.0.0.1"  
BROKER_PORT = 1883
TOPIC = "radiohound/raw"

def main():
    parser = argparse.ArgumentParser(description="RadioHound MQTT raw capture sender")
    parser.add_argument("--duration", type=float, default=None, help="Scanning time, infinite as default")
    args = parser.parse_args()

    sensor = RadioHoundSensorV3()
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)

    print("Starting raw capture...")
    start_time = time.time()
    capture_count = 0

    try:
        while True:
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break

            raw_data = sensor.raw(1.625e9, 1)  
            capture_count += 1
            print(f"Captured {len(raw_data)} bytes of raw data.")

            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            header_str = f"RAW|CAP#{capture_count}|TIME:{timestamp}|"
            header_bytes = header_str.encode("utf-8")
            payload = header_bytes + raw_data
            client.publish(TOPIC, payload, qos=0)

    except KeyboardInterrupt:
        print("Interrupted by user.")

    print("Finished data transmission.")
    client.disconnect()
    sensor.close()

if __name__ == "__main__":
    main()

