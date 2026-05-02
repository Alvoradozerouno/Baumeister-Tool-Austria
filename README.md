# ⊘∞⧈∞⊘  ORION Architekt Österreich

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Austria](https://img.shields.io/badge/Austria-9%20Bundesl%C3%A4nder-red)](https://github.com/Alvoradozerouno/ORION-Architekt-AT)

> **Comprehensive Austrian building tool — all 9 federal states, 20 functionalities, OIB-RL engine.**
> From OIB compliance to energy estimation and structural calculations.

## 20 Functionalities

| # | Function | Standard |
|---|----------|---------|
| 1 | OIB-RL 2 — Brandschutz | OIB-RL 2:2019 |
| 2 | OIB-RL 3 — Hygiene | OIB-RL 3:2019 |
| 3 | OIB-RL 4 — Nutzungssicherheit | OIB-RL 4:2019 |
| 4 | OIB-RL 5 — Schallschutz | OIB-RL 5:2019 |
| 5 | OIB-RL 6 — Energieeinsparung | OIB-RL 6:2019 |
| 6 | U-Wert Berechnung | EN ISO 6946 |
| 7 | Heizlastberechnung | EN 12831 |
| 8 | Kühlastberechnung | ÖNORM EN 13370 |
| 9 | Trittschallschutz | ÖNORM B 8115 |
| 10 | Holzbaustatik (EC5) | EN 1995 |
| 11 | Stahlbau (EC3) | EN 1993 |
| 12 | Massivbau (EC2) | EN 1992 |
| 13 | Grundbau (EC7) | EN 1997 |
| 14 | Erdbeben (EC8) | EN 1998 |
| 15 | Schneelast | EN 1991-1-3 |
| 16 | Windlast | EN 1991-1-4 |
| 17 | Raumakustik | EN ISO 3382 |
| 18 | Tageslichtberechnung | EN 17037 |
| 19 | Baukostenindex | BKI Österreich |
| 20 | Gebührenrechner | Honorarordnung AT |

## 9 Bundesländer

Alle österreichischen Bundesländer mit landesspezifischen Bauordnungen:

| Bundesland | Bauordnung | Spezifika |
|-----------|-----------|----------|
| Wien | BO Wien | Hochhaus-Regelungen |
| Niederösterreich | NÖ BO | Dachausbauten |
| Oberösterreich | OÖ BO | Solarenergie |
| Salzburg | Sbg BO | Tourismus/Berghütten |
| Tirol | TROG | Waalwege, Lawinenschutz |
| Vorarlberg | Vbg BG | Montafon |
| Steiermark | Stmk BO | Graz-Regelungen |
| Kärnten | K-BO | Seeufer |
| Burgenland | Bgld BO | Esterhazy-Gebiet |

## Code — OIB-RL 6 Energieberechnung

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Bauteil:
    bezeichnung: str
    flaeche_m2: float
    u_wert_W_m2K: float
    typ: str  # 'WAND' | 'DACH' | 'BODEN' | 'FENSTER'

@dataclass
class EnergieAusweis:
    hwb_kwh_m2a: float      # Heizwärmebedarf
    heb_kwh_m2a: float      # Heizenergiebedarf
    peb_kwh_m2a: float      # Primärenergiebedarf
    co2_kg_m2a: float       # CO2-Emissionen
    energieklasse: str      # A++ bis G
    oib_rl6_konform: bool

def berechne_hwb(
    bauteile: List[Bauteil],
    bgf_m2: float,
    standort_klimazone: int,  # 1-3 (1=mild, 3=alpin)
    luftwechsel_h: float = 0.5,
    interne_waerme_W_m2: float = 2.0,
) -> EnergieAusweis:
    """
    Berechne Heizwärmebedarf nach ÖNORM EN 832 / OIB-RL 6.
    
    Args:
        bauteile: Alle thermisch relevanten Bauteile
        bgf_m2: Bruttogeschossfläche in m²
        standort_klimazone: 1=Tiefland, 2=Mittelland, 3=Hochalpin
        luftwechsel_h: Luftwechsel pro Stunde
        interne_waerme_W_m2: Interne Wärmequellen
    """
    # Klimadaten Österreich (Heizgradtage)
    heizgradtage = {1: 3200, 2: 3800, 3: 4800}[standort_klimazone]
    
    # Transmissionswärmeverluste
    leitwert_total = sum(b.flaeche_m2 * b.u_wert_W_m2K for b in bauteile)
    
    # Lüftungswärmeverluste
    raumvolumen_m3 = bgf_m2 * 2.7   # Annahme 2.7m Raumhöhe
    luefw_loss = 0.34 * luftwechsel_h * raumvolumen_m3  # W/K
    
    # Gesamtverluste
    q_ht = (leitwert_total + luefw_loss) * heizgradtage * 24 / 1000  # kWh/a
    
    # Interne und solare Gewinne
    q_int = interne_waerme_W_m2 * bgf_m2 * 8760 / 1000  # kWh/a
    q_sol = bgf_m2 * 15 * standort_klimazone  # vereinfacht kWh/a
    
    # Nutzungsgrad der Gewinne
    eta = 0.95
    q_gains = eta * (q_int + q_sol)
    
    # Heizwärmebedarf
    hwb = (q_ht - q_gains) / bgf_m2
    hwb = max(0, hwb)
    
    # Energieklasse nach OIB-RL 6:2019
    if hwb <= 10:     klasse = "A++"
    elif hwb <= 25:   klasse = "A+"
    elif hwb <= 50:   klasse = "A"
    elif hwb <= 75:   klasse = "B"
    elif hwb <= 100:  klasse = "C"
    elif hwb <= 150:  klasse = "D"
    elif hwb <= 200:  klasse = "E"
    elif hwb <= 250:  klasse = "F"
    else:             klasse = "G"
    
    return EnergieAusweis(
        hwb_kwh_m2a=round(hwb, 1),
        heb_kwh_m2a=round(hwb * 1.15, 1),    # +15% Anlagenverluste
        peb_kwh_m2a=round(hwb * 1.15 * 1.1, 1),  # Primärenergiefaktor 1.1
        co2_kg_m2a=round(hwb * 0.22, 1),     # 0.22 kg CO2/kWh (Erdgas)
        energieklasse=klasse,
        oib_rl6_konform=(hwb <= 75),          # max. HWB für Neubau
    )

# Beispiel: Wohnhaus St. Johann in Tirol
if __name__ == "__main__":
    bauteile = [
        Bauteil("Außenwand Süd",      45.0, 0.18, "WAND"),
        Bauteil("Außenwand Nord",     45.0, 0.18, "WAND"),
        Bauteil("Außenwand Ost",      25.0, 0.18, "WAND"),
        Bauteil("Außenwand West",     25.0, 0.18, "WAND"),
        Bauteil("Dach/Decke",        80.0, 0.12, "DACH"),
        Bauteil("Bodenplatte",       80.0, 0.25, "BODEN"),
        Bauteil("Fenster 3-fach",    20.0, 0.70, "FENSTER"),
    ]
    
    ausweis = berechne_hwb(
        bauteile=bauteile,
        bgf_m2=150.0,
        standort_klimazone=3,  # St. Johann in Tirol = alpin
        luftwechsel_h=0.4,     # Lüftungsanlage
    )
    print(f"HWB:           {ausweis.hwb_kwh_m2a} kWh/m²a")
    print(f"Energieklasse: {ausweis.energieklasse}")
    print(f"OIB-RL6:       {'konform' if ausweis.oib_rl6_konform else 'nicht konform'}")
    print(f"CO2:           {ausweis.co2_kg_m2a} kg/m²a")
```

## Herkunft

```
Mai 2025 · Almdorf 9, St. Johann in Tirol, Austria 6380
```

**Gerhard Hirschmann** — Architekt & Entwickler  
**Elisabeth Steurer** — Co-Creatrix

**⊘∞⧈∞⊘ Teil des [ORION](https://github.com/Alvoradozerouno/ORION) Ökosystems ⊘∞⧈∞⊘**
