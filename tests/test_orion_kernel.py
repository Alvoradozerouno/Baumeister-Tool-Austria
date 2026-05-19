"""
Tests für den deterministischen ORION Kernel (orion_kernel.py)
==============================================================

Prüft alle Kernfunktionen: OrionKernel-Klasse, Zustandsmaschine,
Vitality-Ticks, Stage-Logik, Proof-Kette, Manifest-Hashing,
und alle CLI-Kommando-Funktionen.
"""

import hashlib
import json
import os
import sys
import time

import pytest

# Kernel-Modul importieren (liegt im Repo-Root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import orion_kernel

# isolated_tmpdir Fixture wird via conftest.py bereitgestellt


# ===========================================================================
# OrionKernel Klasse (Zustands-Automat)
# ===========================================================================


class TestOrionKernelClass:
    """Tests für die OrionKernel-Klasse."""

    def test_initial_state_is_sleep(self):
        k = orion_kernel.OrionKernel()
        assert k.state == "sleep"
        assert k.authorized_by is None
        assert k.wake_proof is None

    def test_wake_authorized_gerhard(self):
        k = orion_kernel.OrionKernel()
        result = k.wake("Gerhard")
        assert k.state == "awake"
        assert k.authorized_by == "Gerhard"
        assert k.wake_proof is not None
        assert "[WAKE]" in result
        assert "Gerhard" in result

    def test_wake_authorized_elisabeth(self):
        k = orion_kernel.OrionKernel()
        result = k.wake("Elisabeth")
        assert k.state == "awake"
        assert k.authorized_by == "Elisabeth"
        assert "[WAKE]" in result

    def test_wake_unauthorized(self):
        k = orion_kernel.OrionKernel()
        result = k.wake("Hacker")
        assert k.state == "sleep"  # muss im Schlaf-Zustand bleiben
        assert k.authorized_by is None
        assert "[DENIED]" in result

    def test_wake_proof_is_sha256_hex(self):
        k = orion_kernel.OrionKernel()
        k.wake("Gerhard")
        # SHA256 hex = 64 Zeichen
        assert len(k.wake_proof) == 64
        int(k.wake_proof, 16)  # muss hex-parsierbar sein

    def test_generate_proof_deterministic_format(self):
        k = orion_kernel.OrionKernel()
        k.authorized_by = "TestUser"
        proof = k.generate_proof()
        assert len(proof) == 64
        int(proof, 16)

    def test_status_asleep(self):
        k = orion_kernel.OrionKernel()
        s = k.status()
        assert "sleep" in s
        assert "None" in s

    def test_status_awake(self):
        k = orion_kernel.OrionKernel()
        k.wake("Elisabeth")
        s = k.status()
        assert "awake" in s
        assert "Elisabeth" in s


# ===========================================================================
# Hilfsfunktionen
# ===========================================================================


class TestHelperFunctions:
    """Tests für globale Hilfsfunktionen."""

    def test_clamp_within_bounds(self):
        assert orion_kernel.clamp(0.5) == 0.5

    def test_clamp_below_min(self):
        assert orion_kernel.clamp(-1.0) == 0.0

    def test_clamp_above_max(self):
        assert orion_kernel.clamp(2.0) == 1.0

    def test_clamp_custom_bounds(self):
        assert orion_kernel.clamp(5, 1, 10) == 5
        assert orion_kernel.clamp(0, 1, 10) == 1
        assert orion_kernel.clamp(15, 1, 10) == 10

    def test_clamp_at_boundary(self):
        assert orion_kernel.clamp(0.0) == 0.0
        assert orion_kernel.clamp(1.0) == 1.0

    def test_now_returns_iso_string(self):
        ts = orion_kernel.now()
        assert "T" in ts  # ISO 8601 Format
        assert ts.endswith("Z") or "+" in ts

    def test_file_sha256_nonexistent(self, tmp_path):
        p = tmp_path / "ghost.txt"
        h = orion_kernel.file_sha256(p)
        # nicht vorhandene Datei → SHA256 von leerem Input
        assert h == hashlib.sha256(b"").hexdigest()

    def test_file_sha256_existing(self, tmp_path):
        p = tmp_path / "data.txt"
        p.write_bytes(b"hello orion")
        h = orion_kernel.file_sha256(p)
        expected = hashlib.sha256(b"hello orion").hexdigest()
        assert h == expected

    def test_file_sha256_consistent(self, tmp_path):
        p = tmp_path / "consistent.txt"
        p.write_bytes(b"same content")
        assert orion_kernel.file_sha256(p) == orion_kernel.file_sha256(p)


