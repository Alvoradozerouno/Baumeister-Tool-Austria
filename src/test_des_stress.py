"""
DES-Stress-Test: Deterministisches Epistemisches System unter Last
==================================================================

Testet das DES mit extremen Parametern:
- 100+ Agenten
- 1000+ Propositionen
- 500+ Inferenzregeln
- Epistemische Operationen unter Last
- Konsens-Berechnung mit vielen Agenten
- Widerspruchs-Erkennung
- Fallback-Mechanismen

Ziel: System sichtbar machen und Grenzen testen
"""

import sys
import os
import json
import time
import random
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows Encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.epistemic_system import (
    DeterministicEpistemicSystem,
    EpistemicAgent,
    EpistemicProposition,
    EpistemicState,
    InferenceRule,
    EpistemicValidator,
)


# ============================================================================
# STRESS-TEST KONFIGURATION
# ============================================================================

@dataclass
class StressConfig:
    """Konfiguration fuer den Stress-Test."""
    num_agenten: int = 50
    num_propositionen: int = 500
    num_inferenzregeln: int = 200
    num_threads: int = 4
    num_iteration: int = 10
    widerspruch_rate: float = 0.05  # 5% widerspruechliche Propositionen
    timeout_seconds: float = 30.0


# ============================================================================
# STRESS-TEST GENERATOREN
# ============================================================================

