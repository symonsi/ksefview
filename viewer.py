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


def parse_invoice(root):
    data = {}

    # NUMERY
    data["numer"] = get(root, ".//fa:P_2")
    data["ksef_number"] = get(root, ".//fa:KSeFNumber")

    # DATY
    data["data_wystawienia"] = get(root, ".//fa:P_1")
    data["data_utworzenia"] = get(root, ".//fa:DataWytworzeniaFa")
    data["data_zaplaty"] = get(root, ".//fa:DataZaplaty")
    data["data_zamowienia"] = get(root, ".//fa:DataZamowienia")
    data["data_ksef"] = get(root, ".//fa:KSeFDate")

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

        ilosc = float(get(poz, ".//fa:P_8B") or 0)
        cena = float(get(poz, ".//fa:P_9B") or 0)
        netto = float(get(poz, ".//fa:P_11A") or 0)
        vat_kwota = float(get(poz, ".//fa:P_11Vat") or 0)

        wartosc = ilosc * cena
        rabat = wartosc - netto
        brutto = netto + vat_kwota

        items.append({
            "nazwa": get(poz, ".//fa:P_7"),
            "ilosc": ilosc,
            "jm": get(poz, ".//fa:P_8A"),
            "cena": cena,
            "netto": netto,
            "vat_kwota": vat_kwota,
            "vat_proc": get(poz, ".//fa:P_12"),
            "rabat": round(rabat, 2),
            "brutto": round(brutto, 2),
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
            <td>{item['ilosc']} {item['jm']}</td>
            <td>{item['cena']:.2f}</td>
            <td>{item['rabat']:.2f}</td>
            <td>{item['netto']:.2f}</td>
            <td>{item['vat_proc']}%</td>
            <td>{item['vat_kwota']:.2f}</td>
            <td><b>{item['brutto']:.2f}</b></td>
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
        h1 {{ text-align:center; }}
        .row {{ display:flex; justify-content:space-between; margin-top:10px; }}
        .box {{ width:48%; }}
        table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
        th, td {{ border:1px solid #ccc; padding:6px; text-align:center; }}
        th {{ background:#f0f0f0; }}
        .total {{ text-align:right; margin-top:20px; font-size:18px; font-weight:bold; }}
        .dates {{ margin-top:10px; font-size:14px; }}
    </style>
    </head>

    <body>
        <div class="container">
            <h1>FAKTURA</h1>

            <p>
                <b>Numer faktury:</b> {d["numer"]}<br>
                <b>Numer KSeF:</b> {d["ksef_number"]}
            </p>

            <div class="dates">
                Data wystawienia: {d["data_wystawienia"]}<br>
                Data utworzenia: {d["data_utworzenia"]}<br>
                Data zapłaty: {d["data_zaplaty"]}<br>
                Data zamówienia: {d["data_zamowienia"]}<br>
                Data KSeF: {d["data_ksef"]}
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

            <table>
                <tr>
                    <th>#</th>
                    <th>Nazwa</th>
                    <th>Ilość</th>
                    <th>Cena</th>
                    <th>Rabat</th>
                    <th>Netto</th>
                    <th>VAT %</th>
                    <th>VAT</th>
                    <th>Brutto</th>
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
    if len(sys.argv) > 1:
        show(sys.argv[1])
    else:
        Tk().withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if file_path:
            show(file_path)
