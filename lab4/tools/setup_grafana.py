"""Create the InfluxDB datasource and the LAB 4 dashboard in the local Grafana (idempotent)."""
import base64
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DS_UID = "lab4-influx"


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
AUTH = "Basic " + base64.b64encode(
    f"{ENV['GRAFANA_USER']}:{ENV['GRAFANA_PASSWORD']}".encode()).decode()


def api(method, path, body=None):
    req = urllib.request.Request(
        ENV["GRAFANA_URL"] + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": AUTH},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    datasource = {
        "uid": DS_UID,
        "name": "InfluxDB LAB4",
        "type": "influxdb",
        "access": "proxy",
        "url": ENV["INFLUX_URL"],
        "isDefault": True,
        "jsonData": {"version": "Flux", "organization": ENV["INFLUX_ORG"],
                     "defaultBucket": ENV["INFLUX_BUCKET"]},
        "secureJsonData": {"token": ENV["INFLUX_TOKEN"]},
    }
    status, _ = api("GET", f"/api/datasources/uid/{DS_UID}")
    if status == 200:
        status, body = api("PUT", f"/api/datasources/uid/{DS_UID}", datasource)
    else:
        status, body = api("POST", "/api/datasources", datasource)
    print("datasource:", status, body.get("message"))

    dashboard = json.loads((ROOT / "grafana" / "dashboard.json").read_text())
    status, body = api("POST", "/api/dashboards/db",
                       {"dashboard": dashboard, "overwrite": True, "folderUid": ""})
    print("dashboard:", status, ENV["GRAFANA_URL"] + body.get("url", ""))


if __name__ == "__main__":
    main()
