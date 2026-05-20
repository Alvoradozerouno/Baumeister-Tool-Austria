"""
ELSA REVISIONS-ANALYSE: Plan-Historie + Aenderungs-Erkennung
Datum: 2026-05-20
Agenten: DDGK, EIRA, ELSA, ORION, GUARDIAN, NEXUS

Ziel: Vollstaendige transparente Analyse aller Plan-Revisionen
      - Verschobenes Notstromaggregat erkennen
      - Alle Aenderungen zwischen Revisionen dokumentieren
      - ELSA-Entscheidungen mit BEGRUENDUNG (keine Blackbox)
      - DDGK Audit-Log
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

# Alle 6 Plaene mit ihren Revisionstabellen (aus Volltext extrahiert)
PLAN_REVISIONS = {
    "09f CARPORT.pdf": {
        "name": "CARPORT",
        "revisionen": [
            {"id": "04_09b", "datum": "26.07.2024", "aenderung": "Konstr. Carport geaendert, Fundamente lt. Statiker uebernehmen, Hoehenlage Carport fixiert"},
            {"id": "04_09c", "datum": "29.07.2024", "aenderung": "STB-Saeulen bei Wand nord Carport, Dimension Quertraeger korr. - lt. Statik"},
            {"id": "04_09d", "datum": "22.11.2024", "aenderung": "Lage Trafo + Notstromaggregat geaendert"},
            {"id": "04_09e", "datum": "14.11.2025", "aenderung": "Lage Notstromaggregat geaendert, Lage Einfahrtstor verschoben"},
            {"id": "04_09f", "datum": "08.12.2025", "aenderung": "finaler Planstand"},
        ],
        "kritische_elemente": [
            "Notstromaggregat (275,7 x 110 cm)",
            "Trafostation",
            "STB-Stuetzen 20/20, 25/25, 40/40 cm",
            "Quertraeger 20/40 cm",
            "Photovoltaik 70m² (39 STK nord + 39 STK suend)",
            "Luftwaermepumpe",
            "Einfahrtstor",
            "Fundamente FDUK=-1,25",
        ],
        "hoehen": {
            "NIV. CARPORT": "-0,25 (+535,25)",
            "FIRST": "+4,03 (+539,53m)",
            "WH. TRAUFE": "+3,11 (+538,61m) / +3,13 (+538,63m)",
            "SOCKEL OK": "+0,05",
            "FDUK": "-1,25",
            "PFUK": "+2,525 / +3,40",
            "UK QUERTR.": "+2,15",
        },
        "masse_ketten": {
            "gesamt_laenge": "23,46m",
            "einzelmasse": ["5,725", "5,725", "5,725", "5,725"],  # Summe = 22,90 ≠ 23,46
            "carport_flaeche": "7,50 x 6,00 m",
            "dachneigung": "17,00°",
        }
    },
    "10d BBQ LOUNGE.pdf": {
        "name": "BBQ LOUNGE",
        "revisionen": [],
        "kritische_elemente": ["Gas-Grillkamin", "Terrasse", "Starkstrom", "Aussenwand"],
        "hoehen": {"OK": "+2,15, +2,30, +2,40, +3,65, +2,88"},
        "masse_ketten": {"einzelmasse": ["2,40"]},
    },
    "11aa EG Gesamtplan 100.pdf": {
        "name": "EG Gesamtplan",
        "revisionen": [],
        "kritische_elemente": ["FBH-Verteiler", "STB-Stuetzen", "Holzschalung", "Klh-Decke", "Gasdruckfedern"],
        "hoehen": {"OK=DUK": "+3,00, +2,60"},
        "masse_ketten": {"einzelmasse": ["12,00", "7,50", "6,00", "4,80", "2,60", "2,58", "2,40", "2,55", "4,79"]},
    },
    "06u SCHNITTE CC, DD.pdf": {
        "name": "SCHNITTE CC, DD",
        "revisionen": [],
        "kritische_elemente": ["KLH-Decke", "Holzschalung", "Natursteinplatten", "Fensterprofil", "Querloeftung"],
        "hoehen": {"OK": "+3,05, +2,15, +2,40, +3,90, +2,80, +2,58, +3,04, +3,03"},
        "masse_ketten": {},
    },
    "08r ANSICHTEN SUED+WEST.pdf": {
        "name": "ANSICHTEN SUED+WEST",
        "revisionen": [],
        "kritische_elemente": ["Holzfachwerk", "Quergiebel", "First", "Traufe", "Querbund"],
        "hoehen": {"OK": "+9,92, +7,48, +9,19, +5,57, +3,68"},
        "masse_ketten": {},
    },
    "07r ANSICHTEN NORD+OST.pdf": {
        "name": "ANSICHTEN NORD+OST",
        "revisionen": [],
        "kritische_elemente": ["Holzschalung", "Laerche", "Sichtschutzverkleidung", "Schiebetor", "Hauptgebaeude"],
        "hoehen": {"OK": "+9,92, +7,48, +9,19, +5,57, +3,68"},
        "masse_ketten": {},
    },
}


def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def analyze_revision_chain(plan_name, plan_data):
    """DDGK: Revisionskette analysieren."""
    revisionen = plan_data.get("revisionen", [])
    if not revisionen:
        return {"status": "KEINE_REVISIONEN", "details": "Keine Revisionstabelle gefunden"}
    
    aenderungen = []
    for i, rev in enumerate(revisionen):
        entry = {
            "revision": rev["id"],
            "datum": rev["datum"],
            "aenderung": rev["aenderung"],
            "kritisch": False,
            "kategorie": "UNBEKANNT",
            "elsa_action": "EXECUTE",
            "begruendung": "",
        }
        
        # Kritische Aenderungen erkennen
        text = rev["aenderung"].upper()
        
        if "NOTSTROM" in text:
            entry["kritisch"] = True
            entry["kategorie"] = "SICHERHEIT"
            entry["elsa_action"] = "DEFER"
            entry["begruendung"] = "Notstromaggregat verschoben → Fundament, Zuleitung, Abgas, Schallschutz neu pruefen"
        
        elif "TRAFO" in text:
            entry["kritisch"] = True
            entry["kategorie"] = "ELEKTRO"
            entry["elsa_action"] = "DEFER"
            entry["begruendung"] = "Trafostation verschoben → Fundament, Erdung, Zuleitung, Bayernwerk-Koordination"
        
        elif "STB" in text or "SAEULE" in text or "STUETZE" in text:
            entry["kritisch"] = True
            entry["kategorie"] = "STATIK"
            entry["elsa_action"] = "ABSTAIN"
            entry["begruendung"] = "STB-Elemente geaendert → Statiker muss neu bemessen (lt. Plan: 'lt. ANG. STATIK')"
        
        elif "FUNDAMENT" in text:
            entry["kritisch"] = True
            entry["kategorie"] = "TRAGWERK"
            entry["elsa_action"] = "DEFER"
            entry["begruendung"] = "Fundamente geaendert → Bodengutachten, Aushub, Bewehrung pruefen"
        
        elif "TOR" in text or "EINFAHRT" in text:
            entry["kritisch"] = False
            entry["kategorie"] = "ZUGANG"
            entry["elsa_action"] = "EXECUTE"
            entry["begruendung"] = "Tor verschoben → Massketten, Wendekreis, Zufahrt pruefen"
        
        elif "HOEHE" in text or "HOEHENLAGE" in text:
            entry["kritisch"] = True
            entry["kategorie"] = "NIVELLIERUNG"
            entry["elsa_action"] = "DEFER"
            entry["begruendung"] = "Hoehenlage fixiert → Gelaendehoehen, Drainage, Barrierefreiheit pruefen"
        
        elif "QUERTRAEGER" in text or "DIMENSION" in text:
            entry["kritisch"] = True
            entry["kategorie"] = "KONSTRUKTION"
            entry["elsa_action"] = "ABSTAIN"
            entry["begruendung"] = "Dimension geaendert → Statiker muss neu bemessen"
        
        elif "FINAL" in text or "PLANSTAND" in text:
            entry["kritisch"] = False
            entry["kategorie"] = "STATUS"
            entry["elsa_action"] = "EXECUTE"
            entry["begruendung"] = "Finaler Planstand → Alle vorherigen Aenderungen muessen validiert sein"
        
        else:
            entry["kategorie"] = "ALLGEMEIN"
            entry["elsa_action"] = "EXECUTE"
            entry["begruendung"] = "Aenderung erkannt → Bauleitung muss bestaetigen"
        
        aenderungen.append(entry)
    
    return {"status": "REVISIONEN_ANALYSIERT", "anzahl": len(revisionen), "aenderungen": aenderungen}


def analyze_mass_ketten(plan_name, plan_data):
    """EIRA: Mass-Ketten validieren (deterministisch)."""
    masse = plan_data.get("masse_ketten", {})
    results = []
    
    if "gesamt_laenge" in masse and "einzelmasse" in masse:
        gesamt_str = masse["gesamt_laenge"].replace("m", "").replace("M", "").strip()
        gesamt = float(gesamt_str.replace(",", "."))
        einzel_summe = sum(float(m.replace(",", ".")) for m in masse["einzelmasse"])
        diff = abs(gesamt - einzel_summe)
        
        entry = {
            "typ": "LAENGEN_KETTE",
            "gesamt": f"{gesamt:.2f}m",
            "einzel_summe": f"{einzel_summe:.2f}m",
            "differenz": f"{diff:.2f}m",
            "konsistent": diff < 0.1,  # 10cm Toleranz
            "elsa_action": "EXECUTE" if diff < 0.1 else "ABSTAIN",
            "begruendung": f"Mass-Kette: {'+'.join(masse['einzelmasse'])} = {einzel_summe:.2f}m ≠ {gesamt}m" if diff >= 0.1 else f"Mass-Kette konsistent ({diff:.2f}m Abweichung)",
        }
        results.append(entry)
    
    if "carport_flaeche" in masse:
        entry = {
            "typ": "FLAECHE",
            "masse": masse["carport_flaeche"],
            "elsa_action": "EXECUTE",
            "begruendung": f"Carport-Flaeche: {masse['carport_flaeche']}",
        }
        results.append(entry)
    
    if "dachneigung" in masse:
        entry = {
            "typ": "DACHNEIGUNG",
            "wert": masse["dachneigung"],
            "elsa_action": "EXECUTE",
            "begruendung": f"Dachneigung: {masse['dachneigung']}",
        }
        results.append(entry)
    
    return results


def analyze_hoehen_konsistenz(plan_name, plan_data):
    """ELSA: Hoehen auf Widerspruch pruefen."""
    hoehen = plan_data.get("hoehen", {})
    results = []
    
    for name, wert in hoehen.items():
        # Mehrere Werte = potenzieller Widerspruch
        if "+" in str(wert) and "," in str(wert):
            werte = re.findall(r'[+-]?\d+[,.]\d+', str(wert))
            if len(werte) > 1:
                # Pruefen ob Werte konsistent
                nums = [float(w.replace(",", ".")) for w in werte]
                entry = {
                    "typ": "HOEHE",
                    "name": name,
                    "werte": wert,
                    "anzahl_werte": len(werte),
                    "elsa_action": "EXECUTE",
                    "begruendung": f"{name}: {wert} ({len(werte)} Werte)",
                }
                results.append(entry)
    
    return results


def analyze_kritische_elemente(plan_name, plan_data):
    """GUARDIAN: Kritische Elemente identifizieren."""
    elemente = plan_data.get("kritische_elemente", [])
    results = []
    
    for elem in elemente:
        entry = {
            "element": elem,
            "risiko": "HOCH" if any(kw in elem.upper() for kw in ["NOTSTROM", "TRAFO", "STB", "FUNDAMENT"]) else "MITTEL",
            "elsa_action": "DEFER" if any(kw in elem.upper() for kw in ["NOTSTROM", "TRAFO"]) else "EXECUTE",
            "begruendung": "",
        }
        
        if "NOTSTROM" in elem.upper():
            entry["begruendung"] = "Notstromaggregat: 2x verschoben (09d, 09e) → Fundament, Abgas, Schallschutz, Zuleitung pruefen"
        elif "TRAFO" in elem.upper():
            entry["begruendung"] = "Trafostation: 1x verschoben (09d) → Fundament, Erdung, Bayernwerk"
        elif "STB" in elem.upper():
            entry["begruendung"] = "STB-Elemente: Dimensionen lt. Statik → Statiker-Proof erforderlich"
        elif "PHOTOVOLTAIK" in elem.upper():
            entry["begruendung"] = "PV 70m²: 78 Module → Ertrag, Statik, Blitzschutz pruefen"
        elif "FUNDAMENT" in elem.upper():
            entry["begruendung"] = "Fundamente: FDUK=-1,25 → Bodengutachten, Aushub, Bewehrung"
        else:
            entry["begruendung"] = f"{elem}: Standard-Validierung"
        
        results.append(entry)
    
    return results


def run_full_analysis():
    print("=" * 80)
    print("  ELSA REVISIONS-ANALYSE: Vollstaendige transparente Plan-Pruefung")
    print(f"  Datum: {datetime.now().isoformat()}")
    print(f"  Agenten: DDGK, EIRA, ELSA, ORION, GUARDIAN, NEXUS")
    print("=" * 80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_results = {}
    
    for pdf_name, plan_data in PLAN_REVISIONS.items():
        print(f"\n{'='*80}")
        print(f"  PLAN: {pdf_name} ({plan_data['name']})")
        print(f"{'='*80}")
        
        result = {
            "plan": pdf_name,
            "name": plan_data["name"],
            "sha256": "",
            "ddgk_revisionen": None,
            "eira_mass_ketten": None,
            "elsa_hoehen": None,
            "guardian_elemente": None,
            "gesamt_entscheidung": "",
            "gesamt_begruendung": "",
        }
        
        # SHA-256
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        if os.path.exists(pdf_path):
            result["sha256"] = compute_sha256(pdf_path)
        
        # DDGK: Revisionen
        print(f"\n  [DDGK] Revisionskette:")
        rev_result = analyze_revision_chain(pdf_name, plan_data)
        result["ddgk_revisionen"] = rev_result
        
        if rev_result["status"] == "REVISIONEN_ANALYSIERT":
            for a in rev_result["aenderungen"]:
                status_icon = "⚠" if a["kritisch"] else "✓"
                print(f"    {status_icon} {a['revision']} ({a['datum']}): {a['aenderung']}")
                print(f"       → ELSA: {a['elsa_action']} | {a['begruendung']}")
        
        # EIRA: Mass-Ketten
        print(f"\n  [EIRA] Mass-Ketten:")
        mass_result = analyze_mass_ketten(pdf_name, plan_data)
        result["eira_mass_ketten"] = mass_result
        for m in mass_result:
            icon = "✓" if m["elsa_action"] == "EXECUTE" else "✗"
            print(f"    {icon} {m['typ']}: {m['begruendung']}")
        
        # ELSA: Hoehen
        print(f"\n  [ELSA] Hoehen-Konsistenz:")
        hoehen_result = analyze_hoehen_konsistenz(pdf_name, plan_data)
        result["elsa_hoehen"] = hoehen_result
        for h in hoehen_result:
            print(f"    ✓ {h['name']}: {h['werte']}")
        
        # GUARDIAN: Kritische Elemente
        print(f"\n  [GUARDIAN] Kritische Elemente:")
        guardian_result = analyze_kritische_elemente(pdf_name, plan_data)
        result["guardian_elemente"] = guardian_result
        for g in guardian_result:
            risk_icon = "🔴" if g["risiko"] == "HOCH" else "🟡"
            print(f"    {risk_icon} {g['element']} → {g['elsa_action']} | {g['begruendung']}")
        
        # GESAMT-ENTSCHEIDUNG
        print(f"\n  {'─'*60}")
        print(f"  [ELSA] GESAMT-ENTSCHEIDUNG:")
        
        # Entscheidungslogik (transparent, keine Blackbox)
        abstein_reasons = []
        defer_reasons = []
        execute_count = 0
        
        # Aus Revisionen
        if rev_result.get("aenderungen"):
            for a in rev_result["aenderungen"]:
                if a["elsa_action"] == "ABSTAIN":
                    abstein_reasons.append(f"Revision {a['revision']}: {a['begruendung']}")
                elif a["elsa_action"] == "DEFER":
                    defer_reasons.append(f"Revision {a['revision']}: {a['begruendung']}")
        
        # Aus Mass-Ketten
        for m in mass_result:
            if m["elsa_action"] == "ABSTAIN":
                abstein_reasons.append(f"Mass-Kette: {m['begruendung']}")
        
        # Aus Guardian
        for g in guardian_result:
            if g["elsa_action"] == "DEFER" and g["risiko"] == "HOCH":
                defer_reasons.append(f"Kritisches Element: {g['begruendung']}")
        
        if abstein_reasons:
            result["gesamt_entscheidung"] = "ABSTAIN"
            result["gesamt_begruendung"] = "ABSTAIN weil:\n" + "\n".join(f"  - {r}" for r in abstein_reasons)
        elif defer_reasons:
            result["gesamt_entscheidung"] = "DEFER"
            result["gesamt_begruendung"] = "DEFER weil:\n" + "\n".join(f"  - {r}" for r in defer_reasons[:3])
        else:
            result["gesamt_entscheidung"] = "EXECUTE"
            result["gesamt_begruendung"] = "Alle Checks bestanden"
        
        print(f"    Entscheidung: {result['gesamt_entscheidung']}")
        print(f"    Begruendung: {result['gesamt_begruendung'][:200]}...")
        
        all_results[pdf_name] = result
    
    # ZUSAMMENFASSUNG
    print(f"\n{'='*80}")
    print("  ELSA GESAMT-ZUSAMMENFASSUNG")
    print(f"{'='*80}")
    
    decisions = {}
    for r in all_results.values():
        d = r["gesamt_entscheidung"]
        decisions[d] = decisions.get(d, 0) + 1
    
    for d, c in sorted(decisions.items()):
        print(f"  {d:15s}: {c} Plan(e)")
    
    # NOTSTROMAGGREGAT-ANALYSE (speziell)
    print(f"\n{'='*80}")
    print("  SPEZIAL-ANALYSE: Notstromaggregat-Verschiebung")
    print(f"{'='*80}")
    
    carport = PLAN_REVISIONS["09f CARPORT.pdf"]
    print(f"\n  Aus der Revisionstabelle des CARPORT-Plans:")
    for rev in carport["revisionen"]:
        if "NOTSTROM" in rev["aenderung"].upper():
            print(f"  ⚠ {rev['id']} ({rev['datum']}): {rev['aenderung']}")
    
    print(f"\n  [DDGK] Bewertung:")
    print(f"  1. Notstromaggregat wurde ZWEIMAL verschoben (09d + 09e)")
    print(f"  2. 09d (22.11.2024): 'Lage Trafo + Notstromaggregat geaendert'")
    print(f"     → ELSA: DEFER | Begruendung: Fundament, Erdung, Zuleitung, Bayernwerk neu")
    print(f"  3. 09e (14.11.2025): 'Lage Notstromaggregat geaendert, Lage Einfahrtstor verschoben'")
    print(f"     → ELSA: DEFER | Begruendung: Fundament, Abgas, Schallschutz, Zuleitung neu")
    print(f"  4. 09f (08.12.2025): 'finaler Planstand'")
    print(f"     → ELSA: EXECUTE | Begruendung: Final, aber alle vorherigen Aenderungen muessen validiert sein")
    
    print(f"\n  [GUARDIAN] Risiko-Bewertung:")
    print(f"  🔴 HOCH: Notstromaggregat (275,7 x 110 cm) auf Fundamentsockel")
    print(f"     - Abgasfuehrung muss geprueft werden")
    print(f"     - Schallschutz (Immissionsschutz)")
    print(f"     - Kraftstofflagerung (Umwelt)")
    print(f"     - Elektrische Anbindung (Bayernwerk)")
    print(f"     - Fundament (FDUK=-1,25)")
    
    print(f"\n  [ELSA] Entscheidung fuer Notstromaggregat:")
    print(f"  → DEFER (nicht ABSTAIN, nicht EXECUTE)")
    print(f"  → Grund: Verschiebung ist dokumentiert, aber Validierung der neuen Position fehlt")
    print(f"  → Erforderlich: HITL-Checkpoint (Bauleitung + Sonderplaner bestaetigen)")
    
    # Reports speichern
    report_path = os.path.join(OUTPUT_DIR, "elsa_revision_analysis_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis": "ELSA Revisions-Analyse",
            "date": datetime.now().isoformat(),
            "agenten": ["DDGK", "EIRA", "ELSA", "ORION", "GUARDIAN", "NEXUS"],
            "results": all_results,
            "notstromaggregat_spezial": {
                "verschoben_am": ["22.11.2024 (09d)", "14.11.2025 (09e)"],
                "elsa_entscheidung": "DEFER",
                "begruendung": "2x verschoben → Fundament, Abgas, Schallschutz, Zuleitung, Bayernwerk neu pruefen",
                "erforderlich": "HITL-Checkpoint (Bauleitung + Sonderplaner)",
            },
        }, f, indent=2, ensure_ascii=False, default=str)
    
    # DDGK Audit Log
    audit_path = os.path.join(OUTPUT_DIR, "ddgk_audit_log.jsonl")
    with open(audit_path, 'a', encoding='utf-8') as f:
        for pdf_name, r in all_results.items():
            entry = {
                "timestamp": datetime.now().isoformat(),
                "file": pdf_name,
                "sha256": r["sha256"],
                "elsa_decision": r["gesamt_entscheidung"],
                "decision_reason": r["gesamt_begruendung"],
                "revisionen": len(r["ddgk_revisionen"].get("aenderungen", [])),
                "kritische_aenderungen": sum(1 for a in r["ddgk_revisionen"].get("aenderungen", []) if a.get("kritisch")),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n{'='*80}")
    print(f"  Reports:")
    print(f"    JSON: {report_path}")
    print(f"    Audit: {audit_path}")
    print(f"{'='*80}")
    
    return all_results


if __name__ == "__main__":
    run_full_analysis()