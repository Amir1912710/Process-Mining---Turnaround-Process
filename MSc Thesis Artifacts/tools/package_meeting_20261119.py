from pathlib import Path
import zipfile, hashlib, json
from reportlab.pdfgen import canvas
from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]
out = root / 'output/acdm_primary_20261119'
pdf = out / 'Professor_Meeting_2026-11-20.pdf'
c = canvas.Canvas(str(pdf), pagesize=(960, 540))
c.setTitle('Thesis progress, 12 October to 19 November 2026')
for image in sorted((out / 'final_slide_review').glob('slide-*.png')):
    c.drawImage(str(image), 0, 0, width=960, height=540)
    c.showPage()
c.save()
assert len(PdfReader(pdf).pages) == 21

# Start with the original complete template, then overlay subsequent revisions.
entries = {}
for folder in [root / 'output/overleaf_update/before', root / 'output/overleaf_update/language_revision', out / 'overleaf_updated']:
    for p in folder.rglob('*'):
        if p.is_file() and p.suffix.lower() not in {'.pdf', '.log', '.aux', '.out', '.toc', '.synctex'}:
            entries[p.relative_to(folder).as_posix()] = p
sourcezip = out / 'Thesis_ACDM_Primary_Source.zip'
with zipfile.ZipFile(sourcezip, 'w', zipfile.ZIP_DEFLATED) as z:
    for name, p in sorted(entries.items()):
        z.write(p, name)

package = out / 'Professor_Meeting_Package_2026-11-20.zip'
include = ['Professor_Meeting_2026-11-20_Final.pptx', pdf.name, sourcezip.name,
           'ACDM_Berlin_Primary_With_OpenSky_Check.csv',
           'BER_ACDM_Observed_Departures_UTC_Hypothesis.ocel.json',
           'opensky_departure_crosscheck.csv', 'daily_summary.csv', 'summary.json',
           'ocel_integrity.json', 'README.md', 'promenade_acdm_overview.jpg', 'overleaf_updated_proof.jpg']
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in include:
        z.write(out / name, name)
    for folder in ['prepared', 'exploratory_pilot_models']:
        for p in (out / folder).rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(out).as_posix())
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
manifest = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in [pdf, sourcezip, package, out / include[0]]}
(out / 'delivery_manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({'pdf_pages': 21, 'source_files': len(entries), 'outputs': manifest}, indent=2))
