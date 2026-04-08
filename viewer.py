import sys
from lxml import etree
import webbrowser
import tempfile

def show(xml_path):
    html = "<html><body><h2>Faktura KSeF</h2><pre>" + open(xml_path).read() + "</pre></body></html>"
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    f.write(html.encode("utf-8"))
    f.close()
    webbrowser.open(f.name)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(sys.argv[1])
