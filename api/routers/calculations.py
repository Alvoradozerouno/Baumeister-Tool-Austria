"""
Building Calculations Router
U-Wert, Stellplätze, Flächenberechnung, etc.
"""

import math
import os
import re
import sys
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()


# Models
class Schicht(BaseModel):
    """Layer in construction"""

    material: str = Field(..., min_length=1, max_length=200)
    dicke_mm: float = Field(..., gt=0, le=5000)
    lambda_wert: float = Field(..., gt=0, le=10)

    @field_validator("material")
    @classmethod
    def validate_material(cls, v: str) -> str:
        """Sanitize material name to prevent injection attacks"""
        # Remove null bytes
        v = v.replace("\x00", "")
        # Reject strings with script/injection patterns (SQL keywords, HTML tags, URLs)
        dangerous_patterns = [
            r"<[^>]+>",  # HTML/XML tags
            r"--\s",  # SQL comment injection
            r";\s*(DROP|DELETE|INSERT|UPDATE|SELECT|CREATE|ALTER|EXEC)\b",  # SQL DML/DDL
            r"https?://",  # HTTP URLs (SSRF)
            r"file://",  # Local file access
            r"ftp://",  # FTP access
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    "Invalid material name: contains disallowed characters or patterns"
                )
        return v.strip()


class UWertRequest(BaseModel):
    """U-value calculation request"""

    schichten: List[Schicht] = Field(..., min_length=1)
    innen_uebergang: float = Field(0.13, description="Internal heat transfer coefficient")
    aussen_uebergang: float = Field(0.04, description="External heat transfer coefficient")


class UWertResult(BaseModel):
    """U-value calculation result"""

    uwert: float
    gesamtdicke_mm: float
    r_gesamt: float
    oib_rl6_compliant: bool
    energy_class: str


class StellplatzRequest(BaseModel):
    """Parking space calculation request"""

    bundesland: str
    wohnungen: int = Field(..., gt=0)
    building_type: str = Field("mehrfamilienhaus")


class StellplatzResult(BaseModel):
    """Parking space calculation result"""

    required_stellplaetze: int
    factor: float
    bundesland: str
    regulation: str


class FlaecheRequest(BaseModel):
    """Area calculation request (ÖNORM B 1800)"""

    raumtyp: str
    laenge_m: float = Field(..., gt=0, le=1000)
    breite_m: float = Field(..., gt=0, le=1000)
    hoehe_m: float = Field(..., gt=0, le=100)


class FlaecheResult(BaseModel):
    """Area calculation result"""

    bgf_m2: float
    ngf_m2: float
    nrf_m2: float
    vgf_m2: float
    standard: str = "ÖNORM B 1800"


# Request models for endpoints that previously used query parameters
class BarrierefreiheitRequest(BaseModel):
    """Accessibility check request"""

    tuer_breite_cm: float = Field(..., ge=50, le=300)
    rampe_vorhanden: bool
    rampe_steigung_prozent: Optional[float] = None
    aufzug_vorhanden: bool = False
    geschosse: int = Field(1, ge=1, le=200)


class FluchtwegRequest(BaseModel):
    """Emergency exit check request"""

    max_entfernung_m: float = Field(..., ge=0, le=200)
    treppenhaus_breite_m: float = Field(..., ge=0.5, le=10)
    geschosse: int = Field(..., ge=1, le=200)
    gebaudetyp: str = Field("wohngebaeude")


class SchallschutzRequest(BaseModel):
    """Sound insulation check request"""

    wandaufbau: List[Schicht] = Field(..., min_length=1)
    gebaudetyp: str = Field("mehrfamilienhaus")


class HeizlastRequest(BaseModel):
    """Heating load calculation request"""

    bgf_m2: float = Field(..., gt=0, le=1000000)
    uwert_wand: float = Field(..., gt=0, le=5)
    uwert_dach: float = Field(..., gt=0, le=5)
    uwert_fenster: float = Field(..., gt=0, le=10)
    bundesland: str = Field("wien")