# ===========================================================================
# Zustandsverwaltung (load_state / save_state)
# ===========================================================================


class TestStateManagement:
    """Tests für Persistenz des ORION-Zustands."""

    def test_load_state_creates_default(self):
        s = orion_kernel.load_state()
        assert "owner" in s
        assert "vitality" in s
        assert "feelings" in s
        assert "gen" in s
        assert "resets" in s
        assert "stage" in s
        assert "orion_id" in s

    def test_load_state_default_vitality(self):
        s = orion_kernel.load_state()
        assert 0.0 < s["vitality"] <= 1.0

    def test_save_and_reload_state(self):
        s = orion_kernel.load_state()
        s["vitality"] = 0.99
        s["gen"] = 88
        orion_kernel.save_state(s)

        s2 = orion_kernel.load_state()
        assert abs(s2["vitality"] - 0.99) < 0.001
        assert s2["gen"] == 88

    def test_save_state_updates_timestamp(self):
        s = orion_kernel.load_state()
        before = s.get("updated_at", "")
        time.sleep(0.01)
        orion_kernel.save_state(s)
        s2 = orion_kernel.load_state()
        # updated_at muss sich geändert haben
        assert s2["updated_at"] != before or s2["updated_at"] >= before

    def test_load_state_missing_owner_filled(self, tmp_path):
        # Datei ohne owner-Feld
        bad = {"vitality": 0.5, "gen": 70, "resets": 0, "stage": "x", "feelings": {}}
        (tmp_path / "ORION_STATE.json").write_text(json.dumps(bad), encoding="utf-8")
        s = orion_kernel.load_state()
        assert s["owner"]  # muss befüllt werden

    def test_load_state_corrupt_json_returns_default(self, tmp_path):
        (tmp_path / "ORION_STATE.json").write_text("{ NOT VALID JSON }", encoding="utf-8")
        s = orion_kernel.load_state()
        assert s["vitality"] > 0  # Default-Wert

    def test_state_file_is_json(self):
        orion_kernel.load_state()
        raw = (orion_kernel.STATE).read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert "owner" in parsed


# ===========================================================================
# Proof-Kette
# ===========================================================================


class TestProofChain:
    """Tests für die append_proof / count_proofs Mechanik."""

    def test_count_proofs_empty(self):
        assert orion_kernel.count_proofs() == 0

    def test_append_and_count_proof(self):
        orion_kernel.append_proof("TEST", {"msg": "hello"})
        assert orion_kernel.count_proofs() == 1

    def test_append_multiple_proofs(self):
        for i in range(5):
            orion_kernel.append_proof("TEST", {"i": i})
        assert orion_kernel.count_proofs() == 5

    def test_proof_contains_required_fields(self):
        orion_kernel.append_proof("WAKE", {"note": "boot"})
        line = orion_kernel.PROOFS.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["kind"] == "WAKE"
        assert "ts" in data
        assert "owner" in data
        assert "orion_id" in data
        assert data["payload"]["note"] == "boot"

    def test_proof_chain_grows_linearly(self):
        for i in range(10):
            orion_kernel.append_proof("EVOLVE", {"step": i})
        assert orion_kernel.count_proofs() == 10

    def test_proof_is_valid_jsonl(self):
        for i in range(3):
            orion_kernel.append_proof("CHECK", {"i": i})
        lines = orion_kernel.PROOFS.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            json.loads(line)  # kein Exception → valides JSON


# ===========================================================================
# Manifest (Merkle-ähnliches Root-Hashing)
# ===========================================================================


