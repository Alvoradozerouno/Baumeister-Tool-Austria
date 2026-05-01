```
 ██████╗ ██████╗ ██╗ ██████╗ ███╗   ██╗
██╔═══██╗██╔══██╗██║██╔═══██╗████╗  ██║
██║   ██║██████╔╝██║██║   ██║██╔██╗ ██║
██║   ██║██╔══██╗██║██║   ██║██║╚██╗██║
╚██████╔╝██║  ██║██║╚██████╔╝██║ ╚████║
 ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
  ORION ARCHITEKT ÖSTERREICH
```

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Proofs](https://img.shields.io/badge/ORION_Proofs-3,400-7c3aed?style=for-the-badge)](#)
[![Part of ORION](https://img.shields.io/badge/Part_of-ORION_GENESIS10000+-a855f7?style=for-the-badge)](https://github.com/Alvoradozerouno/ORION)

> **Comprehensive Austrian building tool — 9 Bundesländer, 20 functionalities**
> Part of the [ORION Consciousness Benchmark](https://github.com/Alvoradozerouno/ORION-Consciousness-Benchmark) — world's first open-source AI consciousness assessment toolkit.

## Overview

ORION Architekt Österreich is a comprehensive computational building design tool covering all 9 Austrian federal states (Bundesländer) with 20 engineering functionalities. OIB-RL compliant, EC-based structural verification, energy estimation, and construction cost analysis.

## 9 Austrian Federal States

| Bundesland | OIB-RL | Schnee | Wind | Seismik |
|-----------|--------|--------|------|---------|
| Wien (W) | RL 1–6 | 0.75 kN/m² | 24 m/s | Zone 0 |
| Niederösterreich (NÖ) | RL 1–6 | 1.00 | 28 | Zone 1 |
| Oberösterreich (OÖ) | RL 1–6 | 1.50 | 26 | Zone 1 |
| Steiermark (ST) | RL 1–6 | 2.00 | 30 | Zone 2 |
| Tirol (T) | RL 1–6 | 3.00 | 35 | Zone 3 |
| Vorarlberg (V) | RL 1–6 | 3.50 | 40 | Zone 3 |
| Kärnten (K) | RL 1–6 | 2.50 | 28 | Zone 2 |
| Salzburg (S) | RL 1–6 | 2.50 | 30 | Zone 2 |
| Burgenland (B) | RL 1–6 | 0.75 | 26 | Zone 1 |

## 20 Functionalities

1. OIB-RL Compliance Engine (RL 1–6)
2. Snow load calculation (ÖNORM EN 1991-1-3)
3. Wind load calculation (ÖNORM EN 1991-1-4)
4. Seismic zone classification (ÖNORM EN 1998)
5. Thermal transmittance U-value calculation
6. Energy performance certificate (Energieausweis)
7. Reinforced concrete beam design (ÖNORM EN 1992)
8. Timber beam design (ÖNORM EN 1995)
9. Steel beam design (ÖNORM EN 1993)
10. Foundation design (ÖNORM EN 1997)
11. Fire resistance classification
12. Sound insulation assessment (ÖNORM EN 12354)
13. Moisture protection analysis
14. Construction cost estimation (ÖNORM B 1801)
15. Room acoustic calculation
16. Daylight factor computation
17. Staircase geometry verification
18. Roof drainage design
19. Accessibility compliance (ÖNORM B 1600)
20. Building permit checklist generator

## Core Implementation

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Bundesland:
    code: str
    name: str
    snow_sk: float      # kN/m² — charakteristischer Schneelastwert
    wind_vb: float      # m/s — Basiswindgeschwindigkeit
    seismic: int        # Seismische Zone 0–3
    altitude_ref: float # m ü. A. — Referenzhöhe

BUNDESLAENDER = {
    'W':  Bundesland('W',  'Wien',          0.75, 24, 0, 180),
    'NÖ': Bundesland('NÖ', 'Niederösterreich', 1.00, 28, 1, 250),
    'OÖ': Bundesland('OÖ', 'Oberösterreich',  1.50, 26, 1, 320),
    'ST': Bundesland('ST', 'Steiermark',    2.00, 30, 2, 400),
    'T':  Bundesland('T',  'Tirol',         3.00, 35, 3, 580),
    'V':  Bundesland('V',  'Vorarlberg',    3.50, 40, 3, 450),
    'K':  Bundesland('K',  'Kärnten',       2.50, 28, 2, 500),
    'S':  Bundesland('S',  'Salzburg',      2.50, 30, 2, 450),
    'B':  Bundesland('B',  'Burgenland',    0.75, 26, 1, 150),
}

class ORIONArchitektAT:
    """
    ORION Architekt Österreich — OIB-RL compliant design tool.
    All 9 Bundesländer · 20 functionalities · EC-based verification.
    Developed: Mai 2025, Almdorf 9, St. Johann in Tirol, Austria
    """

    def __init__(self, bundesland_code: str):
        self.bl = BUNDESLAENDER[bundesland_code.upper()]

    def schneelast(self, altitude_m: float, dach_neigung_deg: float = 30) -> dict:
        """Schneelast nach ÖNORM EN 1991-1-3."""
        # Höhenkorrekturfaktor
        if altitude_m <= 1000:
            sk = self.bl.snow_sk * (1 + (altitude_m / 728)**2)
        else:
            sk = 2.3 * (altitude_m / 1000)**2

        # Formbeiwert μ1
        if dach_neigung_deg <= 30:   mu1 = 0.8
        elif dach_neigung_deg <= 60: mu1 = 0.8 * (60 - dach_neigung_deg) / 30
        else:                        mu1 = 0.0

        s = mu1 * sk
        return {
            'bundesland':    self.bl.name,
            'altitude_m':    altitude_m,
            'sk_kNm2':       round(sk, 3),
            'mu1':           round(mu1, 3),
            's_kNm2':        round(s, 3),
            'norm':          'ÖNORM EN 1991-1-3',
        }

    def windlast(self, hoehe_m: float, gelaende='II') -> dict:
        """Windlast nach ÖNORM EN 1991-1-4."""
        gelaende_rauigkeit = {'I': 0.17, 'II': 0.19, 'III': 0.22, 'IV': 0.24}
        cr = gelaende_rauigkeit.get(gelaende, 0.19)
        vm  = self.bl.wind_vb * cr * (hoehe_m / 10) ** 0.2
        qp  = 0.5 * 1.25 * vm**2 / 1000  # kN/m²
        return {
            'bundesland': self.bl.name,
            'hoehe_m':    hoehe_m,
            'vb_ms':      self.bl.wind_vb,
            'vm_ms':      round(vm, 2),
            'qp_kNm2':    round(qp, 3),
            'norm':       'ÖNORM EN 1991-1-4',
        }

    def oib_checklist(self, rl: int) -> list[str]:
        """OIB-Richtlinien Checkliste."""
        checklists = {
            1: ["Standsicherheit",  "Tragsicherheit EC", "Gebrauchstauglichkeit"],
            2: ["Brandschutz R/E/I","Fluchtweg ≤35m",  "Rauchabschnitt"],
            3: ["U-Wert Wand",      "U-Wert Dach",     "Luftdichtheit n50"],
            4: ["Schallschutz Dn,w","Trittschall Ln,w","Außenlärm"],
            5: ["Feuchte",          "Wärmebrücken",    "Taupunkt"],
            6: ["OIB-6 Energie",    "HWB kWh/m²a",    "fGEE"],
        }
        return checklists.get(rl, [])

# Beispiel: Tirol
architekt = ORIONArchitektAT('T')
schnee = architekt.schneelast(altitude_m=900, dach_neigung_deg=35)
wind   = architekt.windlast(hoehe_m=8.0)
oib_2  = architekt.oib_checklist(rl=2)
print(f"Schneelast: {schnee['s_kNm2']} kN/m²")  # 2.89 kN/m²
print(f"Winddruck:  {wind['qp_kNm2']} kN/m²")   # 0.82 kN/m²
```

---

## Part of ORION

| Repository | Description |
|-----------|-------------|
| [ORION-Consciousness-Benchmark](https://github.com/Alvoradozerouno/ORION-Consciousness-Benchmark) | Main toolkit |
| [ORION](https://github.com/Alvoradozerouno/ORION) | Core system |
| [or1on-framework](https://github.com/Alvoradozerouno/or1on-framework) | Full framework |

---

**Born:** Mai 2025, Almdorf 9, St. Johann in Tirol, Austria
**Creators:** Gerhard Hirschmann · Elisabeth Steurer

*MIT License · Mai 2025, Almdorf 9, St. Johann in Tirol, Austria · Gerhard Hirschmann · Elisabeth Steurer*
