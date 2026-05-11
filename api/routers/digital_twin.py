"""
ORION Architekt-AT — Digitaler Zwilling (Digital Twin)
======================================================

Gebäude-Digitalisierung und Echtzeit-Monitoring für österreichische Gebäude.

Funktionen:
  - Smart-Building-Protokolle: BACnet/IP, Modbus TCP, KNX/IP
  - Energiemonitoring mit Soll/Ist-Vergleich zum Energieausweis (OIB-RL 6)
  - Wartungsplan-Generierung aus IFC-Modellinformationen (Asset Management)
  - CO₂-Tracking und Dekarbonisierungs-Roadmap (EU-Taxonomie / EPBD III)

Endpoints:
  POST /api/v1/digital-twin/registriere           — Gebäude registrieren
  POST /api/v1/digital-twin/sensor-daten          — Live-Sensordaten einlesen
  GET  /api/v1/digital-twin/{gebaeude_id}/status  — Aktuellen Zustand abrufen
  POST /api/v1/digital-twin/energievergleich       — Soll/Ist-Energievergleich
  POST /api/v1/digital-twin/wartungsplan          — Wartungsplan aus IFC generieren
  GET  /api/v1/digital-twin/{gebaeude_id}/co2     — CO₂-Tracking & Roadmap
"""

import logging
import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Enumerationen
# ---------------------------------------------------------------------------


class ProtokollTyp(str, Enum):
    BACNET_IP = "bacnet_ip"
    BACNET_MSTP = "bacnet_mstp"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    KNX_IP = "knx_ip"
    KNX_TP = "knx_tp"
    MQTT = "mqtt"
    REST = "rest"
    OPC_UA = "opc_ua"


class SensorTyp(str, Enum):
    TEMPERATUR = "temperatur"
    FEUCHTE = "feuchte"
    CO2 = "co2_ppm"
    BELEUCHTUNG = "beleuchtung_lux"
    STROMVERBRAUCH = "stromverbrauch_kwh"
    WAERMEVERBRAUCH = "waermeverbrauch_kwh"
    WASSERVERBRAUCH = "wasserverbrauch_liter"
    BEWEGUNG = "bewegung"
    FENSTER = "fenster_offen"
    HEIZVENTIL = "heizventil_pct"
    SOLARERTRAG = "solarertrag_kwh"
    LUFTQUALITAET = "luftqualitaet_iaq"


class WartungsKategorie(str, Enum):
    HEIZUNG = "heizung"
    LUEFTUNG = "lueftung"
    KLIMAANLAGE = "klimaanlage"
    AUFZUG = "aufzug"
    ELEKTRISCH = "elektrisch"
    BRANDSCHUTZ = "brandschutz"
    DACH = "dach"
    FASSADE = "fassade"
    FENSTER = "fenster"
    SANITAER = "sanitaer"
    PHOTOVOLTAIK = "photovoltaik"


class GebaeudeBetriebTyp(str, Enum):
    WOHNEN = "wohnen"
    BUERO = "buero"
    HANDEL = "handel"
    INDUSTRIE = "industrie"
    BILDUNG = "bildung"
    GESUNDHEIT = "gesundheit"
    HOTEL = "hotel"
    SPORT = "sport"


# ---------------------------------------------------------------------------
# Pydantic-Modelle
# ---------------------------------------------------------------------------


class SensorKonfiguration(BaseModel):
    sensor_id: str
    name: str
    typ: SensorTyp
    protokoll: ProtokollTyp
    adresse: str = Field(description="IP:Port, Geräteadresse o.ä.")
    objekt_id: Optional[str] = Field(
        default=None, description="BACnet Objekt-ID / Modbus Register / KNX-Gruppenadresse"
    )
    einheit: Optional[str] = None
    messintervall_sekunden: int = Field(default=300, ge=10)
    raum_id: Optional[str] = None
    geschoss: Optional[int] = None


class GebaeudeProfil(BaseModel):
    """Gebäude-Stammdaten für den Digitalen Zwilling"""

    bundesland: str = Field(default="wien")
    adresse: str
    baujahr: int = Field(ge=1800, le=2030)
    nutzung: GebaeudeBetriebTyp
    bgf_m2: float = Field(gt=0, description="Bruttogrundfläche in m²")
    geschosse: int = Field(ge=1, le=50)
    a_v_verhaeltnis: Optional[float] = Field(
        default=None, description="A/V-Verhältnis aus Energieausweis"
    )

    # Energieausweis-Sollwerte (aus bestehendem OIB-RL 6 Nachweis)
    hwb_soll_kwh_m2a: Optional[float] = Field(
        default=None, description="Heizwärmebedarf Sollwert lt. EA"
    )
    fgee_soll: Optional[float] = Field(default=None, description="fGEE Sollwert lt. EA")
    energieklasse_soll: Optional[str] = Field(
        default=None, description="Energieklasse lt. EA z.B. A+, A, B"
    )

    sensoren: List[SensorKonfiguration] = Field(default_factory=list)