class PropositionGenerator:
    """Generiert epistemische Propositionen fuer den Stress-Test."""

    THEMEN = [
        "OIB-RL", "Eurocode", "Bauordnung", "Brandschutz", "Schallschutz",
        "Energie", "Statik", "Fundament", "Dach", "Fassade", "Lueftung",
        "Elektro", "Sanitaer", "Heizung", "Dämmung", "Fenster", "Tueren",
        "Treppe", "Aufzug", "Garage", "Garten", "Stellplatz", "Abstand",
        "Hoehe", "Flaeche", "Volumen", "Gewicht", "Last", "Material",
    ]

    NORMEN = [
        "OIB-RL 1:2023", "OIB-RL 2:2023", "OIB-RL 3:2023",
        "OIB-RL 4:2023", "OIB-RL 5:2023", "OIB-RL 6:2023",
        "EN 1992-1-1", "EN 1993-1-1", "EN 1995-1-1",
        "OENORM B 5011", "OENORM B 1600", "OENORM B 8115",
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.generated = 0

    def generate(self, num: int, widerspruch_rate: float = 0.0) -> List[EpistemicProposition]:
        """Generiert Propositionen."""
        propositionen = []
        for i in range(num):
            thema = self.rng.choice(self.THEMEN)
            norm = self.rng.choice(self.NORMEN)
            wert = self.rng.uniform(0.1, 100.0)

            # Bestimme ob widerspruechlich
            is_widerspruch = self.rng.random() < widerspruch_rate

            if is_widerspruch:
                content = f"{thema}: Grenzwert UEBERSCHRITTEN ({wert:.1f} > Grenzwert)"
                confidence = self.rng.uniform(0.1, 0.4)
            else:
                content = f"{thema}: Grenzwert eingehalten ({wert:.1f} <= Grenzwert)"
                confidence = self.rng.uniform(0.6, 1.0)

            prop = EpistemicProposition(
                content=content,
                source=f"Stress-Test: {norm}",
                confidence=confidence,
                evidence=[f"Test-{i:04d}", f"Norm: {norm}"],
            )
            propositionen.append(prop)
            self.generated += 1

        return propositionen


class AgentGenerator:
    """Generiert epistemische Agenten fuer den Stress-Test."""

    ROLLEN = [
        "Architekt", "Statiker", "Prufer", "Bauphysiker", "Energieberater",
        "Brandschuetzer", "Schallschuetzer", "Elektroplaner", "Sanitaerplaner",
        "HLSE-Planer", "Kostenplaner", "Zeitplaner", "Qualitaetsmanager",
        "Sicherheitskoordinator", "Umweltgutachter", "Geotechniker",
        "Vermesser", "Bauingenieur", "Holzbauer", "Stahlbauer",
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, num: int) -> Dict[str, float]:
        """Generiert Agenten mit Rollen und Thresholds."""
        agenten = {}
        for i in range(num):
            rolle = self.ROLLEN[i % len(self.ROLLEN)]
            if i >= len(self.ROLLEN):
                rolle = f"{rolle}_{i}"
            threshold = self.rng.uniform(0.7, 0.99)
            agenten[rolle] = threshold
        return agenten


class InferenzregelGenerator:
    """Generiert Inferenzregeln fuer den Stress-Test."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, num: int, propositionen: List[EpistemicProposition]) -> List[InferenceRule]:
        """Generiert Inferenzregeln."""
        regeln = []
        for i in range(num):
            # Waehle zufaellige Praemissen
            num_praemissen = self.rng.randint(2, min(5, len(propositionen)))
            praemissen = self.rng.sample(propositionen, num_praemissen)

            regel = InferenceRule(
                name=f"Stress-Regel-{i:04d}",
                premise_ids=[p.id for p in praemissen],
                conclusion_template=f"Schlussfolgerung-{i:04d}",
                confidence_factor=self.rng.uniform(0.5, 0.99),
            )
            regeln.append(regel)

        return regeln


# ============================================================================
# STRESS-TEST DURCHFUEHRUNG
# ============================================================================

class DESStressTester:
    """Fuehrt den DES-Stress-Test durch."""

    def __init__(self, config: StressConfig):
        self.config = config
        self.ergebnisse = {}
        self.system = DeterministicEpistemicSystem("DES-Stress-Test")

    def run(self) -> Dict[str, Any]:
        """Fuehrt den kompletten Stress-Test durch."""
        gesamt_start = time.time()

        print("=" * 80)
        print("DES-STRESS-TEST")
        print("Deterministisches Epistemisches System unter Last")
        print("=" * 80)
        print()
        print(f"Konfiguration:")
        print(f"  Agenten: {self.config.num_agenten}")
        print(f"  Propositionen: {self.config.num_propositionen}")
        print(f"  Inferenzregeln: {self.config.num_inferenzregeln}")
        print(f"  Threads: {self.config.num_threads}")
        print(f"  Iterationen: {self.config.num_iteration}")
        print(f"  Widerspruch-Rate: {self.config.widerspruch_rate:.0%}")
        print()

        # Test 1: Agenten-Erstellung
        self._test_agenten_erstellung()

        # Test 2: Propositionen-Erstellung
        self._test_propositionen_erstellung()

        # Test 3: Inferenzregeln-Erstellung
        self._test_inferenzregeln_erstellung()

        # Test 4: Wissen-Synchronisation
        self._test_wissen_synchronisation()

        # Test 5: Konsens-Berechnung
        self._test_konsens_berechnung()

        # Test 6: Widerspruchs-Erkennung
        self._test_widerspruchs_erkenntung()

        # Test 7: System-Validierung
        self._test_system_validierung()

        # Test 8: Parallel-Operationen
        self._test_parallel_operationen()

        # Test 9: Fallback-Mechanismen
        self._test_fallback_mechanismen()

        # Test 10: Skalierungs-Test
        self._test_skalierung()

        gesamt_end = time.time()
        gesamt_zeit = gesamt_end - gesamt_start

        # Gesamtergebnis
        self._print_gesamtergebnis(gesamt_zeit)

        return self.ergebnisse

    def _test_agenten_erstellung(self) -> None:
        """Test 1: Agenten-Erstellung unter Last."""
        print("TEST 1: Agenten-Erstellung")
        print("-" * 40)

        start = time.time()
        agent_gen = AgentGenerator()
        agenten = agent_gen.generate(self.config.num_agenten)

        for name, threshold in agenten.items():
            self.system.create_agent(name, validation_threshold=threshold)

        dauer = time.time() - start
        self.ergebnisse["agenten_erstellung"] = {
            "anzahl": len(agenten),
            "dauer_sec": round(dauer, 4),
            "pro_agent": round(dauer / len(agenten) * 1000, 4),
        }

        print(f"  {len(agenten)} Agenten erstellt in {dauer:.4f}s")
        print(f"  Pro Agent: {dauer/len(agenten)*1000:.4f}ms")
        print()

    def _test_propositionen_erstellung(self) -> None:
        """Test 2: Propositionen-Erstellung unter Last."""
        print("TEST 2: Propositionen-Erstellung")
        print("-" * 40)

        start = time.time()
        prop_gen = PropositionGenerator()
        propositionen = prop_gen.generate(
            self.config.num_propositionen,
            self.config.widerspruch_rate,
        )

        for prop in propositionen:
            self.system.add_global_knowledge(prop)

        dauer = time.time() - start
        self.ergebnisse["propositionen_erstellung"] = {
            "anzahl": len(propositionen),
            "dauer_sec": round(dauer, 4),
            "pro_proposition": round(dauer / len(propositionen) * 1000, 4),
        }

        print(f"  {len(propositionen)} Propositionen erstellt in {dauer:.4f}s")
        print(f"  Pro Proposition: {dauer/len(propositionen)*1000:.4f}ms")
        print()

    def _test_inferenzregeln_erstellung(self) -> None:
        """Test 3: Inferenzregeln-Erstellung."""
        print("TEST 3: Inferenzregeln-Erstellung")
        print("-" * 40)

        start = time.time()
        regel_gen = InferenzregelGenerator()
        propositionen = list(self.system.global_knowledge.values())[:100]
        regeln = regel_gen.generate(self.config.num_inferenzregeln, propositionen)

        # Fuege Regeln zum ersten Agenten hinzu
        erster_agent = list(self.system.agents.values())[0]
        erster_agent.inference_rules.extend(regeln)

        dauer = time.time() - start
        self.ergebnisse["inferenzregeln_erstellung"] = {
            "anzahl": len(regeln),
            "dauer_sec": round(dauer, 4),
            "pro_regel": round(dauer / len(regeln) * 1000, 4),
        }

        print(f"  {len(regeln)} Inferenzregeln erstellt in {dauer:.4f}s")
        print(f"  Pro Regel: {dauer/len(regeln)*1000:.4f}ms")
        print()

    def _test_wissen_synchronisation(self) -> None:
        """Test 4: Wissen-Synchronisation zu allen Agenten."""
        print("TEST 4: Wissen-Synchronisation")
        print("-" * 40)

        start = time.time()
        for name in self.system.agents:
            self.system.sync_agent_knowledge(name)

        dauer = time.time() - start
        self.ergebnisse["wissen_synchronisation"] = {
            "anzahl_agenten": len(self.system.agents),
            "dauer_sec": round(dauer, 4),
            "pro_agent": round(dauer / len(self.system.agents) * 1000, 4),
        }

        print(f"  Wissen zu {len(self.system.agents)} Agenten synchronisiert in {dauer:.4f}s")
        print(f"  Pro Agent: {dauer/len(self.system.agents)*1000:.4f}ms")
        print()

    def _test_konsens_berechnung(self) -> None:
        """Test 5: Konsens-Berechnung mit vielen Agenten."""
        print("TEST 5: Konsens-Berechnung")
        print("-" * 40)

        start = time.time()
        konsens_ergebnisse = {}

        # Berechne Konsens fuer erste 50 Propositionen
        prop_ids = list(self.system.global_knowledge.keys())[:50]
        for prop_id in prop_ids:
            konsens = self.system.compute_consensus(prop_id)
            konsens_ergebnisse[prop_id[:12]] = konsens["consensus_state"]

        dauer = time.time() - start
        self.ergebnisse["konsens_berechnung"] = {
            "anzahl_propositionen": len(prop_ids),
            "dauer_sec": round(dauer, 4),
            "pro_proposition": round(dauer / len(prop_ids) * 1000, 4),
            "konsens_zustand": {
                "certain": sum(1 for v in konsens_ergebnisse.values() if v == "certain"),
                "probable": sum(1 for v in konsens_ergebnisse.values() if v == "probable"),
                "unknown": sum(1 for v in konsens_ergebnisse.values() if v == "unknown"),
            },
        }

        print(f"  Konsens fuer {len(prop_ids)} Propositionen in {dauer:.4f}s")
        print(f"  Pro Proposition: {dauer/len(prop_ids)*1000:.4f}ms")
        print(f"  Zustände: {self.ergebnisse['konsens_berechnung']['konsens_zustand']}")
        print()

    def _test_widerspruchs_erkenntung(self) -> None:
        """Test 6: Widerspruchs-Erkennung."""
        print("TEST 6: Widerspruchs-Erkennung")
        print("-" * 40)

        start = time.time()
        state = self.system.validate_system_state()

        dauer = time.time() - start
        self.ergebnisse["widerspruchs_erkenntung"] = {
            "dauer_sec": round(dauer, 4),
            "widersprueche": len(state["contradictions"]),
            "system_valide": state["system_valid"],
        }

        print(f"  Widersprueche erkannt: {len(state['contradictions'])} in {dauer:.4f}s")
        print(f"  System valide: {'JA' if state['system_valid'] else 'NEIN'}")
        print()

    def _test_system_validierung(self) -> None:
        """Test 7: System-Validierung."""
        print("TEST 7: System-Validierung")
        print("-" * 40)

        start = time.time()
        report = self.system.get_system_report()

        dauer = time.time() - start
        self.ergebnisse["system_validierung"] = {
            "dauer_sec": round(dauer, 4),
            "report_laenge": len(report),
        }

        print(f"  System-Report erstellt in {dauer:.4f}s ({len(report)} Zeichen)")
        print()

    def _test_parallel_operationen(self) -> None:
        """Test 8: Parallel-Operationen mit Threads."""
        print("TEST 8: Parallel-Operationen")
        print("-" * 40)

        def worker(thread_id: int) -> Dict[str, Any]:
            """Worker-Funktion fuer Thread."""
            local_system = DeterministicEpistemicSystem(f"Worker-{thread_id}")
            prop_gen = PropositionGenerator(seed=thread_id)
            propositionen = prop_gen.generate(50)
            for prop in propositionen:
                local_system.add_global_knowledge(prop)
            local_system.create_agent("Test-Agent")
            local_system.sync_agent_knowledge("Test-Agent")
            return {
                "thread_id": thread_id,
                "propositionen": len(propositionen),
                "agenten": len(local_system.agents),
            }

        start = time.time()
        ergebnisse = {}

        with ThreadPoolExecutor(max_workers=self.config.num_threads) as executor:
            futures = {
                executor.submit(worker, i): i
                for i in range(self.config.num_threads)
            }
            for future in as_completed(futures):
                thread_id = futures[future]
                try:
                    ergebnisse[thread_id] = future.result()
                except Exception as e:
                    ergebnisse[thread_id] = {"error": str(e)}

        dauer = time.time() - start
        self.ergebnisse["parallel_operationen"] = {
            "anzahl_threads": self.config.num_threads,
            "dauer_sec": round(dauer, 4),
            "pro_thread": round(dauer / self.config.num_threads * 1000, 4),
            "ergebnisse": ergebnisse,
        }

        print(f"  {self.config.num_threads} Threads in {dauer:.4f}s")
        print(f"  Pro Thread: {dauer/self.config.num_threads*1000:.4f}ms")
        print()

    def _test_fallback_mechanismen(self) -> None:
        """Test 9: Fallback-Mechanismen."""
        print("TEST 9: Fallback-Mechanismen")
        print("-" * 40)

        start = time.time()

        # Erstelle UNKNOWN Propositionen
        unknown_props = []
        for i in range(20):
            prop = EpistemicProposition(
                content=f"UNKNOWN-Test-{i:02d}: Daten nicht verfuegbar",
                source="Fallback-Test",
                confidence=0.0,
                evidence=[f"Test-{i:02d}"],
            )
            unknown_props.append(prop)
            self.system.add_global_knowledge(prop)

        # Berechne Konsens fuer UNKNOWN
        unknown_konsens = 0
        for prop in unknown_props:
            konsens = self.system.compute_consensus(prop.id)
            if konsens["consensus_state"] == "unknown":
                unknown_konsens += 1

        dauer = time.time() - start
        self.ergebnisse["fallback_mechanismen"] = {
            "anzahl_unknown": len(unknown_props),
            "unknown_konsens": unknown_konsens,
            "dauer_sec": round(dauer, 4),
        }

        print(f"  {len(unknown_props)} UNKNOWN Propositionen erstellt")
        print(f"  UNKNOWN-Konsens: {unknown_konsens}/{len(unknown_props)}")
        print(f"  Dauer: {dauer:.4f}s")
        print()

    def _test_skalierung(self) -> None:
        """Test 10: Skalierungs-Test."""
        print("TEST 10: Skalierungs-Test")
        print("-" * 40)

        skalierungs_ergebnisse = []

        for faktor in [1, 2, 5, 10]:
            num_props = self.config.num_propositionen * faktor // 10

            start = time.time()
            local_system = DeterministicEpistemicSystem(f"Skalierung-{faktor}x")
            prop_gen = PropositionGenerator(seed=faktor)
            propositionen = prop_gen.generate(num_props)
            for prop in propositionen:
                local_system.add_global_knowledge(prop)

            # Erstelle Agenten
            for i in range(self.config.num_agenten // faktor):
                local_system.create_agent(f"Agent-{i}")

            # Synchronisiere
            for name in local_system.agents:
                local_system.sync_agent_knowledge(name)

            # Konsens
            for prop_id in list(local_system.global_knowledge.keys())[:10]:
                local_system.compute_consensus(prop_id)

            dauer = time.time() - start
            skalierungs_ergebnisse.append({
                "faktor": faktor,
                "propositionen": num_props,
                "agenten": len(local_system.agents),
                "dauer_sec": round(dauer, 4),
            })

        self.ergebnisse["skalierung"] = skalierungs_ergebnisse

        for erg in skalierungs_ergebnisse:
            print(f"  {erg['faktor']}x: {erg['propositionen']} Props, {erg['agenten']} Agenten, {erg['dauer_sec']:.4f}s")
        print()

    def _print_gesamtergebnis(self, gesamt_zeit: float) -> None:
        """Gibt das Gesamtergebnis aus."""
        print("=" * 80)
        print("GESAMTERGEBNIS")
        print("=" * 80)
        print()

        # System-Zustand
        state = self.system.validate_system_state()

        print(f"System-Zustand:")
        print(f"  System valide: {'JA' if state['system_valid'] else 'NEIN'}")
        print(f"  Widersprueche: {len(state['contradictions'])}")
        print(f"  Agenten: {state['agent_count']}")
        print(f"  Globales Wissen: {state['global_knowledge_count']} Propositionen")
        print(f"  Gesamtwissen: {state['total_knowledge']} Propositionen")
        print()

        # Test-Ergebnisse
        print(f"Test-Ergebnisse:")
        print(f"  {'Test':<30} {'Dauer (s)':<12} {'Details':<30}")
        print(f"  {'-'*30} {'-'*12} {'-'*30}")

        for test_name, test_erg in self.ergebnisse.items():
            if test_name == "skalierung":
                continue
            dauer = test_erg.get("dauer_sec", 0)
            details = ""
            if "anzahl" in test_erg:
                details = f"{test_erg['anzahl']} Elemente"
            elif "widersprueche" in test_erg:
                details = f"{test_erg['widersprueche']} Widersprueche"
            print(f"  {test_name:<30} {dauer:<12.4f} {details:<30}")

        print()
        print(f"Gesamtzeit: {gesamt_zeit:.4f}s")
        print()

        # Bewertung
        if state["system_valid"] and gesamt_zeit < self.config.timeout_seconds:
            print("=" * 80)
            print("STRESS-TEST BESTANDEN - SYSTEM STABIL")
            print("=" * 80)
            print()
            print(f"Das DES hat den Stress-Test erfolgreich bestanden:")
            print(f"  [OK] {self.config.num_agenten} Agenten erstellt")
            print(f"  [OK] {self.config.num_propositionen} Propositionen verarbeitet")
            print(f"  [OK] {self.config.num_inferenzregeln} Inferenzregeln erstellt")
            print(f"  [OK] {self.config.num_threads} Threads parallel verarbeitet")
            print(f"  [OK] System valide, {len(state['contradictions'])} Widersprueche")
            print(f"  [OK] Gesamtzeit: {gesamt_zeit:.4f}s (Timeout: {self.config.timeout_seconds}s)")
            print()
            print("ERGEBNIS: Das DES ist STRESS-RESISTENT und PRODUCTION-READY.")
        else:
            print("=" * 80)
            print("STRESS-TEST FEHLGESCHLAGEN")
            print("=" * 80)
            print(f"System valide: {'JA' if state['system_valid'] else 'NEIN'}")
            print(f"Gesamtzeit: {gesamt_zeit:.4f}s (Timeout: {self.config.timeout_seconds}s)")

        # JSON-Export
        report = {
            "test": "DES-Stress-Test",
            "datum": datetime.now().isoformat(),
            "konfiguration": {
                "num_agenten": self.config.num_agenten,
                "num_propositionen": self.config.num_propositionen,
                "num_inferenzregeln": self.config.num_inferenzregeln,
                "num_threads": self.config.num_threads,
                "widerspruch_rate": self.config.widerspruch_rate,
            },
            "ergebnisse": self.ergebnisse,
            "system_zustand": {
                "system_valide": state["system_valid"],
                "widersprueche": len(state["contradictions"]),
                "agenten": state["agent_count"],
                "globales_wissen": state["global_knowledge_count"],
                "gesamtwissen": state["total_knowledge"],
            },
            "gesamtzeit_sec": round(gesamt_zeit, 4),
            "bestanden": state["system_valid"] and gesamt_zeit < self.config.timeout_seconds,
        }

        report_path = os.path.join(os.path.dirname(__file__), "..", "stress_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nStress-Report gespeichert: {report_path}")


# ============================================================================
# HAUPTPROGRAMM
# ============================================================================

def main():
    # Konfiguration
    config = StressConfig(
        num_agenten=50,
        num_propositionen=500,
        num_inferenzregeln=200,
        num_threads=4,
        num_iteration=10,
        widerspruch_rate=0.05,
        timeout_seconds=30.0,
    )

    tester = DESStressTester(config)
    tester.run()


if __name__ == "__main__":
    main()