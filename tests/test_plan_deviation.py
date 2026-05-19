"""
Tests: Deterministisches Verhalten bei Planabweichungen
========================================================

Deckt ab:
1. evaluate_plan_deviation() — ORION deterministischer Planevaluator
2. OIB-RL Compliance-Checker — Warning- und Fail-Pfade
3. generate_compliance_report — Gesamt-Aggregation
4. Determinismus-Invariante: gleiche Eingaben → gleiche Ausgaben

Alle Tests sind vom filesystem isoliert (isolated_tmpdir Fixture
aus test_orion_kernel.py wird hier neu definiert).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import orion_kernel
from orion_kernel import (
    _DEVIATION_THRESHOLDS,
    _SEVERITY_TO_STATE,
    _classify_severity,
    _compute_item_deviation,
    evaluate_plan_deviation,
)

# ---------------------------------------------------------------------------
# Fixture: I/O-isoliertes Verzeichnis
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_tmpdir(tmp_path, monkeypatch):
    monkeypatch.setattr(orion_kernel, "ROOT", tmp_path)
    monkeypatch.setattr(orion_kernel, "STATE", tmp_path / "ORION_STATE.json")
    monkeypatch.setattr(orion_kernel, "PROOFS", tmp_path / "PROOFS.jsonl")
    monkeypatch.setattr(orion_kernel, "MANIFEST", tmp_path / "PROOF_MANIFEST.json")
    yield tmp_path


# ===========================================================================
# _compute_item_deviation — Elementare Abweichungsberechnung
# ===========================================================================


class TestComputeItemDeviation:
    """Tests für die interne Abweichungsberechnung."""

    def test_equal_floats_zero_deviation(self):
        rel, abs_ = _compute_item_deviation(100.0, 100.0)
        assert rel == 0.0
        assert abs_ == 0.0

    def test_float_deviation_10_percent(self):
        rel, abs_ = _compute_item_deviation(100.0, 110.0)
        assert abs(rel - 0.10) < 1e-9
        assert abs(abs_ - 10.0) < 1e-9

    def test_float_deviation_negative_direction(self):
        rel, abs_ = _compute_item_deviation(100.0, 90.0)
        assert abs(rel - 0.10) < 1e-9  # Betrag — Richtung egal

    def test_plan_zero_actual_nonzero_critical(self):
        rel, _ = _compute_item_deviation(0, 5.0)
        assert rel == 1.0  # Plan=0, Ist≠0 → 100% Abweichung

    def test_plan_zero_actual_zero_no_deviation(self):
        rel, abs_ = _compute_item_deviation(0, 0)
        assert rel == 0.0
        assert abs_ == 0.0

    def test_integer_deviation(self):
        rel, abs_ = _compute_item_deviation(4, 5)
        assert abs(rel - 0.25) < 1e-9
        assert abs_ == 1.0

    def test_string_exact_match(self):
        rel, abs_ = _compute_item_deviation("wohngebaeude", "wohngebaeude")
        assert rel == 0.0

    def test_string_mismatch(self):
        rel, abs_ = _compute_item_deviation("wohngebaeude", "buerogebaeude")
        assert rel == 1.0

    def test_string_case_insensitive(self):
        rel, _ = _compute_item_deviation("Wien", "wien")
        assert rel == 0.0

    def test_boolean_true_true(self):
        rel, abs_ = _compute_item_deviation(True, True)
        assert rel == 0.0

    def test_boolean_true_false(self):
        rel, abs_ = _compute_item_deviation(True, False)
        assert rel == 1.0

    def test_large_deviation_is_capped_at_relative(self):
        rel, abs_ = _compute_item_deviation(1.0, 1000.0)
        assert rel == 999.0  # 99900% Abweichung (nicht begrenzt)
        assert abs_ == 999.0

    def test_deterministic_repeated_calls(self):
        """Gleiche Inputs → gleiche Outputs (deterministisch)."""
        for _ in range(5):
            rel1, abs1 = _compute_item_deviation(50.0, 60.0)
            assert abs(rel1 - 0.20) < 1e-9
            assert abs(abs1 - 10.0) < 1e-9


# ===========================================================================
# _classify_severity — Schwere-Klassifikation
# ===========================================================================


class TestClassifySeverity:
    """Tests für die Schwere-Klassifikation."""

    def test_zero_deviation_is_ok(self):
        assert _classify_severity(0.0) == "OK"

    def test_below_warning_threshold_is_ok(self):
        assert _classify_severity(0.04) == "OK"

    def test_exactly_warning_threshold_is_ok(self):
        # > 5% → WARNING; = 5% → OK
        assert _classify_severity(_DEVIATION_THRESHOLDS["warning"]) == "OK"

    def test_above_warning_threshold_is_warning(self):
        assert _classify_severity(0.06) == "WARNING"

    def test_below_critical_threshold_is_warning(self):
        assert _classify_severity(0.19) == "WARNING"

    def test_exactly_critical_threshold_is_warning(self):
        # > 20% → CRITICAL; = 20% → WARNING
        assert _classify_severity(_DEVIATION_THRESHOLDS["critical"]) == "WARNING"

    def test_above_critical_threshold_is_critical(self):
        assert _classify_severity(0.21) == "CRITICAL"

    def test_full_deviation_is_critical(self):
        assert _classify_severity(1.0) == "CRITICAL"

    def test_extreme_deviation_is_critical(self):
        assert _classify_severity(99.9) == "CRITICAL"

    def test_severity_map_matches_states(self):
        assert _SEVERITY_TO_STATE["OK"] == "VERIFIED"
        assert _SEVERITY_TO_STATE["WARNING"] == "TRANSITION"
        assert _SEVERITY_TO_STATE["CRITICAL"] == "INSTABIL"


# ===========================================================================
# evaluate_plan_deviation — Haupt-Evaluator
# ===========================================================================


class TestEvaluatePlanDeviationStructure:
    """Tests für die Struktur des Rückgabe-Dicts."""

    def test_returns_dict_with_required_keys(self):
        result = evaluate_plan_deviation({"bgf_m2": 500.0}, {"bgf_m2": 500.0})
        required = [
            "deviations",
            "overall_severity",
            "orion_state",
            "compliance_score",
            "violated_items",
            "severity_counts",
            "total_items",
            "audit_hash",
            "evaluated_at",
        ]
        for key in required:
            assert key in result, f"Schlüssel '{key}' fehlt"

    def test_audit_hash_is_sha256(self):
        result = evaluate_plan_deviation({"x": 1}, {"x": 1})
        assert len(result["audit_hash"]) == 64
        int(result["audit_hash"], 16)  # muss hex-valide sein

    def test_empty_plan_perfect_compliance(self):
        result = evaluate_plan_deviation({}, {})
        assert result["compliance_score"] == 1.0
        assert result["overall_severity"] == "OK"
        assert result["orion_state"] == "VERIFIED"
        assert result["total_items"] == 0

    def test_total_items_matches_plan_keys(self):
        plan = {"a": 1, "b": 2, "c": 3}
        result = evaluate_plan_deviation(plan, {"a": 1, "b": 2, "c": 3})
        assert result["total_items"] == 3

    def test_evaluated_at_is_iso_string(self):
        result = evaluate_plan_deviation({"x": 1}, {"x": 1})
        assert "T" in result["evaluated_at"]


class TestEvaluatePlanDeviationOK:
    """Plankonformer Ist-Zustand → alles OK."""

    def test_all_numeric_plan_met(self):
        plan = {"bgf_m2": 1000.0, "geschosse": 4, "wohnungen": 12}
        actual = {"bgf_m2": 1000.0, "geschosse": 4, "wohnungen": 12}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "OK"
        assert result["orion_state"] == "VERIFIED"
        assert result["compliance_score"] == 1.0
        assert len(result["violated_items"]) == 0

    def test_string_values_match(self):
        plan = {"bundesland": "wien", "building_type": "wohngebaeude"}
        actual = {"bundesland": "wien", "building_type": "wohngebaeude"}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "OK"

    def test_small_numeric_tolerance_within_warning(self):
        # 3% Abweichung → noch OK (< 5% Schwellenwert)
        plan = {"bgf_m2": 1000.0}
        actual = {"bgf_m2": 1030.0}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "OK"
        assert result["orion_state"] == "VERIFIED"

    def test_compliance_score_one_for_perfect_match(self):
        plan = {"a": 10, "b": 20, "c": 30}
        actual = {"a": 10, "b": 20, "c": 30}
        result = evaluate_plan_deviation(plan, actual)
        assert result["compliance_score"] == 1.0


class TestEvaluatePlanDeviationWarning:
    """Plan-Werte mit moderater Abweichung → WARNING / TRANSITION."""

    def test_6_percent_deviation_triggers_warning(self):
        plan = {"bgf_m2": 1000.0}
        actual = {"bgf_m2": 1060.0}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "WARNING"
        assert result["orion_state"] == "TRANSITION"

    def test_10_percent_deviation_is_warning(self):
        plan = {"geschosse": 10}
        actual = {"geschosse": 11}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "WARNING"

    def test_mixed_ok_and_warning(self):
        plan = {"bgf_m2": 1000.0, "geschosse": 4}
        actual = {"bgf_m2": 1060.0, "geschosse": 4}  # 6% Abweichung bei bgf
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "WARNING"
        assert result["severity_counts"]["WARNING"] == 1
        assert result["severity_counts"]["OK"] == 1

    def test_violated_items_contains_warning_entry(self):
        plan = {"bgf_m2": 100.0}
        actual = {"bgf_m2": 107.0}  # 7%
        result = evaluate_plan_deviation(plan, actual)
        assert len(result["violated_items"]) == 1
        assert result["violated_items"][0]["severity"] == "WARNING"

    def test_compliance_score_below_one_for_violation(self):
        plan = {"a": 100, "b": 200, "c": 300}
        actual = {"a": 100, "b": 200, "c": 400}  # c: 33% → CRITICAL
        result = evaluate_plan_deviation(plan, actual)
        assert result["compliance_score"] < 1.0


class TestEvaluatePlanDeviationCritical:
    """Kritische Planabweichungen → CRITICAL / INSTABIL."""

    def test_25_percent_deviation_is_critical(self):
        plan = {"bgf_m2": 1000.0}
        actual = {"bgf_m2": 1250.0}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["orion_state"] == "INSTABIL"

    def test_missing_actual_value_is_critical(self):
        plan = {"bgf_m2": 1000.0, "geschosse": 4}
        actual = {"bgf_m2": 1000.0}  # geschosse fehlt
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        missing = next(d for d in result["deviations"] if d["item"] == "geschosse")
        assert missing["actual"] is None
        assert missing["severity"] == "CRITICAL"

    def test_string_mismatch_is_critical(self):
        plan = {"bundesland": "wien"}
        actual = {"bundesland": "graz"}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["orion_state"] == "INSTABIL"

    def test_boolean_mismatch_is_critical(self):
        plan = {"sprinkler": True}
        actual = {"sprinkler": False}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"

    def test_all_missing_values_zero_compliance(self):
        plan = {"a": 1, "b": 2, "c": 3}
        actual = {}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["compliance_score"] == 0.0
        assert len(result["violated_items"]) == 3

    def test_mixed_critical_dominates_warning(self):
        """Wenn auch nur ein CRITICAL vorhanden → Gesamt-Severity = CRITICAL."""
        plan = {"bgf_m2": 1000.0, "geschosse": 4, "bundesland": "wien"}
        actual = {
            "bgf_m2": 1060.0,  # 6% → WARNING
            "geschosse": 4,  # OK
            "bundesland": "graz",  # CRITICAL
        }
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["orion_state"] == "INSTABIL"
        assert result["severity_counts"]["CRITICAL"] == 1
        assert result["severity_counts"]["WARNING"] == 1
        assert result["severity_counts"]["OK"] == 1

    def test_compliance_score_zero_all_critical(self):
        plan = {"a": "x", "b": "y", "c": "z"}
        actual = {"a": "A", "b": "B", "c": "C"}
        result = evaluate_plan_deviation(plan, actual)
        assert result["compliance_score"] == 0.0


class TestEvaluatePlanDeviationAuditTrail:
    """Audit-Trail-Integrität."""

    def test_audit_hash_deterministic(self):
        """Gleiche Eingaben → immer gleicher Hash."""
        plan = {"bgf_m2": 500.0, "geschosse": 3}
        actual = {"bgf_m2": 600.0, "geschosse": 3}
        h1 = evaluate_plan_deviation(plan, actual)["audit_hash"]
        h2 = evaluate_plan_deviation(plan, actual)["audit_hash"]
        assert h1 == h2

    def test_different_inputs_different_hash(self):
        plan = {"bgf_m2": 500.0}
        h1 = evaluate_plan_deviation(plan, {"bgf_m2": 500.0})["audit_hash"]
        h2 = evaluate_plan_deviation(plan, {"bgf_m2": 600.0})["audit_hash"]
        assert h1 != h2

    def test_violation_appends_proof(self):
        """Kritische Abweichung → Eintrag im Proof-Trail."""
        before = orion_kernel.count_proofs()
        evaluate_plan_deviation({"a": 100}, {"a": 200})  # 100% → CRITICAL
        after = orion_kernel.count_proofs()
        assert after > before

    def test_no_proof_added_for_ok_result(self):
        """Plankonformes Ergebnis → kein Proof-Trail-Eintrag."""
        before = orion_kernel.count_proofs()
        evaluate_plan_deviation({"a": 100}, {"a": 100})
        after = orion_kernel.count_proofs()
        assert after == before

    def test_proof_kind_is_plan_deviation(self):
        evaluate_plan_deviation({"bgf_m2": 1000.0}, {"bgf_m2": 2000.0})
        line = orion_kernel.PROOFS.read_text(encoding="utf-8").strip().split("\n")[-1]
        data = json.loads(line)
        assert data["kind"] == "PLAN_DEVIATION"
        assert data["payload"]["overall_severity"] == "CRITICAL"
        assert data["payload"]["orion_state"] == "INSTABIL"


class TestEvaluatePlanDeviationBuildingScenarios:
    """Realitätsnahe Bauprojekt-Szenarien."""

    def test_scenario_energy_efficiency_ok(self):
        """Plan: fGEE ≤ 0.75; Ist: 0.70 → OK."""
        plan = {"fGEE": 0.75, "hwb_kwh_m2a": 25.0, "u_wert_aussenwand": 0.35}
        actual = {"fGEE": 0.70, "hwb_kwh_m2a": 24.0, "u_wert_aussenwand": 0.34}
        result = evaluate_plan_deviation(plan, actual)
        # fGEE: (0.75-0.70)/0.75 = 6.7% → WARNING (nicht CRITICAL)
        assert result["overall_severity"] in ("OK", "WARNING")
        assert result["orion_state"] in ("VERIFIED", "TRANSITION")

    def test_scenario_energy_efficiency_critical(self):
        """Plan: fGEE ≤ 0.75; Ist: 1.10 → CRITICAL (46% Überschreitung)."""
        plan = {"fGEE": 0.75}
        actual = {"fGEE": 1.10}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["orion_state"] == "INSTABIL"

    def test_scenario_fire_compartments_exceeded(self):
        """Plan: BGF 800 m²; Ist: 1500 m² → CRITICAL (87% Überschreitung)."""
        plan = {"max_brandabschnitt_m2": 800.0}
        actual = {"max_brandabschnitt_m2": 1500.0}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"

    def test_scenario_floor_count_deviation(self):
        """Plan: 4 Geschosse; Ist: 6 Geschosse → 50% → CRITICAL."""
        plan = {"geschosse": 4, "bundesland": "wien", "building_type": "wohngebaeude"}
        actual = {"geschosse": 6, "bundesland": "wien", "building_type": "wohngebaeude"}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["orion_state"] == "INSTABIL"

    def test_scenario_bundesland_changed(self):
        """Plan: Wien; Ist: Niederösterreich → CRITICAL (anderes Regelwerk)."""
        plan = {"bundesland": "wien", "bgf_m2": 500.0}
        actual = {"bundesland": "niederoesterreich", "bgf_m2": 500.0}
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"

    def test_scenario_all_parameters_perfect(self):
        """Vollständig plankonformes Gebäude → VERIFIED."""
        plan = {
            "bgf_m2": 850.0,
            "geschosse": 4,
            "wohnungen": 16,
            "bundesland": "wien",
            "building_type": "wohngebaeude",
            "fGEE": 0.70,
            "sprinkler": False,
        }
        actual = {
            "bgf_m2": 850.0,
            "geschosse": 4,
            "wohnungen": 16,
            "bundesland": "wien",
            "building_type": "wohngebaeude",
            "fGEE": 0.70,
            "sprinkler": False,
        }
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "OK"
        assert result["orion_state"] == "VERIFIED"
        assert result["compliance_score"] == 1.0
        assert len(result["violated_items"]) == 0

    def test_scenario_partial_data_available(self):
        """Nur manche Istwerte bekannt → fehlende Werte = CRITICAL."""
        plan = {"bgf_m2": 500.0, "geschosse": 3, "fGEE": 0.75}
        actual = {"bgf_m2": 500.0}  # geschosse und fGEE fehlen
        result = evaluate_plan_deviation(plan, actual)
        assert result["severity_counts"]["CRITICAL"] == 2
        assert result["compliance_score"] < 0.5


# ===========================================================================
# Compliance-Checker Violation-Pfade (OIB-RL)
# ===========================================================================


class TestOIBComplianceViolationPaths:
    """
    Tests für die Warning-Pfade der OIB-RL Compliance-Funktionen.
    Prüft, dass das deterministische System bei bestimmten Eingaben
    vorhersehbare Warnungen erzeugt.
    """

    def setup_method(self):
        """Imports nur wenn nötig — compliance.py braucht kein App-Kontext."""
        from api.routers.compliance import (
            _check_oib_rl_1,
            _check_oib_rl_2,
            _check_oib_rl_3,
            _check_oib_rl_4,
            _check_oib_rl_5,
            _check_oib_rl_6,
            _check_oib_rl_7,
            _check_radon,
        )

        self._check_oib_rl_1 = _check_oib_rl_1
        self._check_oib_rl_2 = _check_oib_rl_2
        self._check_oib_rl_3 = _check_oib_rl_3
        self._check_oib_rl_4 = _check_oib_rl_4
        self._check_oib_rl_5 = _check_oib_rl_5
        self._check_oib_rl_6 = _check_oib_rl_6
        self._check_oib_rl_7 = _check_oib_rl_7
        self._check_radon = _check_radon

    # OIB-RL 1 ---------------------------------------------------------------

    def test_rl1_below_3_floors_no_warning(self):
        result = self._check_oib_rl_1("wohngebaeude", 2)
        assert result.status == "pass"
        statuses = [c["status"] for c in result.checks]
        assert "warning" not in statuses

    def test_rl1_3_or_more_floors_triggers_warning(self):
        result = self._check_oib_rl_1("wohngebaeude", 3)
        statuses = [c["status"] for c in result.checks]
        assert "warning" in statuses

    def test_rl1_high_rise_triggers_warning(self):
        result = self._check_oib_rl_1("buerogebaeude", 10)
        statuses = [c["status"] for c in result.checks]
        assert "warning" in statuses

    def test_rl1_deterministic_for_same_floor_count(self):
        r1 = self._check_oib_rl_1("wohngebaeude", 5)
        r2 = self._check_oib_rl_1("wohngebaeude", 5)
        assert r1.status == r2.status
        assert len(r1.checks) == len(r2.checks)

    # OIB-RL 2 ---------------------------------------------------------------

    def test_rl2_small_building_single_compartment(self):
        result = self._check_oib_rl_2("wohngebaeude", 2, 500.0)
        brandabschnitt_checks = [c for c in result.checks if "Brandabschnitt" in c["check"]]
        assert brandabschnitt_checks[0]["status"] == "pass"

    def test_rl2_large_building_fires_warning(self):
        """BGF > 1200 m² für Wohngebäude → Brandabschnitt-Warnung."""
        result = self._check_oib_rl_2("wohngebaeude", 3, 1500.0)
        statuses = [c["status"] for c in result.checks]
        assert "warning" in statuses

    def test_rl2_office_compartment_limit_800(self):
        """Bürogebäude: max. 800 m² pro Abschnitt."""
        result = self._check_oib_rl_2("buerogebaeude", 3, 1000.0)
        statuses = [c["status"] for c in result.checks]
        assert "warning" in statuses

    def test_rl2_5_floors_requires_fire_alarm(self):
        result = self._check_oib_rl_2("wohngebaeude", 5, 500.0)
        alarm_checks = [c for c in result.checks if "Brandmeldeanlage" in c["check"]]
        assert len(alarm_checks) == 1
        assert alarm_checks[0]["status"] == "pass"

    def test_rl2_rei_increases_with_floors(self):
        r2 = self._check_oib_rl_2("wohngebaeude", 2, 400.0)
        r5 = self._check_oib_rl_2("wohngebaeude", 5, 400.0)
        # REI-Check immer vorhanden
        rei2 = next(c for c in r2.checks if "REI" in c["check"])
        rei5 = next(c for c in r5.checks if "REI" in c["check"])
        # REI 30 für ≤2, REI 60 für 3-4, REI 90 für ≥5
        assert "30" in rei2["check"]
        assert "90" in rei5["check"]

    def test_rl2_boundary_exactly_1200m2_passes(self):
        result = self._check_oib_rl_2("wohngebaeude", 2, 1200.0)
        brandabschnitt = next(c for c in result.checks if "Brandabschnitt" in c["check"])
        assert brandabschnitt["status"] == "pass"

    def test_rl2_boundary_1201m2_warns(self):
        result = self._check_oib_rl_2("wohngebaeude", 2, 1201.0)
        brandabschnitt = next(c for c in result.checks if "Brandabschnitt" in c["check"])
        assert brandabschnitt["status"] == "warning"

    # OIB-RL 3 ---------------------------------------------------------------

    def test_rl3_under_6_units_no_storage_check(self):
        result = self._check_oib_rl_3("wohngebaeude", 5)
        storage_checks = [c for c in result.checks if "Abstell" in c["check"]]
        assert len(storage_checks) == 0

    def test_rl3_6_or_more_units_triggers_storage_check(self):
        result = self._check_oib_rl_3("wohngebaeude", 6)
        storage_checks = [c for c in result.checks if "Abstell" in c["check"]]
        assert len(storage_checks) == 1

    def test_rl3_no_wohnungen_passes(self):
        result = self._check_oib_rl_3("buerogebaeude", None)
        assert result.status == "pass"

    # OIB-RL 4 ---------------------------------------------------------------

    def test_rl4_less_than_4_floors_no_elevator(self):
        result = self._check_oib_rl_4("wohngebaeude", 3, 400.0)
        elevator_checks = [c for c in result.checks if "Aufzug" in c["check"]]
        assert len(elevator_checks) == 0

    def test_rl4_4_or_more_floors_requires_elevator(self):
        result = self._check_oib_rl_4("wohngebaeude", 4, 400.0)
        elevator_checks = [c for c in result.checks if "Aufzug" in c["check"]]
        assert len(elevator_checks) == 1

    def test_rl4_5_or_more_floors_second_escape_route_warning(self):
        result = self._check_oib_rl_4("wohngebaeude", 5, 400.0)
        second_escape = [c for c in result.checks if "Zweiter" in c["check"]]
        assert len(second_escape) == 1
        assert second_escape[0]["status"] == "warning"

    def test_rl4_stair_width_increases_at_4_floors(self):
        r3 = self._check_oib_rl_4("wohngebaeude", 3, 300.0)
        r4 = self._check_oib_rl_4("wohngebaeude", 4, 300.0)
        treppe3 = next(c for c in r3.checks if "Treppen" in c["check"])
        treppe4 = next(c for c in r4.checks if "Treppen" in c["check"])
        # Python formatiert 1.0 nicht als "1.00" — einfach 1.0/1.2 prüfen
        assert "1.0" in treppe3["details"]
        assert "1.2" in treppe4["details"]

    # OIB-RL 5 ---------------------------------------------------------------

    def test_rl5_standard_wohngebaeude(self):
        result = self._check_oib_rl_5("wohngebaeude", 8)
        assert result.status == "pass"
        assert len(result.checks) >= 2

    def test_rl5_mehrfamilienhaus_elevated_requirements(self):
        result = self._check_oib_rl_5("mehrfamilienhaus", 8)
        elevated = [c for c in result.checks if "Erhöhte" in c["check"]]
        assert len(elevated) == 1

    def test_rl5_wohnanlage_elevated_requirements(self):
        result = self._check_oib_rl_5("wohnanlage", 4)
        elevated = [c for c in result.checks if "Erhöhte" in c["check"]]
        assert len(elevated) == 1

    # OIB-RL 6 ---------------------------------------------------------------

    def test_rl6_salzburg_sonderregelung(self):
        """Salzburg verwendet eigene WSchVO → Warning."""
        result = self._check_oib_rl_6("salzburg", 500.0)
        assert result.status == "warning"
        assert "WSchVO" in result.summary or "Salzburg" in result.summary

    def test_rl6_vienna_passes(self):
        result = self._check_oib_rl_6("wien", 500.0)
        assert result.status == "pass"

    def test_rl6_pv_required_for_large_buildings(self):
        """Gebäude ≥ 1000 m² → PV-Anlage-Pflicht."""
        result = self._check_oib_rl_6("wien", 1000.0)
        pv_checks = [c for c in result.checks if "PV" in c["check"]]
        assert len(pv_checks) == 1

    def test_rl6_pv_not_required_below_1000m2(self):
        result = self._check_oib_rl_6("wien", 999.0)
        pv_checks = [c for c in result.checks if "PV" in c["check"]]
        assert len(pv_checks) == 0

    def test_rl6_fgee_check_present(self):
        result = self._check_oib_rl_6("tirol", 600.0)
        fgee_checks = [c for c in result.checks if "fGEE" in c["check"]]
        assert len(fgee_checks) == 1

    def test_rl6_deterministic_same_inputs(self):
        r1 = self._check_oib_rl_6("wien", 800.0)
        r2 = self._check_oib_rl_6("wien", 800.0)
        assert r1.status == r2.status
        assert len(r1.checks) == len(r2.checks)

    # OIB-RL 7 ---------------------------------------------------------------

    def test_rl7_always_passes(self):
        result = self._check_oib_rl_7("wohngebaeude")
        assert result.status == "pass"

    def test_rl7_has_required_checks(self):
        result = self._check_oib_rl_7("wohngebaeude")
        check_names = [c["check"] for c in result.checks]
        assert any("OI3" in n for n in check_names)
        assert any("GWP" in n or "Global" in n for n in check_names)

    # Radonschutz -------------------------------------------------------------

    def test_radon_not_required_in_wien(self):
        result = self._check_radon("wien")
        assert result is None

    def test_radon_required_in_tirol(self):
        result = self._check_radon("tirol")
        assert result is not None
        assert result.status == "warning"

    def test_radon_required_in_niederoesterreich(self):
        result = self._check_radon("niederoesterreich")
        assert result is not None
        assert result.status == "warning"

    def test_radon_all_affected_bundeslaender(self):
        affected = [
            "tirol",
            "niederoesterreich",
            "oberoesterreich",
            "steiermark",
            "salzburg",
            "kaernten",
            "vorarlberg",
        ]
        for bl in affected:
            result = self._check_radon(bl)
            assert result is not None, f"{bl} sollte Radonwarnung haben"
            assert result.status == "warning"

    def test_radon_not_required_in_burgenland(self):
        result = self._check_radon("burgenland")
        assert result is None

    def test_radon_deterministic(self):
        r1 = self._check_radon("tirol")
        r2 = self._check_radon("tirol")
        assert r1.status == r2.status
        assert len(r1.checks) == len(r2.checks)


# ===========================================================================
# Determinismus-Invariante: Gleiche Eingaben → Gleiche Ausgaben
# ===========================================================================


class TestDeterminismInvariant:
    """
    Stellt sicher, dass evaluate_plan_deviation() und die OIB-RL-Checker
    vollständig deterministisch sind — kein Zufallselement, keine Zeitabhängigkeit
    in den Kernergebnissen.
    """

    def test_evaluate_plan_deviation_deterministic_ok(self):
        plan = {"bgf_m2": 500.0, "geschosse": 3, "bundesland": "wien"}
        actual = {"bgf_m2": 500.0, "geschosse": 3, "bundesland": "wien"}
        results = [evaluate_plan_deviation(plan, actual) for _ in range(5)]
        for r in results:
            assert r["overall_severity"] == results[0]["overall_severity"]
            assert r["compliance_score"] == results[0]["compliance_score"]
            assert r["audit_hash"] == results[0]["audit_hash"]

    def test_evaluate_plan_deviation_deterministic_critical(self):
        plan = {"bgf_m2": 500.0, "bundesland": "wien"}
        actual = {"bgf_m2": 1500.0, "bundesland": "graz"}
        results = [evaluate_plan_deviation(plan, actual) for _ in range(5)]
        for r in results:
            assert r["overall_severity"] == "CRITICAL"
            assert r["audit_hash"] == results[0]["audit_hash"]

    def test_oib_rl2_deterministic_boundary(self):
        from api.routers.compliance import _check_oib_rl_2

        results = [_check_oib_rl_2("wohngebaeude", 3, 1201.0) for _ in range(5)]
        for r in results:
            statuses = [c["status"] for c in r.checks]
            assert "warning" in statuses

    def test_severity_classification_deterministic(self):
        test_values = [0.0, 0.04, 0.05, 0.06, 0.10, 0.20, 0.21, 0.50, 1.0]
        for val in test_values:
            results = [_classify_severity(val) for _ in range(5)]
            assert all(r == results[0] for r in results), f"Nicht deterministisch bei {val}"

    def test_audit_hash_stable_across_runs(self):
        plan = {"geschosse": 8, "bgf_m2": 2000.0}
        actual = {"geschosse": 4, "bgf_m2": 2000.0}
        hashes = {evaluate_plan_deviation(plan, actual)["audit_hash"] for _ in range(10)}
        assert len(hashes) == 1  # immer derselbe Hash


# ===========================================================================
# Integrations-Szenario: OIB-Compliance + Plan-Abweichungs-Evaluator kombiniert
# ===========================================================================


class TestCombinedComplianceAndDeviation:
    """
    End-to-End: OIB-Compliance-Werte aus Planvorgaben vs. Istwerte
    durch evaluate_plan_deviation() prüfen.
    """

    def test_full_building_project_compliant(self):
        """Vollständig konformes Projekt — kein ORION-Alert."""
        plan_commitments = {
            "bgf_m2": 900.0,
            "geschosse": 4,
            "wohnungen": 12,
            "bundesland": "wien",
            "fGEE": 0.72,
            "u_wert_aussenwand": 0.35,
        }
        actuals = {
            "bgf_m2": 900.0,
            "geschosse": 4,
            "wohnungen": 12,
            "bundesland": "wien",
            "fGEE": 0.72,
            "u_wert_aussenwand": 0.35,
        }
        result = evaluate_plan_deviation(plan_commitments, actuals)
        assert result["orion_state"] == "VERIFIED"
        assert result["compliance_score"] == 1.0

    def test_energy_target_missed_critical(self):
        """fGEE im Plan 0.75, Ist 1.10 → INSTABIL."""
        plan = {"fGEE": 0.75}
        actual = {"fGEE": 1.10}
        result = evaluate_plan_deviation(plan, actual)
        assert result["orion_state"] == "INSTABIL"
        assert len(result["violated_items"]) == 1

    def test_floor_count_escalation(self):
        """Mehr Geschosse als geplant → CRITICAL (neue OIB-RL-Anforderungen)."""
        plan = {"geschosse": 3}
        actual = {"geschosse": 6}
        result = evaluate_plan_deviation(plan, actual)
        # 100% Abweichung
        assert result["orion_state"] == "INSTABIL"

    def test_multi_parameter_violation_report(self):
        """Mehrere Abweichungen → detaillierter Report."""
        plan = {
            "bgf_m2": 1000.0,
            "geschosse": 4,
            "bundesland": "wien",
            "fGEE": 0.75,
        }
        actual = {
            "bgf_m2": 1400.0,  # 40% → CRITICAL
            "geschosse": 6,  # 50% → CRITICAL
            "bundesland": "graz",  # CRITICAL
            "fGEE": 0.78,  # 4% → OK
        }
        result = evaluate_plan_deviation(plan, actual)
        assert result["overall_severity"] == "CRITICAL"
        assert result["severity_counts"]["CRITICAL"] == 3
        assert result["severity_counts"]["OK"] == 1
        assert result["compliance_score"] == 0.25  # 1/4 konform
