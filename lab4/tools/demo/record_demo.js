// Records the LAB 4 demo video (docs/demo.mp4) and the InfluxDB screenshot
// (docs/influxdb.png) with headless Chrome:
//   title -> ESP32 serial monitor -> Node-RED flow -> InfluxDB data -> Grafana live
//
//   cd tools/demo && npm install && node record_demo.js
const fs = require("fs");
const path = require("path");
const { spawn, execFileSync } = require("child_process");
const puppeteer = require("puppeteer");

const ROOT = path.resolve(__dirname, "..", "..");
const DOCS = path.join(ROOT, "docs");
const FRAMES = path.join(__dirname, "frames");
const FPS = 2;
const SERIAL_PORT = process.env.SERIAL_PORT || "/dev/cu.usbserial-0001";
const PY = process.env.SERIAL_PYTHON ||
  path.join(process.env.HOME, "Library/Application Support/pipx/venvs/mpremote/bin/python");

const env = Object.fromEntries(
  fs.readFileSync(path.join(ROOT, ".env"), "utf8").split("\n")
    .filter((l) => l.includes("="))
    .map((l) => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim()]));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let frameNo = 0;

async function caption(page, step, text) {
  await page.evaluate((step, text) => {
    let el = document.getElementById("lab4-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "lab4-caption";
      el.style.cssText = "position:fixed;left:0;right:0;bottom:0;z-index:2147483647;" +
        "padding:10px 18px;background:rgba(10,12,20,.88);color:#fff;" +
        "font:600 18px -apple-system,Helvetica,Arial;border-top:3px solid #3274d9";
      document.body.appendChild(el);
    }
    el.innerHTML = `<span style="color:#6ea8ff">${step}</span> &nbsp; ${text}`;
  }, step, text);
}

async function capture(page, seconds, onFrame) {
  const n = Math.round(seconds * FPS);
  for (let i = 0; i < n; i++) {
    const t0 = Date.now();
    if (onFrame) await onFrame(i);
    await page.screenshot({ path: path.join(FRAMES, String(frameNo++).padStart(5, "0") + ".png") });
    await sleep(Math.max(0, 1000 / FPS - (Date.now() - t0)));
  }
}

async function clickText(page, text, selector = "*") {
  const handle = await page.waitForFunction((text, selector) => {
    const els = [...document.querySelectorAll(selector)]
      .filter((e) => e.offsetParent && e.textContent.trim() === text);
    return els[els.length - 1];
  }, { timeout: 15000 }, text, selector);
  await handle.click();
}

