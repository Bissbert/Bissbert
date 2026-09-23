#!/usr/bin/env python3
"""Compact stats card generator.

Writes assets/stats.svg (dark) and assets/stats-light.svg (light): four headline
numbers and the language mix of public, non-fork repositories. Contribution
counts are left out because this repo's scheduled commits would inflate them.
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.request
from collections import Counter

USER = os.environ.get("GH_USER", "Bissbert")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

THEMES = {
    "": dict(bg="#0d1117", bg2="#161b22", fg="#e6edf3", dim="#8b949e", rule="#30363d",
             accent="#3fb950", bar="#2ea043", track="#21262d"),
    "-light": dict(bg="#ffffff", bg2="#f6f8fa", fg="#1f2328", dim="#59636e", rule="#d1d9e0",
                   accent="#1a7f37", bar="#1a7f37", track="#eaeef2"),
}
FONT = "'JetBrains Mono', 'SF Mono', 'Cascadia Mono', Menlo, monospace"
WIDTH = 720
PAD_X = 24
TOP_LANGS = 6

QUERY = """query($u:String!,$after:String){user(login:$u){createdAt followers{totalCount}
repositories(ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false,first:100,after:$after){
totalCount pageInfo{hasNextPage endCursor}
nodes{stargazerCount languages(first:20){edges{size node{name}}}}}}}"""


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def gql(variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    if "errors" in data:
        raise RuntimeError(data["errors"][0].get("message", "graphql error"))
    return data["data"]["user"]


def fetch() -> dict:
    after, stars, langs = None, 0, Counter()
    while True:
        user = gql({"u": USER, "after": after})
        repos = user["repositories"]
        for node in repos["nodes"]:
            stars += node["stargazerCount"]
            for edge in node["languages"]["edges"]:
                langs[edge["node"]["name"]] += edge["size"]
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    return {
        "repos": repos["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "since": user["createdAt"][:4],
        "langs": langs,
    }


def build_svg(d: dict, t: dict) -> str:
    total = sum(d["langs"].values()) or 1
    top = d["langs"].most_common(TOP_LANGS)
    other = total - sum(v for _, v in top)
    rows = [(name, v / total) for name, v in top]
    if other > 0:
        rows.append(("Other", other / total))

    tiles = [(str(d["repos"]), "public repos"), (str(d["stars"]), "stars"),
             (str(d["followers"]), "followers"), (d["since"], "on GitHub since")]
    cols, col_w = 2, (WIDTH - 2 * PAD_X) // 2
    lang_top = 128
    lang_stride = 24
    height = lang_top + ((len(rows) + cols - 1) // cols) * lang_stride + 14
    peak = max(share for _, share in rows)
    alt = (f"{d['repos']} public repositories, {d['stars']} stars, {d['followers']} followers. Languages: "
           + ", ".join(f"{n} {s:.0%}" for n, s in rows))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{esc(alt)}">',
        f'  <title>{esc(alt)}</title>',
        f'  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient></defs>',
        f'  <rect width="{WIDTH}" height="{height}" rx="10" fill="url(#bg)"/>',
        f'  <rect x="0.5" y="0.5" width="{WIDTH-1}" height="{height-1}" rx="10" fill="none" stroke="{t["rule"]}"/>',
        f'  <style>text {{ font-family: {FONT}; }}</style>',
    ]
    tile_w = (WIDTH - 2 * PAD_X) / len(tiles)
    for i, (value, label) in enumerate(tiles):
        x = PAD_X + i * tile_w
        out.append(f'  <text x="{x:.0f}" y="54" font-size="26" font-weight="bold" fill="{t["fg"]}">{esc(value)}</text>')
        out.append(f'  <text x="{x:.0f}" y="76" font-size="11" fill="{t["dim"]}">{esc(label)}</text>')
    out.append(f'  <line x1="{PAD_X}" y1="96" x2="{WIDTH-PAD_X}" y2="96" stroke="{t["rule"]}"/>')
    out.append(f'  <text x="{PAD_X}" y="116" font-size="11" fill="{t["dim"]}">languages · public non-fork repos, by bytes</text>')

    name_w, pct_w, gap = 104, 40, 10
    bar_w = col_w - name_w - pct_w - 2 * gap - 16
    for i, (name, share) in enumerate(rows):
        c, r = i % cols, i // cols
        x = PAD_X + c * col_w
        y = lang_top + r * lang_stride + 12
        fill_w = max(4, bar_w * share / peak)
        out.append(f'  <text x="{x}" y="{y+4}" font-size="12" fill="{t["fg"]}">{esc(name[:13])}</text>')
        bx = x + name_w + gap
        out.append(f'  <rect x="{bx}" y="{y-4}" width="{bar_w}" height="8" rx="4" fill="{t["track"]}"/>')
        colour = t["dim"] if name == "Other" else t["bar"]
        out.append(f'  <rect x="{bx}" y="{y-4}" width="{fill_w:.1f}" height="8" rx="4" fill="{colour}"/>')
        out.append(f'  <text x="{bx + bar_w + gap + pct_w}" y="{y+4}" font-size="12" fill="{t["dim"]}" text-anchor="end">{share:.0%}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(assets, exist_ok=True)
    data = fetch()
    for suffix, theme in THEMES.items():
        path = os.path.join(assets, f"stats{suffix}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(data, theme))
        print(f"Written: {path}")


if __name__ == "__main__":
    main()
