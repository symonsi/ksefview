import sys
from lxml import etree
import tempfile
import webbrowser
from tkinter import Tk, filedialog

NS = {"fa": "http://crd.gov.pl/wzor/2023/06/29/12648/"}


def get(el, path):
    x = el.find(path, NS)
    return x.text.strip() if x is not None and x.text else ""


def parse_invoice(root):
    data = {}

    data["numer"] = get(root, ".//fa:P_2")
    data["data"] = get(root, ".//fa:P_1")

    sprzedawca = root.find(".//fa:Podmiot1", NS)
    nabywca = root.find(".//fa:Podmiot2", NS)

    data["sprzedawca"] = {
        "nazwa": get(sprzedawca, ".//fa:Nazwa"),
        "nip": get(sprzedawca, ".//fa:NIP"),
    }

    data["nabywca"] = {
        "nazwa": get(nabywca, ".//fa:Nazwa"),
        "nip": get(nabywca, ".//fa:NIP"),
    }

    items = []
    for poz in root.findall(".//fa:FakturaWiersz", NS):
        items.append({
            "nazwa": get(poz, ".//fa:P_7"),
            "ilosc": get(poz, ".//fa:P_8A"),
            "netto": get(poz, ".//fa:P_11"),
        })

    data["items"] = items
    data["brutto"] = get(root, ".//fa:P_15")

    return data


def show(xml_path):
    tree = etree.parse(xml_path)
    root = tree.getroot()

    data = parse_invoice(root)

    html = f"<html><body><h1>Faktura {data['numer']}</h1>"

    for i in data["items"]:
        html += f"{i['nazwa']} - {i['netto']}<br>"

    html += f"<h2>Do zapłaty: {data['brutto']}</h2></body></html>"

    f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    f.write(html.encode("utf-8"))
    f.close()

    webbrowser.open(f.name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(sys.argv[1])
    else:
        # okno wyboru pliku
        Tk().withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if file_path:
            show(file_path)