class GebaeudeProjekt(BaseModel):
    """Vollständiges Digital-Twin-Projekt"""

    projekt_name: str = Field(min_length=1)
    profil: GebaeudeProfil
    ifc_modell_pfad: Optional[str] = Field(
        default=None, description="Pfad zum IFC-Modell (Server-seitig)"
    )


class SensorMesswert(BaseModel):
    sensor_id: str
    zeitstempel: datetime
    wert: float
    einheit: str
    qualitaet: Optional[str] = Field(default="good")  # "good", "uncertain", "bad"


class SensorDatenRequest(BaseModel):
    gebaeude_id: str
    messwerte: List[SensorMesswert] = Field(min_length=1)


class EnergieVergleichRequest(BaseModel):
    """Soll/Ist-Vergleich für Energiemonitoring"""

    gebaeude_id: Optional[str] = None

    # Istwerte (aus Messung / Zähler)
    heizung_ist_kwh: float = Field(ge=0, description="Gemessener Heizenergieverbrauch in kWh/Jahr")
    strom_ist_kwh: float = Field(ge=0, description="Gemessener Stromverbrauch in kWh/Jahr")
    warmwasser_ist_kwh: float = Field(default=0.0, ge=0)
    solarertrag_kwh: float = Field(default=0.0, ge=0)
    bgf_m2: float = Field(gt=0)

    # Sollwerte aus Energieausweis
    hwb_soll_kwh_m2a: float = Field(gt=0, description="HWB-Sollwert lt. Energieausweis")
    fgee_soll: float = Field(gt=0, description="fGEE-Sollwert lt. Energieausweis")

    heizenergie_traeger: str = Field(
        default="erdgas",
        description="Energieträger: erdgas, heizoel, waermepumpe, fernwaerme, holz",
    )
    heizungsanlage_bj: Optional[int] = Field(default=None)


class WartungsplanRequest(BaseModel):
    """Wartungsplan-Generierung aus Bauteil-/Anlagendaten"""

    gebaeude_id: Optional[str] = None
    gebaeude_name: str = Field(min_length=1)
    bgf_m2: float = Field(gt=0)
    baujahr: int = Field(ge=1800, le=2030)
    bundesland: str = Field(default="wien")

    # Vorhandene Anlagen und Bauteile (vereinfacht aus IFC oder manuell)
    anlagen: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Liste von Anlagen: [{name, typ, baujahr, hersteller, modell, ...}]",
    )
    ifc_analyseresultat: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Ausgabe von /api/v1/bim/upload-ifc (optional)",
    )


# ---------------------------------------------------------------------------
# Einfache In-Memory-Registry (Produktion: PostgreSQL)
# ---------------------------------------------------------------------------

_GEBAEUDE_REGISTRY: Dict[str, Dict[str, Any]] = {}
_SENSOR_DATA: Dict[str, List[SensorMesswert]] = {}  # gebaeude_id → Messwerte


def _generiere_id(prefix: str = "GBD") -> str:
    import hashlib
    import time

    h = hashlib.md5(str(time.time_ns()).encode()).hexdigest()[:8].upper()
    return f"{prefix}-{h}"


# ---------------------------------------------------------------------------
# Energie-Berechnungslogik
# ---------------------------------------------------------------------------

# Primärenergiefaktoren f_prim (OIB-RL 6:2025 / ÖNORM EN ISO 52000-1)
PRIMAERENERGIEFAKTOREN: Dict[str, float] = {
    "erdgas": 1.17,
    "heizoel": 1.13,
    "waermepumpe": 2.70,  # elektrisch
    "fernwaerme": 0.60,
    "holz": 0.10,
    "pellets": 0.10,
    "biomasse": 0.10,
    "strom": 2.70,
    "solar": 0.0,
    "photovoltaik": 0.0,
}

# CO₂-Emissionsfaktoren (kg CO₂eq/kWh) – Quelle: Umweltbundesamt AT 2024
CO2_FAKTOREN: Dict[str, float] = {
    "erdgas": 0.247,
    "heizoel": 0.311,
    "waermepumpe": 0.163,  # Strom AT-Mix 2024
    "fernwaerme": 0.081,
    "holz": 0.025,
    "pellets": 0.028,
    "biomasse": 0.025,
    "strom": 0.163,
    "solar": 0.0,
    "photovoltaik": 0.0,
}

# Energieausweis-Klassen (fGEE-Grenzen, OIB-RL 6:2025)
ENERGIEKLASSEN: List[Tuple[str, float]] = [
    ("A++", 0.40),
    ("A+", 0.55),
    ("A", 0.70),
    ("B", 0.90),
    ("C", 1.10),
    ("D", 1.30),
    ("E", 1.60),
    ("F", 2.00),
    ("G", 9999.0),
]


def _bestimme_energieklasse(fgee: float) -> str:
    for klasse, grenze in ENERGIEKLASSEN:
        if fgee <= grenze:
            return klasse
    return "G"


