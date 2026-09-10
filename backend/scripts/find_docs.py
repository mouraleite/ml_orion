import urllib.request

def fetch_doc(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            print(f"FOUND: {url}")
            return True
    except Exception:
        return False

def test():
    paths = [
        "https://api.sienge.com.br/docs/html-files/commercial-v1.html",
        "https://api.sienge.com.br/docs/html-files/sales-v1.html",
        "https://api.sienge.com.br/docs/html-files/contracts-v1.html",
        "https://api.sienge.com.br/docs/html-files/customers-v1.html",
        "https://api.sienge.com.br/docs/html-files/real-estate-v1.html",
        "https://api.sienge.com.br/docs/yaml-files/commercial-v1.yaml"
    ]
    
    for p in paths:
        fetch_doc(p)

if __name__ == "__main__":
    test()
