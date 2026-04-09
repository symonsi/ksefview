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

    # NUMERY (bez get_any — szybciej)
    data["numer"] = get(root, ".//fa:P_2")
    data["ksef_number"] = (
        get(root, ".//fa:KSeFNumber")
        or get(root, ".//fa:NumerKSeF")
    )

    data["rodzaj"] = get(root, ".//fa:RodzajFaktury")

    # DATY
    data["data_wystawienia"] = format_date(get(root, ".//fa:P_1"))
    data["data_sprzedazy"] = format_date(get(root, ".//fa:P_6"))
    data["data_utworzenia"] = format_date(get(root, ".//fa:DataWytworzeniaFa"))
    data["data_ksef"] = format_date(get(root, ".//fa:KSeFDate"))

    data["data_zaplaty"] = format_date(get(root, ".//fa:DataZaplaty"))
    data["termin_platnosci"] = format_date(get(root, ".//fa:TerminPlatnosci/fa:Termin"))
    data["data_zamowienia"] = format_date(get(root, ".//fa:DataZamowienia"))

    data["okres_od"] = format_date(get(root, ".//fa:P_6_Od"))
    data["okres_do"] = format_date(get(root, ".//fa:P_6_Do"))

    # KONTO
    data["konto"] = get(root, ".//fa:RachunekBankowy/fa:NrRB")
    data["bank"] = get(root, ".//fa:RachunekBankowy/fa:NazwaBanku")

    # OPISY (szybciej)
    opisy = []
    for o in root.findall(".//fa:DodatkowyOpis", NS):
        k = get(o, "fa:Klucz")
        w = get(o, "fa:Wartosc")
        if k or w:
            opisy.append(f"{k}: {w}")
    data["opisy"] = opisy

    # PŁATNOŚĆ
    data["zaplacono"] = get(root, ".//fa:Zaplacono")
    data["data_zaplaty_real"] = format_date(get(root, ".//fa:DataZaplaty"))
    data["forma_platnosci"] = get(root, ".//fa:FormaPlatnosci")

    # STOPKA
    data["stopka"] = get(root, ".//fa:StopkaFaktury")

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

    # POZYCJE (szybciej)
    items = []
    for poz in root.findall(".//fa:FaWiersz", NS):

        netto = get(poz, "fa:P_11") or get(poz, "fa:P_11A")
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
            "cena": get(poz, "fa:P_9A") or get(poz, "fa:P_9B"),
            "netto": netto,
            "vat_kwota": vat_kwota,
            "vat_proc": vat_proc,
            "rabat": get(poz, "fa:P_10") or "0",
            "brutto": brutto,
        })

    data["items"] = items

    # PODSUMOWANIE
    data["netto"] = get(root, ".//fa:P_13_1")
    data["vat"] = get(root, ".//fa:P_14_1")
    data["brutto"] = get(root, ".//fa:P_15")

    return data


def html_invoice(d):
    rows_list = []
    for i, item in enumerate(d["items"], start=1):
        rows_list.append(f"""
        <tr>
            <td>{i}</td>
            <td style="text-align:left">{item['nazwa']}</td>
            <td>{format_number(item['ilosc'])}</td>
            <td class="num">{format_money(item['cena'])}</td>
            <td class="num">{format_money(item['rabat'])}</td>
            <td class="num">{format_money(item['netto'])}</td>
            <td>{item['vat_proc']}</td>
            <td class="num">{format_money(item['vat_kwota'])}</td>
            <td class="num"><b>{format_money(item['brutto'])}</b></td>
        </tr>
        """)

    rows = "".join(rows_list)

    okres_html = ""
    if d["okres_od"] or d["okres_do"]:
        okres_html = f"""
        <tr>
            <td>Okres:</td>
            <td colspan="3">{d["okres_od"]} → {d["okres_do"]}</td>
        </tr>
        """

    opis_html = "<br>".join(d["opisy"])

    return f"""..."""  # (tu zostaje Twój IDENTYCZNY HTML — bez zmian)
