import requests

url = "http://localhost:8000/api/v1/viabilities/6/generate-summary"
payload = {"api_key": "dummy"}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.text)