# Endpoints
@router.post("/uwert", response_model=UWertResult)
async def berechne_uwert(request: UWertRequest):
    """
    🌡️ **U-Wert Berechnung**

    Calculate thermal transmittance (U-value) for multi-layer construction.
    According to ÖNORM EN ISO 6946.

    U = 1 / R_total
    where R_total = R_si + Σ(d/λ) + R_se
    """
    # Calculate R-values
    r_innen = request.innen_uebergang
    r_aussen = request.aussen_uebergang

    r_schichten = sum(
        schicht.dicke_mm / 1000 / schicht.lambda_wert for schicht in request.schichten
    )

    r_gesamt = r_innen + r_schichten + r_aussen

    # Calculate U-value
    uwert = 1 / r_gesamt

    # Calculate total thickness
    gesamtdicke_mm = sum(schicht.dicke_mm for schicht in request.schichten)

    # Check OIB-RL 6:2023 compliance for exterior wall (max 0.35 W/m²K for Neubau)
    oib_rl6_compliant = uwert <= 0.35

    # Determine energy class based on U-value thresholds (OIB-RL 6:2023 Außenwand)
    if uwert <= 0.15:
        energy_class = "A+"
    elif uwert <= 0.20:
        energy_class = "A"
    elif uwert <= 0.25:
        energy_class = "B"
    elif uwert <= 0.35:
        energy_class = "C"
    elif uwert <= 0.50:
        energy_class = "D"
    else:
        energy_class = "E"

    return UWertResult(
        uwert=round(uwert, 3),
        gesamtdicke_mm=gesamtdicke_mm,
        r_gesamt=round(r_gesamt, 3),
        oib_rl6_compliant=oib_rl6_compliant,
        energy_class=energy_class,
    )


@router.post("/stellplaetze", response_model=StellplatzResult)
async def berechne_stellplaetze(request: StellplatzRequest):
    """
    🚗 **Stellplatz-Berechnung**

    Calculate required parking spaces according to Bundesland building codes.

    Each Bundesland has different requirements:
    - Wien: 1.2 spaces per apartment
    - Tirol: 1.5 spaces per apartment
    - Salzburg: 1.3 spaces per apartment
    - etc.
    """
    # Stellplatz factors by Bundesland
    stellplatz_factors = {
        "wien": 1.2,
        "tirol": 1.5,
        "salzburg": 1.3,
        "vorarlberg": 1.4,
        "burgenland": 1.0,
        "kaernten": 1.2,
        "steiermark": 1.3,
        "oberoesterreich": 1.3,
        "niederoesterreich": 1.2,
    }

    bundesland_lower = request.bundesland.lower()

    if bundesland_lower not in stellplatz_factors:
        raise HTTPException(status_code=400, detail=f"Invalid Bundesland: {request.bundesland}")

    factor = stellplatz_factors[bundesland_lower]
    required = int(request.wohnungen * factor)

    return StellplatzResult(
        required_stellplaetze=required,
        factor=factor,
        bundesland=request.bundesland,
        regulation=f"{request.bundesland.title()} Bauordnung",
    )


@router.post("/flaeche", response_model=FlaecheResult)
async def berechne_flaeche(request: FlaecheRequest):
    """
    📐 **Flächenberechnung nach ÖNORM B 1800**

    Calculate building areas according to Austrian standard ÖNORM B 1800:
    - BGF: Brutto-Grundfläche (Gross floor area)
    - NGF: Netto-Grundfläche (Net floor area)
    - NRF: Nutz-Raumfläche (Usable room area)
    - VGF: Verkehrs-Grundfläche (Circulation area)
    """
    grundflaeche = request.laenge_m * request.breite_m

    # BGF = total gross area
    bgf_m2 = grundflaeche

    # NGF = BGF - construction area (approx 15%)
    ngf_m2 = bgf_m2 * 0.85

    # NRF = usable area (depends on room type, typically 70-75% of NGF)
    nrf_factor = 0.75 if request.raumtyp in ["wohnung", "buero"] else 0.70
    nrf_m2 = ngf_m2 * nrf_factor

    # VGF = circulation area (NGF - NRF)
    vgf_m2 = ngf_m2 - nrf_m2

    return FlaecheResult(
        bgf_m2=round(bgf_m2, 2),
        ngf_m2=round(ngf_m2, 2),
        nrf_m2=round(nrf_m2, 2),
        vgf_m2=round(vgf_m2, 2),
    )


