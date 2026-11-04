"""Deploy node-red/flows.json to the local Node-RED, injecting the InfluxDB token from .env."""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE_RED = "http://localhost:1880"


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main():
    env = load_env()
    flows = json.loads((ROOT / "node-red" / "flows.json").read_text())
    for node in flows:
        if node.get("type") == "influxdb":
            node["credentials"] = {"token": env["INFLUX_TOKEN"]}
    req = urllib.request.Request(
        NODE_RED + "/flows",
        data=json.dumps(flows).encode(),
        headers={"Content-Type": "application/json", "Node-RED-Deployment-Type": "full"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print("Node-RED deploy:", resp.status, resp.read().decode())


if __name__ == "__main__":
    main()
