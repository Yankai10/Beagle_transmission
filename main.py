#!/usr/bin/env python3
import argparse
import socket
import sys
import time

# 从 receiver.py 中导入 RadioHoundSensorV3
from receiver import RadioHoundSensorV3

def parse_arguments():
    parser = argparse.ArgumentParser(description="持续扫描并通过TCP传输原始ADC数据")
    parser.add_argument(
        '--freq_start', type=float, default=1615e6,
        help="扫描起始频率(Hz)，默认1615e6"
    )
    parser.add_argument(
        '--freq_end', type=float, default=1635e6,
        help="扫描结束频率(Hz)，默认1635e6"
    )
    parser.add_argument(
        '--gain', type=float, default=1,
        help="增益(dB)，默认1"
    )
    parser.add_argument(
        '--duration', type=int, default=600,
        help="持续扫描的总时长(秒)，默认600秒(10分钟)"
    )
    parser.add_argument(
        '--remote_host', type=str, required=True,
        help="目标主机IP地址(你的Mac的IP)"
    )
    parser.add_argument(
        '--remote_port', type=int, default=5001,
        help="目标主机端口，默认5001"
    )
    return parser.parse_args()

def send_data_tcp(host, port, freq_lims, data):
    """
    创建TCP连接，将单次扫描得到的原始字节数据发送到远程主机。
    在发送前附加一个简单的头部信息，标明频率区间。
    """
    header = f"FREQ:{freq_lims[0]}-{freq_lims[1]}|".encode('utf-8')
    payload = header + data

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        total_sent = 0
        while total_sent < len(payload):
            sent = sock.send(payload[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent
        print(f"  已发送 {len(payload)} 字节到 {host}:{port} (区间 {freq_lims[0]}~{freq_lims[1]})")
    except Exception as e:
        print("  TCP发送失败：", e)
    finally:
        sock.close()

def main():
    args = parse_arguments()

    sensor = RadioHoundSensorV3()
    print('Initialization successfully')

    freq_start = args.freq_start
    freq_end = args.freq_end
    gain = args.gain
    duration = args.duration
    host = args.remote_host
    port = args.remote_port

    print(f"开始持续扫描 {freq_start} ~ {freq_end} Hz，增益={gain} dB，时长={duration}秒。")
    print(f"采集到的数据将通过TCP发送到 {host}:{port}。")

    start_time = time.time()
    elapsed = 0

    while elapsed < duration:
        scan_results = sensor.scan(
            frequency_starts = freq_start,
            frequency_end = freq_end,
            gain = gain,
            rbw = 23437.5,
            debug = 0
        )

        if scan_results is not None:
            print('Get data :)')
            for (f_lims, data) in scan_results:
                send_data_tcp(host, port, f_lims, data)
        else:
            print('failed to get data')

        elapsed = time.time() - start_time
        
    
    # try:
    #     # 在给定持续时间内循环扫描
    #     while elapsed < duration:
    #         # 调用 scan() 获取当前频率范围内的数据
    #         scan_results = sensor.scan(
    #             frequency_start=freq_start,
    #             frequency_end=freq_end,
    #             gain=gain,
    #             debug=0  # 设置为1可查看更多调试信息
    #         )

    #         # 遍历 scan 返回的多段数据 (f_lims, data)
    #         if scan_results is not None:
    #             for (f_lims, data) in scan_results:
    #                 # 立刻通过TCP发送到Mac
    #                 send_data_tcp(host, port, f_lims, data)
    #         else:
    #             print("扫描失败或无数据返回。")

    #         # 更新已用时间
    #         elapsed = time.time() - start_time
    #         # 这里可以加一个很短的sleep，避免过度占用CPU
    #         time.sleep(0.5)

    #     print(f"持续扫描已结束(总时长约{duration}秒)。")

    # except KeyboardInterrupt:
    #     print("用户中断，停止扫描。")

    # except Exception as e:
    #     print("出现异常，停止扫描：", e)

    # finally:
    #     sensor.close()
    #     print("硬件资源已释放，程序退出。")

if __name__ == '__main__':
    main()
