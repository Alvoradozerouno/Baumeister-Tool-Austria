"""
EIRA PDF ANALYSE: 6 Bauplaene - Realer Testlauf
Datum: 2026-05-20
Werkzeuge: PyMuPDF (fitz), re, hashlib

Ziel: PDF-Plaene analysieren -> EIRA Epistemic State bestimmen
"""

import fitz
import os
import re
import json
import hashlib
import sys
import codecs
from datetime import datetime

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

PDF_DIR = r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads"
OUTPUT_DIR = r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads\ORION-ROS2-Consciousness-Node\Baumeister-Tool-Austria\pdf_analysis"

PDF_FILES = [
    "09f CARPORT.pdf",
    "10d BBQ LOUNGE.pdf",
    "11aa EG Gesamtplan 100.pdf",
    "06u SCHNITTE CC, DD.pdf",
    "08r ANSICHTEN SUED+WEST.pdf",
    "07r ANSICHTEN NORD+OST.pdf",
]

# Plan-Typ Erkennung
PLAN_TYPES = {
    "CARPORT": ["CARPORT", "STELLPLATZ", "UBERDACUNG"],
    "BBQ_LOUNGE": ["BBQ", "LOUNGE", "TERRASSE", "GRILL"],
    "GRUNDRISS": ["GRUNDRISS", "GESAMTPLAN", "FLOOR PLAN", "M 1:100", "M 1:50"],
    "SCHNITT": ["SCHNITT", "SECTION", "SCHNITT A", "SCHNITT B", "SCHNITT C", "SCHNITT D"],
    "ANSICHT": ["ANSICHT", "ELEVATION", "FASSADE", "NORD", "SUD", "OST", "WEST"],
}

# Masse erkennen (Meter, cm)
DIM_PATTERNS = [
    r'(\d+[,.]?\d*)\s*[mM]\s*[xX\u00d7]\s*(\d+[,.]?\d*)\s*[mM]',  # 5.00m x 3.50m
    r'(\d+[,.]?\d*)\s*[xX\u00d7]\s*(\d+[,.]?\d*)\s*[mM]',          # 5.00 x 3.50m
    r'(\d+[,.]?\d*)\s*[mM]\s*[xX\u00d7]\s*(\d+[,.]?\d*)',          # 5.00m x 3.50
    r'(\d+[,.]?\d*)\s*[xX\u00d7]\s*(\d+[,.]?\d*)',                  # 5.00 x 3.50
    r'(\d+[,.]?\d*)\s*cm',                                           # 250cm
    r'(\d+[,.]?\d*)\s*[mM]',                                         # 5.00m
]

# Normen/Regeln erkennen
NORM_PATTERNS = [
    r'OIB', r'ONORM', r'EN\s*199', r'EUROCODE', r'BauKG',
    r'RL\s*\d+', r'RICHTLINIE', r'M 1:', r'MA\S*STAB',
]


def detect_plan_type(text):
    """Erkennt den Plan-Typ anhand von Keywords."""
    text_upper = text.upper()
    for plan_type, keywords in PLAN_TYPES.items():
        for kw in keywords:
            if kw in text_upper:
                return plan_type
    return "UNBEKANNT"


def extract_dimensions(text):
    """Extrahiert Masse aus dem Text."""
    dimensions = []
    for pattern in DIM_PATTERNS:
        matches = re.findall(pattern, text[:5000])
        for m in matches:
            if isinstance(m, tuple):
                dimensions.append(f"{m[0]}x{m[1]}")
            else:
                dimensions.append(m)
    return list(set(dimensions))[:10]


def detect_norms(text):
    """Erkennt erwahnte Normen und Richtlinien."""
    text_upper = text.upper()
    found = []
    for pattern in NORM_PATTERNS:
        matches = re.findall(pattern, text_upper)
        found.extend(matches)
    return list(set(found))[:10]


