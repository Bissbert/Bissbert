#!/usr/bin/env python3
"""Daily recon card generator.

Writes assets/recon.svg (dark) and assets/recon-light.svg (light).

Each domain is checked for things its owner controls:
  - TLS certificate: days until expiry
  - HSTS: present, and its max-age
  - Security headers: how many of five are set
  - Edge: whether the domain is served through a CDN. For CDN-fronted domains,
    Shodan InternetDB describes the CDN's shared edge IP, not the origin, so
    its port/vuln counts are only reported for directly exposed hosts.
"""

from __future__ import annotations

import datetime
import os
import socket
import ssl
import urllib.error
import urllib.request

try:
    import requests
except ImportError:
    requests = None

HOSTS = ["bissbert.ch", "bisshub.ch", "gemmology.dev"]

THEMES = {
    "": dict(bg="#0d1117", bg2="#161b22", fg="#e6edf3", dim="#8b949e", rule="#30363d",
             ok="#3fb950", warn="#d29922", err="#f85149"),
    "-light": dict(bg="#ffffff", bg2="#f6f8fa", fg="#1f2328", dim="#59636e", rule="#d1d9e0",
                   ok="#1a7f37", warn="#9a6700", err="#cf222e"),
}
FONT = "'JetBrains Mono', 'SF Mono', 'Cascadia Mono', Menlo, monospace"

WIDTH = 720
PAD_X = 24
COL_HOST = 44
COL_EDGE = 196
COL_CHECKS = 330
CHAR_W = 0.62  # monospace advance as a fraction of font-size, rounded up for fallback fonts

HSTS_MIN_DAYS = 180
TLS_WARN_DAYS = 21
TLS_ERR_DAYS = 7
HEADERS = [
    ("content-security-policy", "CSP"),
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "frame"),
    ("referrer-policy", "referrer"),
    ("permissions-policy", "permissions"),
]
CDN_SERVERS = ("cloudflare", "akamai", "fastly", "cloudfront")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fit(text: str, x: int, size: int) -> str:
    """Truncate text so it cannot run past the card's right padding."""
    max_chars = int((WIDTH - PAD_X - x) / (size * CHAR_W))
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def tls_days(host: str) -> int:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            not_after = tls.getpeercert()["notAfter"]
    expires = datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), datetime.timezone.utc)
    return (expires - datetime.datetime.now(datetime.timezone.utc)).days


