import sys
from lxml import etree
import tempfile
import webbrowser

NS = {"fa": "http://crd.gov.pl/wzor/2023/06/29/12648/"}

def get(el, path):
    x = el.find(path, NS)
    return x.text if x is not None else ""

def get_all(el, path):
    return el.findall(path, NS)

def parse_invoice(root):
    data = {}

    data["numer"] = get(root, ".//fa:P_2")
    data["data"] = get(root, ".//fa:P_1")

    data["sprzedawca"] = {
        "nazwa": get(root, ".//fa:P_3A"),
        "nip": get(root, ".//fa:P_5A"),
    }

    data["nabywca"] = {
        "nazwa": get(root, ".//fa:P_3B"),
        "nip": get(root, ".//fa:P_5B"),
    }

    items = []
    for poz in get_all(root, ".//fa:FakturaWiersz"):
        items.append({
            "nazwa": get(poz, ".//fa:P_7"),
            "ilosc": get(poz, ".//fa:P_8A"),
            "cena": get(poz, ".//fa:P_9A"),
            "netto": get(poz, ".//fa:P_11"),
            "vat": get(poz, ".//fa:P_12"),
        })

    data["items"] = items
    data["brutto"] = get(root, ".//fa:P_15")

    return data

def show(xml_path):
    tree = etree.parse(xml_path)
    root = tree.getroot()

    data = parse_invoice(root)

    html = "<html><body><h1>Faktura</h1>"
    html += f"Numer: {data['numer']}<br>"

    for i in data["items"]:
        html += f"{i['nazwa']} - {i['netto']}<br>"

    html += "</body></html>"

    f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    f.write(html.encode("utf-8"))
    f.close()

    webbrowser.open(f.name)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(sys.argv[1])
