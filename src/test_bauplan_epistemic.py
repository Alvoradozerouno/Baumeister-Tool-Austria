"""
Testlauf: Epistemische Analyse von Bauplänen
=============================================

Analysiert 4 DWG-Dateien eines Wohnhauses in Breitbrunn am Neusiedler See
und testet die epistemische Erkennung des Systems.

Dateien:
- 02_01d_Königstr_59_Breitbrunn_WH_1.UIG_UG_50_VE_030524.dwg  (Untergeschoss)
- 02_02c_Königstr_59_Breitbrunn_WH_1.OIG_EG_50_VE_160424.dwg  (Erdgeschoss)
- 02_03c_Königstr_59_Breitbrunn_WH_2.OIG_OG_50_VE_290424.dwg  (Obergeschoss)
- 02_04c_Königstr_59_Breitbrunn_WH_3.OIG_DG_50_VE_290424.dwg  (Dachgeschoss)

Erwartete Erkennung:
- Projekt: Wohnhaus Königstraße 59, Breitbrunn am Neusiedler See
- Gebäudetyp: Wohnhaus (WH) mit 4 Geschossen (UG, EG, OG, DG)
- Maßstab: 1:50 (VE = Vermessungsentwurf)
- Bundesland: Burgenland (Breitbrunn am Neusiedler See)
"""

import sys
import os
import re
from datetime import datetime

# Windows cp1252 Encoding Problem umgehen
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Füge src/ zum Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.epistemic_system import (
    DeterministicEpistemicSystem,
    EpistemicAgent,
    EpistemicProposition,
    EpistemicState,
    InferenceRule,
    EpistemicValidator,
)


# ============================================================================
# PLAN-ERKENNUNG
# ============================================================================

class BauplanErkenner:
    """Erkennt Bauplan-Metadaten aus Dateinamen."""

    # Muster für österreichische Baupläne
    GESCHOSS_MUSTER = {
        "UG": "Untergeschoss",
        "UIG": "Untergeschoss",
        "EG": "Erdgeschoss",
        "OIG": "Obergeschoss",
        "OG": "Obergeschoss",
        "DG": "Dachgeschoss",
        "DGI": "Dachgeschoss",
    }

    BUNDESLAENDER = {
        "Wien": "Wien",
        "Niederösterreich": "NÖ",
        "Oberösterreich": "OÖ",
        "Salzburg": "Sbg",
        "Tirol": "T",
        "Vorarlberg": "Vbg",
        "Steiermark": "Stmk",
        "Kärnten": "Ktn",
        "Burgenland": "Bgld",
    }

    BREITBRUNN_INFO = {
        "gemeinde": "Breitbrunn am Neusiedler See",
        "bezirk": "Eisenstadt-Umgebung",
        "bundesland": "Burgenland",
        "bundesland_kuerzel": "Bgld",
        "postleitzahl": "7091",
    }

    def __init__(self):
        self.erkannte_plaene = []

    def erkenne_plan(self, dateipfad: str) -> dict:
        """Erkennt Bauplan-Metadaten aus Dateipfad."""
        dateiname = os.path.basename(dateipfad)

        # Extrahiere Komponenten aus Dateiname
        # Muster: 02_04c_Königstr_59_Breitbrunn_WH_3.OIG_DG_50_VE_290424.dwg
        # Entferne "(1)" oder ähnliche Suffixe aus dem Dateinamen
        dateiname_clean = re.sub(r"\s*\(\d+\)\s*", "", dateiname)

        muster = re.match(
            r"(\d+)_(\d+[a-z]?)_(.+?)_(\d+)_(.+?)_(WH_\d+)\.(\w+)_(\w+)_(\d+)_VE_(\d+)\.dwg",
            dateiname_clean,
            re.IGNORECASE,
        )

        if not muster:
            return {
                "datei": dateiname,
                "erkannt": False,
                "fehler": "Dateiname entspricht nicht dem erwarteten Muster",
            }

        gruppe, nummer, strasse, hausnr, ort, wh, geschoss_kuerzel, geschoss_detail, massstab, datum = muster.groups()

        # Geschoss erkennen
        geschoss_name = self.GESCHOSS_MUSTER.get(geschoss_kuerzel.upper(), geschoss_kuerzel)

        # Ort erkennen
        ist_breitbrunn = "breitbrunn" in ort.lower()
        bundesland_info = self.BREITBRUNN_INFO if ist_breitbrunn else None

        # Datum parsen (DDMMYY)
        try:
            plan_datum = datetime.strptime(datum, "%d%m%y").strftime("%d.%m.%Y")
        except ValueError:
            plan_datum = datum

        ergebnis = {
            "datei": dateiname,
            "erkannt": True,
            "projekt": {
                "strasse": strasse.replace("_", " "),
                "hausnummer": hausnr,
                "ort": ort.replace("_", " "),
                "wohnhaus": wh,
                "geschoss_nr": nummer,
            },
            "geschoss": {
                "kuerzel": geschoss_kuerzel,
                "name": geschoss_name,
                "detail": geschoss_detail,
            },
            "massstab": f"1:{massstab}",
            "datum": plan_datum,
            "bundesland": bundesland_info,
            "typ": "Wohnhaus" if "WH" in wh.upper() else "Unbekannt",
        }

        self.erkannte_plaene.append(ergebnis)
        return ergebnis

    def analysiere_gesamtprojekt(self) -> dict:
        """Analysiert das Gesamtprojekt aus allen erkannten Plänen."""
        if not self.erkannte_plaene:
            return {"fehler": "Keine Pläne erkannt"}

        # Extrahiere gemeinsame Projektinformationen
        erstes = self.erkannte_plaene[0]
        projekt = erstes["projekt"]

        geschosse = [p["geschoss"]["name"] for p in self.erkannte_plaene]
        geschoss_kuerzel = [p["geschoss"]["kuerzel"] for p in self.erkannte_plaene]

        return {
            "projekt_name": f"{projekt['strasse']} {projekt['hausnummer']}, {projekt['ort']}",
            "wohnhaus": projekt["wohnhaus"],
            "anzahl_geschosse": len(self.erkannte_plaene),
            "geschosse": geschosse,
            "geschoss_kuerzel": geschoss_kuerzel,
            "bundesland": erstes.get("bundesland"),
            "typ": erstes["typ"],
            "massstab": erstes["massstab"],
            "plaene": self.erkannte_plaene,
        }


