import urllib.request
import json
import ssl

def download_sienge_swagger():
    # Sienge public docs swagger url
    url = "https://api.sienge.com.br/docs/swagger.json"
    
    # Bypass SSL if needed
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            with open("sienge_swagger.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print("Swagger downloaded successfully.")
    except Exception as e:
        print(f"Error downloading swagger: {e}")
        # Try alternate url
        try:
            url2 = "https://api.sienge.com.br/public/api/v1/swagger.json"
            req2 = urllib.request.Request(url2)
            with urllib.request.urlopen(req2, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
                with open("sienge_swagger.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print("Swagger downloaded from alternate URL.")
        except Exception as e2:
            print(f"Alternate error: {e2}")

if __name__ == "__main__":
    download_sienge_swagger()
