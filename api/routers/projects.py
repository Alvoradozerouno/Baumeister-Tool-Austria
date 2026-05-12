"""
Projects Router
Office/project workspace for Austrian architecture firms.

Provides:
- Create/list/update building projects
- Bundesland-aware project metadata
- Quick OIB-RL compliance summary per project
- Export-ready project data

Note: Projects are stored in-memory in this implementation.
For production use, connect a database via the existing api.database module.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

# In-memory project store (replace with DB in production)
_projects: Dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    """Create a new building project"""

    name: str = Field(..., min_length=1, max_length=200, description="Projektname")
    bundesland: str = Field(..., description="Bundesland (z.B. 'wien', 'tirol')")
    building_type: str = Field(
        ...,
        description="Gebäudetyp (z.B. 'einfamilienhaus', 'mehrfamilienhaus', 'buerogebaeude')",
    )
    bgf_m2: float = Field(..., gt=0, le=500000, description="Brutto-Grundfläche in m²")
    geschosse: int = Field(..., ge=1, le=100, description="Anzahl Geschoße")
    wohnungen: Optional[int] = Field(None, ge=0, description="Anzahl Wohneinheiten")
    beschreibung: Optional[str] = Field(None, max_length=2000, description="Projektbeschreibung")
    buero_name: Optional[str] = Field(None, max_length=200, description="Name des Planungsbüros")
    ziviltechniker: Optional[str] = Field(None, max_length=200, description="Befugter Ziviltechniker")

    @field_validator("bundesland")
    @classmethod
    def validate_bundesland(cls, v: str) -> str:
        valid = {
            "burgenland", "kaernten", "niederoesterreich", "oberoesterreich",
            "salzburg", "steiermark", "tirol", "vorarlberg", "wien",
        }
        if v.lower() not in valid:
            raise ValueError(f"Ungültiges Bundesland '{v}'. Gültig: {sorted(valid)}")
        return v.lower()

    @field_validator("building_type")
    @classmethod
    def validate_building_type(cls, v: str) -> str:
        valid = {
            "einfamilienhaus", "doppelhaushälfte", "reihenhaus",
            "mehrfamilienhaus", "wohnanlage", "buerogebaeude",
            "gewerbe", "industrie", "sonderbau", "umbau", "zubau",
        }
        normalized = v.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        v_norm = v.lower()
        if v_norm not in valid and normalized not in valid:
            # Accept any string not matching known types (open-ended list)
            pass
        return v.lower()


class ProjectUpdate(BaseModel):
    """Update an existing project"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    bgf_m2: Optional[float] = Field(None, gt=0, le=500000)
    geschosse: Optional[int] = Field(None, ge=1, le=100)
    wohnungen: Optional[int] = Field(None, ge=0)
    beschreibung: Optional[str] = Field(None, max_length=2000)
    buero_name: Optional[str] = Field(None, max_length=200)
    ziviltechniker: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(
        None,
        description="Projektstatus: 'planung', 'einreichung', 'genehmigung', 'ausfuehrung', 'abgeschlossen'",
    )


class ProjectOut(BaseModel):
    """Project output model"""

    id: str
    name: str
    bundesland: str
    building_type: str
    bgf_m2: float
    geschosse: int
    wohnungen: Optional[int]
    beschreibung: Optional[str]
    buero_name: Optional[str]
    ziviltechniker: Optional[str]
    status: str
    erstellt_am: str
    geaendert_am: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=ProjectOut, status_code=201)
async def create_project(project: ProjectCreate):
    """
    ➕ **Neues Projekt anlegen**

    Legt ein neues Bauprojekt an mit bundeslandspezifischen Metadaten.
    Das Projekt ist die zentrale Arbeitseinheit für Compliance-Checks,
    Berechnungen und Berichte.

    ⚠️ **Ziviltechniker-Pflicht**: Für behördliche Einreichungen sind Pläne
    von einem befugten Ziviltechniker (Architekt oder Ingenieurkonsulent)
    zu unterschreiben (ZTG 2019).
    """
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    project_data = {
        "id": project_id,
        **project.model_dump(),
        "status": "planung",
        "erstellt_am": now,
        "geaendert_am": now,
    }
    _projects[project_id] = project_data
    return project_data


