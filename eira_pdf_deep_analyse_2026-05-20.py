"""
EIRA PDF DEEP ANALYSE: 6 Bauplaene - Volltext + Validierung
Datum: 2026-05-20
Werkzeuge: PyMuPDF (fitz), re, hashlib, json

Ziel: Vollstaendige Textextraktion, verbesserte Dimensions-Erkennung,
       ELSA Validierungsbericht, DDGK Audit-Log
"""

import fitz
import os
import re
import json
import hashlib
import sys
import codecs
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

PDF_DIR = r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "pdf_analysis")

PDF_FILES = [
    "09f CARPORT.pdf",
    "10d BBQ LOUNGE.pdf",
    "11aa EG Gesamtplan 100.pdf",
    "06u SCHNITTE CC, DD.pdf",
    "08r ANSICHTEN SUED+WEST.pdf",
    "07r ANSICHTEN NORD+OST.pdf",
]

# Plan-Typ Erkennung mit Praezision
PLAN_TYPES = {
    "CARPORT": ["CARPORT", "STELLPLATZ", "UBERDACUNG", "EINHAUSUNG"],
    "BBQ_LOUNGE": ["BBQ", "LOUNGE", "GRILLKAMIN", "GOLFAKADEMIE"],
    "GRUNDRISS": ["GRUNDRISS", "GESAMTPLAN", "M 1:100"],
    "SCHNITT": ["SCHNITT CC", "SCHNITT DD", "SCHNITT A-", "SCHNITT B-"],
    "ANSICHT": ["ANSICHT S", "ANSICHT W", "ANSICHT N", "ANSICHT O", "FASSADE"],
}

# Oesterreichische Massformate (Meter mit Komma)
# Filter: Nur werte zwischen 0.5 und 50 Meter sind realistische Baumasse
def extract_real_dimensions(text):
    """Extrahiert reale Baumasse (nicht Koordinaten)."""
    dimensions = []
    
    # Meter-Masse: 7,50 x 6,00 m oder 7.50x6.00
    pattern1 = r'(\d+[,.]\d{2})\s*[xX\u00d7]\s*(\d+[,.]\d{2})'
    for m in re.findall(pattern1, text):
        try:
            w = float(m[0].replace(',', '.'))
            h = float(m[1].replace(',', '.'))
            if 0.5 <= w <= 50 and 0.5 <= h <= 50:
                dimensions.append(f"{m[0]} x {m[1]} m")
        except:
            pass
    
    # Einzelwerte in Meter: 2,40 m, 2.30m
    pattern2 = r'(\d+[,.]\d{2})\s*m\b'
    for m in re.findall(pattern2, text):
        try:
            v = float(m.replace(',', '.'))
            if 0.5 <= v <= 50:
                dimensions.append(f"{m} m")
        except:
            pass
    
    # Hoehe/Hoehenangaben: +3,00, +2,60
    pattern3 = r'[+](\d+[,.]\d{2})'
    for m in re.findall(pattern3, text):
        try:
            v = float(m.replace(',', '.'))
            if 0 <= v <= 20:
                dimensions.append(f"OK +{m}")
        except:
            pass
    
    # cm-Angaben (nur wenn > 10cm und < 1000cm)
    pattern4 = r'(\d{2,3})\s*cm'
    for m in re.findall(pattern4, text):
        try:
            v = int(m)
            if 10 <= v <= 1000:
                dimensions.append(f"{m} cm")
        except:
            pass
    
    return list(dict.fromkeys(dimensions))[:15]  # Deduplizieren


def detect_norms_and_rules(text):
    """Erkennt Normen, OIB-Richtlinien, Bauvorschriften."""
    found = []
    text_upper = text.upper()
    
    # OIB Richtlinien
    oib_patterns = [r'OIB[-\s]*RL\s*\d+', r'OIB[-\s]*RICHTLINIE\s*\d+']
    for p in oib_patterns:
        found.extend(re.findall(p, text_upper))
    
    # Normen: EN 1992, OENORM B 1992, etc.
    norm_patterns = [
        r'EN\s*\d+[ -]?\d+',
        r'OENORM\s*[A-ZB]?\s*\d+[ -]?\d*',
        r'DIN\s*\d+',
        r'EUROCODE\s*\d+',
    ]
    for p in norm_patterns:
        found.extend(re.findall(p, text_upper))
    
    # BauKG, BauO
    if 'BAUKG' in text_upper:
        found.append('BauKG')
    if 'BAUO' in text_upper:
        found.append('BauO')
    if 'HOHE' in text_upper or 'HOHEN' in text_upper:
        found.append('Hohenregelung')
    
    # Statische Angaben
    if 'KB' in text_upper or 'KN/M' in text_upper:
        found.append('Krafteinleitung')
    if 'STB' in text_upper:
        found.append('Stahlbeton')
    if 'KLH' in text_upper or 'BSH' in text_upper:
        found.append('Holzbau')
    if 'FBH' in text_upper:
        found.append('Fussbodenheizung')
    
    return list(set(found))