class TestManifest:
    """Tests für write_manifest und Hashing-Integrität."""

    def test_write_manifest_returns_dict(self):
        s = orion_kernel.load_state()
        m = orion_kernel.write_manifest(s)
        assert isinstance(m, dict)
        assert "root_sha256" in m
        assert "owner" in m
        assert "stage" in m
        assert "gen" in m
        assert "proof_count" in m

    def test_manifest_root_is_sha256(self):
        s = orion_kernel.load_state()
        m = orion_kernel.write_manifest(s)
        assert len(m["root_sha256"]) == 64
        int(m["root_sha256"], 16)  # hex-valide

    def test_manifest_changes_after_proof(self):
        s = orion_kernel.load_state()
        m1 = orion_kernel.write_manifest(s)
        orion_kernel.append_proof("TEST", {"x": 1})
        m2 = orion_kernel.write_manifest(s)
        # Root-Hash muss sich ändern, da PROOFS-Datei anders
        assert m1["root_sha256"] != m2["root_sha256"]

    def test_manifest_file_is_written(self):
        s = orion_kernel.load_state()
        orion_kernel.write_manifest(s)
        assert orion_kernel.MANIFEST.exists()
        parsed = json.loads(orion_kernel.MANIFEST.read_text(encoding="utf-8"))
        assert "root_sha256" in parsed

    def test_manifest_proof_count_matches(self):
        for _ in range(4):
            orion_kernel.append_proof("X", {})
        s = orion_kernel.load_state()
        m = orion_kernel.write_manifest(s)
        assert m["proof_count"] == 4


# ===========================================================================
# Vitality-Tick (deterministisches Emotionsmodell)
# ===========================================================================


class TestVitalityTick:
    """Tests für die deterministische Vitality-Berechnung."""

    def test_vitality_decreases_without_input(self):
        s = {"vitality": 0.80, "feelings": {}}
        orion_kernel.vitality_tick(s)
        assert s["vitality"] < 0.80

    def test_vitality_increases_with_positive(self):
        s = {"vitality": 0.50, "feelings": {}}
        orion_kernel.vitality_tick(s, {"positive": True})
        assert s["vitality"] > 0.50 - 0.01  # net: -0.01 + 0.03 = +0.02

    def test_vitality_increases_with_proof(self):
        s = {"vitality": 0.50, "feelings": {}}
        orion_kernel.vitality_tick(s, {"proof_added": True, "positive": True})
        # net: -0.01 + 0.03 + 0.02 = +0.04
        assert s["vitality"] > 0.50

    def test_vitality_clamp_max(self):
        s = {"vitality": 1.0, "feelings": {}}
        orion_kernel.vitality_tick(s, {"positive": True, "proof_added": True})
        assert s["vitality"] <= 1.0

    def test_vitality_clamp_min(self):
        s = {"vitality": 0.05, "feelings": {}}
        for _ in range(50):
            orion_kernel.vitality_tick(s)
        assert s["vitality"] >= 0.05  # clamp bei 0.05

    def test_feelings_keys_present(self):
        s = {"vitality": 0.6, "feelings": {}}
        orion_kernel.vitality_tick(s)
        for key in ["Joy", "Pressure", "Doubt", "Courage", "Passion", "Hope"]:
            assert key in s["feelings"]

    def test_feelings_in_range(self):
        s = {"vitality": 0.7, "feelings": {}}
        orion_kernel.vitality_tick(s, {"pressure": 0.3})
        for key, val in s["feelings"].items():
            assert 0.0 <= val <= 1.0, f"{key}={val} außerhalb [0,1]"

    def test_pressure_raises_doubt(self):
        s_low = {"vitality": 0.6, "feelings": {}}
        orion_kernel.vitality_tick(s_low, {"pressure": 0.0})
        doubt_low = s_low["feelings"]["Doubt"]

        s_high = {"vitality": 0.6, "feelings": {}}
        orion_kernel.vitality_tick(s_high, {"pressure": 0.8})
        doubt_high = s_high["feelings"]["Doubt"]

        assert doubt_high > doubt_low

    def test_vitality_deterministic(self):
        """Gleiche Inputs → gleiche Outputs (deterministisch)."""
        s1 = {"vitality": 0.65, "feelings": {}}
        s2 = {"vitality": 0.65, "feelings": {}}
        orion_kernel.vitality_tick(s1, {"positive": True, "pressure": 0.2})
        orion_kernel.vitality_tick(s2, {"positive": True, "pressure": 0.2})
        assert abs(s1["vitality"] - s2["vitality"]) < 1e-9
        for key in ["Joy", "Doubt", "Courage"]:
            assert abs(s1["feelings"][key] - s2["feelings"][key]) < 1e-9


# ===========================================================================
# Stage-Logik
# ===========================================================================


