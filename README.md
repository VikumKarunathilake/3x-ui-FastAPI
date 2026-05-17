# 3x-ui-FastAPI

A robust FastAPI application designed to seamlessly interact with [3x-ui](https://github.com/MHSanaei/3x-ui) panel databases and logs. This API acts as an interface to retrieve client configurations, monitor network traffic, and aggregate IP access data by parsing `access.log` into a structured, dedicated SQLite database (`traffic.db`).

## Features

- **Client Lookup**: Retrieve detailed client traffic limits and usage configurations directly from the `x-ui.db` database using either their Database ID or Email.
- **Log Aggregation**: Automatically runs a background process (`collector.py`) that monitors the `access.log` and aggregates IP addresses associated with specific clients into a secondary database (`traffic.db`).
- **IP Tracking**: Query the API to retrieve a history of unique IP addresses used by a specific client.
- **Automated DB Initialization**: Automatically ensures that the secondary `traffic.db` schema is created upon startup.
- **Fast & Modern**: Built with FastAPI for high performance, automatic documentation generation, and asynchronous execution.

## Requirements

- Python 3.9+
- Existing `x-ui.db` database file.
- Existing `access.log` from your 3x-ui installation.

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repository_url>
   cd 3x-ui-FastAPI
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # .venv\Scripts\activate   # On Windows
   ```

3. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration:**

   Copy the sample environment file and update the paths to point to your actual database and log locations.

   ```bash
   cp .env.example .env
   ```

   **`.env` variables:**
   - `XUI_DB_PATH`: Path to the primary 3x-ui SQLite database (default: `/etc/x-ui/x-ui.db`)
   - `TRAFFIC_DB_PATH`: Path to where the secondary traffic database will be stored (default: `/etc/x-ui/traffic.db`)
   - `ACCESS_LOG_PATH`: Path to the 3x-ui access logs (default: `/usr/local/x-ui/access.log`)
   - `COLLECT_INTERVAL`: Seconds between each log collection cycle (default: `60`)
   - `CACHE_TTL`: Cache time-to-live in seconds (default: `60`)

## Running the Application (Ubuntu Production Setup)

While you can run the server directly using uvicorn, for an Ubuntu server environment, it is highly recommended to run the API as a background `systemd` service. This ensures the API starts automatically on boot and restarts if it crashes.

### 1. Test Run

First, verify the application runs without errors:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```
*(Press `Ctrl+C` to stop after confirming it works).*

### 2. Setup Systemd Service

Create a new service file:

```bash
sudo nano /etc/systemd/system/3x-ui-fastapi.service
```

Paste the following configuration (adjust `/opt/3x-ui-FastAPI` if you cloned it elsewhere, and ensure the `User` has permissions to read `/etc/x-ui/` and `/usr/local/x-ui/`):

```ini
[Unit]
Description=3x-ui FastAPI Service
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/opt/3x-ui-FastAPI
Environment="PATH=/opt/3x-ui-FastAPI/.venv/bin"
ExecStart=/opt/3x-ui-FastAPI/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start the Service

Reload systemd and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable 3x-ui-fastapi
sudo systemctl start 3x-ui-fastapi
```

Check the status to ensure it's running smoothly:
```bash
sudo systemctl status 3x-ui-fastapi
```

## API Endpoints

Once running, you can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`. If you are accessing this remotely, you may need to set up a reverse proxy (like Nginx) or SSH port forwarding.

### Available Routes

- **`GET /`** - API Health check and information.
- **`GET /api/clients/{email}`** - Get client traffic limits and statistics by their Email.
- **`GET /api/clients/id/{client_id}`** - Get client traffic limits and statistics by their Database ID.
- **`GET /api/logs/ips/{client_id}`** - Get a list of all unique IP addresses recently seen for a specific client ID.

## Architecture

- **`api/main.py`**: The FastAPI application entry point, lifecycle manager, and background task spawner.
- **`api/database.py`**: Handles database connections for both `x-ui.db` (read-only) and `traffic.db` (read-write).
- **`api/collector.py`**: The background worker that parses `access.log` at specified intervals.
- **`api/routers/`**: Contains the route definitions for clients and logs.
- **`api/schemas.py`**: Pydantic models for request and response validation.

## License

MIT License. See `LICENSE` for more information.