def extract_keywords_structured(text, plan_type):
    """Strukturierte Keyword-Extraktion nach Kategorien."""
    text_upper = text.upper()
    
    categories = {
        "Bauteile": ["STB", "KLH", "BSH", "HOLZ", "STAHL", "BETON", "FENSTER", "TUER", "TOR",
                     "DECKE", "WAND", "BODEN", "DACH", "FUNDAMENT", "STUETZE"],
        "Technik": ["FBH", "HLK", "ELEKTRO", "WASSER", "KANAL", "LUEFTUNG", "HEIZUNG",
                    "STARKSTROM", "SOLAR", "PV", "NOTSTROM"],
        "Oertlichkeit": ["NORD", "SUED", "OST", "WEST", "TERRASSE", "GARTEN", "EINGANG",
                        "ZUGANG", "FAHRZEUG", "PKW"],
        "Massangaben": ["M 1:", "MASSSTAB", "MAS", "H= ", "+", "CM", "MM"],
        "Planung": ["ENTWURF", "AUSFUEHRUNG", "WERKPLANUNG", "EINREICHPLAN", "POLIERPLAN",
                   "BESTAND", "NEU", "ABBRECHEN"],
    }
    
    result = {}
    for cat, keywords in categories.items():
        found = [kw for kw in keywords if kw in text_upper]
        if found:
            result[cat] = found
    
    return result


def determine_elsa_validation(epistemic_state, dims, norms, keywords, plan_type):
    """ELSA Validierungs-Engine."""
    issues = []
    checks_passed = []
    
    # Check 1: Text verfuegbar
    if epistemic_state == "VERIFIED":
        checks_passed.append("Text extrahierbar")
    else:
        issues.append(f"Text nicht voll verfuegbar: {epistemic_state}")
    
    # Check 2: Plan-Typ erkennbar
    if plan_type != "UNBEKANNT":
        checks_passed.append(f"Plan-Typ: {plan_type}")
    else:
        issues.append("Plan-Typ nicht erkennbar")
    
    # Check 3: Masse vorhanden
    real_dims = [d for d in dims if not d.startswith('OK')]
    if len(real_dims) >= 2:
        checks_passed.append(f"{len(real_dims)} reale Masse erkannt")
    else:
        issues.append(f"Nur {len(real_dims)} reale Masse - unvollstaendig")
    
    # Check 4: Normen/Regeln
    if norms:
        checks_passed.append(f"Normen erkannt: {', '.join(norms[:3])}")
    else:
        issues.append("Keine Normen/Regeln erkannt")
    
    # Check 5: Bauteile vorhanden
    if "Bauteile" in keywords:
        checks_passed.append(f"Bauteile: {', '.join(keywords['Bauteile'][:3])}")
    else:
        issues.append("Keine Bauteile erkennbar")
    
    # Check 6: Technik-Infos
    if "Technik" in keywords:
        checks_passed.append(f"Technik: {', '.join(keywords['Technik'][:3])}")
    
    # ELSA Entscheidung
    if len(issues) == 0:
        decision = "EXECUTE"
        reason = "Alle Checks bestanden"
    elif len(issues) <= 2:
        decision = "DEFER"
        reason = f"Minor issues: {'; '.join(issues)}"
    else:
        decision = "ABSTAIN"
        reason = f"Major issues: {'; '.join(issues[:3])}"
    
    return {
        "decision": decision,
        "reason": reason,
        "checks_passed": checks_passed,
        "issues": issues,
    }


