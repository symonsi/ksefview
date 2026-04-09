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


def parse_invoice(root):
    data = {}

    data["numer"] = get(root, ".//fa:P_2")
    data["ksef_number"] = get(root, ".//fa:KSeFNumber") or get(root, ".//fa:NumerKSeF")

    # DATY
    data["data_wystawienia"] = format_date(get(root, ".//fa:P_1"))
    data["data_sprzedazy"] = format_date(get(root, ".//fa:P_6"))
    data["termin"] = format_date(get(root, ".//fa:TerminPlatnosci/fa:Termin"))

    data["okres_od"] = format_date(get(root, ".//fa:P_6_Od"))
    data["okres_do"] = format_date(get(root, ".//fa:P_6_Do"))

    # PŁATNOŚĆ
    data["zaplacono"] = get(root, ".//fa:Zaplacono")
    data["data_zaplaty"] = format_date(get(root, ".//fa:DataZaplaty"))
    data["forma"] = get(root, ".//fa:FormaPlatnosci")

    # KONTO
    data["konto"] = get(root, ".//fa:RachunekBankowy/fa:NrRB")
    data["bank"] = get(root, ".//fa:RachunekBankowy/fa:NazwaBanku")

    # OPIS
    opisy = []
    for o in root.findall(".//fa:DodatkowyOpis", NS):
        k = get(o, "fa:Klucz")
        w = get(o, "fa:Wartosc")
        if k or w:
            opisy.append(f"{k}: {w}")
    data["opisy"] = opisy

    # STOPKA
    data["stopka"] = get(root, ".//fa:StopkaFaktury")

    # POZYCJE + VAT
    items = []
    vat_map = {}

    for poz in root.findall(".//fa:FaWiersz", NS):

        netto = get(poz, "fa:P_11")
        vat_proc = get(poz, "fa:P_12")

        try:
            netto_f = float(netto)
        except:
            netto_f = 0

        try:
            vat_rate = float(vat_proc)
            vat_val = netto_f * vat_rate / 100
        except:
            vat_val = 0

        # VAT SUMMARY
        if vat_proc not in vat_map:
            vat_map[vat_proc] = {"netto": 0, "vat": 0}

        vat_map[vat_proc]["netto"] += netto_f
        vat_map[vat_proc]["vat"] += vat_val

        items.append({
            "nazwa": get(poz, "fa:P_7"),
            "ilosc": get(poz, "fa:P_8B"),
            "cena": get(poz, "fa:P_9A"),
            "netto": netto,
            "vat_proc": vat_proc,
            "vat": vat_val,
            "brutto": netto_f + vat_val
        })

    data["items"] = items
    data["vat_summary"] = vat_map

    # SUMY
    data["netto"] = sum(v["netto"] for v in vat_map.values())
    data["vat"] = sum(v["vat"] for v in vat_map.values())
    data["brutto"] = get(root, ".//fa:P_15")

    return data


def html_invoice(d):
    rows = ""
    for i, item in enumerate(d["items"], 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{item['nazwa']}</td>
            <td>{format_number(item['ilosc'])}</td>
            <td class="num">{format_money(item['cena'])}</td>
            <td class="num">{format_money(item['netto'])}</td>
            <td>{item['vat_proc']}</td>
            <td class="num">{format_money(item['vat'])}</td>
            <td class="num">{format_money(item['brutto'])}</td>
        </tr>
        """

    # VAT TABLE
    vat_rows = ""
    for stawka, v in d["vat_summary"].items():
        vat_rows += f"""
        <tr>
            <td>{stawka}</td>
            <td class="num">{format_money(v['netto'])}</td>
            <td class="num">{format_money(v['vat'])}</td>
            <td class="num">{format_money(v['netto'] + v['vat'])}</td>
        </tr>
        """

    vat_table = f"""
    <div style="margin-top:15px;">
    <b>VAT:</b>
    <table style="width:300px;">
        <tr>
            <th>%</th>
            <th>Netto</th>
            <th>VAT</th>
            <th>Brutto</th>
        </tr>
        {vat_rows}
        <tr>
            <th>SUMA</th>
            <th class="num">{format_money(d['netto'])}</th>
            <th class="num">{format_money(d['vat'])}</th>
            <th class="num">{format_money(d['netto'] + d['vat'])}</th>
        </tr>
    </table>
    </div>
    """

    okres = f"{d['okres_od']} → {d['okres_do']}" if d["okres_od"] else ""
    opis = "<br>".join(d["opisy"])

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial; padding:20px; }}
        table {{ border-collapse:collapse; width:100%; margin-top:10px; }}
        th, td {{ border:1px solid #ccc; padding:5px; }}
        th {{ background:#eee; }}
        .num {{ text-align:right; }}
    </style>
    </head>
    <body>

    <b>Numer:</b> {d["numer"]}<br>
    <b>KSeF:</b> {d["ksef_number"]}<br><br>

    <table>
        <tr>
            <td>Wyst:</td><td>{d["data_wystawienia"]}</td>
            <td>Sprzedaż:</td><td>{d["data_sprzedazy"]}</td>
            <td>Termin:</td><td>{d["termin"]}</td>
        </tr>
        <tr>
            <td>Okres:</td><td colspan="5">{okres}</td>
        </tr>
    </table>

    <table>
        <tr>
            <th>#</th><th>Nazwa</th><th>Ilość</th><th>Cena</th><th>Netto</th><th>%</th><th>VAT</th><th>Brutto</th>
        </tr>
        {rows}
    </table>

    {vat_table}

    <div style="margin-top:10px;">
        <b>Do zapłaty:</b> {format_money(d["brutto"])} zł<br><br>

        <b>Płatność:</b>
        {"Zapłacona" if d["zaplacono"]=="1" else "Nie zapłacona"},
        {forma_platnosci_txt(d["forma"])},
        {d["data_zaplaty"]}<br><br>

        <b>Konto:</b> {d["konto"]} {d["bank"]}<br><br>

        <b>Opis:</b><br>
        {opis}<br><br>

        {d["stopka"]}
    </div>

    </body>
    </html>
    """


def show(xml_path):
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()

        html = html_invoice(parse_invoice(root))

        f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        f.write(html.encode("utf-8"))
        f.close()

        webbrowser.open(f.name)
        input("Enter...")

    except Exception as e:
        print("BŁĄD:", e)
        input("Enter...")


if __name__ == "__main__":
    Tk().withdraw()
    path = filedialog.askopenfilename(filetypes=[("XML", "*.xml")])
    if path:
        show(path)
