"""Fetch and validate free HTTP proxies for crawlers (testing)."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx

OUTPUT = Path(os.getenv("PROXY_OUTPUT", "/app/data/proxies.json"))
SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]


def fetch_proxy_lists() -> list[str]:
    proxies: set[str] = []
    for url in SOURCES:
        try:
            resp = httpx.get(url, timeout=20.0, follow_redirects=True)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                        proxies.add(f"http://{line}")
        except Exception:
            continue
    return sorted(proxies)


def validate_proxy(proxy: str, timeout: float = 8.0) -> bool:
    try:
        resp = httpx.get(
            "https://httpbin.org/ip",
            proxy=proxy,
            timeout=timeout,
            follow_redirects=True,
        )
        return resp.status_code == 200
    except Exception:
        return False


def main() -> int:
    manual = os.getenv("PROXY_LIST", "")
    manual_proxies = [p.strip() for p in manual.split(",") if p.strip()]

    if manual_proxies:
        working = manual_proxies
    else:
        candidates = fetch_proxy_lists()[:40]
        working = [p for p in candidates if validate_proxy(p)][:10]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"proxies": working}, indent=2), encoding="utf-8")
    print(f"Saved {len(working)} proxies to {OUTPUT}")
    return 0 if working else 1


if __name__ == "__main__":
    sys.exit(main())