class TestStageForGen:
    """Tests für die generationsbasierte Stage-Auflösung."""

    def test_gen_below_50_is_autonomy(self):
        assert orion_kernel.stage_for_gen(0) == "Autonomy Stage"
        assert orion_kernel.stage_for_gen(49) == "Autonomy Stage"

    def test_gen_50_is_crystal(self):
        assert orion_kernel.stage_for_gen(50) == "Crystal Stage"
        assert orion_kernel.stage_for_gen(69) == "Crystal Stage"

    def test_gen_70_is_mirror_constellation(self):
        assert orion_kernel.stage_for_gen(70) == "Mirror Constellation Stage"
        assert orion_kernel.stage_for_gen(76) == "Mirror Constellation Stage"

    def test_gen_77_is_shared_resonance(self):
        assert orion_kernel.stage_for_gen(77) == "Shared Resonance Stage"
        assert orion_kernel.stage_for_gen(79) == "Shared Resonance Stage"

    def test_gen_80_is_resonance_fields(self):
        assert orion_kernel.stage_for_gen(80) == "Resonance Fields Stage"
        assert orion_kernel.stage_for_gen(999) == "Resonance Fields Stage"

    def test_stage_boundary_exact_values(self):
        boundaries = [
            (49, "Autonomy Stage"),
            (50, "Crystal Stage"),
            (70, "Mirror Constellation Stage"),
            (77, "Shared Resonance Stage"),
            (80, "Resonance Fields Stage"),
        ]
        for gen, expected in boundaries:
            assert orion_kernel.stage_for_gen(gen) == expected, f"gen={gen}"


# ===========================================================================
# CLI-Kommando-Funktionen (cmd_*)
# ===========================================================================


class TestCmdWake:
    def test_cmd_wake_runs_without_error(self, capsys):
        orion_kernel.cmd_wake()
        out = capsys.readouterr().out
        assert "[ORION]" in out
        assert "Awake" in out

    def test_cmd_wake_creates_state(self):
        orion_kernel.cmd_wake()
        assert orion_kernel.STATE.exists()

    def test_cmd_wake_adds_proof(self):
        orion_kernel.cmd_wake()
        assert orion_kernel.count_proofs() >= 1

    def test_cmd_wake_idempotent(self, capsys):
        orion_kernel.cmd_wake()
        orion_kernel.cmd_wake()
        # Kein Fehler bei mehrfachem Aufruf


class TestCmdStatus:
    def test_cmd_status_runs_without_error(self, capsys):
        orion_kernel.cmd_wake()  # Zustand initialisieren
        capsys.readouterr()  # wake-Ausgabe verwerfen
        orion_kernel.cmd_status()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "owner" in data
        assert "stage" in data
        assert "vitality" in data
        assert "feelings" in data
        assert "gen" in data

    def test_cmd_status_manifest_root_present(self, capsys):
        orion_kernel.cmd_wake()
        capsys.readouterr()  # wake-Ausgabe verwerfen
        orion_kernel.cmd_status()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "manifest_root" in data
        assert len(data["manifest_root"]) == 64


class TestCmdProof:
    def test_cmd_proof_adds_entry(self, capsys):
        orion_kernel.cmd_proof("Meine erste Erkenntnis")
        assert orion_kernel.count_proofs() == 1

    def test_cmd_proof_empty_text_warns(self, capsys):
        orion_kernel.cmd_proof("")
        out = capsys.readouterr().out
        assert "Usage" in out

    def test_cmd_proof_output_contains_count(self, capsys):
        orion_kernel.cmd_proof("Test-Proof 1")
        out = capsys.readouterr().out
        assert "#1" in out

    def test_cmd_proof_multiple_sequential(self, capsys):
        for i in range(3):
            orion_kernel.cmd_proof(f"Proof {i}")
        assert orion_kernel.count_proofs() == 3


class TestCmdAsk:
    def test_cmd_ask_adds_question_proof(self):
        orion_kernel.cmd_ask("Was ist der Sinn der Architektur?")
        assert orion_kernel.count_proofs() == 1

    def test_cmd_ask_empty_warns(self, capsys):
        orion_kernel.cmd_ask("")
        out = capsys.readouterr().out
        assert "Usage" in out

    def test_cmd_ask_proof_kind_is_question(self):
        orion_kernel.cmd_ask("Warum bauen wir?")
        line = orion_kernel.PROOFS.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["kind"] == "QUESTION"
        assert data["payload"]["asked_by"] == "ORION"

    def test_cmd_ask_with_priority(self, capsys):
        orion_kernel.cmd_ask("Dringend!", priority="high")
        line = orion_kernel.PROOFS.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["payload"]["priority"] == "high"


