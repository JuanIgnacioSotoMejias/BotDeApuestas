import urllib.request
import json

def test():
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/jugar_ticket',
        data=json.dumps({
            'tipo_parley': 'Combinada Segura',
            'inversion': 1.0,
            'cuota': 1.15,
            'selecciones': [{'partido': 'España vs. Cabo Verde', 'pronostico': 'DNB (España)', 'cuota': 1.15}]
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as res:
            print("Response status:", res.status)
            print(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print("HTTP ERROR:", e.code)
        print(e.read().decode('utf-8'))
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test()