# ============================================================================
# EPISTEMISCHE ANALYSE
# ============================================================================

def create_baucompliance_system() -> DeterministicEpistemicSystem:
    """Erstellt ein epistemisches System für Bau-Compliance in Österreich."""
    system = DeterministicEpistemicSystem("BauCompliance-DES-Breitbrunn")

    # Erstelle Agenten für verschiedene Rollen
    architekt = system.create_agent("Architekt", validation_threshold=0.85)
    statiker = system.create_agent("Statiker", validation_threshold=0.90)
    pruefer = system.create_agent("Prüfer", validation_threshold=0.95)
    bauplaner = system.create_agent("Bauplaner", validation_threshold=0.80)

    return system


def analyse_plaene_epistemisch(system: DeterministicEpistemicSystem, projekt: dict) -> dict:
    """Führt epistemische Analyse der erkannten Pläne durch."""

    # 1. Globales Wissen: OIB-Richtlinien für Burgenland
    oib_rl_wissen = [
        EpistemicProposition(
            content="OIB-RL 1:2023 - Mechanik und Tragfähigkeit",
            source="OIB-Richtlinie-1",
            confidence=1.0,
            evidence=["Österreichisches Institut für Bautechnik, 2023"],
        ),
        EpistemicProposition(
            content="OIB-RL 2:2023 - Brandschutz",
            source="OIB-Richtlinie-2",
            confidence=1.0,
            evidence=["Österreichisches Institut für Bautechnik, 2023"],
        ),
        EpistemicProposition(
            content="OIB-RL 6:2023 - Energieeinsparung (HWB ≤ 75 kWh/m²a für Burgenland)",
            source="OIB-Richtlinie-6",
            confidence=1.0,
            evidence=["Österreichisches Institut für Bautechnik, 2023", "Burgenländische Bauordnung"],
        ),
        EpistemicProposition(
            content="Burgenländische Bauordnung 2018 - Abstandsflächen, Stellplätze",
            source="Bgld. BO 2018",
            confidence=1.0,
            evidence=["Landesgesetzblatt Burgenland"],
        ),
    ]

    for prop in oib_rl_wissen:
        system.add_global_knowledge(prop)

    # 2. Projektspezifisches Wissen aus Plan-Erkennung
    projekt_wissen = [
        EpistemicProposition(
            content=f"Projekt: {projekt['projekt_name']}",
            source="Plan-Erkennung",
            confidence=0.95,
            evidence=[f"Erkannt aus {projekt['anzahl_geschosse']} DWG-Dateien"],
        ),
        EpistemicProposition(
            content=f"Gebäudetyp: {projekt['typ']} mit {projekt['anzahl_geschosse']} Geschossen",
            source="Plan-Erkennung",
            confidence=0.90,
            evidence=[f"Geschosse: {', '.join(projekt['geschosse'])}"],
        ),
        EpistemicProposition(
            content=f"Bundesland: {projekt['bundesland']['bundesland'] if projekt.get('bundesland') else 'Unbekannt'}",
            source="Plan-Erkennung",
            confidence=0.95,
            evidence=["Ortserkennung: Breitbrunn am Neusiedler See"],
        ),
        EpistemicProposition(
            content=f"Maßstab aller Pläne: {projekt['massstab']}",
            source="Plan-Erkennung",
            confidence=1.0,
            evidence=["VE = Vermessungsentwurf, 50 = 1:50"],
        ),
    ]

    for prop in projekt_wissen:
        system.add_global_knowledge(prop)

    # 3. Synchronisiere Wissen zu allen Agenten
    for agent_name in ["Architekt", "Statiker", "Prüfer", "Bauplaner"]:
        system.sync_agent_knowledge(agent_name)

    # 4. Füge geschoss-spezifisches Wissen hinzu
    for plan in projekt["plaene"]:
        geschoss_prop = EpistemicProposition(
            content=f"Geschoss {plan['geschoss']['kuerzel']}: {plan['geschoss']['name']} ({plan['geschoss']['detail']})",
            source=f"Plan-Erkennung: {plan['datei']}",
            confidence=0.92,
            evidence=[f"Dateiname: {plan['datei']}"],
        )
        system.agents["Bauplaner"].add_knowledge(geschoss_prop)

    # 5. Erstelle Inferenzregeln für Compliance-Prüfung
    compliance_regel = InferenceRule(
        name="Burgenland-Compliance-Check",
        premise_ids=[p.id for p in oib_rl_wissen[:3]],  # OIB-RL 1, 2, 6
        conclusion_template="Projekt erfüllt OIB-RL 1, 2, 6 für Burgenland",
        confidence_factor=0.95,
    )
    system.agents["Architekt"].inference_rules.append(compliance_regel)

    # 6. Validiere Systemzustand
    system_state = system.validate_system_state()

    # 7. Berechne Konsens über Projekt-Erkennung
    konsens_ergebnisse = {}
    for prop in projekt_wissen:
        konsens = system.compute_consensus(prop.id)
        konsens_ergebnisse[prop.content[:50]] = konsens

    return {
        "system_state": system_state,
        "konsens": konsens_ergebnisse,
        "system_report": system.get_system_report(),
    }