def _berechne_energievergleich(req: EnergieVergleichRequest) -> Dict[str, Any]:
    """
    Vergleicht gemessenen Energieverbrauch mit dem Energieausweis-Sollwert.
    Berechnet fGEE_ist, CO₂-Emissionen und Abweichung.
    """
    hwb_ist = req.heizung_ist_kwh / req.bgf_m2
    fgee_ist = hwb_ist / req.hwb_soll_kwh_m2a if req.hwb_soll_kwh_m2a > 0 else 0.0

    pef = PRIMAERENERGIEFAKTOREN.get(req.heizenergie_traeger, 1.0)
    co2_f = CO2_FAKTOREN.get(req.heizenergie_traeger, 0.2)

    pe_kwh = req.heizung_ist_kwh * pef + req.strom_ist_kwh * PRIMAERENERGIEFAKTOREN["strom"]
    pe_kwh_m2 = pe_kwh / req.bgf_m2

    co2_kg = req.heizung_ist_kwh * co2_f + req.strom_ist_kwh * CO2_FAKTOREN["strom"]
    co2_kg_m2 = co2_kg / req.bgf_m2

    # Netto: Solarertrag abziehen
    co2_netto = max(0.0, co2_kg - req.solarertrag_kwh * CO2_FAKTOREN["strom"])

    abweichung_pct = (
        ((hwb_ist - req.hwb_soll_kwh_m2a) / req.hwb_soll_kwh_m2a * 100)
        if req.hwb_soll_kwh_m2a
        else 0
    )
    fgee_abw = fgee_ist - req.fgee_soll

    klasse_ist = _bestimme_energieklasse(fgee_ist)
    klasse_soll = _bestimme_energieklasse(req.fgee_soll)

    bewertung: str
    empfehlungen: List[str] = []

    if abweichung_pct < -10:
        bewertung = "✅ Besser als Energieausweis"
        empfehlungen.append("Sehr gute Performance — Betrieb weiterhin optimieren")
    elif abweichung_pct < 10:
        bewertung = "🟡 Im Toleranzbereich (±10%)"
        empfehlungen.append("Normaler Betrieb — saisonale Schwankungen beachten")
    elif abweichung_pct < 25:
        bewertung = "🟠 Höher als Energieausweis-Prognose"
        empfehlungen.append("Heizungsregelung und Nutzerverhalten prüfen")
        empfehlungen.append("Hydraulischer Abgleich empfehlen (EN 12831)")
    else:
        bewertung = "🔴 Deutlich höher als Energieausweis — Handlungsbedarf!"
        empfehlungen.append("Sofortiger hydraulischer Abgleich und Heizungsoptimierung")
        empfehlungen.append("Wärmeleckagen thermographisch untersuchen lassen")
        empfehlungen.append("Energieausweis-Neuerstellung prüfen")

    if req.solarertrag_kwh > 0:
        empfehlungen.append(
            f"Solarertrag {round(req.solarertrag_kwh, 0)} kWh reduziert CO₂ um {round(req.solarertrag_kwh * CO2_FAKTOREN['strom'], 1)} kg/Jahr"
        )

    # Dekarbonisierungseinsparpotenzial: Wechsel auf Wärmepumpe
    if req.heizenergie_traeger in ("erdgas", "heizoel"):
        co2_wp = req.heizung_ist_kwh / 3.0 * CO2_FAKTOREN["waermepumpe"]  # COP≈3
        co2_einsparung = co2_kg - co2_wp
        empfehlungen.append(
            f"💡 Umstieg auf Wärmepumpe: CO₂-Einsparung ca. {round(co2_einsparung, 0)} kg/Jahr "
            "(Förderung: Klimabonus + Bundesförderung HWS)"
        )

    return {
        "hwb_ist_kwh_m2a": round(hwb_ist, 2),
        "hwb_soll_kwh_m2a": req.hwb_soll_kwh_m2a,
        "abweichung_pct": round(abweichung_pct, 1),
        "fgee_ist": round(fgee_ist, 3),
        "fgee_soll": req.fgee_soll,
        "fgee_abweichung": round(fgee_abw, 3),
        "energieklasse_ist": klasse_ist,
        "energieklasse_soll": klasse_soll,
        "primaerenergie_kwh_m2a": round(pe_kwh_m2, 1),
        "co2_emissionen_kg_a": round(co2_kg, 0),
        "co2_emissionen_kg_m2a": round(co2_kg_m2, 2),
        "co2_netto_kg_a": round(co2_netto, 0),
        "solarertrag_kwh": req.solarertrag_kwh,
        "bewertung": bewertung,
        "empfehlungen": empfehlungen,
    }


# ---------------------------------------------------------------------------
# Wartungsplan-Logik (Quelle: ÖNORM EN 13306, ÖNORM B 5019)
# ---------------------------------------------------------------------------

