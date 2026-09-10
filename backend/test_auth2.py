import urllib.request
import urllib.parse
import json

try:
    data = urllib.parse.urlencode({'username': 'admin@mouraleite.com.br', 'password': '123'}).encode()
    req = urllib.request.Request('http://localhost:8000/api/v1/login/access-token', data=data)
    res = urllib.request.urlopen(req)
    token = json.loads(res.read()).get('access_token')
    
    req2 = urllib.request.Request('http://localhost:8000/api/v1/tracking/summary', headers={'Authorization': f'Bearer {token}'})
    res2 = urllib.request.urlopen(req2)
    print("Status:", res2.getcode())
    items = json.loads(res2.read()).get('items', [])
    print("Items:", len(items))
except urllib.error.HTTPError as e:
    print(f"Error: {e}")
    print(e.read().decode())
except Exception as e:
    print(f"Error: {e}")
