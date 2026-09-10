import urllib.request
import urllib.parse
import base64
import json

def test_bank_movements():
    bill_id = 98657 # Our known bill
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')

    # Test /installments with withBankMovements
    url1 = f"https://api.sienge.com.br/mouraleite/public/api/v1/bills/{bill_id}/installments?withBankMovements=true"
    req1 = urllib.request.Request(url1)
    req1.add_header("Authorization", f"Basic {base64_auth}")

    try:
        with urllib.request.urlopen(req1) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("Installments withBankMovements=true:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Erro url1: {e}")

if __name__ == "__main__":
    test_bank_movements()