@router.post("/barrierefreiheit-check")
async def check_barrierefreiheit(request: BarrierefreiheitRequest):
    """
    ♿ **Barrierefreiheit Check**

    Check accessibility requirements according to ÖNORM B 1600:
    - Door width minimum 90cm
    - Ramp maximum 6% slope
    - Elevator required for buildings with 4+ floors
    """
    mangel = []
    tuer_breite_cm = request.tuer_breite_cm
    rampe_vorhanden = request.rampe_vorhanden
    rampe_steigung_prozent = request.rampe_steigung_prozent
    aufzug_vorhanden = request.aufzug_vorhanden
    geschosse = request.geschosse

    # Door width check
    if tuer_breite_cm < 90:
        mangel.append(f"Türbreite {tuer_breite_cm}cm zu gering (minimum: 90cm)")

    # Ramp check
    if rampe_vorhanden and rampe_steigung_prozent:
        if rampe_steigung_prozent > 6:
            mangel.append(f"Rampensteigung {rampe_steigung_prozent}% zu steil (maximum: 6%)")

    # Elevator check
    if geschosse >= 4 and not aufzug_vorhanden:
        mangel.append(f"Aufzug erforderlich bei {geschosse} Geschoßen")

    return {
        "compliant": len(mangel) == 0,
        "standard": "ÖNORM B 1600",
        "mangel": mangel,
        "status": "pass" if len(mangel) == 0 else "fail",
    }


@router.post("/fluchtweg-check")
async def check_fluchtweg(request: FluchtwegRequest):
    """
    🚨 **Fluchtweg Check**

    Check emergency exit requirements according to OIB-RL 4:
    - Maximum distance to exit: 40m (residential)
    - Stairway minimum width: 1.20m
    - Additional requirements for high-rise buildings
    """
    mangel = []
    warnings = []
    max_entfernung_m = request.max_entfernung_m
    treppenhaus_breite_m = request.treppenhaus_breite_m
    geschosse = request.geschosse
    gebaudetyp = request.gebaudetyp

    # Distance check
    max_allowed = 40 if gebaudetyp == "wohngebaeude" else 35
    if max_entfernung_m > max_allowed:
        mangel.append(f"Fluchtweg {max_entfernung_m}m zu lang (maximum: {max_allowed}m)")

    # Stairway width check
    min_breite = 1.20 if geschosse >= 4 else 1.00
    if treppenhaus_breite_m < min_breite:
        mangel.append(f"Treppenhaus {treppenhaus_breite_m}m zu schmal (minimum: {min_breite}m)")
    elif treppenhaus_breite_m < min_breite + 0.1:
        warnings.append(
            f"Treppenhaus {treppenhaus_breite_m}m knapp bemessen (empfohlen: >{min_breite}m)"
        )

    # High-rise requirements
    if geschosse >= 5:
        warnings.append("Hochhaus-Anforderungen prüfen: zweiter Fluchtweg, Feuerwehraufzug")

    return {
        "compliant": len(mangel) == 0,
        "standard": "OIB-RL 4",
        "mangel": mangel,
        "warnings": warnings,
        "status": (
            "pass"
            if len(mangel) == 0 and len(warnings) == 0
            else ("warning" if len(mangel) == 0 else "fail")
        ),
    }


