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

    # Sprzedawca
    data["sprzedawca"] = {
        "nazwa": get(root, ".//fa:P_3A"),
        "nip": get(root, ".//fa:P_5A"),
        "adres": get(root, ".//fa:P_3A/fa:Adres")
    }

    # Nabywca
    data["nabywca"] = {
        "nazwa": get(root, ".//fa:P_3B"),
        "nip": get(root, ".//fa:P_5B"),
        "adres": get(root, ".//fa:P_3B/fa:Adres")
    }

    # Pozycje
    items = []
    for poz in get_all(root, ".//fa:FakturaWiersz"):
        item = {
            "nazwa": get(poz, ".//fa:P_7"),
            "ilosc": get(poz, ".//fa:P_8A"),
            "cena": get(poz, ".//fa:P_9A"),
            "netto": get(poz, ".//fa:P_11"),
            "vat": get(poz, ".//fa:P_12"),
        }
        items.append(item)

    data["items"] = items

    data["netto"] = get(root, ".//fa:P_13_1")
    data["vat"] = get(root, ".//fa:P_14_1")
    data["brutto"] = get(root, ".//fa:P_15")

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
                </div>
                <div class="box">
                    <b>Nabywca:</b><br>
                    {d["nabywca"]["nazwa"]}<br>
                    NIP: {d["nabywca"]["nip"]}<br>
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
    tree = etree.parse(xml_path)
    root = tree.getroot()

    data = parse_invoice(root)
    html = html_invoice(data)

    f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    f.write(html.encode("utf-8"))
    f.close()

    webbrowser.open(f.name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(sys.argv[1])