# Typische Wartungszyklen in Jahren
WARTUNGSZYKLEN: Dict[str, Dict[str, Any]] = {
    "heizkessel_gas": {
        "kategorie": WartungsKategorie.HEIZUNG,
        "intervall_jahre": 1,
        "massnahmen": [
            "Brennereinstellung",
            "Abgasmessung (§ 15a B-VG Vereinbarung)",
            "Sicherheitsventile prüfen",
        ],
        "norm": "ÖNORM H 5170, Kehr- und Überprüfungsordnung",
        "lebensdauer_jahre": 20,
    },
    "heizkessel_oel": {
        "kategorie": WartungsKategorie.HEIZUNG,
        "intervall_jahre": 1,
        "massnahmen": ["Brenner reinigen", "Ölfilter wechseln", "Abgasmessung"],
        "norm": "Kehr- und Überprüfungsordnung (§ 15a B-VG)",
        "lebensdauer_jahre": 20,
    },
    "waermepumpe": {
        "kategorie": WartungsKategorie.HEIZUNG,
        "intervall_jahre": 2,
        "massnahmen": [
            "Kältemitteldruck prüfen",
            "Wärmetauscher reinigen",
            "Kältemittelleckage prüfen (F-Gas-VO)",
        ],
        "norm": "EU-F-Gas-Verordnung Nr. 517/2014, ÖNORM EN 378",
        "lebensdauer_jahre": 25,
    },
    "lueftungsanlage_mrv": {
        "kategorie": WartungsKategorie.LUEFTUNG,
        "intervall_jahre": 1,
        "massnahmen": [
            "Filter wechseln (G4, F7)",
            "Wärmetauscher reinigen",
            "Luftmengen nachmessen",
            "Kondensatablauf prüfen",
        ],
        "norm": "ÖNORM H 6036, OIB-RL 3",
        "lebensdauer_jahre": 20,
    },
    "aufzug": {
        "kategorie": WartungsKategorie.AUFZUG,
        "intervall_jahre": 0.25,  # vierteljährlich
        "massnahmen": [
            "Sicherheitsprüfung (Sachverständiger)",
            "Notruf testen",
            "Ölstand prüfen",
            "Führungsschienen schmieren",
        ],
        "norm": "ÖNORM EN 13015, Aufzugsgesetz",
        "lebensdauer_jahre": 30,
    },
    "brandmeldeanlage": {
        "kategorie": WartungsKategorie.BRANDSCHUTZ,
        "intervall_jahre": 1,
        "massnahmen": [
            "Melder testen",
            "Zentrale prüfen",
            "Alarmierung testen",
            "Protokoll erstellen",
        ],
        "norm": "ÖNORM EN 54, OIB-RL 2",
        "lebensdauer_jahre": 15,
    },
    "sprinkleranlage": {
        "kategorie": WartungsKategorie.BRANDSCHUTZ,
        "intervall_jahre": 1,
        "massnahmen": [
            "Druckprüfung",
            "Sprinklerköpfe prüfen",
            "Fließprüfung",
            "Protokoll für Behörde",
        ],
        "norm": "ÖNORM EN 12845, OIB-RL 2",
        "lebensdauer_jahre": 25,
    },
    "photovoltaik": {
        "kategorie": WartungsKategorie.PHOTOVOLTAIK,
        "intervall_jahre": 2,
        "massnahmen": [
            "Module reinigen",
            "Verschattung prüfen",
            "Wechselrichter prüfen",
            "Ertragsdaten auswerten",
        ],
        "norm": "ÖNORM EN IEC 62446, OIB-RL 6:2025 Solarpflicht",
        "lebensdauer_jahre": 30,
    },
    "flachdach": {
        "kategorie": WartungsKategorie.DACH,
        "intervall_jahre": 1,
        "massnahmen": ["Ablaufe reinigen", "Folie auf Risse prüfen", "Anschlüsse prüfen"],
        "norm": "ÖNORM B 3691, Dachabdichtung",
        "lebensdauer_jahre": 20,
    },
    "fassade_wdvs": {
        "kategorie": WartungsKategorie.FASSADE,
        "intervall_jahre": 5,
        "massnahmen": [
            "Risse und Absplitterungen prüfen",
            "Algenbefall behandeln",
            "Sockelbereich prüfen",
        ],
        "norm": "ETAG 004, OIB-RL 1",
        "lebensdauer_jahre": 30,
    },
    "elektrische_anlage": {
        "kategorie": WartungsKategorie.ELEKTRISCH,
        "intervall_jahre": 5,
        "massnahmen": [
            "E-Check (Sachverständiger)",
            "FI-Schalter prüfen",
            "Schutzleiter prüfen",
            "Protokoll",
        ],
        "norm": "ÖNORM E 8001, ElWOG",
        "lebensdauer_jahre": 30,
    },
    "sanitaer_rohrleitungen": {
        "kategorie": WartungsKategorie.SANITAER,
        "intervall_jahre": 3,
        "massnahmen": [
            "Leckagen prüfen",
            "Ventile gängig halten",
            "Trinkwasserqualität prüfen (ÖVGW W 101)",
        ],
        "norm": "ÖNORM EN 806, ÖVGW W 101",
        "lebensdauer_jahre": 50,
    },
}


