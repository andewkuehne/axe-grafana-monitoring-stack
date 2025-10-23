# Axe Miner Monitoring Stack

A Docker-based monitoring solution for Axe-compatible miners using a dynamic IP manager, InfluxDB, and Grafana.

## Overview

This project provides a ready-to-use monitoring stack for Axe miners (such as NerdAxe, BitAxe, etc.) that expose a `/api/system/info` JSON endpoint. It includes:

  * **InfluxDB 2.7** for time-series data storage.
  * **Grafana** for visualization and dashboarding.
  * **Telegraf** as the metric-gathering agent.
  * **Miner Manager (Web App)**: A simple web UI to dynamically add or remove miner IPs without restarting any services.

## Features

  * Real-time monitoring of all your miners from a single dashboard.
  * Tracks hashrate, efficiency (J/TH), temperatures, power, voltage, shares (accepted, rejected, stale), and more.
  * **Dynamic IP Management**: Add/remove miner IPs via a web UI at `http://localhost:5000`.
  * Pre-configured Grafana dashboard (`miner-dashboard.json`).
  * Persistent storage for both InfluxDB and Grafana data.
  * Environment-based configuration.

## Requirements

  * Docker and Docker Compose
  * Git (for cloning the repository)

## Quick Start

1.  **Clone this repository:**

    ```
    git clone https://github.com/andewkuehne/axe-grafana-monitoring-stack
    cd axe-grafana-monitoring-stack
    ```

2.  **Create your environment file:**
    Create a file named `.env` and copy the contents of `env.example` into it. This file contains all your secret passwords and tokens.

    ```bash
    # On Linux/macOS
    cp env.txt .env
    ```

3.  **Start the services:**
    Use the `--build` flag the first time to build the new `miner-manager` image.

    ```
    docker-compose up -d --build
    ```

4.  **Add Your Miners:**

      * Open your browser and navigate to the **Miner Manager UI** at `http://localhost:5001`.
      * Add the IP addresses of your miners, one per line.
      * Click "Save IP List".

5.  **Access Grafana:**

      * Open your browser and navigate to `http://localhost:3000`.
      * Log in with the credentials specified in your `.env` file (e.g., `admin/admin`).

6.  **Import the Dashboard:**

      * In Grafana, go to the **Dashboards** section (four-square icon).
      * Click **"New"** -\> **"Import"**.
      * Upload the `miner-dashboard.json` file provided in this repository.
      * The dashboard should automatically link to the pre-provisioned `InfluxDB` datasource and start displaying data.

## Configuration

### Environment Variables

All configuration is handled in the `.env` file:

  * `DOCKER_INFLUXDB_INIT_USERNAME`: InfluxDB admin username.
  * `DOCKER_INFLUXDB_INIT_PASSWORD`: InfluxDB admin password.
  * `DOCKER_INFLUXDB_INIT_ORG`: InfluxDB organization name.
  * `DOCKER_INFLUXDB_INIT_BUCKET`: InfluxDB bucket name.
  * `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`: InfluxDB admin token (Telegraf uses this).
  * `DOCKER_GRAFANA_INIT_USERNAME`: Grafana admin username.
  * `DOCKER_GRAFANA_INIT_PASSWORD`: Grafana admin password.

### How It Works

This stack uses a simple, robust polling mechanism:

1.  **Telegraf** is configured to poll a single endpoint: `http://miner-manager:5001/metrics` every 10 minutes (or as set in `telegraf/telegraf.conf`).
2.  The **Miner Manager** service receives this request. It reads its list of IPs (from `miner-manager-data/ips.txt`).
3.  It then polls the `/api/system/info` endpoint of *every* IP in its list.
4.  It parses the different JSON responses, standardizes the data (e.g., converts `"1.5G"` to a number), and formats it all into Influx Line Protocol.
5.  It sends this complete data block back to Telegraf, which writes it to **InfluxDB**.
6.  **Grafana** reads from InfluxDB to display the data.

This design means you can add or remove 50 miners in the web UI, and Telegraf's configuration never needs to change or restart.

## Persistence

Data is persisted using Docker volumes:

  * `influxdb-data`: Stores all your time-series metrics.
  * `grafana-data`: Stores your Grafana settings and dashboards.
  * `miner-manager-data`: Stores the `ips.txt` file for your miner list.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