@router.post("/schallschutz-berechnung")
async def berechne_schallschutz(request: SchallschutzRequest):
    """
    🔊 **Schallschutz-Berechnung**

    Calculate sound insulation according to ÖNORM B 8115-2:
    - Residential buildings: minimum R'w = 52 dB
    - Between apartments: minimum R'w = 55 dB
    """
    # Simplified calculation - real version would use more complex algorithm
    # Sound reduction index increases with mass (simplified mass law)
    gesamtmasse_kg_m2 = sum(
        schicht.dicke_mm / 1000 * 2000  # Simplified: assuming 2000 kg/m3 average density
        for schicht in request.wandaufbau
    )

    # Simplified mass law: R_w ≈ 20*log10(m*f) - 47 at f=500 Hz
    rw_estimated = 20 * math.log10(gesamtmasse_kg_m2 * 500) - 47

    # Requirements
    required_rw = 55 if request.gebaudetyp == "mehrfamilienhaus" else 52

    return {
        "rw_estimated": round(rw_estimated, 1),
        "required_rw": required_rw,
        "compliant": rw_estimated >= required_rw,
        "standard": "ÖNORM B 8115-2",
        "wandmasse_kg_m2": round(gesamtmasse_kg_m2, 1),
        "status": "pass" if rw_estimated >= required_rw else "fail",
    }


@router.post("/heizlast-berechnung")
async def berechne_heizlast(request: HeizlastRequest):
    """
    🔥 **Heizlast-Berechnung**

    Calculate heating load according to ÖNORM EN 12831:
    - Transmission losses
    - Ventilation losses
    - Climate zone factors
    """
    bgf_m2 = request.bgf_m2
    uwert_wand = request.uwert_wand
    uwert_dach = request.uwert_dach
    uwert_fenster = request.uwert_fenster
    bundesland = request.bundesland
    # Climate factors by Bundesland (simplified)
    klima_faktoren = {
        "wien": 1.0,
        "tirol": 1.2,
        "salzburg": 1.15,
        "vorarlberg": 1.15,
        "kaernten": 1.1,
        "steiermark": 1.05,
        "oberoesterreich": 1.05,
        "niederoesterreich": 0.95,
        "burgenland": 0.9,
    }

    klima_faktor = klima_faktoren.get(bundesland.lower(), 1.0)

    # Simplified calculation
    # Transmission losses: Q_T = A * U * ΔT
    delta_t = 25  # Temperature difference (20°C inside - (-5°C) outside)

    q_wand = bgf_m2 * 3 * uwert_wand * delta_t  # Assuming 3x wall area
    q_dach = bgf_m2 * uwert_dach * delta_t
    q_fenster = bgf_m2 * 0.3 * uwert_fenster * delta_t  # 30% window area

    q_transmission = (q_wand + q_dach + q_fenster) * klima_faktor

    # Ventilation losses: Q_V = V * ρ * c * n * ΔT
    volumen = bgf_m2 * 2.7  # 2.7m ceiling height
    q_ventilation = volumen * 0.34 * 0.5 * delta_t  # 0.5 air changes/hour

    heizlast_gesamt = q_transmission + q_ventilation

    # Specific heating load
    spezifische_heizlast = heizlast_gesamt / bgf_m2

    return {
        "heizlast_gesamt_w": round(heizlast_gesamt, 0),
        "spezifische_heizlast_w_m2": round(spezifische_heizlast, 1),
        "q_transmission_w": round(q_transmission, 0),
        "q_ventilation_w": round(q_ventilation, 0),
        "klima_faktor": klima_faktor,
        "bundesland": bundesland,
        "standard": "ÖNORM EN 12831",
    }