def fetch_headers(host: str) -> dict[str, str]:
    req = urllib.request.Request(f"https://{host}/", headers={"User-Agent": "bissbert-recon-card"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:  # a 4xx/5xx still carries the headers we want
        return {k.lower(): v for k, v in e.headers.items()}


def hsts_days(value: str | None) -> int | None:
    if not value:
        return None
    for part in value.split(";"):
        k, _, v = part.strip().partition("=")
        if k.lower() == "max-age" and v.strip().isdigit():
            return int(v) // 86400
    return 0


def internetdb(ip: str) -> dict:
    if requests is None:
        return {}
    resp = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=10)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()


def check(host: str) -> dict:
    r = {"host": host, "error": None}
    try:
        ip = socket.gethostbyname(host)
    except OSError as e:
        r["error"] = f"dns fail · {type(e).__name__}"
        return r
    try:
        r["tls"] = tls_days(host)
        hdrs = fetch_headers(host)
    except Exception as e:
        r["error"] = f"https fail · {type(e).__name__}"
        return r

    r["hsts"] = hsts_days(hdrs.get("strict-transport-security"))
    csp = hdrs.get("content-security-policy", "")
    present = [h for h, _ in HEADERS if h in hdrs or (h == "x-frame-options" and "frame-ancestors" in csp)]
    r["headers"] = len(present)

    server = hdrs.get("server", "").lower()
    cdn = next((c for c in CDN_SERVERS if c in server), None)
    try:
        idb = internetdb(ip)
    except Exception:
        idb = {}
    if cdn is None and "cdn" in (idb.get("tags") or []):
        cdn = "cdn"
    r["cdn"] = cdn
    r["ports"] = len(idb.get("ports") or [])
    r["vulns"] = len(idb.get("vulns") or [])
    return r


def summarise(r: dict) -> tuple[str, list[tuple[str, str]], str]:
    """Returns (edge, [(check text, level)], row severity); levels are ok/warn/err."""
    if r["error"]:
        return "—", [(r["error"], "err")], "err"

    tls = r["tls"]
    parts = [(f"TLS {tls}d", "err" if tls < TLS_ERR_DAYS else "warn" if tls < TLS_WARN_DAYS else "ok")]

    hsts = r["hsts"]
    if hsts is None:
        parts.append(("no HSTS", "warn"))
    else:
        parts.append((f"HSTS {hsts}d", "ok" if hsts >= HSTS_MIN_DAYS else "warn"))

    parts.append((f"headers {r['headers']}/{len(HEADERS)}", "ok" if r["headers"] >= 3 else "warn"))

    if r["cdn"]:
        edge = f"{r['cdn']} edge"
    else:
        edge = f"direct · {r['ports']} ports"
        parts.append((f"{r['vulns']} vulns", "err" if r["vulns"] else "ok"))

    levels = [lvl for _, lvl in parts]
    severity = "err" if "err" in levels else "warn" if "warn" in levels else "ok"
    return edge, parts, severity


def build_svg(rows: list[dict], stamp: str, t: dict) -> str:
    head_y, label_y, first_y, stride = 40, 72, 102, 34
    foot_y = first_y + (len(rows) - 1) * stride + 38
    height = foot_y + 22
    alt = "Daily recon card: TLS, HSTS and security-header checks for " + ", ".join(r["host"] for r in rows)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{esc(alt)}">',
        f'  <title>{esc(alt)}</title>',
        f'  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient></defs>',
        f'  <rect width="{WIDTH}" height="{height}" rx="10" fill="url(#bg)"/>',
        f'  <rect x="0.5" y="0.5" width="{WIDTH-1}" height="{height-1}" rx="10" fill="none" stroke="{t["rule"]}"/>',
        f'  <style>text {{ font-family: {FONT}; }}</style>',
        f'  <text x="{PAD_X}" y="{head_y}" font-size="13" font-weight="bold" fill="{t["ok"]}">$ recon --daily</text>',
        f'  <text x="{WIDTH-PAD_X}" y="{head_y}" font-size="12" fill="{t["dim"]}" text-anchor="end">{esc(stamp)}</text>',
        f'  <line x1="{PAD_X}" y1="{head_y+12}" x2="{WIDTH-PAD_X}" y2="{head_y+12}" stroke="{t["rule"]}"/>',
    ]
    for x, label in ((COL_HOST, "host"), (COL_EDGE, "served via"), (COL_CHECKS, "checks")):
        out.append(f'  <text x="{x}" y="{label_y}" font-size="11" fill="{t["dim"]}">{label}</text>')

    for i, r in enumerate(rows):
        y = first_y + i * stride
        edge, checks, sev = summarise(r)
        out.append(f'  <circle cx="{PAD_X+6}" cy="{y-4}" r="4" fill="{t[sev]}"/>')
        out.append(f'  <text x="{COL_HOST}" y="{y}" font-size="13" font-weight="600" fill="{t["fg"]}">{esc(fit(r["host"], COL_HOST, 13))}</text>')
        out.append(f'  <text x="{COL_EDGE}" y="{y}" font-size="12" fill="{t["dim"]}">{esc(fit(edge, COL_EDGE, 12))}</text>')
        room = int((WIDTH - PAD_X - COL_CHECKS) / (12 * CHAR_W))
        spans, used = [], 0
        for j, (text, lvl) in enumerate(checks):
            sep = " · " if j else ""
            if used + len(sep) + len(text) > room:
                spans.append(f'<tspan fill="{t["dim"]}">{esc(sep)}…</tspan>')
                break
            used += len(sep) + len(text)
            colour = t["fg"] if lvl == "ok" else t[lvl]
            spans.append(f'<tspan fill="{t["dim"]}">{esc(sep)}</tspan><tspan fill="{colour}">{esc(text)}</tspan>')
        out.append(f'  <text x="{COL_CHECKS}" y="{y}" font-size="12" xml:space="preserve">{"".join(spans)}</text>')
        if i < len(rows) - 1:
            out.append(f'  <line x1="{PAD_X}" y1="{y+14}" x2="{WIDTH-PAD_X}" y2="{y+14}" stroke="{t["rule"]}" stroke-width="0.5" stroke-dasharray="2,3"/>')

    foot = f"headers: CSP · nosniff · frame · referrer · permissions  ·  amber = HSTS<{HSTS_MIN_DAYS}d or TLS<{TLS_WARN_DAYS}d"
    out.append(f'  <text x="{PAD_X}" y="{foot_y}" font-size="10.5" fill="{t["dim"]}">{esc(fit(foot, PAD_X, 10.5))}</text>')
    out.append("</svg>")
    return "\n".join(out)


def error_svg(msg: str, stamp: str, t: dict) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="96" viewBox="0 0 {WIDTH} 96" role="img" aria-label="Recon card error">'
        f'<rect width="{WIDTH}" height="96" rx="10" fill="{t["bg"]}" stroke="{t["rule"]}"/>'
        f'<text x="{PAD_X}" y="44" font-family="monospace" font-size="13" fill="{t["err"]}">{esc(fit("recon error: " + msg, PAD_X, 13))}</text>'
        f'<text x="{PAD_X}" y="68" font-family="monospace" font-size="11" fill="{t["dim"]}">{esc(stamp)}</text>'
        "</svg>"
    )


def main() -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d UTC")
    assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(assets, exist_ok=True)
    try:
        rows = [check(h) for h in HOSTS]
        render = lambda t: build_svg(rows, stamp, t)
    except Exception as exc:
        render = lambda t: error_svg(str(exc), stamp, t)
    for suffix, theme in THEMES.items():
        path = os.path.join(assets, f"recon{suffix}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(theme))
        print(f"Written: {path}")


if __name__ == "__main__":
    main()
