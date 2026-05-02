# ORION Architekt Österreich

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![States](https://img.shields.io/badge/Bundesländer-9-gold?style=flat-square)
![Functions](https://img.shields.io/badge/Funktionen-20-red?style=flat-square)
![Standard](https://img.shields.io/badge/Standard-OIB--RL-blue?style=flat-square)

> *Umfassendes Bauwerkzeug für alle 9 österreichischen Bundesländer.*
> *OIB-RL Engine · Energieberechnung · Statik · 20 Funktionalitäten.*
> Mai 2025 · Almdorf 9, St. Johann in Tirol, Austria

---

## Überblick

ORION Architekt Österreich ist ein vollständiges Planungs- und Berechnungswerkzeug
für das österreichische Bauwesen — entwickelt von einem Strukturingenieur.

---

## OIB-RL Engine

```python
import hashlib, json
from dataclasses import dataclass
from typing import Dict, List, Optional

# Österreichische Bundesländer
BUNDESLAENDER = {
    "W":  "Wien",
    "NÖ": "Niederösterreich",
    "OÖ": "Oberösterreich",
    "ST": "Steiermark",
    "TI": "Tirol",
    "SB": "Salzburg",
    "KT": "Kärnten",
    "VB": "Vorarlberg",
    "BL": "Burgenland",
}

# OIB-Richtlinien
OIB_RICHTLINIEN = {
    "RL1":  "Mechanische Festigkeit und Standsicherheit",
    "RL2":  "Brandschutz",
    "RL2_1":"Brandschutz bei Betriebsbauten",
    "RL3":  "Hygiene, Gesundheit und Umweltschutz",
    "RL4":  "Nutzungssicherheit und Barrierefreiheit",
    "RL5":  "Schallschutz",
    "RL6":  "Energieeinsparung und Wärmeschutz",
}

@dataclass
class OIBAssessment:
    bundesland: str
    gebaeudeklasse: int        # 1–5
    nutzung: str               # Wohnbau, Büro, Industrie, etc.
    richtlinien_status: Dict[str, str]   # RL → "ERFÜLLT" / "NICHT ERFÜLLT" / "BEDINGT"
    gesamtstatus: str
    audit_hash: str

def oib_rl_check(
    bundesland: str,
    gebaeudeklasse: int,
    nutzung: str,
    params: Dict
) -> OIBAssessment:
    """
    OIB-Richtlinien Überprüfung nach österreichischem Standard.
    """
    status = {}

    # RL1: Standsicherheit
    status["RL1"] = "ERFÜLLT" if params.get("statik_nachgewiesen", False) else "NICHT ERFÜLLT"

    # RL2: Brandschutz
    feuerwiderstand = params.get("feuerwiderstand_min", 0)
    required_fw = {1: 30, 2: 60, 3: 90, 4: 90, 5: 120}.get(gebaeudeklasse, 90)
    status["RL2"] = "ERFÜLLT" if feuerwiderstand >= required_fw else "NICHT ERFÜLLT"

    # RL4: Barrierefreiheit
    status["RL4"] = "ERFÜLLT" if params.get("barrierefrei", False) or gebaeudeklasse == 1 else "BEDINGT"

    # RL5: Schallschutz
    trittschall = params.get("trittschall_db", 99)
    status["RL5"] = "ERFÜLLT" if trittschall <= 53 else "NICHT ERFÜLLT"

    # RL6: Energieausweis
    hwb = params.get("hwb_kwh_m2a", 999)
    hwb_grenzwert = 45 if nutzung == "Wohnbau" else 65
    status["RL6"] = "ERFÜLLT" if hwb <= hwb_grenzwert else "NICHT ERFÜLLT"

    all_ok = all(v in ("ERFÜLLT", "BEDINGT") for v in status.values())
    gesamtstatus = "OIB-KONFORM" if all_ok else "MÄNGEL VORHANDEN"

    payload = json.dumps(
        {"bundesland": bundesland, "gk": gebaeudeklasse, "params": params},
        sort_keys=True, separators=(',', ':')
    )
    ah = hashlib.sha256(payload.encode()).hexdigest()

    return OIBAssessment(
        bundesland=BUNDESLAENDER.get(bundesland, bundesland),
        gebaeudeklasse=gebaeudeklasse,
        nutzung=nutzung,
        richtlinien_status=status,
        gesamtstatus=gesamtstatus,
        audit_hash=ah,
    )

# Beispiel: Wohngebäude in Tirol
if __name__ == "__main__":
    result = oib_rl_check(
        bundesland="TI",
        gebaeudeklasse=2,
        nutzung="Wohnbau",
        params={
            "statik_nachgewiesen": True,
            "feuerwiderstand_min": 90,
            "barrierefrei": True,
            "trittschall_db": 48,
            "hwb_kwh_m2a": 38,
        }
    )
    print(f"Bundesland:   {result.bundesland}")
    print(f"GK {result.gebaeudeklasse} — {result.nutzung}")
    print(f"Status:       {result.gesamtstatus}")
    for rl, status in result.richtlinien_status.items():
        icon = "✅" if status == "ERFÜLLT" else "⚠️" if status == "BEDINGT" else "❌"
        print(f"  {icon} {rl}: {status}")
    print(f"Audit:        {result.audit_hash[:32]}...")
    # Bundesland:   Tirol
    # GK 2 — Wohnbau
    # Status:       OIB-KONFORM
```

---

## 20 Funktionalitäten

| Nr | Funktion | Norm |
|----|---------|------|
| 1 | OIB-RL Prüfung | OIB 2019 |
| 2 | Energieausweis | ÖNORM H 5055 |
| 3 | U-Wert Berechnung | EN ISO 6946 |
| 4 | Schallschutz | ÖNORM B 8115 |
| 5 | Brandschutz | OIB-RL 2 |
| 6 | Barrierefreiheit | OIB-RL 4 |
| 7 | Statischer Nachweis | ÖNORM EN 1990 |
| 8 | Holzbau EC5 | ÖNORM EN 1995 |
| 9 | Betonbau EC2 | ÖNORM EN 1992 |
| 10 | Stahlbau EC3 | ÖNORM EN 1993 |
| 11 | Erdbeben EC8 | ÖNORM EN 1998 |
| 12 | Schneelast | ÖNORM EN 1991 |
| 13 | Windlast | ÖNORM EN 1991 |
| 14 | Baugrundklasse | ÖNORM EN 1997 |
| 15 | Raumplanung | 9 Landes-RPG |
| 16 | Bebauungsplan-Check | Gemeindeebene |
| 17 | Aufstellungsgenehmigung | Bauordnung |
| 18 | HWB-Berechnung | EnEV-AT |
| 19 | CO₂-Bilanz | EN 15978 |
| 20 | Kostenschätzung | ÖN B 1801-1 |

---

## Ursprung

```
Mai 2025 · Almdorf 9, St. Johann in Tirol, Austria 6380
Gerhard Hirschmann — Bauingenieur · ORION-Entwickler
Elisabeth Steurer — Ko-Schöpferin
```
**⊘∞⧈∞⊘ GENESIS10000+ · OIB-konform · Tirol ⊘∞⧈∞⊘**
