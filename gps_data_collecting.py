#!/usr/bin/env python3
import time
import gps
import json
import statistics
import sys

def run_gps_json_logger(
    output_file="/home/debian/rh_trans_test/Beagle_transmission/gps_data.json",
    duration_sec=None
):

    session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

    latest_tpv = None
    latest_sky = None
    last_sky_seq = None

    start_time = time.time()

    while True:
        if duration_sec is not None:
            elapsed = time.time() - start_time
            if elapsed >= duration_sec:
                print(f"[INFO] Reached {duration_sec} seconds, stopping.")
                break

        try:
            report = session.next()
        except StopIteration:
            print("GPSD has terminated.")
            break
        except Exception as e:
            print(f"[ERROR] Error while reading GPS data: {e}")
            time.sleep(1)
            continue

        cls = report.get('class', '')

        if cls == 'TPV':
            latest_tpv = report

        elif cls == 'SKY':
            latest_sky = report

            sky_seq = latest_sky.get('seq', None)
            if sky_seq is not None and sky_seq == last_sky_seq:
                continue
            last_sky_seq = sky_seq

            sat_list = latest_sky.get('satellites', [])
            used_satellites = [sat for sat in sat_list if sat.get('used', False)]
            if not used_satellites:
                continue

            if not latest_tpv:
                continue

            lat = getattr(latest_tpv, 'lat', 'N/A')
            lon = getattr(latest_tpv, 'lon', 'N/A')
            alt = getattr(latest_tpv, 'alt', 'N/A')
            spd = getattr(latest_tpv, 'speed', 'N/A')
            tpv_time = getattr(latest_tpv, 'time', 'N/A')

            cnr_list = []
            for sat in used_satellites:
                cnr_val = sat.get('ss', None)
                if isinstance(cnr_val, (int, float)):
                    cnr_list.append(cnr_val)

            mean_cnr = None
            median_cnr = None
            variance_cnr = None
            if cnr_list:
                mean_cnr = statistics.mean(cnr_list)
                median_cnr = statistics.median(cnr_list)
                variance_cnr = statistics.pvariance(cnr_list)

            record = {
                "tpv_time": tpv_time,
                "latitude": lat,
                "longitude": lon,
                "altitude_m": alt,
                "speed_m_s": spd,
                "satellites_used": len(used_satellites),
                "mean_cnr": mean_cnr,
                "median_cnr": median_cnr,
                "variance_cnr": variance_cnr,
                "used_satellites": []
            }

            for sat in used_satellites:
                record["used_satellites"].append({
                    "prn": sat.get("PRN", "N/A"),
                    "az": sat.get("az", "N/A"),
                    "el": sat.get("el", "N/A"),
                    "cnr": sat.get("ss", "N/A")
                })

            try:
                with open(output_file, 'a', encoding='utf-8') as f:
                    json.dump(record, f, ensure_ascii=False)
                    f.write('\n')
                print(f"[INFO] Wrote a record to {output_file}")
            except Exception as e:
                print(f"[ERROR] Failed to write JSON to file: {e}")

        time.sleep(0.5)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dur = int(sys.argv[1])
    else:
        dur = None

    run_gps_json_logger(
        output_file="/home/debian/rh_trans_test/Beagle_transmission/gps_data.json",
        duration_sec=dur
    )

