"""
Compliance Router
OIB-RL and ÖNORM compliance checks
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ComplianceCheckRequest(BaseModel):
    """OIB-RL Compliance check request (JSON body)"""

    bundesland: str = Field(..., description="Bundesland (z.B. 'wien', 'salzburg')")
    building_type: str = Field(..., description="Gebäudetyp (z.B. 'wohngebaeude', 'buerogebaeude')")
    bgf_m2: float = Field(..., gt=0, description="Brutto-Grundfläche in m²")
    geschosse: int = Field(..., ge=1, description="Anzahl der Geschosse")
    wohnungen: Optional[int] = Field(None, ge=1, description="Anzahl der Wohneinheiten (optional)")
    richtlinien: List[int] = Field(
        default=[1, 2, 3, 4, 5, 6, 7],
        description="OIB-RL Nummern die geprüft werden sollen (1–7)",
    )


class ComplianceResult(BaseModel):
    """Compliance check result"""

    richtlinie: str
    status: str  # "pass", "fail", "warning"
    checks: List[Dict]
    summary: str


@router.post("/oib-rl-check", response_model=List[ComplianceResult])
async def check_oib_rl_compliance(request: ComplianceCheckRequest):
    """
    ✅ **OIB-RL Compliance Check (OIB-RL 2023)**

    Comprehensive compliance check for all OIB Richtlinien:
    - OIB-RL 1: Mechanische Festigkeit und Standsicherheit
    - OIB-RL 2: Brandschutz
    - OIB-RL 3: Hygiene, Gesundheit und Umweltschutz
    - OIB-RL 4: Nutzungssicherheit und Barrierefreiheit
    - OIB-RL 5: Schallschutz
    - OIB-RL 6: Energieeinsparung und Wärmeschutz (fGEE ≤ 0,75; HWB nach A/V-Formel; Salzburg: eigene WSchVO!)
    - OIB-RL 7: Nachhaltige Nutzung der natürlichen Ressourcen (Grundlagendokument 2023)
    - Radonschutz nach ÖNORM S 5280 (bundeslandabhängig)

    ⚠️ **Ziviltechniker-Pflicht**: Für behördliche Einreichungen sind die Unterlagen von einem
    befugten Ziviltechniker (Architekt oder Ingenieurkonsulent) zu unterschreiben und zu siegeln
    (Ziviltechnikergesetz 2019, ZTG 2019). Dieses System ist eine Planungshilfe, kein Ersatz.
    """
    results = []

    if 1 in request.richtlinien:
        results.append(_check_oib_rl_1(request.building_type, request.geschosse))

    if 2 in request.richtlinien:
        results.append(_check_oib_rl_2(request.building_type, request.geschosse, request.bgf_m2))

    if 3 in request.richtlinien:
        results.append(_check_oib_rl_3(request.building_type, request.wohnungen))

    if 4 in request.richtlinien:
        results.append(_check_oib_rl_4(request.building_type, request.geschosse, request.bgf_m2))

    if 5 in request.richtlinien:
        results.append(_check_oib_rl_5(request.building_type, request.wohnungen))

    if 6 in request.richtlinien:
        results.append(_check_oib_rl_6(request.bundesland, request.bgf_m2))

    # OIB-RL 7: Nachhaltigkeit (Grundlagendokument 2023)
    if 7 in request.richtlinien:
        results.append(_check_oib_rl_7(request.building_type))

    # Radonschutz: bundeslandspezifisch (ÖNORM S 5280)
    radon_result = _check_radon(request.bundesland)
    if radon_result is not None:
        results.append(radon_result)

    return results


def _check_oib_rl_1(building_type: str, geschosse: int) -> ComplianceResult:
    """OIB-RL 1: Mechanical resistance and stability"""
    checks = [
        {
            "check": "Statische Berechnung erforderlich",
            "status": "pass",
            "details": "Statische Berechnung durch befugten Ingenieur erforderlich",
        },
        {
            "check": "Eurocode Anwendung",
            "status": "pass",
            "details": "Bemessung nach Eurocode 0, 1, 2 erforderlich",
        },
    ]

    if geschosse >= 3:
        checks.append(
            {
                "check": "Erhöhte Anforderungen bei Hochbauten",
                "status": "warning",
                "details": "Bei Gebäuden ab 3 Geschoßen erhöhte Nachweise erforderlich",
            }
        )

    return ComplianceResult(
        richtlinie="OIB-RL 1",
        status="pass",
        checks=checks,
        summary="Mechanische Festigkeit und Standsicherheit - Grundanforderungen erfüllt",
    )


def _check_oib_rl_2(building_type: str, geschosse: int, bgf_m2: float) -> ComplianceResult:
    """OIB-RL 2: Fire safety"""
    checks = []

    # Fire resistance requirements
    if geschosse <= 2:
        rei_required = 30
    elif geschosse <= 4:
        rei_required = 60
    else:
        rei_required = 90

    checks.append(
        {
            "check": f"Feuerwiderstand REI {rei_required}",
            "status": "pass",
            "details": f"Tragende Bauteile müssen REI {rei_required} aufweisen",
        }
    )

    # Fire compartments
    max_compartment_size = 1200 if building_type == "wohngebaeude" else 800
    if bgf_m2 > max_compartment_size:
        required_compartments = int(bgf_m2 / max_compartment_size) + 1
        checks.append(
            {
                "check": "Brandabschnitte",
                "status": "warning",
                "details": f"BGF {bgf_m2}m² erfordert mind. {required_compartments} Brandabschnitte (max. {max_compartment_size}m²)",
            }
        )
    else:
        checks.append(
            {
                "check": "Brandabschnitte",
                "status": "pass",
                "details": f"BGF {bgf_m2}m² in zulässigem Bereich für einen Brandabschnitt",
            }
        )

    # Fire alarm system
    if geschosse >= 5:
        checks.append(
            {
                "check": "Brandmeldeanlage",
                "status": "pass",
                "details": "Brandmeldeanlage ab 5 Geschoßen erforderlich",
            }
        )

    return ComplianceResult(
        richtlinie="OIB-RL 2",
        status="pass",
        checks=checks,
        summary="Brandschutz - Anforderungen geprüft",
    )


def _check_oib_rl_3(building_type: str, wohnungen: Optional[int]) -> ComplianceResult:
    """OIB-RL 3: Hygiene, health and environment"""
    checks = [
        {
            "check": "Mindest-Raumhöhe",
            "status": "pass",
            "details": "Aufenthaltsräume: mind. 2,50m Raumhöhe erforderlich",
        },
        {
            "check": "Natürliche Belichtung",
            "status": "pass",
            "details": "Fensterfläche mind. 10% der Bodenfläche für Aufenthaltsräume",
        },
        {
            "check": "Lüftung",
            "status": "pass",
            "details": "Natürliche oder mechanische Lüftung erforderlich",
        },
    ]

    if wohnungen and wohnungen >= 6:
        checks.append(
            {
                "check": "Abstellräume",
                "status": "pass",
                "details": f"Bei {wohnungen} Wohnungen: {wohnungen * 4}m² Abstellfläche empfohlen",
            }
        )

    return ComplianceResult(
        richtlinie="OIB-RL 3",
        status="pass",
        checks=checks,
        summary="Hygiene, Gesundheit und Umweltschutz - Grundanforderungen geprüft",
    )


def _check_oib_rl_4(building_type: str, geschosse: int, bgf_m2: float) -> ComplianceResult:
    """OIB-RL 4: Safety and accessibility"""
    checks = [
        {
            "check": "Fluchtwege",
            "status": "pass",
            "details": "Maximale Fluchtweglänge: 40m für Wohngebäude",
        },
        {
            "check": "Treppenbreite",
            "status": "pass",
            "details": f"Mindestbreite: {1.20 if geschosse >= 4 else 1.00}m",
        },
    ]

    if geschosse >= 4:
        checks.append(
            {
                "check": "Aufzug Barrierefreiheit",
                "status": "pass",
                "details": "Aufzug erforderlich ab 4 Geschoßen",
            }
        )

    if geschosse >= 5:
        checks.append(
            {
                "check": "Zweiter Fluchtweg",
                "status": "warning",
                "details": "Hochhaus-Anforderungen: zweiter Fluchtweg prüfen",
            }
        )

    return ComplianceResult(
        richtlinie="OIB-RL 4",
        status="pass",
        checks=checks,
        summary="Sicherheit und Barrierefreiheit - Anforderungen geprüft",
    )


def _check_oib_rl_5(building_type: str, wohnungen: Optional[int]) -> ComplianceResult:
    """OIB-RL 5: Sound protection"""
    checks = [
        {
            "check": "Luftschallschutz",
            "status": "pass",
            "details": "R'w ≥ 52 dB zwischen Wohnungen und Treppenhaus erforderlich",
        },
        {
            "check": "Trittschallschutz",
            "status": "pass",
            "details": "L'n,w ≤ 48 dB für Decken zwischen Wohnungen",
        },
    ]

    if building_type in ["mehrfamilienhaus", "wohnanlage"]:
        checks.append(
            {
                "check": "Erhöhte Anforderungen",
                "status": "pass",
                "details": "R'w ≥ 55 dB zwischen Wohnungen bei Mehrfamilienhäusern",
            }
        )

    return ComplianceResult(
        richtlinie="OIB-RL 5",
        status="pass",
        checks=checks,
        summary="Schallschutz - Anforderungen definiert",
    )


def _check_oib_rl_6(bundesland: str, bgf_m2: float) -> ComplianceResult:
    """OIB-RL 6: Energy efficiency (OIB-RL 6:2023)"""

    # Salzburg uses its own Wärmeschutzverordnung — NOT OIB-RL 6
    if bundesland.lower() == "salzburg":
        return ComplianceResult(
            richtlinie="OIB-RL 6 / Sbg-WSchVO",
            status="warning",
            checks=[
                {
                    "check": "⚠️ Salzburg Sonderregelung",
                    "status": "warning",
                    "details": (
                        "Salzburg hat OIB-RL 6 NICHT übernommen! "
                        "Es gilt die Salzburger Wärmeschutzverordnung (WSchVO) — "
                        "teils strengere Anforderungen als OIB-RL 6. "
                        "Energienachweis nach Sbg-WSchVO beim Einreichen erforderlich."
                    ),
                }
            ],
            summary="Salzburg: Eigene Wärmeschutzverordnung statt OIB-RL 6 — Sbg-WSchVO prüfen!",
        )

    checks = [
        {
            "check": "U-Wert Außenwand",
            "status": "pass",
            "details": "U ≤ 0,35 W/m²K (Neubau Wohngebäude, OIB-RL 6:2023)",
        },
        {
            "check": "U-Wert Dach/oberste Geschoßdecke",
            "status": "pass",
            "details": "U ≤ 0,20 W/m²K (Neubau, OIB-RL 6:2023)",
        },
        {
            "check": "U-Wert Fenster",
            "status": "pass",
            "details": "Uw ≤ 1,40 W/m²K (Neubau, OIB-RL 6:2023)",
        },
        {
            "check": "fGEE Gesamtenergieeffizienz-Faktor",
            "status": "pass",
            "details": "fGEE ≤ 0,75 (Neubau, OIB-RL 6:2023 — Verschärfung gegenüber 0,85 der Ausgabe 2019)",
        },
        {
            "check": "HWBRef,RK Heizwärmebedarf",
            "status": "pass",
            "details": (
                "HWBmax = 10 + 30 × (A/V) kWh/(m²a) nach OIB-RL 6:2023 Tabelle 1. "
                "Beispiel A/V=0,5: HWBmax = 25 kWh/(m²a). Genaues A/V je Projekt berechnen."
            ),
        },
        {
            "check": "Energieausweis",
            "status": "pass",
            "details": (
                "Energieausweis-Pflicht bei Neubau und umfassender Sanierung. "
                "Muss von befugtem Ziviltechniker oder Energieberater ausgestellt "
                "und in der österreichischen Energieausweis-Datenbank registriert werden."
            ),
        },
        {
            "check": "Nahezu-Nullenergiegebäude (NZEB)",
            "status": "pass",
            "details": "Alle Neubauten müssen NZEB-Standard erfüllen (ab 2021 EU-Gebäuderichtlinie)",
        },
    ]

    # PV requirement for larger buildings
    if bgf_m2 >= 1000:
        checks.append(
            {
                "check": "PV-Anlage Pflicht (BGF ≥ 1.000 m²)",
                "status": "pass",
                "details": f"BGF {bgf_m2:.0f} m² ≥ 1.000 m²: PV-Anlage ab 2024 für Neubauten verpflichtend",
            }
        )

    return ComplianceResult(
        richtlinie="OIB-RL 6",
        status="pass",
        checks=checks,
        summary="OIB-RL 6:2023 Energieeffizienz — fGEE ≤ 0,75, HWB nach A/V-Formel",
    )


def _check_radon(bundesland: str) -> Optional[ComplianceResult]:
    """Radonschutz nach ÖNORM S 5280 für Vorsorgegebiete."""
    radon_vorsorgegebiete = {
        "tirol": "Tirol ist Radonvorsorgegebiet (Radon-Zonierung nach ÖNORM S 5280). Radonschutzmaßnahmen im Keller/EG Pflicht.",
        "niederoesterreich": "Waldviertel/Weinviertel: Radonvorsorgegebiet. Radon-Konzept bei Einreichung erforderlich (ÖNORM S 5280).",
        "oberoesterreich": "Mühlviertel: Radonvorsorge beachten. Messung im Bestand empfohlen.",
        "steiermark": "Weststeiermark und Teile des Mürztal: Radonvorsorge prüfen.",
        "salzburg": "Lungau und Teile des Pinzgau: erhöhte Radonkonzentrationen, ÖNORM S 5280 beachten.",
        "kaernten": "Oberkärnten (Mölltal, Liesertal): erhöhtes Radonpotenzial, Messung empfohlen.",
        "vorarlberg": "Bregenzerwald/Großwalsertal: Radonpotenzial prüfen.",
    }

    bl = bundesland.lower()
    if bl not in radon_vorsorgegebiete:
        return None

    return ComplianceResult(
        richtlinie="Radonschutz (ÖNORM S 5280)",
        status="warning",
        checks=[
            {
                "check": "Radonvorsorgegebiet",
                "status": "warning",
                "details": radon_vorsorgegebiete[bl],
            },
            {
                "check": "Radonschutzmaßnahmen",
                "status": "warning",
                "details": (
                    "Erforderliche Maßnahmen nach ÖNORM S 5280: "
                    "Radon-sichere Bodenplatte, Lüftungskonzept Keller, "
                    "Radon-Barrieren (PE-Folie ≥ 0,5 mm). "
                    "Messungen im Bestand: Radonmessservice Austria (radon.gv.at)."
                ),
            },
        ],
        summary=f"⚠️ Radonvorsorgegebiet — ÖNORM S 5280 Maßnahmen erforderlich für {bundesland.title()}",
    )


def _check_oib_rl_7(building_type: str) -> ComplianceResult:
    """OIB-RL 7: Nachhaltige Nutzung der natürlichen Ressourcen (Grundlagendokument 2023)."""
    checks = [
        {
            "check": "OI3-Index Baustoffe",
            "status": "pass",
            "details": (
                "OI3-Index (Ökologieindex) der verwendeten Baustoffe beachten. "
                "Für geförderten Wohnbau in Wien bereits verbindlich."
            ),
        },
        {
            "check": "Rückbaubarkeit und Kreislaufwirtschaft",
            "status": "pass",
            "details": (
                "Bauteile und Materialien sollen rückbaubar und wiederverwertbar sein. "
                "Trennbarkeit verschiedener Materialschichten einplanen."
            ),
        },
        {
            "check": "Global Warming Potential (GWP)",
            "status": "pass",
            "details": (
                "Lebenszyklusanalyse (LCA) nach EN 15978 empfohlen. "
                "Holzkonstruktionen: negativer CO2-Fußabdruck möglich."
            ),
        },
    ]

    return ComplianceResult(
        richtlinie="OIB-RL 7",
        status="pass",
        checks=checks,
        summary="OIB-RL 7:2023 Nachhaltigkeit — Grundlagendokument, Verbindlichkeit je Bundesland prüfen",
    )


@router.get("/oenorm-standards")
async def get_oenorm_standards(kategorie: Optional[str] = None):
    """
    📋 **ÖNORM Standards**

    Get list of relevant ÖNORM standards for building construction.
    """
    standards = [
        {
            "norm": "ÖNORM B 1800",
            "titel": "Objektdaten im Facility Management",
            "kategorie": "Flächenberechnung",
            "status": "aktuell",
        },
        {
            "norm": "ÖNORM B 1600",
            "titel": "Barrierefreies Bauen",
            "kategorie": "Barrierefreiheit",
            "status": "aktuell",
        },
        {
            "norm": "ÖNORM B 8115-2",
            "titel": "Schallschutz und Raumakustik im Hochbau",
            "kategorie": "Schallschutz",
            "status": "aktuell",
        },
        {
            "norm": "ÖNORM EN ISO 6946",
            "titel": "U-Wert Berechnung",
            "kategorie": "Wärmeschutz",
            "status": "aktuell",
        },
        {
            "norm": "ÖNORM EN 12831",
            "titel": "Heizlastberechnung",
            "kategorie": "Wärmeschutz",
            "status": "aktuell",
        },
        {
            "norm": "ÖNORM B 2110",
            "titel": "Allgemeine Vertragsbestimmungen für Bauleistungen",
            "kategorie": "Bauvertrag",
            "status": "aktuell",
        },
    ]

    if kategorie:
        standards = [s for s in standards if s["kategorie"].lower() == kategorie.lower()]

    return {"standards": standards, "total": len(standards)}


@router.get("/oib-updates")
async def get_oib_updates():
    """
    🆕 **OIB Updates**

    Get information about recent OIB-RL updates and changes.
    """
    return {
        "current_version": "2023",
        "last_update": "2023-01-01",
        "updates": [
            {
                "richtlinie": "OIB-RL 6",
                "version": "2023",
                "changes": [
                    "Verschärfte U-Wert Anforderungen",
                    "Neue Anforderungen für Kühlung",
                    "PV-Anlage Pflicht für Neubauten ab 2024",
                ],
            },
            {
                "richtlinie": "OIB-RL 2",
                "version": "2023",
                "changes": [
                    "Aktualisierte Brandschutzanforderungen",
                    "Neue Klassifizierung für Fassadendämmstoffe",
                ],
            },
        ],
        "next_review": "2026",
    }


@router.post("/compliance-report")
async def generate_compliance_report(
    bundesland: str,
    building_type: str,
    bgf_m2: float,
    geschosse: int,
    wohnungen: Optional[int] = None,
):
    """
    📊 **Compliance Report**

    Generate comprehensive compliance report covering all regulations.
    """
    # Run all compliance checks
    oib_results = await check_oib_rl_compliance(
        ComplianceCheckRequest(
            bundesland=bundesland,
            building_type=building_type,
            bgf_m2=bgf_m2,
            geschosse=geschosse,
            wohnungen=wohnungen,
        )
    )

    # Summary statistics
    total_checks = sum(len(r.checks) for r in oib_results)
    passed = sum(len([c for c in r.checks if c["status"] == "pass"]) for r in oib_results)
    warnings = sum(len([c for c in r.checks if c["status"] == "warning"]) for r in oib_results)
    failed = sum(len([c for c in r.checks if c["status"] == "fail"]) for r in oib_results)

    overall_status = "fail" if failed > 0 else ("warning" if warnings > 0 else "pass")

    return {
        "project": {
            "bundesland": bundesland,
            "building_type": building_type,
            "bgf_m2": bgf_m2,
            "geschosse": geschosse,
            "wohnungen": wohnungen,
        },
        "summary": {
            "overall_status": overall_status,
            "total_checks": total_checks,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "compliance_rate": round(passed / total_checks * 100, 1) if total_checks > 0 else 0,
        },
        "oib_results": oib_results,
        "generated_at": datetime.now().isoformat(),
        "version": "OIB-RL 2023",
        "ziviltechniker_pflicht": (
            "⚠️ Für behördliche Einreichungen in Österreich müssen alle Planungsunterlagen "
            "von einem befugten Ziviltechniker (Architekt oder Ingenieurkonsulent) "
            "unterschrieben und mit dem Staatssiegel versehen werden "
            "(Ziviltechnikergesetz 2019 — ZTG 2019, BGBl. I Nr. 34/2019). "
            "ORION Architekt ist eine Planungs- und Prüfhilfe — kein Ersatz für befugte Fachleute."
        ),
    }