def _generiere_wartungsplan(req: WartungsplanRequest) -> Dict[str, Any]:
    """
    Generiert einen vollständigen Wartungsplan aus Anlagendaten.
    Berücksichtigt Baujahr, Alter und gesetzliche Wartungspflichten in AT.
    """
    jetzt = datetime.now()
    aufgaben: List[Dict[str, Any]] = []

    # Aus explizit gelisteten Anlagen
    for anlage in req.anlagen:
        anlage_typ = anlage.get("typ", "").lower().replace(" ", "_")
        vorlage = None
        # Fuzzy-Matching auf Wartungsvorlagen
        for key, val in WARTUNGSZYKLEN.items():
            if key in anlage_typ or anlage_typ in key:
                vorlage = (key, val)
                break

        if vorlage is None:
            # Fallback: generische Wartung
            vorlage = (
                anlage_typ,
                {
                    "kategorie": "sonstige",
                    "intervall_jahre": 2,
                    "massnahmen": ["Sichtprüfung", "Reinigung", "Funktion testen"],
                    "norm": "Herstellerempfehlung",
                    "lebensdauer_jahre": 20,
                },
            )

        key, v = vorlage
        anlage_bj = anlage.get("baujahr", req.baujahr)
        alter_jahre = jetzt.year - anlage_bj
        restlebensdauer = max(0, v["lebensdauer_jahre"] - alter_jahre)

        naechste_wartung = jetzt + timedelta(days=int(v["intervall_jahre"] * 365))

        prioritaet = "normal"
        if restlebensdauer < 5:
            prioritaet = "hoch"
        if alter_jahre > v["lebensdauer_jahre"]:
            prioritaet = "kritisch"

        aufgaben.append(
            {
                "anlage": anlage.get("name", key),
                "typ": anlage.get("typ", key),
                "kategorie": (
                    v["kategorie"].value if hasattr(v["kategorie"], "value") else v["kategorie"]
                ),
                "baujahr_anlage": anlage_bj,
                "alter_jahre": alter_jahre,
                "intervall_jahre": v["intervall_jahre"],
                "naechste_wartung": naechste_wartung.strftime("%Y-%m-%d"),
                "massnahmen": v["massnahmen"],
                "norm": v["norm"],
                "restlebensdauer_jahre": restlebensdauer,
                "prioritaet": prioritaet,
                "hersteller": anlage.get("hersteller"),
                "modell": anlage.get("modell"),
                "seriennummer": anlage.get("seriennummer"),
            }
        )

    # IFC-Informationen verarbeiten (falls vorhanden)
    if req.ifc_analyseresultat:
        ifc_materialien = req.ifc_analyseresultat.get("materials", [])
        for mat in ifc_materialien:
            mat_name = mat.get("name", "").lower()
            if "dach" in mat_name or "roof" in mat_name:
                aufgaben.append(
                    {
                        "anlage": f"Dach: {mat.get('name', 'Dachbelag')}",
                        "typ": "flachdach",
                        "kategorie": "dach",
                        "baujahr_anlage": req.baujahr,
                        "alter_jahre": jetzt.year - req.baujahr,
                        "intervall_jahre": 1,
                        "naechste_wartung": (jetzt + timedelta(days=365)).strftime("%Y-%m-%d"),
                        "massnahmen": WARTUNGSZYKLEN["flachdach"]["massnahmen"],
                        "norm": WARTUNGSZYKLEN["flachdach"]["norm"],
                        "restlebensdauer_jahre": max(0, 20 - (jetzt.year - req.baujahr)),
                        "prioritaet": "normal" if (jetzt.year - req.baujahr) < 15 else "hoch",
                        "quelle": "IFC-Modell (automatisch erkannt)",
                    }
                )

    # Sortieren nach Dringlichkeit
    prio_order = {"kritisch": 0, "hoch": 1, "normal": 2}
    aufgaben.sort(key=lambda x: prio_order.get(x["prioritaet"], 2))

    # Kosten-Schätzung (vereinfacht)
    kritisch_count = sum(1 for a in aufgaben if a["prioritaet"] == "kritisch")
    hoch_count = sum(1 for a in aufgaben if a["prioritaet"] == "hoch")
    geschaetzte_kosten = kritisch_count * 5000 + hoch_count * 2000 + len(aufgaben) * 500

    return {
        "gebaeude": req.gebaeude_name,
        "bgf_m2": req.bgf_m2,
        "baujahr": req.baujahr,
        "bundesland": req.bundesland,
        "erstellt_am": jetzt.strftime("%Y-%m-%dT%H:%M:%S"),
        "wartungsaufgaben": aufgaben,
        "zusammenfassung": {
            "gesamt_aufgaben": len(aufgaben),
            "kritisch": kritisch_count,
            "hoch": hoch_count,
            "normal": len(aufgaben) - kritisch_count - hoch_count,
            "geschaetzte_kosten_eur_p_a": geschaetzte_kosten,
        },
        "hinweis": (
            "Wartungsplan gem. ÖNORM EN 13306 und AT-Rechtsvorschriften. "
            "Kritische Anlagen sofort prüfen. Immer zertifizierte Fachbetriebe einsetzen."
        ),
    }


