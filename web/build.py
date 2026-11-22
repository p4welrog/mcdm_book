"""Składa index.html: szablon + źródła pakietów mcdm_book i mcdm_ryzyko, most web.py, xlrd, pliki .mcf z płyty
i mapa kotwic transkrypcji książki (book_anchors.json).

python web/build.py            → index.html w katalogu głównym repozytorium
"""
import base64
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent

files = {}
for pkg in ("mcdm_ryzyko", "mcdm_book"):
    for f in sorted((ROOT / pkg).rglob("*.py")):
        if f.name != "__main__.py" and "__pycache__" not in f.parts:
            files[f.relative_to(ROOT).as_posix()] = {"text": f.read_text(encoding="utf-8")}
for f in sorted((ROOT / "mcdm_book" / "data").glob("*.mcf")) + sorted((ROOT / "mcdm_book" / "data").glob("*.json")):
    files[f"mcdm_book/data/{f.name}"] = {"b64": base64.b64encode(f.read_bytes()).decode()}
files["web.py"] = {"text": (HERE / "web.py").read_text(encoding="utf-8")}
with zipfile.ZipFile(next((HERE / "vendor").glob("xlrd-*.whl"))) as z:
    for n in z.namelist():
        if n.startswith("xlrd/") and n.endswith(".py"):
            files[f"vendor/{n}"] = {"text": z.read(n).decode("utf-8")}
        if n.endswith("LICENSE"):
            files["vendor/xlrd/LICENSE"] = {"text": z.read(n).decode("utf-8")}

payload = json.dumps(files, ensure_ascii=False).replace("</", "<\\/")
# kotwice wersji webowej transkrypcji (generuje build.py transkrypcji: web_build/odsylacze.json)
book = (HERE / "book_anchors.json").read_text(encoding="utf-8").strip()
html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__PYFILES__*/", payload).replace("/*__BOOKMAP__*/", book)
# lista przykładów otwieranych z adresu (?example=…) — dla przycisków „Uruchom w aplikacji” w transkrypcji
import sys
sys.path.insert(0, str(ROOT))
from mcdm_book import examples as book_ex  # noqa: E402
from mcdm_book import api as book_api  # noqa: E402
app = {e["id"]: {"method": e["method"], "title": e["title"]} for e in book_ex.listing()}
for i, title in {"P8.1": "STEM-DPR (dialog), dane z przykładu 8.1", "P8.2": "STEM-DPR (dialog), dane z przykładu 8.1",
                 "P8.3": "INSDECM (dialog), dane z przykładu 8.1", "P8.4": "INSDECM (dialog), dane z przykładu 8.1",
                 "P8.5": "ATO-DPR (dialog), ustawienia przykładu 8.5", "R10": "STEM-DPR (dialog), 14 portfeli z rozdz. 10"}.items():
    app[i] = {"method": "dialog", "title": title}
(HERE / "app_examples.json").write_text(json.dumps(app, ensure_ascii=False, indent=1), encoding="utf-8")
out = ROOT / "index.html"
out.write_text(html, encoding="utf-8")
print(out, len(html.encode()) // 1024, "KB,", len(files), "plików")
