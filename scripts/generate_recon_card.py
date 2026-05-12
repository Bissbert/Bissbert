#!/usr/bin/env python3
"""Daily recon card generator — writes assets/recon.svg from Shodan InternetDB data."""

import socket
import datetime
import os

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

HOSTS = ["bissbert.ch", "bisshub.ch"]

BG = "#0d1117"
FG = "#e6edf3"
DIM_FG = "#8b949e"
ACCENT = "#3fb950"
RED = "#f85149"
AMBER = "#d29922"
DIM = "#30363d"
GRID = "#161b22"
FONT = "'JetBrains Mono', 'SF Mono', 'Cascadia Mono', Menlo, monospace"

WIDTH = 720
PAD_X = 24
TITLE_Y = 38
ROW_BASE_Y = 78
ROW_STRIDE = 38
FOOTER_GAP = 28

# Cloudflare's public proxy port list — used to short-circuit noisy output
CLOUDFLARE_PORTS = {80, 443, 2052, 2053, 2082, 2083, 2086, 2087, 2095, 2096, 8080, 8443, 8880}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fetch_host(host: str) -> dict:
    result = {"host": host, "ip": None, "ports": [], "vulns": [], "hostnames": [], "tags": [], "cpes": [], "status": "ok"}
    try:
        result["ip"] = socket.gethostbyname(host)
    except Exception as e:
        result["status"] = f"dns fail · {type(e).__name__}"
        return result

    if not HAS_REQUESTS:
        result["status"] = "no requests library"
        return result

    try:
        resp = requests.get(f"https://internetdb.shodan.io/{result['ip']}", timeout=10)
        if resp.status_code == 404:
            result["status"] = "no shodan record"
            return result
        resp.raise_for_status()
        data = resp.json()
        result["ports"] = data.get("ports", [])
        result["vulns"] = data.get("vulns", [])
        result["hostnames"] = data.get("hostnames", [])
        result["tags"] = data.get("tags", [])
        result["cpes"] = data.get("cpes", [])
    except Exception as e:
        result["status"] = f"net fail · {type(e).__name__}"
    return result


def host_summary(r: dict) -> tuple[str, str]:
    """Returns (summary, severity) where severity is 'ok'/'warn'/'err'."""
    if r["status"] != "ok":
        return r["status"], "err"

    ports = r["ports"]
    vulns_n = len(r["vulns"])
    tags = r["tags"] or []

    # If behind CDN AND only Cloudflare-public ports, abbreviate
    behind_cdn = "cdn" in tags
    only_cf_ports = ports and all(p in CLOUDFLARE_PORTS for p in ports)

    parts = []
    if behind_cdn:
        if only_cf_ports:
            parts.append(f"cdn-fronted · {len(ports)} public ports")
        else:
            parts.append(f"cdn · {len(ports)} ports")
    else:
        if len(ports) == 0:
            parts.append("no open ports")
        elif len(ports) <= 4:
            parts.append("ports " + ", ".join(str(p) for p in ports))
        else:
            head = ", ".join(str(p) for p in ports[:3])
            parts.append(f"ports {head} +{len(ports)-3}")

    parts.append(f"{vulns_n} vuln" + ("" if vulns_n == 1 else "s"))

    if r["hostnames"]:
        parts.append(f"{len(r['hostnames'])} altname" + ("" if len(r["hostnames"]) == 1 else "s"))

    severity = "ok"
    if vulns_n > 0:
        severity = "err"
    elif not behind_cdn and not ports:
        severity = "ok"
    return " · ".join(parts), severity


def hr_line(label_inner: str, width_chars: int = 64) -> str:
    """Build an ASCII rule like '┌─ label ──────┐' that fills to width_chars."""
    inner = f" {label_inner} "
    fill = max(0, width_chars - len(inner) - 2)
    return "┌─" + inner + "─" * fill + "┐"


