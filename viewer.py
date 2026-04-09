import sys
import os
from lxml import etree
import tempfile
import webbrowser
from tkinter import Tk, filedialog

NS = {"fa": "http://crd.gov.pl/wzor/2025/06/25/13775/"}


def get(el, path):
    try:
        if el is None:
            return ""
        x = el.find(path, NS)
        return x.text.strip() if x is not None and x.text else ""
    except Exception as e:
        print("Błąd get:", e)
        return ""


def format_date(dt):
    try:
        return dt.split("T")[0] if dt else ""
    except:
        return ""


def format_money(n):
    try:
        return f"{float(n):.2f}".replace(".", ",")
    except:
        return ""


def parse_invoice(root):
    print("START parse_invoice")

    data = {}

    data["numer"] = get(root, ".//fa:P_2")
    data["ksef"] = get(root, ".//fa:KSeFNumber")

    print("Numer:", data["numer"])

    data["data"] = format_date(get(root, ".//fa:P_1"))

    # POZYCJE
    items = []
    for poz in root.findall(".//fa:FaWiersz", NS):
        print("Pozycja...")

        netto = get(poz, "fa:P_11")
        vat = get(poz, "fa:P_12")

        try:
            netto_f = float(netto)
            vat_f = float(vat)
            vat_kw = netto_f * vat_f / 100
            brutto = netto_f + vat_kw
        except:
            vat_kw = 0
            brutto = 0

        items.append({
            "nazwa": get(poz, "fa:P_7"),
            "netto": netto,
            "vat": vat,
            "brutto": brutto
        })

    data["items"] = items

    print("KONIEC parse_invoice")
    return data


def html_invoice(d):
    print("Buduję HTML")

    rows = ""
    for i, item in enumerate(d["items"], 1):
        rows += f"<tr><td>{i}</td><td>{item['nazwa']}</td><td>{item['netto']}</td></tr>"

    return f"""
    <html>
    <body>
    <h2>{d['numer']}</h2>
    <table border=1>
    {rows}
    </table>
    </body>
    </html>
    """


def show(xml_path):
    print("START show")

    try:
        print("Plik:", xml_path)

        if not os.path.exists(xml_path):
            print("❌ NIE MA PLIKU")
            input("Enter...")
            return

        print("Parsuję XML...")
        tree = etree.parse(xml_path)
        root = tree.getroot()

        print("XML OK")

        data = parse_invoice(root)

        html = html_invoice(data)

        print("Zapis HTML...")
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        f.write(html.encode("utf-8"))
        f.close()

        print("Plik:", f.name)

        webbrowser.open(f.name)

        print("OK KONIEC")
        input("Naciśnij Enter...")

    except Exception as e:
        print("❌ BŁĄD GŁÓWNY:", e)
        input("Enter...")


if __name__ == "__main__":
    print("START PROGRAM")

    try:
        Tk().withdraw()
        path = filedialog.askopenfilename(filetypes=[("XML", "*.xml")])

        print("Wybrany:", path)

        if path:
            show(path)
        else:
            print("Nie wybrano pliku")
            input("Enter...")

    except Exception as e:
        print("CRASH:", e)
        input("Enter...")
