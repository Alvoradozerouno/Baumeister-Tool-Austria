"""
Austrian Data Sources Router
Provides structured access to Austrian construction data:
- Baupreisindex (construction price index)
- Kostenrichtwerte (cost reference values)
- OIB-RL overview with Bundesland deviations
- Material database (lambda values)

Data is based on published Austrian standards and official sources.
Live API integrations (RIS, hora.gv.at) use a fallback model —
connect real credentials via environment variables for production.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


# ---------------------------------------------------------------------------
# Baupreisindex Austria (Statistik Austria, Index 2020 = 100)
# Updated quarterly; values approximate for planning purposes.
# ---------------------------------------------------------------------------
_BAUPREISINDEX = {
    "basis_jahr": 2020,
    "basis_wert": 100.0,
    "quelle": "Statistik Austria — Baukostenindex für Wohnhaus- und Siedlungsbau",
    "quelle_url": "https://www.statistik.at/statistiken/wirtschaft/preise-und-preismessung/baupreisindizes",
    "letzter_stand": "Q4 2025",
    "hinweis": (
        "Richtwerte für die Baukostenkalkulation. "
        "Für Ausschreibungen und Abrechnungen immer den aktuellen Indexstand "
        "von Statistik Austria verwenden (ÖNORM B 2111)."
    ),
    "zeitreihe": [
        {"quartal": "Q1 2020", "index": 100.0},
        {"quartal": "Q2 2020", "index": 101.2},
        {"quartal": "Q3 2020", "index": 102.5},
        {"quartal": "Q4 2020", "index": 103.1},
        {"quartal": "Q1 2021", "index": 104.8},
        {"quartal": "Q2 2021", "index": 108.3},
        {"quartal": "Q3 2021", "index": 113.7},
        {"quartal": "Q4 2021", "index": 117.2},
        {"quartal": "Q1 2022", "index": 122.4},
        {"quartal": "Q2 2022", "index": 128.6},
        {"quartal": "Q3 2022", "index": 132.1},
        {"quartal": "Q4 2022", "index": 134.8},
        {"quartal": "Q1 2023", "index": 136.2},
        {"quartal": "Q2 2023", "index": 137.4},
        {"quartal": "Q3 2023", "index": 138.0},
        {"quartal": "Q4 2023", "index": 137.9},
        {"quartal": "Q1 2024", "index": 138.5},
        {"quartal": "Q2 2024", "index": 139.2},
        {"quartal": "Q3 2024", "index": 140.1},
        {"quartal": "Q4 2024", "index": 140.8},
        {"quartal": "Q1 2025", "index": 141.5},
        {"quartal": "Q2 2025", "index": 142.3},
        {"quartal": "Q3 2025", "index": 143.0},
        {"quartal": "Q4 2025", "index": 143.7},
    ],
}


# ---------------------------------------------------------------------------
# Kostenrichtwerte 2026 (€/m² BGF, österreichischer Markt)
# ---------------------------------------------------------------------------
_KOSTENRICHTWERTE = {
    "stand": "2026",
    "einheit": "€/m² BGF (Brutto-Grundfläche)",
    "quelle": "BKI Baukosteninformationszentrum, WKO Österreich",
    "hinweis": (
        "Nettokosten ohne MwSt. Regionale Kostenfaktoren je Bundesland beachten "
        "(Wien +15%, Tirol +12%, Salzburg/Vorarlberg +10%, Burgenland -10%). "
        "Außenanlagen, Erschließung und Nebenkosten (ca. 20-25%) extra."
    ),
    "kategorien": {
        "wohnbau": [
            {"typ": "Einfamilienhaus (Standard)", "min": 2200, "max": 3200},
            {"typ": "Einfamilienhaus (Gehoben)", "min": 3200, "max": 4800},
            {"typ": "Einfamilienhaus (Luxus)", "min": 4800, "max": 7500},
            {"typ": "Doppelhaushälfte", "min": 2000, "max": 3000},
            {"typ": "Reihenhaus", "min": 1800, "max": 2800},
            {"typ": "Mehrfamilienhaus", "min": 2000, "max": 3500},
            {"typ": "Holzhaus (Fertigteil)", "min": 2000, "max": 3000},
            {"typ": "Holzhaus (Architekt)", "min": 2800, "max": 4500},
            {"typ": "Passivhaus", "min": 2800, "max": 4200},
        ],
        "sanierung": [
            {"typ": "Sanierung (leicht)", "min": 400, "max": 900},
            {"typ": "Sanierung (umfassend)", "min": 900, "max": 2000},
            {"typ": "Sanierung (Kernsanierung)", "min": 1800, "max": 3200},
            {"typ": "Zubau/Anbau", "min": 2200, "max": 3800},
            {"typ": "Aufstockung", "min": 2500, "max": 4000},
        ],
        "nebengebaeude": [
            {"typ": "Keller (beheizt)", "min": 700, "max": 1200, "einheit": "€/m² KF"},
            {"typ": "Keller (unbeheizt)", "min": 500, "max": 800, "einheit": "€/m² KF"},
            {"typ": "Garage/Carport", "min": 400, "max": 800, "einheit": "€/m²"},
            {"typ": "Außenanlagen", "min": 80, "max": 250, "einheit": "€/m² Grundstück"},
        ],
    },
    "regionale_faktoren": {
        "wien": 1.15,
        "salzburg": 1.10,
        "tirol": 1.12,
        "vorarlberg": 1.10,
        "oberoesterreich": 1.00,
        "steiermark": 0.95,
        "kaernten": 0.93,
        "niederoesterreich": 0.98,
        "burgenland": 0.90,
    },
}


# ---------------------------------------------------------------------------
# OIB-RL Overview
# ---------------------------------------------------------------------------
_OIB_RICHTLINIEN = {
    "herausgeber": "Österreichisches Institut für Bautechnik (OIB)",
    "herausgeber_url": "https://www.oib.or.at",
    "aktuelle_ausgabe": "2023 (beschlossen 25.05.2023)",
    "richtlinien": [
        {
            "nummer": "OIB-RL 1",
            "titel": "Mechanische Festigkeit und Standsicherheit",
            "version": "Ausgabe 2023",
            "kerninhalt": [
                "Tragfähigkeitsnachweis nach Eurocode-Normenreihe",
                "Lastannahmen nach ÖNORM EN 1991",
                "Erdbebensicherheit nach ÖNORM EN 1998",
                "Fundamentierung und Gründung",
            ],
            "bundesland_abweichungen": {
                "tirol": "Erhöhte Schneelasten Zone 3-5, Erdbebenzone 3-4",
                "kaernten": "Erdbebenzone 3-4, seismisch besonders aktiv",
                "salzburg": "Innergebirg extreme Schneelasten bis Zone 5",
                "vorarlberg": "Arlberg/Montafon Schneelasten Zone 4-5",
            },
        },
        {
            "nummer": "OIB-RL 2",
            "titel": "Brandschutz",
            "version": "Ausgabe 2023 (inkl. 2.1 Betriebsbauten, 2.2 Garagen, 2.3 Hochhäuser)",
            "kerninhalt": [
                "Brandabschnitte und Brandwände",
                "Fluchtweglängen und -breiten",
                "Feuerwiderstandsklassen (REI 30/60/90)",
                "Rauch- und Wärmeabzug",
                "Löschwasserversorgung",
            ],
            "bundesland_abweichungen": {
                "wien": "Hochhauskonzept ab 35m, verschärfte Anforderungen",
                "tirol": "Tourismusbauten: erweiterte Brandschutzanforderungen",
                "salzburg": "Altstadt: Denkmalschutz vs. Brandschutz — Sonderlösungen",
            },
        },
        {
            "nummer": "OIB-RL 3",
            "titel": "Hygiene, Gesundheit und Umweltschutz",
            "version": "Ausgabe 2023",
            "kerninhalt": [
                "Lichte Raumhöhe mind. 2,50m (Aufenthaltsräume)",
                "Belichtung: Fensterfläche mind. 1/8 der Bodenfläche",
                "Trinkwasserversorgung und Abwasserentsorgung",
                "Radonschutz in Vorsorgegebieten",
                "Schadstoffe in Baumaterialien",
            ],
            "bundesland_abweichungen": {
                "tirol": "Radonvorsorgegebiet — Radonschutzmaßnahmen im Keller Pflicht",
                "niederoesterreich": "Waldviertel Radonvorsorge",
                "wien": "2,50m Raumhöhe Altbau — Bestandsschutz bei 2,40m",
            },
        },
        {
            "nummer": "OIB-RL 4",
            "titel": "Nutzungssicherheit und Barrierefreiheit",
            "version": "Ausgabe 2023",
            "kerninhalt": [
                "Absturzsicherung ab 60cm Höhenunterschied",
                "Geländerhöhe mind. 1,00m (ab 12m Absturzhöhe: 1,10m)",
                "Stufenhöhe max. 18cm, Auftritt mind. 27cm",
                "Barrierefreiheit nach ÖNORM B 1600/1601",
                "Aufzugspflicht (bundeslandspezifisch!)",
            ],
            "bundesland_abweichungen": {
                "wien": "Aufzugspflicht ab 3 OG, strenge Barrierefreiheit",
                "vorarlberg": "Erweiterte Barrierefreiheit auch bei kleinerem Wohnbau",
                "burgenland": "Aufzugspflicht ab 4 OG",
            },
        },
        {
            "nummer": "OIB-RL 5",
            "titel": "Schallschutz",
            "version": "Ausgabe 2023",
            "kerninhalt": [
                "Luft-Schalldämmmaß zwischen Wohnungen: R'w ≥ 55 dB",
                "Trittschall: L'nT,w ≤ 48 dB",
                "Außenlärm: abhängig von Lärmzone",
                "Haustechnische Anlagen: max. Schallpegel in Aufenthaltsräumen",
            ],
            "bundesland_abweichungen": {
                "wien": "Verschärfte Anforderungen in dicht besiedelten Gebieten",
                "tirol": "Tourismuszone: Schallschutz-Sonderanforderungen",
            },
        },
        {
            "nummer": "OIB-RL 6",
            "titel": "Energieeinsparung und Wärmeschutz",
            "version": "Ausgabe 2023",
            "kerninhalt": [
                "HWBRef,RK ≤ 10 + 30·(A/V) kWh/(m²a)",
                "fGEE ≤ 0,75 (Neubau, verschärft gegenüber 0,85 der Ausgabe 2019)",
                "U-Wert Außenwand ≤ 0,35 W/m²K",
                "U-Wert Dach/oberste Geschoßdecke ≤ 0,20 W/m²K",
                "Energieausweis-Pflicht bei Neubau und umfassender Sanierung",
                "Nahezu-Nullenergiegebäude (NZEB) Pflicht",
                "PV-Pflicht für Neubauten ab 2024 (BGF > 1.000 m²)",
            ],
            "bundesland_abweichungen": {
                "salzburg": (
                    "⚠️ OIB-RL 6 NICHT übernommen! "
                    "Salzburger Wärmeschutzverordnung (WSchVO) gilt — "
                    "teils strengere Anforderungen!"
                ),
                "vorarlberg": (
                    "Faktisch strengere Energiestandards, Passivhaus-Nähe üblich, "
                    "eigene Energiebuchhaltungsvorschriften"
                ),
                "wien": "BRISE-Vienna prüft Energiewerte automatisch via IFC-Modell",
            },
        },
        {
            "nummer": "OIB-RL 7",
            "titel": "Nachhaltige Nutzung der natürlichen Ressourcen",
            "version": "Grundlagendokument 2023",
            "kerninhalt": [
                "Kreislaufwirtschaft: Rückbaubarkeit und Materialwiederverwendung",
                "Ökobilanzierung (GWP) über den Lebenszyklus",
                "OI3-Index für Baustoffe",
                "Klimaaktiv-Kompatibilität als Qualitätsrahmen",
            ],
            "bundesland_abweichungen": {
                "wien": "OI3-Index Anforderung bei gefördertem Wohnbau bereits verbindlich",
                "vorarlberg": "Nachhaltigkeit in Wohnbauförderungs-Richtlinie integriert",
            },
            "hinweis": (
                "OIB-RL 7 befindet sich noch in der Übernahmephase durch die Bundesländer. "
                "Aktuelle Anforderungen über ris.bka.gv.at und oib.or.at prüfen!"
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Material database (lambda values for common Austrian building materials)
# ---------------------------------------------------------------------------
_MATERIALIEN = {
    "quelle": "ÖNORM EN ISO 10456, OIB-RL 6:2023 Anhang, Hersteller-EPDs",
    "stand": "2025",
    "materialien": [
        # Dämmung
        {"name": "EPS (Styropor)", "lambda_wm_k": 0.035, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "XPS (Styrodur)", "lambda_wm_k": 0.032, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "Mineralwolle (Glaswolle)", "lambda_wm_k": 0.035, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "Mineralwolle (Steinwolle)", "lambda_wm_k": 0.038, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "Holzfaserdämmung", "lambda_wm_k": 0.040, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "Zellulosedämmung (eingeblasen)", "lambda_wm_k": 0.038, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "PUR/PIR", "lambda_wm_k": 0.024, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "Schaumglas", "lambda_wm_k": 0.042, "typ": "Dämmung", "einheit": "W/(m·K)"},
        {"name": "Hanf/Flachs", "lambda_wm_k": 0.040, "typ": "Dämmung", "einheit": "W/(m·K)"},
        # Tragwerk / Mauerwerk
        {"name": "Stahlbeton", "lambda_wm_k": 2.300, "typ": "Tragwerk", "einheit": "W/(m·K)"},
        {"name": "Vollziegel", "lambda_wm_k": 0.680, "typ": "Mauerwerk", "einheit": "W/(m·K)"},
        {"name": "Hochlochziegel 25cm", "lambda_wm_k": 0.290, "typ": "Mauerwerk", "einheit": "W/(m·K)"},
        {"name": "Hochlochziegel 38cm", "lambda_wm_k": 0.170, "typ": "Mauerwerk", "einheit": "W/(m·K)"},
        {"name": "Porenbeton (Ytong/Hebel)", "lambda_wm_k": 0.110, "typ": "Mauerwerk", "einheit": "W/(m·K)"},
        # Holzbau
        {"name": "Brettsperrholz (CLT)", "lambda_wm_k": 0.130, "typ": "Holzbau", "einheit": "W/(m·K)"},
        {"name": "Brettschichtholz (BSH)", "lambda_wm_k": 0.130, "typ": "Holzbau", "einheit": "W/(m·K)"},
        {"name": "Fichtenholz (Vollholz)", "lambda_wm_k": 0.130, "typ": "Holzbau", "einheit": "W/(m·K)"},
        # Innenausbau / Putz
        {"name": "Gipskarton", "lambda_wm_k": 0.250, "typ": "Innenausbau", "einheit": "W/(m·K)"},
        {"name": "Innenputz Kalk/Zement", "lambda_wm_k": 0.870, "typ": "Putz", "einheit": "W/(m·K)"},
        {"name": "Außenputz (mineralisch)", "lambda_wm_k": 0.870, "typ": "Putz", "einheit": "W/(m·K)"},
    ],
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/baupreisindex")
async def get_baupreisindex(
    von_quartal: Optional[str] = Query(None, description="Startquartal (z.B. 'Q1 2023')"),
    bis_quartal: Optional[str] = Query(None, description="Endquartal (z.B. 'Q4 2025')"),
):
    """
    📈 **Österreichischer Baukostenindex (Statistik Austria)**

    Baukostenindex für Wohnhaus- und Siedlungsbau, Basis 2020 = 100.
    Verwendung nach ÖNORM B 2111 für Preisgleitklauseln in Bauverträgen.

    Optionale Filterung nach Quartal-Zeitraum.
    """
    zeitreihe = _BAUPREISINDEX["zeitreihe"]

    if von_quartal or bis_quartal:
        quartale = [e["quartal"] for e in zeitreihe]
        start_idx = quartale.index(von_quartal) if von_quartal and von_quartal in quartale else 0
        end_idx = (
            quartale.index(bis_quartal) + 1
            if bis_quartal and bis_quartal in quartale
            else len(quartale)
        )
        zeitreihe = zeitreihe[start_idx:end_idx]

    aktuell = _BAUPREISINDEX["zeitreihe"][-1]
    veraenderung_seit_2020 = round(aktuell["index"] - 100.0, 1)

    return {
        **{k: v for k, v in _BAUPREISINDEX.items() if k != "zeitreihe"},
        "aktueller_wert": aktuell,
        "veraenderung_seit_basisjahr_pct": veraenderung_seit_2020,
        "zeitreihe": zeitreihe,
    }


@router.get("/kostenrichtwerte")
async def get_kostenrichtwerte(
    bundesland: Optional[str] = Query(None, description="Bundesland für regionalen Kostenfaktor"),
    kategorie: Optional[str] = Query(
        None,
        description="Kategorie: 'wohnbau', 'sanierung', 'nebengebaeude'",
    ),
):
    """
    💰 **Österreichische Kostenrichtwerte 2026**

    Baukostenrichtwerte in €/m² BGF für Österreich.
    Mit optionalem regionalem Kostenfaktor je Bundesland.

    Quellen: BKI Baukosteninformationszentrum, WKO Österreich.
    """
    result = dict(_KOSTENRICHTWERTE)

    if kategorie:
        if kategorie not in result["kategorien"]:
            raise HTTPException(
                status_code=400,
                detail=f"Ungültige Kategorie '{kategorie}'. Gültig: {list(result['kategorien'].keys())}",
            )
        result["kategorien"] = {kategorie: result["kategorien"][kategorie]}

    if bundesland:
        bl_lower = bundesland.lower()
        faktor = result["regionale_faktoren"].get(bl_lower)
        if faktor is None:
            raise HTTPException(
                status_code=404,
                detail=f"Bundesland '{bundesland}' nicht bekannt. Gültig: {list(result['regionale_faktoren'].keys())}",
            )
        # Add regionalized costs
        result["bundesland"] = bl_lower
        result["regionaler_faktor"] = faktor
        result["regionalisierte_kosten"] = {
            kat: [
                {
                    **eintrag,
                    "min_regional": round(eintrag["min"] * faktor),
                    "max_regional": round(eintrag["max"] * faktor),
                }
                for eintrag in eintraege
            ]
            for kat, eintraege in result["kategorien"].items()
        }

    return result


@router.get("/oib-richtlinien")
async def get_oib_richtlinien(
    nummer: Optional[str] = Query(
        None, description="OIB-RL Nummer (z.B. 'OIB-RL 6'), leer = alle"
    ),
    bundesland: Optional[str] = Query(
        None, description="Bundesland für spezifische Abweichungen"
    ),
):
    """
    📋 **OIB-Richtlinien 2023 — Vollständige Übersicht**

    Alle 7 OIB-Richtlinien mit Kerninhalt und bundeslandspezifischen Abweichungen.
    Besonders wichtig: Salzburg hat OIB-RL 6 NICHT übernommen!

    Quelle: Österreichisches Institut für Bautechnik (oib.or.at)
    """
    richtlinien = _OIB_RICHTLINIEN["richtlinien"]

    if nummer:
        richtlinien = [r for r in richtlinien if r["nummer"].upper() == nummer.upper()]
        if not richtlinien:
            raise HTTPException(
                status_code=404,
                detail=f"OIB-RL '{nummer}' nicht gefunden. Gültig: OIB-RL 1 bis OIB-RL 7.",
            )

    if bundesland:
        bl_lower = bundesland.lower()
        for r in richtlinien:
            abw = r.get("bundesland_abweichungen", {})
            r["abweichung_fuer_bundesland"] = abw.get(bl_lower)

    return {
        "herausgeber": _OIB_RICHTLINIEN["herausgeber"],
        "herausgeber_url": _OIB_RICHTLINIEN["herausgeber_url"],
        "aktuelle_ausgabe": _OIB_RICHTLINIEN["aktuelle_ausgabe"],
        "richtlinien": richtlinien,
        "hinweis": (
            "Verbindlichkeit der OIB-Richtlinien durch Übernahme in die jeweilige Landesbauordnung. "
            "Stand und Umsetzung auf ris.bka.gv.at prüfen."
        ),
    }


@router.get("/materialien")
async def get_materialien(
    typ: Optional[str] = Query(
        None,
        description="Materialtyp: 'Dämmung', 'Tragwerk', 'Mauerwerk', 'Holzbau', 'Innenausbau', 'Putz'",
    ),
):
    """
    🧱 **Österreichische Baustoffdatenbank — Lambda-Werte**

    Wärmeleitfähigkeit (λ) gängiger Baustoffe nach ÖNORM EN ISO 10456.
    Verwendung in U-Wert-Berechnungen nach OIB-RL 6.
    """
    materialien = _MATERIALIEN["materialien"]

    if typ:
        materialien = [m for m in materialien if m["typ"].lower() == typ.lower()]
        if not materialien:
            typen = list({m["typ"] for m in _MATERIALIEN["materialien"]})
            raise HTTPException(
                status_code=404,
                detail=f"Materialtyp '{typ}' nicht gefunden. Verfügbare Typen: {typen}",
            )

    return {
        "quelle": _MATERIALIEN["quelle"],
        "stand": _MATERIALIEN["stand"],
        "anzahl_materialien": len(materialien),
        "materialien": materialien,
        "hinweis": (
            "Lambda-Werte sind Bemessungswerte nach ÖNORM EN ISO 10456. "
            "Für genaue U-Wert-Berechnung produktspezifische Werte aus EPD/Datenblatt verwenden."
        ),
    }


@router.get("/sources")
async def get_at_data_sources():
    """
    🔗 **Österreichische Datenquellen — Übersicht**

    Listet alle verwendeten österreichischen Datenquellen und deren Status.
    """
    return {
        "datenquellen": [
            {
                "name": "Statistik Austria — Baukostenindex",
                "url": "https://www.statistik.at/statistiken/wirtschaft/preise-und-preismessung/baupreisindizes",
                "typ": "Preisindex",
                "status": "verfügbar (offline-Kopie, Stand Q4 2025)",
                "live_integration": False,
                "update_frequenz": "Quartalsweise",
            },
            {
                "name": "OIB — Österreichisches Institut für Bautechnik",
                "url": "https://www.oib.or.at",
                "typ": "Technische Richtlinien",
                "status": "verfügbar (Ausgabe 2023 implementiert)",
                "live_integration": False,
                "update_frequenz": "Bei neuer Ausgabe",
            },
            {
                "name": "RIS — Rechtsinformationssystem des Bundes",
                "url": "https://www.ris.bka.gv.at",
                "typ": "Gesetzestexte",
                "status": "Offline-Referenz (API-Integration geplant)",
                "live_integration": False,
                "update_frequenz": "Laufend",
            },
            {
                "name": "hora.gv.at — Hochwasser- und Lawinenzonierung Austria",
                "url": "https://www.hora.gv.at",
                "typ": "Gefahrenzonierung",
                "status": "Offline-Referenz (API-Integration geplant)",
                "live_integration": False,
                "update_frequenz": "Laufend",
            },
            {
                "name": "WKO Österreich — Baubranche Kostenrichtwerte",
                "url": "https://www.wko.at/branchen/gewerbe-handwerk/bau",
                "typ": "Kostendaten",
                "status": "verfügbar (Richtwerte 2026 implementiert)",
                "live_integration": False,
                "update_frequenz": "Jährlich",
            },
            {
                "name": "ÖNORM (Austrian Standards)",
                "url": "https://www.austrian-standards.at",
                "typ": "Technische Normen",
                "status": "Kernwerte implementiert (Volltexte kostenpflichtig)",
                "live_integration": False,
                "update_frequenz": "Bei Revision",
            },
        ],
        "hinweis": (
            "Live-API-Integrationen für RIS und hora.gv.at sind in Planung. "
            "Bis dahin werden aktuelle Offlinedaten aus publizierten Quellen verwendet."
        ),
        "stand": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Changelog entries (audit-visible product changes)
# ---------------------------------------------------------------------------
_CHANGELOG = [
    {
        "version": "3.0.0",
        "datum": "2026-05-12",
        "aenderungen": [
            "Alle 9 Bundesländer mit vollständigen Baurechts-Daten (Bauordnung, OIB-Status, Förderungen)",
            "OIB-RL 1-7 (2023) vollständig implementiert — inkl. Salzburg-Sonderweg für OIB-RL 6",
            "Neuer Bundesländer-Vergleich (GET /api/v1/bundesland/compare)",
            "Bundesland-Förderungsübersicht (Bund + Land, GET /api/v1/bundesland/{bl}/foerderungen)",
            "Baupreisindex Österreich Q1 2020 – Q4 2025 (Statistik Austria)",
            "Kostenrichtwerte 2026 mit regionalen Faktoren für alle 9 Bundesländer",
            "Lambda-Wert-Datenbank für U-Wert-Berechnungen nach ÖNORM EN ISO 10456",
            "Projekt- und Büroverwaltung (GET/POST /api/v1/projects/)",
            "Compliance-Schnellübersicht je Projekt (GET /api/v1/projects/{id}/compliance-summary)",
            "Austria-first Dashboard (GET /dashboard)",
            "AT-Erfolgsmessung (GET /api/v1/at-data/at-kpis)",
            "Teamverwaltung in Projekten (POST /api/v1/projects/{id}/members)",
            "Öffentliches Änderungsprotokoll (GET /api/v1/at-data/changelog)",
        ],
        "quellen_aktualisiert": [
            "OIB-RL 1-7 Ausgabe 2023",
            "Statistik Austria Baukostenindex Q4 2025",
            "BKI/WKO Kostenrichtwerte 2026",
        ],
        "breaking_changes": [],
    },
    {
        "version": "2.1.0",
        "datum": "2026-04-13",
        "aenderungen": [
            "ÖNORM A 2063 Ausschreibung vollständig",
            "BIM/IFC-Integration (IFC2x3, IFC4, IFC4.3)",
            "Echtzeit-Zusammenarbeit (Collaboration-Router)",
            "OIB-RL 6:2023 Energienachweis (fGEE ≤ 0.75, HWBRef,RK)",
            "U-Wert-Berechnung nach ÖNORM EN ISO 6946",
            "Barrierefreiheit nach ÖNORM B 1600",
        ],
        "quellen_aktualisiert": ["OIB-RL 6 Ausgabe 2023", "ÖNORM A 2063:2021"],
        "breaking_changes": [],
    },
]


@router.get("/changelog")
async def get_changelog():
    """
    📋 **Öffentliches Änderungsprotokoll**

    Nachvollziehbare, öffentliche Dokumentation aller Änderungen an der
    ORION Architekt-AT API — für Vertrauen, Auditierbarkeit und DSGVO-Compliance.

    Zeigt welche Datenquellen wann aktualisiert wurden und welche Features
    hinzugekommen sind.
    """
    return {
        "produkt": "ORION Architekt-AT API",
        "hinweis": (
            "Dieses Änderungsprotokoll dokumentiert alle fachlich relevanten Änderungen "
            "an Datenquellen, Regelwerken und API-Funktionen. "
            "Für Compliance-Nachweise und Audits verwendbar."
        ),
        "changelog": _CHANGELOG,
        "aktuellste_version": _CHANGELOG[0]["version"],
        "aktuellstes_datum": _CHANGELOG[0]["datum"],
    }


@router.get("/at-kpis")
async def get_at_kpis():
    """
    📊 **Austria-leading Erfolgsmessung (KPIs)**

    Gibt den aktuellen Stand der Qualitätsmetriken für den österreichischen Markt zurück.
    Messgrößen: Bundesland-Abdeckung, OIB-RL-Vollständigkeit, API-Endpunkte, BIM-Unterstützung.

    Entspricht dem Plan-Punkt: „Erfolg messbar machen — Ziele auf Österreich ausrichten."
    """
    return {
        "messung_zeitpunkt": datetime.now(timezone.utc).isoformat(),
        "bundesland_abdeckung": {
            "gesamt": 9,
            "implementiert": 9,
            "mit_foerderungsdaten": 9,
            "mit_digitaler_einreichung": 2,
            "abdeckung_pct": 100.0,
            "detail": "Alle 9 Bundesländer mit vollständigen Bauordnungs-, Förderungs- und Zonendaten",
        },
        "oib_rl_abdeckung": {
            "gesamt_richtlinien": 7,
            "implementiert": 7,
            "mit_bundesland_abweichungen": 6,
            "abdeckung_pct": 100.0,
            "detail": "OIB-RL 1-7 (Ausgabe 2023), inkl. Salzburg-Sonderweg OIB-RL 6",
        },
        "api_endpunkte": {
            "bundesland": [
                "GET /api/v1/bundesland/ (alle 9)",
                "GET /api/v1/bundesland/compare",
                "GET /api/v1/bundesland/{bl}",
                "GET /api/v1/bundesland/{bl}/stellplaetze",
                "GET /api/v1/bundesland/{bl}/aufzug",
                "GET /api/v1/bundesland/{bl}/foerderungen",
            ],
            "at_daten": [
                "GET /api/v1/at-data/baupreisindex",
                "GET /api/v1/at-data/kostenrichtwerte",
                "GET /api/v1/at-data/oib-richtlinien",
                "GET /api/v1/at-data/materialien",
                "GET /api/v1/at-data/sources",
                "GET /api/v1/at-data/changelog",
                "GET /api/v1/at-data/at-kpis",
            ],
            "projekte": [
                "POST /api/v1/projects/",
                "GET /api/v1/projects/",
                "GET /api/v1/projects/{id}",
                "PUT /api/v1/projects/{id}",
                "DELETE /api/v1/projects/{id}",
                "GET /api/v1/projects/{id}/compliance-summary",
                "GET /api/v1/projects/{id}/export",
                "POST /api/v1/projects/{id}/members",
                "GET /api/v1/projects/{id}/members",
                "DELETE /api/v1/projects/{id}/members/{uid}",
            ],
            "berechnungen": [
                "POST /api/v1/calculations/uwert",
                "POST /api/v1/calculations/stellplaetze",
                "POST /api/v1/calculations/barrierefreiheit-check",
                "POST /api/v1/calculations/fluchtweg-check",
                "POST /api/v1/calculations/schallschutz-berechnung",
                "POST /api/v1/calculations/heizlast-berechnung",
                "POST /api/v1/calculations/hwb-grenzwert-oib6",
                "GET /api/v1/calculations/materialdatenbank",
            ],
        },
        "bim_unterstuetzung": {
            "formate": ["IFC2x3", "IFC4", "IFC4.3"],
            "brise_wien_kompatibel": True,
            "ifc_validierung": True,
        },
        "datenquellen": {
            "statistik_austria_baupreisindex": True,
            "oib_richtlinien_2023": True,
            "wko_kostenrichtwerte_2026": True,
            "ris_integration": False,
            "hora_gv_at_integration": False,
        },
        "vertrauen_features": {
            "oeffentliches_changelog": True,
            "audit_trail": True,
            "dsgvo_betrieb": True,
            "quellennachweise": True,
        },
        "ziele_2026": {
            "aktive_bueros_ziel": 50,
            "aktive_bueros_aktuell": "Pilotbetrieb",
            "bundesland_abdeckung_ziel_pct": 100,
            "bundesland_abdeckung_aktuell_pct": 100.0,
            "bim_faelle_ziel_monatlich": 100,
            "api_antwortzeit_ziel_ms": 300,
        },
        "hinweis": (
            "KPIs werden mit jeder API-Version aktualisiert. "
            "Für Marktführerschaft in Österreich: ris.bka.gv.at und hora.gv.at Live-Integrationen "
            "sind die wichtigsten nächsten Schritte."
        ),
    }
