import sys
import os
from lxml import etree
import tempfile
import webbrowser
from tkinter import Tk, filedialog

NS = {"fa": "http://crd.gov.pl/wzor/2025/06/25/13775/"}


def get(el, path):
    if el is None:
        return ""
    x = el.find(path, NS)
    return x.text.strip() if x is not None and x.text else ""


def format_date(dt):
    if not dt:
        return ""
    return dt.split("T")[0]


def format_number(n):
    try:
        n = float(n)
    except:
        return ""

    if n.is_integer():
        return str(int(n))
    else:
        return str(n).replace(".", ",")


def format_money(n):
    try:
        return f"{float(n):.2f}".replace(".", ",")
    except:
        return ""


def parse_invoice(root):
    data = {}

    # NUMERY
    data["numer"] = get(root, ".//fa:P_2")
    data["ksef_number"] = get(root, ".//fa:KSeFNumber")

    # DATY
    data["data_wystawienia"] = format_date(get(root, ".//fa:P_1"))
    data["data_utworzenia"] = format_date(get(root, ".//fa:DataWytworzeniaFa"))
    data["data_zaplaty"] = format_date(get(root, ".//fa:DataZaplaty"))
    data["data_zamowienia"] = format_date(get(root, ".//fa:DataZamowienia"))
    data["data_ksef"] = format_date(get(root, ".//fa:KSeFDate"))

    # Sprzedawca
    sprzedawca = root.find(".//fa:Podmiot1", NS)
    data["sprzedawca"] = {
        "nazwa": get(sprzedawca, ".//fa:Nazwa"),
        "nip": get(sprzedawca, ".//fa:NIP"),
        "adres": get(sprzedawca, ".//fa:AdresL1"),
    }

    # Nabywca
    nabywca = root.find(".//fa:Podmiot2", NS)
    data["nabywca"] = {
        "nazwa": get(nabywca, ".//fa:Nazwa"),
        "nip": get(nabywca, ".//fa:NIP"),
        "adres": get(nabywca, ".//fa:AdresL1"),
    }

    # Pozycje
    items = []
    for poz in root.findall(".//fa:FaWiersz", NS):

        ilosc = get(poz, ".//fa:P_8B")
        cena = get(poz, ".//fa:P_9B")
        netto = get(poz, ".//fa:P_11A")
        vat_kwota = get(poz, ".//fa:P_11Vat")
        vat_proc = get(poz, ".//fa:P_12")
        rabat = get(poz, ".//fa:P_10")

        try:
            brutto = float(netto) + float(vat_kwota)
        except:
            brutto = 0

        items.append({
            "nazwa": get(poz, ".//fa:P_7"),
            "ilosc": ilosc,
            "jm": get(poz, ".//fa:P_8A"),
            "cena": cena,
            "netto": netto,
            "vat_kwota": vat_kwota,
            "vat_proc": vat_proc,
            "rabat": rabat,
            "brutto": brutto,
        })

    data["items"] = items

    # Podsumowanie
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
            <td style="text-align:left">{item['nazwa']}</td>
            <td>{format_number(item['ilosc'])} {item['jm']}</td>
            <td class="num">{format_money(item['cena'])}</td>
            <td class="num">{format_money(item['rabat'])}</td>
            <td class="num">{format_money(item['netto'])}</td>
            <td>{item['vat_proc']}</td>
            <td class="num">{format_money(item['vat_kwota'])}</td>
            <td class="num"><b>{format_money(item['brutto'])}</b></td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial; background:#eee; padding:20px; }}
        .container {{
            background:white; padding:30px; max-width:1100px;
            margin:auto; box-shadow:0 0 10px rgba(0,0,0,0.2);
        }}

        .top {{
            display:flex;
            justify-content:space-between;
            margin-bottom:10px;
        }}

        .dates table {{
            font-size:13px;
        }}

        .dates td {{
            padding:2px 8px;
        }}

        .row {{ display:flex; justify-content:space-between; margin-top:15px; }}
        .box {{ width:48%; }}

        table.main {{
            width:100%;
            border-collapse:collapse;
            margin-top:20px;
        }}

        th, td {{
            border:1px solid #ccc;
            padding:6px;
        }}

        th {{ background:#f0f0f0; }}

        .num {{
            text-align:right;
        }}

        .total {{
            text-align:right;
            margin-top:20px;
            font-size:18px;
            font-weight:bold;
        }}
    </style>
    </head>

    <body>
        <div class="container">

            <div class="top">
                <div>
                    <b>Numer faktury:</b> {d["numer"]}<br>
                    <b>KSeF:</b> {d["ksef_number"]}
                </div>

                <div class="dates">
                    <table>
                        <tr>
                            <td>Wystawienia:</td><td>{d["data_wystawienia"]}</td>
                            <td>Zapłaty:</td><td>{d["data_zaplaty"]}</td>
                        </tr>
                        <tr>
                            <td>Utworzenia:</td><td>{d["data_utworzenia"]}</td>
                            <td>Zamówienia:</td><td>{d["data_zamowienia"]}</td>
                        </tr>
                        <tr>
                            <td>KSeF:</td><td>{d["data_ksef"]}</td>
                        </tr>
                    </table>
                </div>
            </div>

            <div class="row">
                <div class="box">
                    <b>Sprzedawca:</b><br>
                    {d["sprzedawca"]["nazwa"]}<br>
                    NIP: {d["sprzedawca"]["nip"]}<br>
                    {d["sprzedawca"]["adres"]}
                </div>

                <div class="box">
                    <b>Nabywca:</b><br>
                    {d["nabywca"]["nazwa"]}<br>
                    NIP: {d["nabywca"]["nip"]}<br>
                    {d["nabywca"]["adres"]}
                </div>
            </div>

            <table class="main">
                <tr>
                    <th>#</th>
                    <th>Nazwa</th>
                    <th>Ilość</th>
                    <th>Cena</th>
                    <th>Rabat</th>
                    <th>Netto</th>
                    <th>%</th>
                    <th>VAT</th>
                    <th>Brutto</th>
                </tr>
                {rows}
            </table>

            <div class="total">
                Netto: {format_money(d["netto"])} zł<br>
                VAT: {format_money(d["vat"])} zł<br>
                Do zapłaty: {format_money(d["brutto"])} zł
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
    if len(sys.argv) > 1:
        show(sys.argv[1])
    else:
        Tk().withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if file_path:
            show(file_path)