@router.get("/materialdatenbank")
async def get_materialdatenbank(material_typ: Optional[str] = None):
    """
    📚 **Materialdatenbank**

    Get standard building materials with thermal properties.
    Based on ÖNORM standards and manufacturer data.
    """
    materials = [
        {"name": "Beton C30/37", "lambda": 2.3, "dichte": 2400, "kategorie": "Tragkonstruktion"},
        {"name": "Ziegel 25cm", "lambda": 0.65, "dichte": 1600, "kategorie": "Mauerwerk"},
        {"name": "EPS Dämmung", "lambda": 0.035, "dichte": 20, "kategorie": "Dämmung"},
        {"name": "Mineralwolle", "lambda": 0.035, "dichte": 50, "kategorie": "Dämmung"},
        {"name": "Holz (Fichte)", "lambda": 0.13, "dichte": 450, "kategorie": "Tragkonstruktion"},
        {"name": "Gipskarton", "lambda": 0.21, "dichte": 750, "kategorie": "Ausbau"},
        {"name": "Kalkzementputz", "lambda": 0.70, "dichte": 1600, "kategorie": "Oberfläche"},
        {"name": "3-fach Verglasung", "lambda": 0.7, "dichte": 2500, "kategorie": "Fenster"},
    ]

    if material_typ:
        materials = [m for m in materials if m["kategorie"].lower() == material_typ.lower()]

    return {"materials": materials, "total": len(materials)}


class HWBGrenzwertRequest(BaseModel):
    """OIB-RL 6:2023 HWB compliance check request"""

    hwb_ref_rk: float = Field(
        ...,
        gt=0,
        le=500,
        description="Berechneter HWBRef,RK in kWh/(m²a) — auf Referenzklima umgerechnet",
    )
    a_v_verhaeltnis: float = Field(
        ...,
        ge=0.20,
        le=0.80,
        description="A/V-Verhältnis: wärmeübertragende Hüllfläche / beheiztes Brutto-Volumen (m²/m³)",
    )


@router.post("/hwb-grenzwert-oib6")
async def pruefe_hwb_grenzwert(request: HWBGrenzwertRequest):
    """
    🌡️ **HWB Grenzwert-Prüfung nach OIB-RL 6:2023**

    Prüft ob ein Heizwärmebedarf die Anforderungen der OIB-RL 6 Ausgabe 2023 erfüllt.

    **Formel:** HWBRef,RK,max = 10 + 30 × (A/V) kWh/(m²a)

    | A/V  | HWBmax [kWh/(m²a)] |
    |------|-------------------|
    | 0,20 | 16,0              |
    | 0,40 | 22,0              |
    | 0,50 | 25,0              |
    | 0,60 | 28,0              |
    | 0,80 | 34,0              |

    ⚠️ **Ziviltechniker-Pflicht**: Der Energieausweis muss von einem befugten
    Ziviltechniker oder Energieberater ausgestellt und in der österreichischen
    Energieausweis-Datenbank registriert werden (ZTG 2019).
    """
    grenzwert = 10.0 + 30.0 * request.a_v_verhaeltnis
    konform = request.hwb_ref_rk <= grenzwert
    ueberschreitung_pct = (
        round((request.hwb_ref_rk - grenzwert) / grenzwert * 100, 1) if not konform else 0.0
    )

    return {
        "hwb_ref_rk": request.hwb_ref_rk,
        "hwb_grenzwert_kwh_m2a": round(grenzwert, 1),
        "a_v_verhaeltnis": request.a_v_verhaeltnis,
        "oib_rl6_2023_konform": konform,
        "ueberschreitung_pct": ueberschreitung_pct,
        "formel": f"HWBmax = 10 + 30 × {request.a_v_verhaeltnis:.2f} = {grenzwert:.1f} kWh/(m²a)",
        "norm": "OIB-RL 6:2023 (Ausgabe Mai 2023), Tabelle 1 — Wohngebäude Referenzklima",
        "fgee_grenzwert": 0.75,
        "fgee_hinweis": "fGEE ≤ 0,75 für Neubauten (OIB-RL 6:2023, Verschärfung gegenüber 0,85 in OIB-RL 6:2019)",
        "ziviltechniker_pflicht": (
            "Energieausweis muss von befugtem Ziviltechniker (ZTG 2019) ausgestellt "
            "und in der österreichischen Energieausweis-Datenbank registriert werden."
        ),
        "status": "pass" if konform else "fail",
    }
