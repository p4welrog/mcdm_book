"""Składa index.html: szablon + źródła pakietów mcdm_book i mcdm_cd, most web.py, xlrd i pliki .mcf z płyty.

python web/build.py            → index.html w katalogu głównym repozytorium
"""
import base64
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent

files = {}
for pkg in ("mcdm_cd", "mcdm_book"):
    for f in sorted((ROOT / pkg).glob("*.py")):
        if f.name != "__main__.py":
            files[f"{pkg}/{f.name}"] = {"text": f.read_text(encoding="utf-8")}
for f in sorted((ROOT / "mcdm_cd" / "data").glob("*.mcf")) + sorted((ROOT / "mcdm_cd" / "data").glob("*.json")):
    files[f"mcdm_cd/data/{f.name}"] = {"b64": base64.b64encode(f.read_bytes()).decode()}
files["web.py"] = {"text": (HERE / "web.py").read_text(encoding="utf-8")}
with zipfile.ZipFile(next((HERE / "vendor").glob("xlrd-*.whl"))) as z:
    for n in z.namelist():
        if n.startswith("xlrd/") and n.endswith(".py"):
            files[f"vendor/{n}"] = {"text": z.read(n).decode("utf-8")}
        if n.endswith("LICENSE"):
            files["vendor/xlrd/LICENSE"] = {"text": z.read(n).decode("utf-8")}

payload = json.dumps(files, ensure_ascii=False).replace("</", "<\\/")
html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__PYFILES__*/", payload)
out = ROOT / "index.html"
out.write_text(html, encoding="utf-8")
print(out, len(html.encode()) // 1024, "KB,", len(files), "plików")
