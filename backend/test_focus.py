import urllib.request
import urllib.error

url = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativaMercadoAnuais?$format=json&$filter=Indicador%20eq%20'IPCA'%20and%20baseCalculo%20eq%200&$orderby=Data%20desc&$top=5&$select=Indicador,Data,Mediana,Media,DataReferencia"

try:
    resp = urllib.request.urlopen(url)
    print("SUCCESS")
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}")
    print(e.read().decode())