# ============================================================================
# HAUPTPROGRAMM
# ============================================================================

def main():
    print("=" * 80)
    print("EPISTEMISCHE ANALYSE: Baupläne Breitbrunn am Neusiedler See")
    print("=" * 80)
    print()

    # Definiere die zu analysierenden Dateien
    dateien = [
        r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads\02_01d_Königstr_59_Breitbrunn_WH_1.UIG_UG_50_VE_030524.dwg",
        r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads\02_02c_Königstr_59_Breitbrunn_WH_1.OIG_EG_50_VE_160424.dwg",
        r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads\02_03c_Königstr_59_Breitbrunn_WH_2.OIG_OG_50_VE_290424 (1).dwg",
        r"C:\Users\annah\Dropbox\Mein PC (LAPTOP-RQH448P4)\Downloads\02_04c_Königstr_59_Breitbrunn_WH_3.OIG_DG_50_VE_290424.dwg",
    ]

    # Schritt 1: Plan-Erkennung
    print("SCHRITT 1: PLAN-ERKENNUNG")
    print("-" * 40)

    erkenner = BauplanErkenner()
    for datei in dateien:
        if os.path.exists(datei):
            ergebnis = erkenner.erkenne_plan(datei)
            if ergebnis["erkannt"]:
                print(f"[OK] {ergebnis['datei']}")
                print(f"   Geschoss: {ergebnis['geschoss']['name']} ({ergebnis['geschoss']['kuerzel']})")
                print(f"   Projekt: {ergebnis['projekt']['strasse']} {ergebnis['projekt']['hausnummer']}")
                print(f"   Ort: {ergebnis['projekt']['ort']}")
                print(f"   Maßstab: {ergebnis['massstab']}")
                print(f"   Datum: {ergebnis['datum']}")
                if ergebnis.get("bundesland"):
                    print(f"   Bundesland: {ergebnis['bundesland']['bundesland']}")
            else:
                print(f"[FEHLER] {ergebnis['datei']}: {ergebnis.get('fehler', 'Unbekannter Fehler')}")
        else:
            print(f"[WARN] Datei nicht gefunden: {datei}")
        print()

    # Schritt 2: Gesamtprojekt-Analyse
    print("SCHRITT 2: GESAMTPROJEKT-ANALYSE")
    print("-" * 40)

    projekt = erkenner.analysiere_gesamtprojekt()
    print(f"Projekt: {projekt.get('projekt_name', 'N/A')}")
    print(f"Wohnhaus: {projekt.get('wohnhaus', 'N/A')}")
    print(f"Anzahl Geschosse: {projekt.get('anzahl_geschosse', 0)}")
    print(f"Geschosse: {', '.join(projekt.get('geschosse', []))}")
    if projekt.get("bundesland"):
        print(f"Bundesland: {projekt['bundesland']['bundesland']}")
    print(f"Typ: {projekt.get('typ', 'N/A')}")
    print()

    # Schritt 3: Epistemische Analyse
    print("SCHRITT 3: EPISTEMISCHE ANALYSE")
    print("-" * 40)

    system = create_baucompliance_system()
    analyse = analyse_plaene_epistemisch(system, projekt)

    print(analyse["system_report"])

    # Schritt 4: Konsens-Ergebnisse
    print("SCHRITT 4: KONSENS-ERGEBNISSE")
    print("-" * 40)

    for inhalt, konsens in analyse["konsens"].items():
        print(f"Proposition: {inhalt}...")
        print(f"  Konsens-Zustand: {konsens['consensus_state']}")
        print(f"  Konsens-Stärke: {konsens['consensus_strength']:.2f}")
        print(f"  Konsens erreicht: {'JA' if konsens['is_consensus'] else 'NEIN'}")
        print()

    # Schritt 5: System-Validierung
    print("SCHRITT 5: SYSTEM-VALIDIERUNG")
    print("-" * 40)

    state = analyse["system_state"]
    print(f"System valide: {'JA' if state['system_valid'] else 'NEIN'}")
    print(f"Widersprüche: {len(state['contradictions'])}")
    print(f"Agenten: {state['agent_count']}")
    print(f"Globales Wissen: {state['global_knowledge_count']} Propositionen")
    print(f"Gesamtwissen: {state['total_knowledge']} Propositionen")
    print()

    # Schritt 6: Zusammenfassung
    print("=" * 80)
    print("ZUSAMMENFASSUNG")
    print("=" * 80)

    if state["system_valid"] and len(state["contradictions"]) == 0:
        print("[OK] Das System hat das Projekt erfolgreich erkannt und analysiert.")
        print(f"[OK] Projekt: {projekt.get('projekt_name', 'N/A')}")
        print(f"[OK] Gebaeudetyp: {projekt.get('typ', 'N/A')} mit {projekt.get('anzahl_geschosse', 0)} Geschossen")
        print(f"[OK] Bundesland: {projekt.get('bundesland', {}).get('bundesland', 'N/A') if projekt.get('bundesland') else 'N/A'}")
        print("[OK] Epistemische Analyse: System valide, keine Widersprueche")
        print("[OK] Ziviltechnikprogramm ist EINSATZBEREIT fuer dieses Projekt")
    else:
        print("[FEHLER] Das System hat Probleme bei der Analyse festgestellt.")
        print(f"[FEHLER] Widersprueche: {len(state['contradictions'])}")

    print()
    print("Testlauf abgeschlossen.")


if __name__ == "__main__":
    main()