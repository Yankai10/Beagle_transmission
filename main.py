import paho.mqtt.client as mqtt
import time
from datetime import datetime
from receiver import RadioHoundSensorV3

BROKER_HOST = "127.0.0.1"  # MQTT Broker 运行在 BeagleBone
BROKER_PORT = 1883
TOPIC = "radiohound/raw"

def main():
    sensor = RadioHoundSensorV3()
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)

    print("Starting repeated raw capture...")
    start_time = time.time()
    duration = 10  # 采集 10 秒
    elapsed = 0
    capture_count = 0

    while elapsed < duration:
        raw_data = sensor.raw(1.625e9, 1)  # 采集 IQ 数据
        capture_count += 1
        print(f"Captured {len(raw_data)} bytes of raw data.")

        # 获取精确到微秒的当前时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        header_str = f"RAW|CAP#{capture_count}|TIME:{timestamp}|"
        header_bytes = header_str.encode("utf-8")
        payload = header_bytes + raw_data
        client.publish(TOPIC, payload, qos=0)

        elapsed = time.time() - start_time

    print("Finished data transmission.")
    client.disconnect()
    sensor.close()

if __name__ == "__main__":
    main()
