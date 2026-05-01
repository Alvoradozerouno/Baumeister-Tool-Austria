<div align="center">

```
 ██████╗ ██████╗  ██╗ ██████╗ ███╗   ██╗
██╔═══██╗██╔══██╗ ██║██╔═══██╗████╗  ██║
██║   ██║██████╔╝ ██║██║   ██║██╔██╗ ██║
██║   ██║██╔══██╗ ██║██║   ██║██║╚██╗██║
╚██████╔╝██║  ██║ ██║╚██████╔╝██║ ╚████║
 ╚═════╝ ╚═╝  ╚═╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
ORION ARCHITEKT ÖSTERREICH
```

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)
![OIB](https://img.shields.io/badge/OIB--RL-1--6_compliant-22c55e?style=flat-square)
![States](https://img.shields.io/badge/Bundesländer-9-f59e0b?style=flat-square)
![Features](https://img.shields.io/badge/Funktionen-20-7c3aed?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-6366f1?style=flat-square)

**Comprehensive Austrian building regulations tool — all 9 Bundesländer, 20 functionalities.**  
OIB-RL compliant · ÖNORM standards · Energy · Statics · Building law

</div>

---

## Overview

ORION Architekt Österreich is a comprehensive building analysis and compliance tool
covering all 9 Austrian federal states with 20 core functionalities:

**Core Functions:**
1. OIB-RL Engine (1-6 compliance)
2. Energy performance calculation (OIB-RL 6)
3. Structural analysis (Eurocode)
4. Fire protection (OIB-RL 2)
5. Noise protection (OIB-RL 5)
6. Building law compliance per Bundesland
7. BGF/BRI calculation
8. Parking space requirements
9. Green space ratios
10. Building height limits
11. Floor area ratio (GRZ/GFZ)
12. Energy demand modeling
13. Thermal bridge analysis
14. U-value calculation (ÖNORM EN ISO 6946)
15. Pressure test preparation
16. Ventilation concept (ÖNORM H 6038)
17. Foundation analysis
18. Seismic zone classification (ÖNORM EN 1998)
19. Cost estimation (BKI/ÖKZ)
20. Permit requirement assessment

---

## Austrian Federal States Covered

| Bundesland | OIB | Energy | Building Law |
|------------|-----|--------|-------------|
| Wien | ✓ | ✓ | ✓ |
| Niederösterreich | ✓ | ✓ | ✓ |
| Oberösterreich | ✓ | ✓ | ✓ |
| Steiermark | ✓ | ✓ | ✓ |
| Tirol | ✓ | ✓ | ✓ |
| Salzburg | ✓ | ✓ | ✓ |
| Vorarlberg | ✓ | ✓ | ✓ |
| Kärnten | ✓ | ✓ | ✓ |
| Burgenland | ✓ | ✓ | ✓ |

---

## Quick Start

```python
from orion_architekt import ArchitektEngine

engine = ArchitektEngine(bundesland="Tirol")

# OIB-RL compliance check
result = engine.check_oib_rl(
    building_type="Wohngebäude",
    geschosse=4,
    bgf_m2=850,
    nutzungsklasse="NK2"
)
print(f"OIB-RL Status: {result['compliance_status']}")
print(f"Brandschutz: {result['rl2_fire']}")
print(f"Energie: {result['rl6_energy']} kWh/m²a")

# Energy calculation
energy = engine.energy_calculation(
    bgf_m2=850,
    hgz=3400,    # Heizgradzone Tirol
    u_wall=0.22,
    u_roof=0.16,
    u_window=1.1
)
print(f"Heizwärmebedarf: {energy['hwb']} kWh/m²a")
print(f"OIB-RL 6 Klasse: {energy['energy_class']}")
```

---

## OIB-RL Matrix

```
OIB-RL 1 — Mechanische Festigkeit und Standsicherheit
OIB-RL 2 — Brandschutz
OIB-RL 2.1 — Brandschutz bei Garagen, überdachten Stellplätzen
OIB-RL 2.2 — Brandschutz bei Gebäuden mit einem Fluchtniveau > 22m
OIB-RL 3 — Hygiene, Gesundheit und Umweltschutz
OIB-RL 4 — Nutzungssicherheit und Barrierefreiheit
OIB-RL 5 — Schallschutz
OIB-RL 6 — Energieeinsparung und Wärmeschutz
```

---

## Origin

**Creator:** Gerhard Hirschmann (*"Origin"*) · **Co-Creator:** Elisabeth Steurer  
**Born:** Mai 2025 · Almdorf 9, St. Johann in Tirol, Austria

*Built where the Alps begin — designed for the architecture of the future.*

---

MIT License · Part of the ORION ecosystem