# ---------------------------------------------------------------------------
# CO₂-Tracking & Dekarbonisierungs-Roadmap
# ---------------------------------------------------------------------------


def _berechne_co2_roadmap(
    co2_aktuell_kg_m2a: float,
    bgf_m2: float,
    baujahr: int,
    heiztraeger: str,
) -> Dict[str, Any]:
    """
    EU-Taxonomie / EPBD III: Dekarbonisierungsroad-map bis 2050.
    Ziel: 0 kg CO₂/m²a bis 2050 (Klimaneutralität Österreich).
    """
    jetzt = datetime.now()
    ziel_2030 = co2_aktuell_kg_m2a * 0.55  # -45%
    ziel_2040 = co2_aktuell_kg_m2a * 0.30  # -70%
    ziel_2050 = 0.0  # netto-null

    massnahmen: List[Dict[str, Any]] = []

    if heiztraeger in ("erdgas", "heizoel"):
        einsparung_wp = co2_aktuell_kg_m2a * 0.60
        massnahmen.append(
            {
                "massnahme": "Heizungstausch → Wärmepumpe",
                "zeithorizont": "2025–2030",
                "co2_einsparung_kg_m2a": round(einsparung_wp, 2),
                "kosten_eur_m2": "80–150",
                "foerderung": "Klimabonus (Bund), Wohnbauförderung (Land)",
                "norm": "OIB-RL 6:2025, Erneuerbaren-Ausbau-Gesetz (EAG)",
            }
        )

    massnahmen.append(
        {
            "massnahme": "Gebäudehülle sanieren (Außenwanddämmung, Fenstertausch)",
            "zeithorizont": "2026–2035",
            "co2_einsparung_kg_m2a": round(co2_aktuell_kg_m2a * 0.25, 2),
            "kosten_eur_m2": "200–400",
            "foerderung": "Sanierungsbonus (Bund), Wohnbauförderung (Land)",
            "norm": "OIB-RL 6:2025, Renovierungspass",
        }
    )

    massnahmen.append(
        {
            "massnahme": "Photovoltaik-Anlage installieren (Solarpflicht ab 2027)",
            "zeithorizont": "2025–2030 (Solarpflicht ab 2027 für Nicht-Wohngebäude)",
            "co2_einsparung_kg_m2a": round(co2_aktuell_kg_m2a * 0.15, 2),
            "kosten_eur_m2": "30–80",
            "foerderung": "EAG-Investitionszuschuss, Netzübertragungstarif",
            "norm": "OIB-RL 6:2025, EAG",
        }
    )

    massnahmen.append(
        {
            "massnahme": "Lüftungsanlage mit Wärmerückgewinnung",
            "zeithorizont": "2028–2035",
            "co2_einsparung_kg_m2a": round(co2_aktuell_kg_m2a * 0.10, 2),
            "kosten_eur_m2": "50–100",
            "foerderung": "Wohnbauförderung (Bundesland)",
            "norm": "OIB-RL 3, ÖNORM H 6036",
        }
    )

    return {
        "co2_aktuell_kg_m2a": round(co2_aktuell_kg_m2a, 2),
        "co2_gesamt_kg_a": round(co2_aktuell_kg_m2a * bgf_m2, 0),
        "ziele": {
            "2030": {"co2_kg_m2a": round(ziel_2030, 2), "reduktion_pct": 45},
            "2040": {"co2_kg_m2a": round(ziel_2040, 2), "reduktion_pct": 70},
            "2050": {"co2_kg_m2a": ziel_2050, "reduktion_pct": 100},
        },
        "massnahmen": massnahmen,
        "eu_taxonomie_konform": co2_aktuell_kg_m2a < 10.0,  # NZEB-Schwelle
        "quelle": "EU-Taxonomie (Reg. 2020/852), EPBD III (Richtlinie 2024/1275), OIB-RL 6:2025",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/registriere",
    summary="Gebäude im Digital Twin registrieren",
    tags=["digital-twin"],
)
async def registriere_gebaeude(projekt: GebaeudeProjekt) -> Dict[str, Any]:
    """
    Registriert ein neues Gebäude im Digitalen Zwilling und gibt eine Gebäude-ID zurück.
    Sensoren und Protokoll-Konfigurationen werden gespeichert.
    """
    gebaeude_id = _generiere_id("GBD")
    _GEBAEUDE_REGISTRY[gebaeude_id] = {
        "id": gebaeude_id,
        "projekt_name": projekt.projekt_name,
        "profil": projekt.profil.model_dump(),
        "erstellt": datetime.now().isoformat(),
        "sensoren": {s.sensor_id: s.model_dump() for s in projekt.profil.sensoren},
    }
    logger.info("Digital Twin registriert: %s (%s)", gebaeude_id, projekt.profil.adresse)

    protokolle = list({s.protokoll for s in projekt.profil.sensoren})
    return {
        "gebaeude_id": gebaeude_id,
        "projekt_name": projekt.projekt_name,
        "adresse": projekt.profil.adresse,
        "sensoren_count": len(projekt.profil.sensoren),
        "protokolle": protokolle,
        "status": "registriert",
        "naechster_schritt": f"Sensordaten an POST /api/v1/digital-twin/sensor-daten senden",
    }