async function main() {
  fs.rmSync(FRAMES, { recursive: true, force: true });
  fs.mkdirSync(FRAMES, { recursive: true });

  // serial monitor in the background for the whole recording
  const serialLines = [];
  const serialProc = spawn(PY, [path.join(__dirname, "serial_tail.py"), SERIAL_PORT]);
  serialProc.stdout.on("data", (d) => serialLines.push(...d.toString().split("\n").filter(Boolean)));
  serialProc.stderr.on("data", (d) => serialLines.push("[serial] " + d.toString().trim()));

  const browser = await puppeteer.launch({ headless: true, defaultViewport: { width: 1280, height: 720 } });
  const page = await browser.newPage();

  // 1. title card
  await page.setContent(`<body style="margin:0;height:100vh;display:flex;flex-direction:column;
    justify-content:center;align-items:center;background:#111217;color:#eee;font-family:-apple-system,Helvetica">
    <div style="font-size:44px;font-weight:700">LAB 4 - Multi-Sensor IoT Monitoring</div>
    <div style="font-size:24px;margin-top:14px;color:#9aa">ESP32 + MicroPython &rarr; Node-RED &rarr; InfluxDB &rarr; Grafana</div>
    <div style="font-size:20px;margin-top:34px;color:#bbb;line-height:1.7;text-align:center">
      MQ-5 gas (moving average + SAFE / WARNING / DANGER)<br>MLX90614 body temperature (fever flag &ge; 32.5 &deg;C)<br>
      BMP280 pressure + altitude &nbsp;&middot;&nbsp; DS3231 timestamp</div>
    <div style="font-size:16px;margin-top:34px;color:#777">${new Date().toLocaleString()}</div></body>`);
  await capture(page, 5);

  // 2. serial monitor: raw vs moving average + risk + fever
  // opening the port can reset the board; wait until it is printing readings
  for (let i = 0; i < 90 && !serialLines.some((l) => l.includes("GAS raw=")); i++) await sleep(1000);
  await page.setContent(`<body style="margin:0;background:#0c0c0c;color:#cfcfcf;font:15px Menlo,monospace">
    <div style="background:#2a2a2a;color:#aaa;padding:8px 14px;font:13px -apple-system">ESP32 serial monitor - ${SERIAL_PORT} @ 115200</div>
    <pre id="log" style="margin:0;padding:12px 14px;white-space:pre-wrap"></pre></body>`);
  await caption(page, "1/4 Edge logic", "ESP32 prints raw MQ-5 vs 5-sample moving average, risk level, fever flag, pressure, altitude");
  await capture(page, 18, async () => {
    const lines = serialLines.filter((l) => !l.includes("i2c.master")).slice(-26).join("\n");
    await page.evaluate((t) => {
      document.getElementById("log").innerHTML = t
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/\bSAFE\b/g, '<b style="color:#73bf69">SAFE</b>')
        .replace(/\bWARNING\b/g, '<b style="color:#ff9830">WARNING</b>')
        .replace(/\bDANGER\b/g, '<b style="color:#f2495c">DANGER</b>');
    }, lines || "waiting for serial data ...");
  });

  // 3. Node-RED flow
  await page.goto("http://localhost:1880/", { waitUntil: "networkidle2" });
  await sleep(3000);
  // first-run "Enable Update Notifications" dialog covers the flow
  await clickText(page, "No, do not enable notifications", "button").catch(() => {});
  await sleep(1500);
  // then the "Welcome to Node-RED" tour: close it with its x button
  await page.evaluate(() => {
    const title = [...document.querySelectorAll("*")].find((e) =>
      e.childElementCount === 0 && e.textContent.trim().startsWith("Welcome to Node-RED"));
    let box = title;
    for (let i = 0; i < 6 && box; i++, box = box.parentElement) {
      const close = [...box.querySelectorAll("button, a, i")].find((b) =>
        !/Start/.test(b.textContent) && b.getBoundingClientRect().width < 40);
      if (close) { close.click(); return; }
    }
  });
  await sleep(1000);
  await caption(page, "2/4 Node-RED", "HTTP POST /lab4/data -> validate + build point -> InfluxDB 2 (bucket iot, measurement lab4)");
  await capture(page, 9);

  // 4. InfluxDB Data Explorer, raw table of the latest points
  await page.goto("http://localhost:8086/signin", { waitUntil: "networkidle2" });
  await page.type('input[type="text"]', env.INFLUX_USER);
  await page.type('input[type="password"]', env.INFLUX_PASSWORD);
  await page.keyboard.press("Enter");
  await page.waitForNavigation({ waitUntil: "networkidle2" }).catch(() => {});
  const orgs = await (await fetch(`${env.INFLUX_URL}/api/v2/orgs?org=${env.INFLUX_ORG}`,
    { headers: { Authorization: `Token ${env.INFLUX_TOKEN}` } })).json();
  await page.goto(`http://localhost:8086/orgs/${orgs.orgs[0].id}/data-explorer`, { waitUntil: "networkidle2" });
  await sleep(2000);
  await clickText(page, "Script Editor", "button, [data-testid] , span");
  await sleep(1000);
  await page.click(".monaco-editor");
  await page.keyboard.down("Meta"); await page.keyboard.press("KeyA"); await page.keyboard.up("Meta");
  await page.keyboard.press("Backspace");
  await page.keyboard.type(
    'from(bucket: "iot") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "lab4" and r.device == "esp32-lab4") ' +
    '|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value") ' +
    '|> keep(columns: ["_time", "device", "gas_raw", "gas_avg", "risk_level", "body_temp", "fever_flag", "pressure", "altitude", "rtc_time"]) ' +
    '|> sort(columns: ["_time"], desc: true)');
  await page.keyboard.press("Escape");
  await clickText(page, "Submit", "button, span");
  await sleep(3000);
  // "View Raw Data" switch sits just right of its label
  const box = await page.evaluate(() => {
    const el = [...document.querySelectorAll("*")].find((e) =>
      e.childElementCount === 0 && e.textContent.trim() === "View Raw Data");
    const r = el.getBoundingClientRect();
    return { x: r.right, y: r.top + r.height / 2 };
  });
  await page.mouse.click(box.x + 16, box.y);
  await sleep(2000);
  await page.screenshot({ path: path.join(DOCS, "influxdb.png") });
  await caption(page, "3/4 InfluxDB", "Points stored in bucket iot, measurement lab4 (latest first)");
  await capture(page, 10);

  // 5. Grafana dashboard, live
  await page.setExtraHTTPHeaders({
    Authorization: "Basic " + Buffer.from(`${env.GRAFANA_USER}:${env.GRAFANA_PASSWORD}`).toString("base64"),
  });
  await page.goto(`${env.GRAFANA_URL}/d/lab4-iot/x?orgId=1&from=now-5m&to=now&kiosk&refresh=5s`,
    { waitUntil: "networkidle2" });
  await sleep(4000);
  await page.screenshot({ path: path.join(DOCS, "grafana.png") });
  await caption(page, "4/4 Grafana", "Gas average, risk level, body temp gauge, pressure, altitude, DS3231 timestamp - refresh 5 s");
  await capture(page, 36);

  await browser.close();
  serialProc.kill();

  const out = path.join(DOCS, "demo.mp4");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS),
    "-i", path.join(FRAMES, "%05d.png"), "-vf", "fps=30,format=yuv420p",
    "-c:v", "libx264", "-crf", "23", out], { stdio: "inherit" });
  fs.rmSync(FRAMES, { recursive: true, force: true });
  console.log(`wrote ${out} (${(frameNo / FPS).toFixed(0)} s), docs/influxdb.png, docs/grafana.png`);
}

main().catch((e) => { console.error(e); process.exit(1); });