def compute_sha256(filepath):
    """SHA-256 Hash der PDF-Datei fur Audit Chain."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def determine_epistemic_state(pages, text_len, has_text, dimensions, plan_type):
    """Bestimmt den EIRA Epistemic State."""
    if not has_text and pages > 0:
        return "ABSTAIN", "Nur Bilder, kein Text extrahierbar"
    if text_len < 50:
        return "UNKNOWN", "Zu wenig Text fur Validierung"
    if plan_type == "UNBEKANNT":
        return "TRANSITION", "Plan-Typ nicht eindeutig erkennbar"
    if len(dimensions) == 0:
        return "TRANSITION", "Keine Masse erkannt, OCR moglicherweise notig"
    return "VERIFIED", "Text, Plan-Typ und Masse erkannt"


def analyze_pdf(pdf_name):
    """Analysiert eine einzelne PDF-Datei."""
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    
    if not os.path.exists(pdf_path):
        return {"file": pdf_name, "status": "NOT_FOUND"}
    
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        file_size = os.path.getsize(pdf_path)
        sha256 = compute_sha256(pdf_path)
        
        # Text extrahieren (alle Seiten)
        all_text = ""
        page_texts = []
        for i, page in enumerate(doc):
            text = page.get_text()
            all_text += text
            page_texts.append({"page": i+1, "text_len": len(text), "text_preview": text[:200].strip()})
        
        # Preview-Bild (Seite 1)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        first_page = doc[0]
        pix = first_page.get_pixmap(dpi=150)
        img_name = pdf_name.replace('.pdf', '_preview.png')
        img_path = os.path.join(OUTPUT_DIR, img_name)
        pix.save(img_path)
        
        # Analyse
        has_text = len(all_text.strip()) > 50
        plan_type = detect_plan_type(all_text)
        dimensions = extract_dimensions(all_text)
        norms = detect_norms(all_text)
        state, reason = determine_epistemic_state(num_pages, len(all_text), has_text, dimensions, plan_type)
        
        # Keywords extrahieren
        keywords = []
        for word in all_text.split():
            if len(word) > 4 and word.isupper():
                keywords.append(word)
        keywords = list(set(keywords))[:20]
        
        result = {
            "file": pdf_name,
            "status": "OK",
            "sha256": sha256,
            "pages": num_pages,
            "size_kb": round(file_size / 1024, 1),
            "text_len": len(all_text),
            "has_text": has_text,
            "plan_type": plan_type,
            "dimensions": dimensions,
            "norms": norms,
            "keywords": keywords,
            "epistemic_state": state,
            "epistemic_reason": reason,
            "preview": img_name,
            "page_details": page_texts[:3],  # Nur erste 3 Seiten
        }
        
        doc.close()
        return result
        
    except Exception as e:
        return {"file": pdf_name, "status": "ERROR", "error": str(e)}


def run_analysis():
    print("=" * 70)
    print("  EIRA PDF ANALYSE: 6 Bauplaene - Realer Testlauf")
    print(f"  Datum: {datetime.now().isoformat()}")
    print(f"  Werkzeuge: PyMuPDF {fitz.__version__}, re, hashlib")
    print("=" * 70)
    
    results = []
    for pdf_name in PDF_FILES:
        print(f"\n{'─' * 60}")
        print(f"  Analysiere: {pdf_name}")
        print(f"{'─' * 60}")
        
        result = analyze_pdf(pdf_name)
        results.append(result)
        
        if result.get("status") == "OK":
            print(f"  Seiten       : {result['pages']}")
            print(f"  Groesse      : {result['size_kb']} KB")
            print(f"  Text         : {result['text_len']} Zeichen")
            print(f"  Plan-Typ     : {result['plan_type']}")
            print(f"  EIRA State   : {result['epistemic_state']}")
            print(f"  EIRA Reason  : {result['epistemic_reason']}")
            if result['dimensions']:
                print(f"  Masse        : {', '.join(result['dimensions'][:5])}")
            if result['norms']:
                print(f"  Normen       : {', '.join(result['norms'][:5])}")
            print(f"  SHA-256      : {result['sha256'][:16]}...")
            print(f"  Preview      : {result['preview']}")
        elif result.get("status") == "NOT_FOUND":
            print(f"  [!!] Datei nicht gefunden")
        else:
            print(f"  [!!] Fehler: {result.get('error', 'unbekannt')}")
    
    # Zusammenfassung
    print(f"\n{'=' * 70}")
    print("  ZUSAMMENFASSUNG")
    print(f"{'=' * 70}")
    
    states = {}
    for r in results:
        if r.get("status") == "OK":
            state = r["epistemic_state"]
            states[state] = states.get(state, 0) + 1
    
    for state, count in sorted(states.items()):
        print(f"  {state:15s}: {count} Datei(en)")
    
    print(f"\n  Gesamt: {len([r for r in results if r.get('status') == 'OK'])}/{len(PDF_FILES)} analysiert")
    
    # JSON Report speichern
    report_path = os.path.join(OUTPUT_DIR, "eira_pdf_analysis_report.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis": "EIRA PDF Analyse",
            "date": datetime.now().isoformat(),
            "tool": f"PyMuPDF {fitz.__version__}",
            "results": results,
        }, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n  Report: {report_path}")
    print(f"{'=' * 70}")
    
    return results


if __name__ == "__main__":
    results = run_analysis()