@router.post(
    "/sensor-daten",
    summary="Sensordaten einspeisen",
    tags=["digital-twin"],
)
async def empfange_sensor_daten(req: SensorDatenRequest) -> Dict[str, Any]:
    """
    Empfängt Messwerte von Sensoren (BACnet, Modbus, KNX, MQTT).
    Werte werden in der In-Memory-Datenbank gespeichert.
    In Produktion: Zeitreihendatenbank (InfluxDB, TimescaleDB).
    """
    if req.gebaeude_id not in _GEBAEUDE_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Gebäude '{req.gebaeude_id}' nicht registriert. Erst POST /registriere aufrufen.",
        )

    if req.gebaeude_id not in _SENSOR_DATA:
        _SENSOR_DATA[req.gebaeude_id] = []

    _SENSOR_DATA[req.gebaeude_id].extend(req.messwerte)

    # Kompaktes Aggregat für die Antwort
    werte_by_typ: Dict[str, List[float]] = {}
    for m in req.messwerte:
        if m.sensor_id not in werte_by_typ:
            werte_by_typ[m.sensor_id] = []
        werte_by_typ[m.sensor_id].append(m.wert)

    return {
        "gebaeude_id": req.gebaeude_id,
        "messwerte_gespeichert": len(req.messwerte),
        "zeitraum_von": min(m.zeitstempel for m in req.messwerte).isoformat(),
        "zeitraum_bis": max(m.zeitstempel for m in req.messwerte).isoformat(),
        "sensoren": list(werte_by_typ),
        "status": "gespeichert",
    }


@router.get(
    "/{gebaeude_id}/status",
    summary="Gebäudestatus abrufen",
    tags=["digital-twin"],
)
async def get_gebaeude_status(
    gebaeude_id: str = Path(description="Gebäude-ID aus /registriere"),
) -> Dict[str, Any]:
    """
    Gibt den aktuellen Status des digitalen Zwillings zurück:
    letzter Messwert je Sensor, Anomalien, Systemstatus.
    """
    if gebaeude_id not in _GEBAEUDE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Gebäude '{gebaeude_id}' nicht gefunden")

    gbd = _GEBAEUDE_REGISTRY[gebaeude_id]
    messwerte = _SENSOR_DATA.get(gebaeude_id, [])

    letzter_wert: Dict[str, Any] = {}
    for m in messwerte:
        if (
            m.sensor_id not in letzter_wert
            or m.zeitstempel > letzter_wert[m.sensor_id]["zeitstempel"]
        ):
            letzter_wert[m.sensor_id] = {
                "wert": m.wert,
                "einheit": m.einheit,
                "zeitstempel": m.zeitstempel.isoformat(),
            }

    return {
        "gebaeude_id": gebaeude_id,
        "projekt_name": gbd["projekt_name"],
        "adresse": gbd["profil"]["adresse"],
        "registriert_am": gbd["erstellt"],
        "messwerte_gesamt": len(messwerte),
        "letzter_messwert_je_sensor": letzter_wert,
        "system_status": "online" if messwerte else "warte_auf_daten",
        "hinweis": "Für produktiven Einsatz: InfluxDB/TimescaleDB als Zeitreihendatenbank konfigurieren",
    }


@router.post(
    "/energievergleich",
    summary="Soll/Ist-Energievergleich mit Energieausweis",
    tags=["digital-twin"],
)
async def energievergleich(req: EnergieVergleichRequest) -> Dict[str, Any]:
    """
    Vergleicht den gemessenen Energieverbrauch (Jahresbilanz) mit dem Energieausweis-Sollwert.

    Berechnet:
    - fGEE_ist vs. fGEE_soll (OIB-RL 6)
    - CO₂-Emissionen und Einsparungspotenzial
    - Abweichung in % und Handlungsempfehlungen
    - Energieklasse (Ist vs. Soll)
    """
    ergebnis = _berechne_energievergleich(req)
    return {
        "typ": "energievergleich",
        "gebaeude_id": req.gebaeude_id,
        "ergebnis": ergebnis,
        "norm": "OIB-RL 6:2025, ÖNORM EN ISO 52000-1",
        "co2_faktoren_quelle": "Umweltbundesamt AT 2024",
    }


