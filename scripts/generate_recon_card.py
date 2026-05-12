#!/usr/bin/env python3
"""Daily recon card generator — writes assets/recon.svg from Shodan InternetDB data."""

import socket
import datetime
import textwrap
import os

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

HOSTS = ["bissbert.ch", "bisshub.ch"]

BG = "#0d1117"
FG = "#e6edf3"
ACCENT = "#3fb950"
RED = "#f85149"
DIM = "#484f58"
FONT = "'JetBrains Mono', 'SF Mono', 'Cascadia Mono', Menlo, monospace"

WIDTH = 720
ROW_H = 52
PADDING_TOP = 56
TITLE_H = 44
FOOTER_H = 36

SVG_H = TITLE_H + len(HOSTS) * ROW_H + FOOTER_H + PADDING_TOP + 16


def trunc(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1] + "…"


def fmt_list(items: list, max_chars: int = 60) -> str:
    if not items:
        return "—"
    joined = ", ".join(str(i) for i in items)
    return trunc(joined, max_chars)


def fetch_host(host: str) -> dict:
    result = {"host": host, "ip": None, "ports": [], "vulns": [], "hostnames": [], "tags": [], "cpes": [], "status": "ok"}
    try:
        ip = socket.gethostbyname(host)
        result["ip"] = ip
    except Exception as e:
        result["status"] = f"unreachable · {type(e).__name__}"
        return result

    if not HAS_REQUESTS:
        result["status"] = "no requests library"
        return result

    try:
        resp = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=10)
        if resp.status_code == 404:
            result["status"] = "no exposure"
            return result
        resp.raise_for_status()
        data = resp.json()
        result["ports"] = data.get("ports", [])
        result["vulns"] = data.get("vulns", [])
        result["hostnames"] = data.get("hostnames", [])
        result["tags"] = data.get("tags", [])
        result["cpes"] = data.get("cpes", [])
    except Exception as e:
        result["status"] = f"unreachable · {type(e).__name__}"
    return result


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_svg(rows: list[dict], utc_date: str) -> str:
    height = PADDING_TOP + TITLE_H + len(rows) * ROW_H + FOOTER_H + 16
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">')
    lines.append(f'  <rect width="{WIDTH}" height="{height}" rx="10" fill="{BG}"/>')
    # border
    lines.append(f'  <rect width="{WIDTH}" height="{height}" rx="10" fill="none" stroke="{DIM}" stroke-width="1"/>')

    # font face hint (no @import needed, just specify family)
    lines.append(f'  <style>text {{ font-family: {FONT}; }}</style>')

    # Title row
    title_text = esc(f"┌─ DAILY RECON · {utc_date} UTC ─┐")
    ty = PADDING_TOP - 12
    lines.append(f'  <text x="24" y="{ty}" font-size="13" fill="{ACCENT}" font-weight="bold">{title_text}</text>')

    # Data rows
    for i, r in enumerate(rows):
        y_base = PADDING_TOP + TITLE_H + i * ROW_H
        host = esc(r["host"])
        ip_str = esc(r["ip"]) if r["ip"] else "?.?.?.?"

        # host name
        lines.append(f'  <text x="40" y="{y_base}" font-size="13" fill="{ACCENT}">▸ {host}</text>')

        if r["status"] == "ok":
            ip_label = f"→  {ip_str}"
            ports_str = esc(fmt_list(r["ports"], 50))
            vulns_count = len(r["vulns"])
            tags_str = esc(fmt_list(r["tags"], 40))

            # second line
            lines.append(f'  <text x="56" y="{y_base + 20}" font-size="12" fill="{FG}">{esc(ip_label)}   ports: {ports_str}</text>')
            vulns_color = RED if vulns_count > 0 else FG
            lines.append(f'  <text x="56" y="{y_base + 36}" font-size="12" fill="{FG}">vulns: <tspan fill="{vulns_color}">{vulns_count}</tspan>   tags: {tags_str}</text>')
        else:
            status_str = esc(r["status"])
            lines.append(f'  <text x="56" y="{y_base + 20}" font-size="12" fill="{RED}">{status_str}</text>')

        # separator
        sep_y = y_base + ROW_H - 4
        lines.append(f'  <line x1="24" y1="{sep_y}" x2="{WIDTH - 24}" y2="{sep_y}" stroke="{DIM}" stroke-width="0.5"/>')

    # Footer
    footer_y = PADDING_TOP + TITLE_H + len(rows) * ROW_H + 20
    footer_text = esc(f"└─ source: internetdb.shodan.io · auto-updated daily ─┘")
    lines.append(f'  <text x="24" y="{footer_y}" font-size="11" fill="{DIM}">{footer_text}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    utc_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    rows = [fetch_host(h) for h in HOSTS]
    svg = build_svg(rows, utc_date)

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "recon.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written: {out_path}")


try:
    main()
except Exception as exc:
    # Fallback: emit a minimal error SVG so the README never shows a broken image
    import os, datetime
    utc_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    error_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120" viewBox="0 0 720 120">
  <rect width="720" height="120" rx="10" fill="#0d1117"/>
  <text x="24" y="56" font-family="monospace" font-size="13" fill="#f85149">recon error: {str(exc)[:80]}</text>
  <text x="24" y="80" font-family="monospace" font-size="11" fill="#484f58">{utc_date} UTC</text>
</svg>"""
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "recon.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(error_svg)
    print(f"Error SVG written: {out_path} — cause: {exc}")
