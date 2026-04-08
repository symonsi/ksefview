import sys
import os
from lxml import etree
import tempfile
import webbrowser
from tkinter import Tk, filedialog

NS = {"fa": "http://crd.gov.pl/wzor/2023/06/29/12648/"}


# bezpieczne pobieranie z namespace
def get(el, path):
    if el is None:
        return ""
    x = el.find(path, NS)
    return x.text.strip() if x is not None and x.text else ""


# fallback bez namespace (ważne dla różnych XML)
def get_any(root, tag):
    for el in root.iter():
        if el.tag.endswith(tag):
            return el.text.strip() if el.text else ""
    return ""


def parse_invoice(root):
    data = {}

    # podstawowe dane
    data["numer"] = get(root, ".//fa:P_2") or get_any(root, "P_2")
    data["data"] = get(root, ".//fa:P_1") or get_any(root, "P_1")

    # sprzedawca
    sprzedawca = root.find(".//fa:Podmiot1", NS)
    if sprzedawca is None:
        sprzedawca = root

    data["sprzedawca"] = {
        "nazwa": get(sprzedawca, ".//fa:Nazwa") or get_any(root, "Nazwa"),
        "nip": get(sprzedawca, ".//fa:NIP") or get_any(root, "NIP"),
        "ulica": get(sprzedawca, ".//fa:Ulica"),
        "miasto": get(sprzedawca, ".//fa:Miejscowosc"),
        "kod": get(sprzedawca, ".//fa:KodPocztowy"),
    }

    # nabywca
    nabywca = root.find(".//fa:Podmiot2", NS)
    if nabywca is None:
        nabywca = root

    data["nabywca"] = {
        "nazwa": get(nabywca, ".//fa:Nazwa"),
        "nip": get(nabywca, ".//fa:NIP"),
        "ulica": get(nabywca, ".//fa:Ulica"),
        "miasto": get(nabywca, ".//fa:Miejscowosc"),
        "kod": get(nabywca, ".//fa:KodPocztowy"),
    }

    # pozycje faktury
    items = []
    for poz in root.iter():
        if poz.tag.endswith("FakturaWiersz"):
            item = {
                "nazwa": get(poz, ".//fa:P_7") or get_any(poz, "P_7"),
                "ilosc": get(poz, ".//fa:P_8A") or get_any(poz, "P_8A"),
                "cena": get(poz, ".//fa:P_9A") or get_any(poz, "P_9A"),
                "netto": get(poz, ".//fa:P_11") or get_any(poz, "P_11"),
                "vat": get(poz, ".//fa:P_12") or get_any(poz, "P_12"),
            }
            items.append(item)

    data["items"] = items

    # podsumowanie
    data["netto"] = get(root, ".//fa:P_13_1") or get_any(root, "P_13_1")
    data["vat"] = get(root, ".//fa:P_14_1") or get_any(root, "P_14_1")
    data["brutto"] = get(root, ".//fa:P_15") or get_any(root, "P_15")

    return data


def html_invoice(d):
    rows = ""
    for i, item in enumerate(d["items"], start=1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{item['nazwa']}</td>
            <td>{item['ilosc']}</td>
            <td>{item['cena']}</td>
            <td>{item['netto']}</td>
            <td>{item['vat']}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial;
            background: #eee;
            padding: 20px;
        }}
        .container {{
            background: white;
            padding: 30px;
            max-width: 900px;
            margin: auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
        }}
        h1 {{
            text-align: center;
        }}
        .row {{
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
        }}
        .box {{
            width: 48%;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: center;
        }}
        th {{
            background: #f0f0f0;
        }}
        .total {{
            text-align: right;
            margin-top: 20px;
            font-size: 18px;
            font-weight: bold;
        }}
    </style>
    </head>

    <body>
        <div class="container">
            <h1>FAKTURA</h1>

            <p><b>Numer:</b> {d["numer"]} | <b>Data:</b> {d["data"]}</p>

            <div class="row">
                <div class="box">
                    <b>Sprzedawca:</b><br>
                    {d["sprzedawca"]["nazwa"]}<br>
                    NIP: {d["sprzedawca"]["nip"]}<br>
                    {d["sprzedawca"]["ulica"]}<br>
                    {d["sprzedawca"]["kod"]} {d["sprzedawca"]["miasto"]}
                </div>

                <div class="box">
                    <b>Nabywca:</b><br>
                    {d["nabywca"]["nazwa"]}<br>
                    NIP: {d["nabywca"]["nip"]}<br>
                    {d["nabywca"]["ulica"]}<br>
                    {d["nabywca"]["kod"]} {d["nabywca"]["miasto"]}
                </div>
            </div>

            <table>
                <tr>
                    <th>#</th>
                    <th>Nazwa</th>
                    <th>Ilość</th>
                    <th>Cena</th>
                    <th>Netto</th>
                    <th>VAT</th>
                </tr>
                {rows}
            </table>

            <div class="total">
                Netto: {d["netto"]} zł<br>
                VAT: {d["vat"]} zł<br>
                Do zapłaty: {d["brutto"]} zł
            </div>
        </div>
    </body>
    </html>
    """


def show(xml_path):
    if not os.path.exists(xml_path):
        print("Plik nie istnieje:", xml_path)
        input("Enter...")
        return

    tree = etree.parse(xml_path)
    root = tree.getroot()

    data = parse_invoice(root)
    html = html_invoice(data)

    f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    f.write(html.encode("utf-8"))
    f.close()

    webbrowser.open(f.name)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            show(sys.argv[1])
        else:
            Tk().withdraw()
            file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
            if file_path:
                show(file_path)
    except Exception as e:
        import traceback
        print("BŁĄD:", e)
        traceback.print_exc()
        input("Naciśnij Enter żeby zamknąć...")