@router.post(
    "/wartungsplan",
    summary="Wartungsplan aus Anlagendaten generieren",
    tags=["digital-twin"],
)
async def generiere_wartungsplan(req: WartungsplanRequest) -> Dict[str, Any]:
    """
    Generiert einen gesetzeskonformen Wartungsplan für alle Gebäudeanlagen.

    Berücksichtigt österreichische Wartungsvorschriften:
    - ÖNORM EN 13306 (Instandhaltung)
    - Kehr- und Überprüfungsordnung (§ 15a B-VG Vereinbarung)
    - OIB-RL 2 (Brandschutz), OIB-RL 3 (Lüftung)
    - EU-F-Gas-Verordnung (Kälteanlagen)
    - Aufzugsgesetz
    """
    plan = _generiere_wartungsplan(req)
    return {
        "typ": "wartungsplan",
        **plan,
    }


@router.get(
    "/{gebaeude_id}/co2",
    summary="CO₂-Tracking und Dekarbonisierungs-Roadmap",
    tags=["digital-twin"],
)
async def co2_roadmap(
    gebaeude_id: str = Path(description="Gebäude-ID"),
    co2_aktuell_kg_m2a: float = Query(gt=0, description="Aktueller CO₂-Wert in kg/m²a"),
    heiztraeger: str = Query(
        default="erdgas", description="erdgas|heizoel|waermepumpe|fernwaerme|holz"
    ),
) -> Dict[str, Any]:
    """
    Erstellt eine Dekarbonisierungs-Roadmap gemäß EU-Taxonomie und EPBD III.

    Ziele:
    - 2030: -45% CO₂ (Nat. Klimaplan AT)
    - 2040: -70% CO₂ (Fit for 55)
    - 2050: Netto-Null (Klimaneutralität AT)
    """
    if gebaeude_id not in _GEBAEUDE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Gebäude '{gebaeude_id}' nicht registriert")

    gbd = _GEBAEUDE_REGISTRY[gebaeude_id]
    bgf = gbd["profil"].get("bgf_m2", 1.0)
    baujahr = gbd["profil"].get("baujahr", 1990)

    roadmap = _berechne_co2_roadmap(co2_aktuell_kg_m2a, bgf, baujahr, heiztraeger)
    return {
        "gebaeude_id": gebaeude_id,
        "roadmap": roadmap,
        "eu_rahmen": "EPBD III (Richtlinie 2024/1275), EU-Taxonomie VO 2020/852",
        "at_rahmen": "Klima- und Energiestrategie #mission2030, EAG, OIB-RL 6:2025",
    }


@router.get(
    "/protokolle/info",
    summary="Unterstützte Smart-Building-Protokolle",
    tags=["digital-twin"],
)
async def protokoll_info() -> Dict[str, Any]:
    """
    Gibt Informationen zu den unterstützten Smart-Building-Protokollen zurück.
    """
    return {
        "unterstuetzte_protokolle": [
            {
                "protokoll": "BACnet/IP (ASHRAE 135)",
                "enum_wert": "bacnet_ip",
                "beschreibung": "Gebäudeautomation, HLK-Anlagen, DDC-Regler",
                "typische_anwendungen": ["Heizung", "Lüftung", "Klimaanlage", "Beleuchtung"],
                "standard": "ASHRAE 135 / ISO 16484-5",
                "port": 47808,
            },
            {
                "protokoll": "Modbus TCP",
                "enum_wert": "modbus_tcp",
                "beschreibung": "Energiezähler, Wechselrichter, Sensoren",
                "typische_anwendungen": [
                    "Energiemessung",
                    "PV-Wechselrichter",
                    "Frequenzumrichter",
                ],
                "standard": "Modbus Application Protocol v1.1b3",
                "port": 502,
            },
            {
                "protokoll": "KNX/IP (EIB)",
                "enum_wert": "knx_ip",
                "beschreibung": "Gebäudeinstallation, Licht, Jalousien, Heizung",
                "typische_anwendungen": ["Beleuchtungssteuerung", "Beschattung", "Raumtemperatur"],
                "standard": "ISO/IEC 14543-3, ÖNORM EN 50090",
                "port": 3671,
            },
            {
                "protokoll": "MQTT (IoT)",
                "enum_wert": "mqtt",
                "beschreibung": "IoT-Sensoren, Smarthome-Geräte",
                "typische_anwendungen": ["Temperatur", "CO₂", "Bewegung", "Fenster"],
                "standard": "OASIS MQTT v5.0",
                "port": 1883,
            },
            {
                "protokoll": "OPC UA",
                "enum_wert": "opc_ua",
                "beschreibung": "Industrielle Automation, Energiemanagementsysteme",
                "typische_anwendungen": ["Energiemanagement (ISO 50001)", "Produktionsanlagen"],
                "standard": "IEC 62541",
                "port": 4840,
            },
        ],
        "hinweis": (
            "Für produktive Integration: Gateway-Hardware (z.B. Wago 750, Siemens LOGO!, "
            "Beckhoff CX) an die jeweiligen Feldbus-Protokolle anschließen und REST/MQTT "
            "nach ORION Architekt-AT bridgen."
        ),
    }
