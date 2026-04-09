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


def forma_platnosci_txt(v):
    return {
        "1": "gotówka",
        "2": "przelew",
        "3": "karta",
        "6": "przelew"
    }.get(v, v)


# 🔥 ZMIANA: dodany xml_path
def parse_invoice(root, xml_path):
    data = {}

    data["numer"] = get(root, ".//fa:P_2")

    ksef = get(root, ".//fa:KSeFNumber")

    # 🔥 FALLBACK NA NAZWĘ PLIKU
    if not ksef:
        ksef = os.path.splitext(os.path.basename(xml_path))[0]

    data["ksef_number"] = ksef

    data["data_wystawienia"] = format_date(get(root, ".//fa:P_1"))
    data["data_sprzedazy"] = format_date(get(root, ".//fa:P_6"))
    data["data_utworzenia"] = format_date(get(root, ".//fa:DataWytworzeniaFa"))
    data["data_ksef"] = format_date(get(root, ".//fa:KSeFDate"))
    data["data_zaplaty"] = format_date(get(root, ".//fa:DataZaplaty"))
    data["termin_platnosci"] = format_date(get(root, ".//fa:TerminPlatnosci/fa:Termin"))

    data["okres_od"] = format_date(get(root, ".//fa:P_6_Od"))
    data["okres_do"] = format_date(get(root, ".//fa:P_6_Do"))

    data["konto"] = get(root, ".//fa:RachunekBankowy/fa:NrRB")
    data["bank"] = get(root, ".//fa:RachunekBankowy/fa:NazwaBanku")

    opisy = []
    for o in root.findall(".//fa:DodatkowyOpis", NS):
        k = get(o, "fa:Klucz")
        w = get(o, "fa:Wartosc")
        if k or w:
            opisy.append(f"{k}: {w}")
    data["opisy"] = opisy

    data["zaplacono"] = get(root, ".//fa:Zaplacono")
    data["data_zaplaty_real"] = format_date(get(root, ".//fa:DataZaplaty"))
    data["forma_platnosci"] = get(root, ".//fa:FormaPlatnosci")

    data["stopka"] = get(root, ".//fa:StopkaFaktury")

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

    items = []
    for poz in root.findall(".//fa:FaWiersz", NS):
        netto = get(poz, "fa:P_11")
        vat_proc = get(poz, "fa:P_12")

        try:
            netto_f = float(netto)
            vat_f = float(vat_proc)
            vat_kwota = netto_f * vat_f / 100
            brutto = netto_f + vat_kwota
        except:
            vat_kwota = 0
            brutto = 0

        items.append({
            "nazwa": get(poz, "fa:P_7"),
            "ilosc": get(poz, "fa:P_8B"),
            "cena": get(poz, "fa:P_9A"),
            "netto": netto,
            "vat_kwota": vat_kwota,
            "vat_proc": vat_proc,
            "brutto": brutto,
        })

    data["items"] = items

    data["netto"] = get(root, ".//fa:P_13_1") or get(root, ".//fa:P_13_2")
    data["vat"] = get(root, ".//fa:P_14_1") or get(root, ".//fa:P_14_2")
    data["brutto"] = get(root, ".//fa:P_15")

    return data


def html_invoice(d):
    rows = ""

    vat_summary = {}

    for i, item in enumerate(d["items"], start=1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td style="text-align:left">{item['nazwa']}</td>
            <td>{format_number(item['ilosc'])}</td>
            <td class="num">{format_money(item['cena'])}</td>
            <td class="num">{format_money(item['netto'])}</td>
            <td>{item['vat_proc']}%</td>
            <td class="num">{format_money(item['vat_kwota'])}</td>
            <td class="num"><b>{format_money(item['brutto'])}</b></td>
        </tr>
        """

        rate = item["vat_proc"]
        vat_summary.setdefault(rate, {"netto": 0, "vat": 0})
        vat_summary[rate]["netto"] += float(item["netto"])
        vat_summary[rate]["vat"] += float(item["vat_kwota"])

    vat_rows = ""
    for rate, vals in vat_summary.items():
        vat_rows += f"""
        <tr>
            <td>{rate}%</td>
            <td class="num">{format_money(vals["netto"])}</td>
            <td class="num">{format_money(vals["vat"])}</td>
            <td class="num">{format_money(vals["netto"] + vals["vat"])}</td>
        </tr>
        """

    okres_html = ""
    if d["okres_od"] or d["okres_do"]:
        okres_html = f"<tr><td>Okres:</td><td>{d['okres_od']} → {d['okres_do']}</td></tr>"

    opis_html = "<br>".join(d["opisy"])

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial; background:#eee; padding:20px; }}
        .container {{ background:white; padding:30px; max-width:1100px; margin:auto; }}

        .top {{ display:flex; justify-content:space-between; }}
        .dates {{ width:350px; }}

        .row {{ display:flex; justify-content:space-between; margin-top:20px; }}
        .box {{ width:48%; }}

        .num {{ text-align:right; }}
        table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
        th, td {{ border:1px solid #ccc; padding:6px; }}
        th {{ background:#f0f0f0; }}

        .summary {{ width:300px; margin-left:auto; margin-top:20px; }}
        .summary td {{ border:none; padding:4px; }}

        .extra {{ margin-top:30px; }}

        .vat-left {{ width:50%; margin-top:20px; }}
    </style>
    </head>

    <body>
    <div class="container">

    <div class="top">
        <div>
            <h2>FAKTURA</h2>
            <b>Numer:</b> {d["numer"]}<br>
            <b>KSeF:</b> {d["ksef_number"]}<br>
        </div>

        <table class="dates">
            <tr><td>Wystawienia:</td><td>{d["data_wystawienia"]}</td></tr>
            <tr><td>Sprzedaży:</td><td>{d["data_sprzedazy"]}</td></tr>
            <tr><td>KSeF:</td><td>{d["data_ksef"]}</td></tr>
            <tr><td>Termin:</td><td>{d["termin_platnosci"]}</td></tr>
            {okres_html}
        </table>
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
            <th>#</th><th>Nazwa</th><th>Ilość</th><th>Cena</th><th>Netto</th><th>%</th><th>VAT</th><th>Brutto</th>
        </tr>
        {rows}
    </table>

    <table class="vat-left">
        <tr><th>VAT %</th><th>Netto</th><th>VAT</th><th>Brutto</th></tr>
        {vat_rows}
    </table>

    <table class="summary">
        <tr><td>Netto:</td><td class="num">{format_money(d["netto"])}</td></tr>
        <tr><td>VAT:</td><td class="num">{format_money(d["vat"])}</td></tr>
        <tr><td><b>Brutto:</b></td><td class="num"><b>{format_money(d["brutto"])}</b></td></tr>
    </table>

    <div class="extra">
        <b>Konto:</b> {d["konto"]} ({d["bank"]})<br><br>

        <b>Płatność:</b><br>
        Status: {"Zapłacona" if d["zaplacono"] == "1" else "Nie zapłacona"}<br>
        Data: {d["data_zaplaty_real"]}<br>
        Forma: {forma_platnosci_txt(d["forma_platnosci"])}<br><br>

        <b>Opis:</b><br>
        {opis_html}<br><br>

        {"<b>Uwagi:</b><br>" + d["stopka"] if d["stopka"] else ""}
    </div>

    </div>
    </body>
    </html>
    """


def show(xml_path):
    tree = etree.parse(xml_path)
    root = tree.getroot()

    # 🔥 ZMIANA
    data = parse_invoice(root, xml_path)

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
            
