import requests

try:
    res = requests.post('http://localhost:8000/api/v1/login', data={'username': 'admin@mouraleite.com.br', 'password': '123'})
    token = res.json().get('access_token')
    if not token:
        print("Login failed", res.text)
    else:
        res2 = requests.get('http://localhost:8000/api/v1/tracking/summary', headers={'Authorization': f'Bearer {token}'})
        print(f"Status: {res2.status_code}")
        if res2.status_code == 200:
            print(f"Items: {len(res2.json().get('items', []))}")
        else:
            print(res2.text)
except Exception as e:
    print(f"Error: {e}")
