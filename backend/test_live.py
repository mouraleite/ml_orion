import urllib.request
import json

try:
    req = urllib.request.Request('http://localhost:8000/api/v1/tracking/summary')
    res = urllib.request.urlopen(req)
    print("Status:", res.getcode())
    print("Response:", res.read().decode()[:500])
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print("Response:", e.read().decode())
except Exception as e:
    print(f"Error: {e}")
