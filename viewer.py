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


def get_all(root, path):
    return [el.text.strip() for el in root.findall(path, NS) if el.text]


def get_any(root, tag):
    for el in root.iter():
        if el.tag.endswith(tag):
            return el.text.strip() if el.text else ""
    return ""


def format_date(dt):
    return dt.split("T")[0] if dt else ""


def format_number(n):
    try:
        n = float(n)
        return str(int(n)) if n.is_integer() else str(n).replace(".", ",")
    except:
        return ""


def format_money(n):
    try:
        return f"{float(n):.2f}".replace(".", ",")
    except:
        return ""


def parse_invoice(root):
    data = {}

    data["numer"] = get(root, ".//fa:P_2")

    data["ksef_number"] = (
        get(root, ".//fa:KSeFNumber")
        or get_any(root, "KSeFNumber")
    )

    # DATY
    data["data_wystawienia"] = format_date(get(root, ".//fa:P_1"))
    data["data_sprzedazy"] = format_date(get(root, ".//fa:P_6"))
    data["data_ksef"] = format_date(get(root, ".//fa:KSeFDate"))
    data["termin"] = format_date(get(root, ".//fa:TerminPlatnosci/fa:Termin"))

    # KONTO
    data["konto"] = get(root, ".//fa:RachunekBankowy/fa:NrRB")
    data["bank"] = get(root, ".//fa:RachunekBankowy/fa:NazwaBanku")

    # OPISY
    opisy = []
    for o in root.findall(".//fa:DodatkowyOpis", NS):
        k = get(o, ".//fa:Klucz")
        w = get(o, ".//fa:Wartosc")
        if k or w:
            opisy.append(f"{k}: {w}")
    data["opisy"] = opisy

    # PODMIOTY
    sprzedawca = root.find(".//fa:Podmiot1", NS)
    nabywca = root.find(".//fa:Podmiot2", NS)

    data["sprzedawca"] = {
        "nazwa": get(sprzedawca, ".//fa:Nazwa"),
        "nip": get(sprzedawca, ".//fa:NIP"),
        "adres": get(sprzedawca, ".//fa:AdresL1"),
    }

    data["nabywca"] = {
        "nazwa": get(nabywca, ".//fa:Nazwa"),
        "nip": get(nabywca, ".//fa:NIP"),
        "adres": get(nabywca, ".//fa:AdresL1"),
    }

    # POZYCJE
    items = []
    for poz in root.findall(".//fa:FaWiersz", NS):

        ilosc = get(poz, ".//fa:P_8B")
        cena = get(poz, ".//fa:P_9A")
        netto = get(poz, ".//fa:P_11")
        vat_proc = get(poz, ".//fa:P_12")

        try:
            netto_f = float(netto)
            vat_f = float(vat_proc)
            vat_kwota = netto_f * vat_f / 100
            brutto = netto_f + vat_kwota
        except:
            vat_kwota = 0
            brutto = 0

        items.append({
            "nazwa": get(poz, ".//fa:P_7"),
            "ilosc": ilosc,
            "cena": cena,
            "netto": netto,
            "vat_proc": vat_proc,
            "vat_kwota": vat_kwota,
            "brutto": brutto,
        })

    data["items"] = items

    data["netto"] = get(root, ".//fa:P_13_1")
    data["vat"] = get(root, ".//fa:P_14_1")
    data["brutto"] = get(root, ".//fa:P_15")

    return data


def html_invoice(d):
    rows = ""
    for i, item in enumerate(d["items"], 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td style="text-align:left">{item['nazwa']}</td>
            <td>{format_number(item['ilosc'])}</td>
            <td class="num">{format_money(item['cena'])}</td>
            <td class="num">{format_money(item['netto'])}</td>
            <td>{item['vat_proc']}</td>
            <td class="num">{format_money(item['vat_kwota'])}</td>
            <td class="num">{format_money(item['brutto'])}</td>
        </tr>
        """

    opisy_html = "<br>".join(d["opisy"])

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial; background:#eee; padding:20px; }}
        .container {{ background:white; padding:30px; max-width:1100px; margin:auto; }}
        .num {{ text-align:right; }}
        table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
        th, td {{ border:1px solid #ccc; padding:6px; }}
        th {{ background:#f0f0f0; }}
        .box {{ margin-top:20px; }}
    </style>
    </head>

    <body>
        <div class="container">

            <b>Numer:</b> {d["numer"]}<br>
            <b>KSeF:</b> {d["ksef_number"]}<br><br>

            <b>Daty:</b><br>
            Wystawienia: {d["data_wystawienia"]}<br>
            Sprzedaży: {d["data_sprzedazy"]}<br>
            Termin: {d["termin"]}<br>
            KSeF: {d["data_ksef"]}<br>

            <div class="box">
                <b>Sprzedawca:</b><br>
                {d["sprzedawca"]["nazwa"]}<br>
                {d["sprzedawca"]["adres"]}
            </div>

            <div class="box">
                <b>Nabywca:</b><br>
                {d["nabywca"]["nazwa"]}<br>
                {d["nabywca"]["adres"]}
            </div>

            <table>
                <tr>
                    <th>#</th>
                    <th>Nazwa</th>
                    <th>Ilość</th>
                    <th>Cena</th>
                    <th>Netto</th>
                    <th>%</th>
                    <th>VAT</th>
                    <th>Brutto</th>
                </tr>
                {rows}
            </table>

            <div class="box">
                <b>Do zapłaty:</b> {format_money(d["brutto"])} zł
            </div>

            <div class="box">
                <b>Konto:</b> {d["konto"]}<br>
                {d["bank"]}
            </div>

            <div class="box">
                <b>Opis:</b><br>
                {opisy_html}
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
    else:
        Tk().withdraw()
        path = filedialog.askopenfilename(filetypes=[("XML", "*.xml")])
        if path:
            show(path)
