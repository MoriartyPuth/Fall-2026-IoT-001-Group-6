"""Generate grafana/dashboard.json (Flux queries against bucket iot, measurement lab4)."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DS = {"type": "influxdb", "uid": "lab4-influx"}


def flux(field, latest=False, value_only=False):
    q = ('from(bucket: "iot")\n'
         '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
         f'  |> filter(fn: (r) => r._measurement == "lab4" and r._field == "{field}")\n')
    if latest:
        q += '  |> last()\n'
    if value_only:
        q += '  |> keep(columns: ["_value"])\n'
    else:
        q += '  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n'
    return q + f'  |> yield(name: "{field}")'


def thresholds(*steps):
    return {"mode": "absolute",
            "steps": [{"color": c, "value": v} for v, c in steps]}


def panel(pid, title, ptype, x, y, w, h, targets, unit=None, display=None,
          th=None, mappings=None, options=None, custom=None, minv=None, maxv=None,
          decimals=None):
    defaults = {"color": {"mode": "thresholds" if th else "palette-classic"}}
    if unit:
        defaults["unit"] = unit
    if display:
        defaults["displayName"] = display
    if th:
        defaults["thresholds"] = th
    if mappings:
        defaults["mappings"] = mappings
    if custom:
        defaults["custom"] = custom
    if decimals is not None:
        defaults["decimals"] = decimals
    if minv is not None:
        defaults["min"] = minv
    if maxv is not None:
        defaults["max"] = maxv
    return {
        "id": pid, "title": title, "type": ptype, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"refId": chr(65 + i), "datasource": DS, "query": q}
                    for i, q in enumerate(targets)],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": options or {},
    }


def value_map(pairs):
    return [{"type": "value", "options": {
        str(v): {"text": text, "color": color, "index": i}
        for i, (v, text, color) in enumerate(pairs)}}]


STAT_LAST = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
             "colorMode": "background", "graphMode": "none", "textMode": "value",
             "justifyMode": "center"}
STAT_SPARK = dict(STAT_LAST, colorMode="value", graphMode="area")
LINE = {"lineWidth": 2, "fillOpacity": 15, "showPoints": "never", "spanNulls": True,
        "thresholdsStyle": {"mode": "off"}}

panels = [
    # Row 1: status tiles
    panel(1, "Gas Risk Level", "stat", 0, 0, 6, 5, [flux("risk_code", True)],
          th=thresholds((None, "green"), (1, "orange"), (2, "red")),
          mappings=value_map([(0, "SAFE", "green"), (1, "WARNING", "orange"), (2, "DANGER", "red")]),
          options=STAT_LAST),
    panel(2, "Body Temperature (MLX90614)", "gauge", 6, 0, 6, 10, [flux("body_temp", True)],
          unit="celsius", display="Body temp", minv=20, maxv=42,
          th=thresholds((None, "blue"), (28, "green"), (32.5, "red")),
          options={"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                   "showThresholdMarkers": True, "showThresholdLabels": True}),
    panel(3, "Fever Flag", "stat", 12, 0, 6, 5, [flux("fever_flag", True)],
          th=thresholds((None, "green"), (1, "red")),
          mappings=value_map([(0, "NORMAL (0)", "green"), (1, "FEVER (1)", "red")]),
          options=STAT_LAST),
    panel(4, "DS3231 Timestamp", "stat", 18, 0, 6, 5, [flux("rtc_time", True, value_only=True)],
          th=thresholds((None, "blue")),
          options=dict(STAT_LAST, colorMode="none",
                       reduceOptions={"calcs": ["lastNotNull"], "fields": "/.*/", "values": False})),
    panel(5, "Pressure (hPa) - BMP280", "stat", 0, 5, 6, 5, [flux("pressure", True)],
          unit="pressurehpa", display="Pressure", th=thresholds((None, "purple")), decimals=2,
          options=dict(STAT_SPARK, colorMode="value", graphMode="none")),
    panel(6, "Gas Average (current)", "stat", 12, 5, 6, 5, [flux("gas_avg", True)],
          display="Gas avg (ADC)", th=thresholds((None, "green"), (2100, "orange"), (2600, "red")),
          options=dict(STAT_SPARK, graphMode="none")),
    panel(7, "Altitude (m)", "stat", 18, 5, 6, 5, [flux("altitude", True)],
          unit="lengthm", display="Altitude", th=thresholds((None, "text")), decimals=1,
          options=dict(STAT_SPARK, colorMode="value", graphMode="none")),
    # Row 2: time series
    panel(8, "Gas Average (moving avg, 5 samples)", "timeseries", 0, 10, 24, 9,
          [flux("gas_avg"), flux("gas_raw")],
          th=thresholds((None, "green"), (2100, "orange"), (2600, "red")),
          custom=dict(LINE, thresholdsStyle={"mode": "dashed+area"}), minv=0, maxv=4095,
          options={"legend": {"displayMode": "list", "placement": "bottom"},
                   "tooltip": {"mode": "multi"}}),
    panel(9, "Pressure Graph (hPa)", "timeseries", 0, 19, 12, 8, [flux("pressure")],
          unit="pressurehpa", display="Pressure", custom=LINE,
          options={"legend": {"displayMode": "list", "placement": "bottom"}}),
    panel(10, "Altitude Graph (m)", "timeseries", 12, 19, 12, 8, [flux("altitude")],
          unit="lengthm", display="Altitude", custom=LINE,
          options={"legend": {"displayMode": "list", "placement": "bottom"}}),
    panel(11, "Body vs Room Temperature", "timeseries", 0, 27, 24, 8,
          [flux("body_temp"), flux("room_temp")], unit="celsius",
          th=thresholds((None, "green"), (32.5, "red")),
          custom=dict(LINE, fillOpacity=0, thresholdsStyle={"mode": "dashed"}),
          options={"legend": {"displayMode": "list", "placement": "bottom"},
                   "tooltip": {"mode": "multi"}}),
]

# series names for multi-query time series panels
for p, names in ((panels[7], ("gas_avg", "gas_raw")), (panels[10], ("body_temp", "room_temp"))):
    p["fieldConfig"]["overrides"] = [
        {"matcher": {"id": "byFrameRefID", "options": chr(65 + i)},
         "properties": [{"id": "displayName", "value": n}]}
        for i, n in enumerate(names)]
panels[7]["fieldConfig"]["overrides"].append(
    {"matcher": {"id": "byFrameRefID", "options": "B"},
     "properties": [{"id": "custom.lineWidth", "value": 1},
                    {"id": "custom.fillOpacity", "value": 0},
                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "#8e8e8e"}}]})
panels[7]["fieldConfig"]["overrides"].insert(0,
    {"matcher": {"id": "byFrameRefID", "options": "A"},
     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "#3274D9"}}]})

panels[10]["fieldConfig"]["overrides"].append(
    {"matcher": {"id": "byFrameRefID", "options": "B"},
     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "#FF9830"}}]})

dashboard = {
    "uid": "lab4-iot",
    "title": "LAB 4 - Multi-Sensor IoT Monitoring",
    "tags": ["lab4", "esp32"],
    "timezone": "browser",
    "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"},
    "schemaVersion": 39,
    "panels": panels,
}

(ROOT / "grafana" / "dashboard.json").write_text(json.dumps(dashboard, indent=2) + "\n")
print("wrote grafana/dashboard.json")