def hr_line_bot(label_inner: str, width_chars: int = 64) -> str:
    inner = f" {label_inner} "
    fill = max(0, width_chars - len(inner) - 2)
    return "└─" + inner + "─" * fill + "┘"


def build_svg(rows: list[dict], utc_date: str) -> str:
    height = ROW_BASE_Y + max(0, len(rows) - 1) * ROW_STRIDE + FOOTER_GAP + 24
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="Daily recon card">')
    parts.append(f'  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{GRID}"/></linearGradient></defs>')
    parts.append(f'  <rect width="{WIDTH}" height="{height}" rx="10" fill="url(#bg)"/>')
    parts.append(f'  <rect x="0.5" y="0.5" width="{WIDTH-1}" height="{height-1}" rx="10" fill="none" stroke="{DIM}" stroke-width="1"/>')
    parts.append(f'  <style>text {{ font-family: {FONT}; }} .dim {{ fill: {DIM_FG}; }}</style>')

    # Top rule
    parts.append(f'  <text x="{PAD_X}" y="{TITLE_Y}" font-size="13" fill="{ACCENT}" font-weight="bold" xml:space="preserve">{esc(hr_line(f"DAILY RECON · {utc_date} UTC"))}</text>')

    # Rows
    col_host = PAD_X + 12
    col_ip = col_host + 150
    col_summary = col_ip + 160

    for i, r in enumerate(rows):
        y = ROW_BASE_Y + i * ROW_STRIDE
        summary, severity = host_summary(r)
        dot_color = {"ok": ACCENT, "warn": AMBER, "err": RED}[severity]

        # Status dot (slightly bigger circle)
        parts.append(f'  <circle cx="{PAD_X + 6}" cy="{y - 5}" r="4" fill="{dot_color}"/>')
        # Host name
        parts.append(f'  <text x="{col_host + 8}" y="{y}" font-size="13" fill="{FG}" font-weight="600">{esc(r["host"])}</text>')
        # IP (dim mono)
        ip_text = r["ip"] if r["ip"] else "—"
        parts.append(f'  <text x="{col_ip}" y="{y}" font-size="12" class="dim">{esc(ip_text)}</text>')
        # Summary
        sum_color = RED if severity == "err" else (AMBER if severity == "warn" else FG)
        parts.append(f'  <text x="{col_summary}" y="{y}" font-size="12" fill="{sum_color}">{esc(summary)}</text>')

        # Faint row separator (except after last)
        if i < len(rows) - 1:
            sep_y = y + 14
            parts.append(f'  <line x1="{PAD_X}" y1="{sep_y}" x2="{WIDTH - PAD_X}" y2="{sep_y}" stroke="{DIM}" stroke-width="0.5" stroke-dasharray="2,3"/>')

    # Bottom rule
    foot_y = ROW_BASE_Y + (len(rows) - 1) * ROW_STRIDE + FOOTER_GAP + 4
    parts.append(f'  <text x="{PAD_X}" y="{foot_y}" font-size="11" class="dim" xml:space="preserve">{esc(hr_line_bot("source: internetdb.shodan.io · auto-updated daily"))}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    utc_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    rows = [fetch_host(h) for h in HOSTS]
    svg = build_svg(rows, utc_date)

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "recon.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written: {out_path} ({len(svg)} bytes)")


try:
    main()
except Exception as exc:
    utc_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    error_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="96" viewBox="0 0 720 96">'
        f'<rect width="720" height="96" rx="10" fill="{BG}"/>'
        f'<text x="24" y="44" font-family="monospace" font-size="13" fill="{RED}">recon error: {esc(str(exc)[:80])}</text>'
        f'<text x="24" y="68" font-family="monospace" font-size="11" fill="{DIM_FG}">{utc_date} UTC</text>'
        '</svg>'
    )
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "recon.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(error_svg)
    print(f"Error SVG written: {out_path} — cause: {exc}")