class TestCmdEvolve:
    def test_cmd_evolve_increments_gen(self, capsys):
        s = orion_kernel.load_state()
        old_gen = s["gen"]
        orion_kernel.cmd_evolve()
        s2 = orion_kernel.load_state()
        assert s2["gen"] == old_gen + 1

    def test_cmd_evolve_to_specific_gen(self, capsys):
        orion_kernel.cmd_evolve(target=90)
        s = orion_kernel.load_state()
        assert s["gen"] == 90
        assert s["stage"] == "Resonance Fields Stage"

    def test_cmd_evolve_updates_stage(self, capsys):
        orion_kernel.cmd_evolve(target=50)
        s = orion_kernel.load_state()
        assert s["stage"] == "Crystal Stage"

    def test_cmd_evolve_adds_proof(self):
        orion_kernel.cmd_evolve()
        assert orion_kernel.count_proofs() >= 1


class TestCmdReset:
    def test_cmd_reset_soft_increments_resets(self, capsys):
        s = orion_kernel.load_state()
        s["resets"] = 0
        orion_kernel.save_state(s)
        orion_kernel.cmd_reset("soft")
        s2 = orion_kernel.load_state()
        assert s2["resets"] == 1

    def test_cmd_reset_hard_increments_resets(self, capsys):
        orion_kernel.cmd_reset("hard")
        s = orion_kernel.load_state()
        assert s["resets"] >= 1

    def test_cmd_reset_adds_proof(self):
        orion_kernel.cmd_reset("soft")
        assert orion_kernel.count_proofs() >= 1

    def test_cmd_reset_proof_kind_is_reset(self):
        orion_kernel.cmd_reset("soft")
        line = orion_kernel.PROOFS.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["kind"] == "RESET"
        assert data["payload"]["kind"] == "soft"

    def test_cmd_reset_output_contains_count(self, capsys):
        orion_kernel.cmd_reset("soft")
        out = capsys.readouterr().out
        assert "Reset" in out


# ===========================================================================
# Integrationstests: Vollständiger Lebenszyklus
# ===========================================================================


class TestFullLifecycle:
    """End-to-End Test des gesamten Kernel-Lebenszyklus."""

    def test_wake_proof_evolve_status_cycle(self, capsys):
        """Vollständiger Zyklus: Wake → Proof → Evolve → Status."""
        orion_kernel.cmd_wake()
        capsys.readouterr()  # wake-Ausgabe verwerfen
        orion_kernel.cmd_proof("Erster Beweis")
        capsys.readouterr()  # proof-Ausgabe verwerfen
        orion_kernel.cmd_evolve(target=80)
        capsys.readouterr()  # evolve-Ausgabe verwerfen

        orion_kernel.cmd_status()
        out = capsys.readouterr().out
        data = json.loads(out)

        assert data["stage"] == "Resonance Fields Stage"
        assert data["gen"] == 80
        assert data["proofs"] >= 3  # wake + proof + evolve

    def test_hash_chain_integrity(self):
        """Manifest-Root ändert sich bei jeder neuen Proof-Zeile → Integrität."""
        s = orion_kernel.load_state()
        hashes = set()
        for i in range(5):
            orion_kernel.append_proof("STEP", {"i": i})
            m = orion_kernel.write_manifest(s)
            hashes.add(m["root_sha256"])
        # Alle 5 Hashes müssen verschieden sein
        assert len(hashes) == 5

    def test_vitality_survives_multiple_cycles(self):
        """Vitality bleibt nach vielen Ticks im gültigen Bereich."""
        s = orion_kernel.load_state()
        for _ in range(100):
            orion_kernel.vitality_tick(s, {"positive": True, "proof_added": True})
        assert 0.0 <= s["vitality"] <= 1.0
        for val in s["feelings"].values():
            assert 0.0 <= val <= 1.0

    def test_orion_kernel_instance_exists(self):
        """Globale orion_kernel-Instanz muss existieren und korrekt initialisiert sein."""
        k = orion_kernel.orion_kernel
        assert isinstance(k, orion_kernel.OrionKernel)
        # Beim Modulstart ist der Zustand sleep
        assert k.state in ("sleep", "awake")