@router.get("/", response_model=List[ProjectOut])
async def list_projects(
    bundesland: Optional[str] = None,
    status: Optional[str] = None,
    buero_name: Optional[str] = None,
):
    """
    📋 **Projekte auflisten**

    Listet alle Projekte mit optionaler Filterung nach Bundesland, Status
    oder Büro.
    """
    projects = list(_projects.values())

    if bundesland:
        projects = [p for p in projects if p["bundesland"] == bundesland.lower()]
    if status:
        projects = [p for p in projects if p["status"] == status.lower()]
    if buero_name:
        projects = [
            p
            for p in projects
            if p.get("buero_name") and buero_name.lower() in p["buero_name"].lower()
        ]

    return projects


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str):
    """
    🔍 **Projekt abrufen**

    Gibt alle Details eines Projekts zurück.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail=f"Projekt '{project_id}' nicht gefunden.")
    return _projects[project_id]


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, update: ProjectUpdate):
    """
    ✏️ **Projekt aktualisieren**

    Aktualisiert einzelne Felder eines bestehenden Projekts.
    Erlaubte Status-Werte: planung, einreichung, genehmigung, ausfuehrung, abgeschlossen.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail=f"Projekt '{project_id}' nicht gefunden.")

    valid_stati = {"planung", "einreichung", "genehmigung", "ausfuehrung", "abgeschlossen"}
    if update.status and update.status not in valid_stati:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Status '{update.status}'. Gültig: {sorted(valid_stati)}",
        )

    project = _projects[project_id]
    for field, value in update.model_dump(exclude_unset=True).items():
        project[field] = value
    project["geaendert_am"] = datetime.now(timezone.utc).isoformat()

    _projects[project_id] = project
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """
    🗑️ **Projekt löschen**

    Löscht ein Projekt dauerhaft.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail=f"Projekt '{project_id}' nicht gefunden.")
    del _projects[project_id]


@router.get("/{project_id}/compliance-summary")
async def get_project_compliance_summary(project_id: str):
    """
    ✅ **Projekt Compliance-Zusammenfassung**

    Gibt eine Schnellübersicht der OIB-RL-Anforderungen und kritischen
    Prüfpunkte für das Projekt zurück — ohne vollständige Detailberechnung.

    Für den vollständigen Check: POST /api/v1/compliance/oib-rl-check
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail=f"Projekt '{project_id}' nicht gefunden.")

    p = _projects[project_id]
    bl = p["bundesland"]
    geschosse = p["geschosse"]
    bgf = p["bgf_m2"]
    wohnungen = p.get("wohnungen") or 0

    # Quick compliance flags
    flags = []

    if bl == "salzburg":
        flags.append({
            "typ": "warning",
            "bereich": "OIB-RL 6 / Energie",
            "meldung": (
                "⚠️ Salzburg hat OIB-RL 6 NICHT übernommen. "
                "Salzburger Wärmeschutzverordnung (WSchVO) gilt stattdessen!"
            ),
        })

    if bl in {"tirol", "niederoesterreich", "oberoesterreich", "steiermark", "salzburg", "kaernten", "vorarlberg"}:
        flags.append({
            "typ": "warning",
            "bereich": "Radonschutz",
            "meldung": f"Radonvorsorgegebiet — ÖNORM S 5280 Maßnahmen für {bl.title()} prüfen.",
        })

    aufzug_ab = 3 if bl == "wien" else 4
    if geschosse >= aufzug_ab:
        flags.append({
            "typ": "info",
            "bereich": "OIB-RL 4 / Barrierefreiheit",
            "meldung": f"Aufzug erforderlich (ab {aufzug_ab}. OG in {bl.title()}).",
        })

    if bgf >= 1000:
        flags.append({
            "typ": "info",
            "bereich": "OIB-RL 6 / Energie",
            "meldung": f"BGF {bgf:.0f} m² ≥ 1.000 m²: PV-Anlage für Neubauten ab 2024 verpflichtend.",
        })

    if geschosse >= 5:
        flags.append({
            "typ": "warning",
            "bereich": "OIB-RL 2 / Brandschutz",
            "meldung": "Ab 5 Geschoßen: erhöhte Brandschutzanforderungen, zweiter Fluchtweg prüfen.",
        })

    if wohnungen >= 6:
        flags.append({
            "typ": "info",
            "bereich": "OIB-RL 3 / Hygiene",
            "meldung": f"Ab 6 Wohnungen: Abstellräume empfohlen ({wohnungen * 4} m² gesamt).",
        })

    return {
        "projekt_id": project_id,
        "projekt_name": p["name"],
        "bundesland": bl,
        "bundesland_name": bl.title(),
        "building_type": p["building_type"],
        "bgf_m2": bgf,
        "geschosse": geschosse,
        "wohnungen": wohnungen,
        "compliance_flags": flags,
        "anzahl_warnungen": sum(1 for f in flags if f["typ"] == "warning"),
        "anzahl_hinweise": sum(1 for f in flags if f["typ"] == "info"),
        "empfehlung": (
            "Für den vollständigen OIB-RL-Check: POST /api/v1/compliance/oib-rl-check. "
            "Für BIM-basierte Prüfung: POST /api/v1/bim/validate-bim. "
            "⚠️ Alle behördlichen Einreichungen benötigen einen befugten Ziviltechniker (ZTG 2019)."
        ),
        "erstellt_am": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{project_id}/export")
async def export_project(project_id: str, format: str = "json"):
    """
    📤 **Projekt exportieren**

    Exportiert Projektdaten in verschiedenen Formaten.
    Unterstützte Formate: json (weitere in Planung: pdf, xlsx)
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail=f"Projekt '{project_id}' nicht gefunden.")

    if format.lower() != "json":
        raise HTTPException(
            status_code=400,
            detail="Derzeit nur JSON-Export unterstützt. PDF/XLSX-Export in Entwicklung.",
        )

    p = _projects[project_id]
    return {
        "export_format": "json",
        "export_zeitpunkt": datetime.now(timezone.utc).isoformat(),
        "projekt": p,
        "hinweis": (
            "Exportdaten dienen als Planungsgrundlage. "
            "Für behördliche Zwecke sind Unterlagen von einem befugten "
            "Ziviltechniker zu erstellen und zu unterschreiben (ZTG 2019)."
        ),
    }
