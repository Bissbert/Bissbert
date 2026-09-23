<div align="center">

<img src="https://capsule-render.vercel.app/api?type=wave&color=0:0d1117,100:3fb950&height=180&section=header&text=Bissbert&fontColor=e6edf3&fontSize=64&animation=fadeIn" />

<a href="https://github.com/Bissbert"><img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=20&duration=3000&pause=900&color=3FB950&center=true&vCenter=true&width=720&lines=OT+%2F+systems+security+engineer.;Shell+tools+for+production+systems.;Computational+geometry+on+the+side." /></a>

</div>

---

## Currently

I work in cybersecurity for critical electricity infrastructure in Switzerland, mostly on OT network visibility, asset discovery and detection-as-code.

I also run [MOOR security](https://moor-security.ch), a security consultancy in Zürich for Swiss companies and industrial operators. It does vulnerability assessments, security consulting, awareness training and incident response.

## Projects

**Security and systems**
- **[POSIX-hardening](https://github.com/Bissbert/POSIX-hardening)**: 21 scripts for hardening Debian, with automatic rollback and protection against locking yourself out of SSH.
- **[posix-ids](https://github.com/Bissbert/posix-ids)**: Linux IDS with no dependencies. Sends its alerts to Splunk.
- **[splunk-security-alerts](https://github.com/Bissbert/splunk-security-alerts)**: framework for managing Splunk detection rules as code.
- **[zbx-cli](https://github.com/Bissbert/zbx-cli)**: Zabbix client written in plain shell, for hosts where you can't install anything.
- **[topdesk-cli](https://github.com/Bissbert/topdesk-cli)**: shell client for scripting Topdesk ITSM.
- **[toolbox.sh](https://github.com/Bissbert/toolbox.sh)**: POSIX shell framework for building Git-style CLIs, scaffolded from JSON.

**Outside work**
- **[minecraft-litematica](https://github.com/Bissbert/minecraft-litematica)**: generates Litematica schematics from signed distance functions, i.e. 3D shapes combined with boolean operations.
- **[obsidianMathsExecutor](https://github.com/Bissbert/obsidianMathsExecutor)**: Obsidian plugin that evaluates LaTeX maths in your notes.
- **[jewlarray.ch](https://jewlarray.ch)**: my gemstone business. I facet, identify and sell stones.

## Daily recon

A GitHub Action checks my domains every night: days until the TLS certificate expires, the HSTS max-age, and how many of five security headers are set. Sites behind a CDN are marked as such, because a port scan of them would only show the CDN. The result is committed back to this repo as an SVG.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/recon-light.svg" />
    <img src="assets/recon.svg" alt="Daily recon card: TLS expiry, HSTS and security-header checks for bissbert.ch, bisshub.ch and gemmology.dev" />
  </picture>
</p>

## Stack

<p align="center">
  <img src="https://skillicons.dev/icons?i=bash,python,rust,ts,java,docker,linux,grafana&theme=dark&perline=8" alt="Stack icons" />
</p>

## Activity

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/stats-light.svg" />
    <img src="assets/stats.svg" alt="Public repositories, stars, followers and language mix" />
  </picture>
</p>
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/activity-light.svg" />
    <img src="assets/activity.svg" alt="Contribution activity (in-bounds snake scan)" />
  </picture>
</p>

## Elsewhere

- [moor-security.ch](https://moor-security.ch): security consulting
- [LinkedIn](https://www.linkedin.com/in/fabian-moor-2930001b6/)
- [bissbert.ch](https://bissbert.ch): occasional write-ups
- [jewlarray.ch](https://jewlarray.ch): gemstone shop
