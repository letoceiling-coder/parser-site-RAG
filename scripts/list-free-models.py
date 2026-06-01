#!/usr/bin/env python3
import json, urllib.request
KEY = open("/opt/parser-site-rag/.env").read().split("OPENROUTER_API_KEY=")[1].split("\n")[0].strip()
req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {KEY}"})
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
for m in data.get("data", []):
    mid = m.get("id", "")
    if ":free" in mid:
        print(mid)