def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def analyze_pdf_deep(pdf_name):
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        return {"file": pdf_name, "status": "NOT_FOUND"}
    
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        file_size = os.path.getsize(pdf_path)
        sha256 = compute_sha256(pdf_path)
        
        # Volltext
        all_text = ""
        for page in doc:
            all_text += page.get_text()
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Preview
        first_page = doc[0]
        pix = first_page.get_pixmap(dpi=150)
        img_name = pdf_name.replace('.pdf', '_preview.png').replace(' ', '_')
        img_path = os.path.join(OUTPUT_DIR, img_name)
        pix.save(img_path)
        doc.close()
        
        # Analysen
        plan_type = "UNBEKANNT"
        text_upper = all_text.upper()
        for pt, kws in PLAN_TYPES.items():
            for kw in kws:
                if kw in text_upper:
                    plan_type = pt
                    break
            if plan_type != "UNBEKANNT":
                break
        
        dimensions = extract_real_dimensions(all_text)
        norms = detect_norms_and_rules(all_text)
        keywords = extract_keywords_structured(all_text, plan_type)
        
        epistemic_state = "VERIFIED" if len(all_text.strip()) > 50 else "ABSTAIN"
        
        elsa = determine_elsa_validation(epistemic_state, dimensions, norms, keywords, plan_type)
        
        # Volltext speichern
        txt_path = os.path.join(OUTPUT_DIR, pdf_name.replace('.pdf', '_fulltext.txt').replace(' ', '_'))
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(all_text)
        
        return {
            "file": pdf_name,
            "status": "OK",
            "sha256": sha256,
            "pages": num_pages,
            "size_kb": round(file_size / 1024, 1),
            "text_len": len(all_text),
            "plan_type": plan_type,
            "dimensions": dimensions,
            "norms_rules": norms,
            "categories": keywords,
            "epistemic_state": epistemic_state,
            "elsa_validation": elsa,
            "preview": img_name,
            "fulltext_file": os.path.basename(txt_path),
        }
        
    except Exception as e:
        return {"file": pdf_name, "status": "ERROR", "error": str(e)}


def run_deep_analysis():
    print("=" * 70)
    print("  EIRA PDF DEEP ANALYSE: 6 Bauplaene")
    print(f"  Datum: {datetime.now().isoformat()}")
    print(f"  Werkzeug: PyMuPDF {fitz.__version__}")
    print("=" * 70)
    
    results = []
    for pdf_name in PDF_FILES:
        print(f"\n{'='*60}")
        print(f"  {pdf_name}")
        print(f"{'='*60}")
        
        result = analyze_pdf_deep(pdf_name)
        results.append(result)
        
        if result.get("status") == "OK":
            print(f"  Seiten       : {result['pages']}")
            print(f"  Text         : {result['text_len']} Zeichen")
            print(f"  Plan-Typ     : {result['plan_type']}")
            print(f"  EIRA State   : {result['epistemic_state']}")
            print(f"  Dimensionen  : {len(result['dimensions'])} erkannt")
            for d in result['dimensions'][:8]:
                print(f"    - {d}")
            print(f"  Normen       : {len(result['norms_rules'])}")
            for n in result['norms_rules']:
                print(f"    - {n}")
            print(f"  Kategorien   : {list(result['categories'].keys())}")
            print(f"  ELSA Decision: {result['elsa_validation']['decision']}")
            print(f"  ELSA Reason  : {result['elsa_validation']['reason']}")
    
    # Zusammenfassung
    print(f"\n{'='*70}")
    print("  ELSA GESAMT-VALIDIERUNG")
    print(f"{'='*70}")
    
    decisions = {}
    for r in results:
        if r.get("status") == "OK":
            d = r["elsa_validation"]["decision"]
            decisions[d] = decisions.get(d, 0) + 1
    
    for d, c in sorted(decisions.items()):
        print(f"  {d:15s}: {c} Plan(e)")
    
    print(f"\n  Gesamt: {len([r for r in results if r.get('status') == 'OK'])}/{len(PDF_FILES)}")
    
    # Reports speichern
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # JSON Report
    report_path = os.path.join(OUTPUT_DIR, "eira_deep_analysis_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis": "EIRA PDF Deep Analyse",
            "date": datetime.now().isoformat(),
            "tool": f"PyMuPDF {fitz.__version__}",
            "results": results,
            "summary": decisions,
        }, f, indent=2, ensure_ascii=False, default=str)
    
    # DDGK Audit Log
    audit_path = os.path.join(OUTPUT_DIR, "ddgk_audit_log.jsonl")
    with open(audit_path, 'a', encoding='utf-8') as f:
        for r in results:
            if r.get("status") == "OK":
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "file": r["file"],
                    "sha256": r["sha256"],
                    "elsa_decision": r["elsa_validation"]["decision"],
                    "epistemic_state": r["epistemic_state"],
                    "plan_type": r["plan_type"],
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n  Reports:")
    print(f"    JSON: {report_path}")
    print(f"    Audit: {audit_path}")
    print(f"    Volltexte: {OUTPUT_DIR}")
    print(f"{'='*70}")
    
    return results


if __name__ == "__main__":
    run_deep_analysis()