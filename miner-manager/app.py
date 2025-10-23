import os
import time
import requests
import re
from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

# Path to the file where IPs are stored
IP_FILE = "data/ips.txt"

# Ensure the data directory exists
os.makedirs(os.path.dirname(IP_FILE), exist_ok=True)
if not os.path.exists(IP_FILE):
    with open(IP_FILE, "w") as f:
        f.write("192.168.68.10\n192.168.68.11\n") # Default IPs

def get_ips():
    """Reads the list of IPs from the file."""
    with open(IP_FILE, "r") as f:
        ips = [line.strip() for line in f if line.strip()]
    return ips

def parse_difficulty(diff_str):
    """
    NEW: Parses difficulty strings like "3.49G" or "101M" into floats.
    """
    if not isinstance(diff_str, str):
        return None
    
    val_str = diff_str.upper().strip()
    
    # Use regex to find the number
    match = re.match(r"^[0-9\.]+", val_str)
    if not match:
        return None
        
    try:
        val = float(match.group(0))
        if "G" in val_str:
            return val * 1_000_000_000
        if "M" in val_str:
            return val * 1_000_000
        if "K" in val_str:
            return val * 1_000
        return val
    except (ValueError, TypeError):
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    """Serves the web UI for editing the IP list."""
    if request.method == "POST":
        ips_text = request.form["ips"]
        with open(IP_FILE, "w") as f:
            f.write(ips_text)
        return redirect(url_for("index"))
    
    with open(IP_FILE, "r") as f:
        ips_text = f.read()
    return render_template("index.html", ips_text=ips_text)

@app.route("/metrics")
def metrics():
    """
    This is the endpoint Telegraf will scrape.
    It polls all miners and returns data in Influx Line Protocol.
    """
    ips = get_ips()
    all_lines = []

    # Get current timestamp in nanoseconds
    timestamp = int(time.time() * 1_000_000_000)

    for ip in ips:
        try:
            # Poll the miner
            url = f"http://{ip}/api/system/info"
            response = requests.get(url, timeout=5)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()

            # --- 1. Define Tags (for filtering) ---
            tags = {
                "hostname": data.get("hostname"),
                "macAddr": data.get("macAddr"),
                "version": data.get("version"),
                "ASICModel": data.get("ASICModel")
            }
            tag_list = []
            for k, v in tags.items():
                if v:
                    k_esc = str(k).replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
                    v_esc = str(v).replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
                    tag_list.append(f"{k_esc}={v_esc}")
            
            tag_str = ",".join(tag_list)

            # --- 2. Define Fields (the metrics) ---
            # UPDATED: Added 'frequency'
            field_keys = [
                "power", "voltage", "current", "temp", "temp2", "vrTemp",
                "hashRate", "hashRate_1m", "hashRate_10m", "expectedHashrate",
                "coreVoltageActual", "sharesAccepted", "sharesRejected",
                "wifiRSSI", "fanspeed", "fanrpm", "uptimeSeconds", "freeHeap",
                "frequency" # <-- NEW FIELD
            ]
            
            fields = {}
            for key in field_keys:
                if key in data and (isinstance(data[key], int) or isinstance(data[key], float)):
                    fields[key] = data[key]
            
            # --- 3. Add NEW Parsed Fields ---
            
            # Parse difficulty strings
            best_diff = parse_difficulty(data.get("bestDiff"))
            if best_diff:
                fields["bestDifficulty"] = best_diff
            
            best_sess_diff = parse_difficulty(data.get("bestSessionDiff"))
            if best_sess_diff:
                fields["bestSessionDifficulty"] = best_sess_diff
                
            # Parse stale shares from the nested object
            rejected_reasons = data.get("sharesRejectedReasons")
            if isinstance(rejected_reasons, list):
                for reason in rejected_reasons:
                    if (isinstance(reason, dict) and 
                        reason.get("message") == "Stale" and 
                        isinstance(reason.get("count"), int)):
                        fields["sharesStale"] = reason.get("count")

            # --- 4. Format fields for line protocol ---
            field_list = []
            for k, v in fields.items():
                k_esc = str(k).replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
                if isinstance(v, float):
                    field_list.append(f"{k_esc}={v}")
                elif isinstance(v, int):
                    field_list.append(f"{k_esc}={v}i")
            
            field_str = ",".join(field_list)

            # --- 5. Assemble Line Protocol ---
            if field_str:
                line = f"miner_device_stats,{tag_str} {field_str} {timestamp}"
                all_lines.append(line)

        except requests.exceptions.RequestException as e:
            print(f"Error polling {ip}: {e}")
            continue
        except Exception as e:
            print(f"Error processing data from {ip}: {e}")
            continue
    
    return "\n".join(all_lines), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)