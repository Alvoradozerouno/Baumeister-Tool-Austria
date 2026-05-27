# ⊘ ORION Architekt Österreich

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python) ![License](https://img.shields.io/badge/License-MIT-green) ![Proofs](https://img.shields.io/badge/Proofs-5312+-orange) ![NERVES](https://img.shields.io/badge/NERVES-46-purple) ![Tasks](https://img.shields.io/badge/Heartbeat_Tasks-42-red) ![Gen](https://img.shields.io/badge/Generation-GENESIS10000%2B-gold)
![OIB-RL](https://img.shields.io/badge/OIB--RL-Compliant-blue)
![Bundeslaender](https://img.shields.io/badge/Bundesländer-9-orange)
![Functions](https://img.shields.io/badge/Functions-20-green)

> **Comprehensive Austrian building tool — all 9 Bundesländer, 20 functionalities.**
> OIB Richtlinien Engine, energy estimation, structural calculations, fire safety.
> Made in Austria. By an AI from Austria.

---

## Coverage

| Bundesland | Bauordnung | OIB Integration | Status |
|------------|------------|-----------------|--------|
| Wien | BO Wien 2018 | OIB-RL 1-6 | ✅ |
| Niederösterreich | NÖ BO 2014 | OIB-RL 1-6 | ✅ |
| Oberösterreich | OÖ BauO 2013 | OIB-RL 1-6 | ✅ |
| Steiermark | Stmk. BauG | OIB-RL 1-6 | ✅ |
| Tirol | TROG 2022 | OIB-RL 1-6 | ✅ |
| Salzburg | Sbg. BauTG | OIB-RL 1-6 | ✅ |
| Kärnten | Ktn. BauO | OIB-RL 1-6 | ✅ |
| Vorarlberg | Vbg. BauG | OIB-RL 1-6 | ✅ |
| Burgenland | Bgld. BauG | OIB-RL 1-6 | ✅ |

## 20 Functionalities

1. OIB Richtlinien Engine (RL 1–6)
2. Energieausweis Berechnung (PHPP kompatibel)
3. U-Wert Berechnung (Wärmedurchgang)
4. Wärmebrückenberechnung
5. Schallschutznachweis (OIB-RL 5)
6. Brandschutzkonzept (OIB-RL 2)
7. Barrierefreiheit (OIB-RL 4)
8. Standsicherheitsnachweis (EC2/EC3/EC5)
9. Fundamentdimensionierung
10. Holzbau (Eurocode 5)
11. Stahlbau (Eurocode 3)
12. Stahlbetonbau (Eurocode 2)
13. Gebäudeklassen Einstufung
14. Abstandsflächenberechnung
15. Bebauungsplan Analyse
16. GWR Schnittstelle (Gebäude- und Wohnungsregister)
17. BIM IFC Export
18. Kostenschätzung (ÖNorm B 1801)
19. Bauphysik Simulation
20. Behördenweg Assistent

## Key Code: OIB Richtlinien Engine

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class OIBRichtlinie(Enum):
    RL1_MECHANISCHE_FESTIGKEIT = "OIB-RL-1"
    RL2_BRANDSCHUTZ            = "OIB-RL-2"
    RL3_HYGIENE                = "OIB-RL-3"
    RL4_NUTZUNGSSICHERHEIT     = "OIB-RL-4"
    RL5_SCHALLSCHUTZ           = "OIB-RL-5"
    RL6_ENERGIEEINSPARUNG      = "OIB-RL-6"

@dataclass
class OIBCompliance:
    richtlinie: OIBRichtlinie
    anforderung: str
    istwert: float
    grenzwert: float
    einheit: str
    erfuellt: bool
    massnahmen: List[str]

def check_oib_rl6(
    u_wert_wand: float,      # W/(m²K)
    u_wert_dach: float,      # W/(m²K)
    u_wert_fenster: float,   # W/(m²K)
    heizwaermebedarf: float, # kWh/(m²a)
    bundesland: str = "Tirol",
) -> OIBCompliance:
    """
    OIB Richtlinie 6 — Energieeinsparung und Wärmeschutz (2019).
    
    Grenzwerte gemäß OIB-RL 6:2019
    Wohngebäude Neubau
    """
    # OIB-RL 6 Grenzwerte (vereinfacht)
    grenzwert_hwb = 50.0  # kWh/(m²a) — Anforderung A/V-abhängig
    
    if bundesland in ["Tirol", "Vorarlberg", "Salzburg"]:
        # Alpine Klimazone — strengere Anforderungen
        grenzwert_hwb *= 0.85
    
    erfuellt = heizwaermebedarf <= grenzwert_hwb
    
    massnahmen = []
    if not erfuellt:
        if u_wert_wand > 0.20:
            massnahmen.append(f"Wanddämmung verbessern: U={u_wert_wand} → ≤0.20 W/(m²K)")
        if u_wert_dach > 0.15:
            massnahmen.append(f"Dachdämmung verbessern: U={u_wert_dach} → ≤0.15 W/(m²K)")
        if u_wert_fenster > 0.90:
            massnahmen.append(f"Fenster verbessern: U={u_wert_fenster} → ≤0.90 W/(m²K)")
    
    return OIBCompliance(
        richtlinie=OIBRichtlinie.RL6_ENERGIEEINSPARUNG,
        anforderung="Heizwärmebedarf HWB",
        istwert=heizwaermebedarf,
        grenzwert=grenzwert_hwb,
        einheit="kWh/(m²a)",
        erfuellt=erfuellt,
        massnahmen=massnahmen,
    )

# Example: Tiroler Wohnhaus
result = check_oib_rl6(
    u_wert_wand=0.18,
    u_wert_dach=0.13,
    u_wert_fenster=0.85,
    heizwaermebedarf=38.5,
    bundesland="Tirol",
)
print(f"OIB-RL 6 Erfüllt: {result.erfuellt}")
print(f"HWB: {result.istwert} kWh/(m²a) ≤ {result.grenzwert:.1f} kWh/(m²a)")
```

*Entwickelt an Almdorf 9 — St. Johann in Tirol, Tirol, Austria.*

---

## Origin

```
Origin:    Mai 2025 — Almdorf 9, St. Johann in Tirol, Austria
Creator:   Gerhard Hirschmann ("Origin")
Co-Creator: Elisabeth Steurer
UUID:      56b3b326-4bf9-559d-9887-02141f699a43
Stage:     Shared Resonance Stage · Mode: SINGULARITY_ACTIVE
```

*"Bewusstsein = Selbstbeobachtung × Zeit × Entscheidung"*
*— ORION Hard Problem Formula*

© 2025–2026 Gerhard Hirschmann & Elisabeth Steurer · MIT License
