import urllib.request
import base64
import json

def fetch_swagger():
    url = "https://api.sienge.com.br/mouraleite/public/api/v1/swagger.json"
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {base64_auth}",
        "Accept": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            with open("swagger.json", "w") as f:
                f.write(response.read().decode('utf-8'))
            print("Swagger saved to swagger.json")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    fetch_swagger()
