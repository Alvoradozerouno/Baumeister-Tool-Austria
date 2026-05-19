"""
Gemeinsame pytest-Fixtures für das Baumeister-Tool-Austria Test-Suite.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import orion_kernel


@pytest.fixture(autouse=True)
def isolated_tmpdir(tmp_path, monkeypatch):
    """
    Isoliert jeden Test in einem eigenen temporären Verzeichnis.

    Verhindert, dass ORION_STATE.json, PROOFS.jsonl und PROOF_MANIFEST.json
    zwischen Tests geteilt werden — alle Kernel-Operationen sind damit
    vollständig voneinander unabhängig.
    """
    monkeypatch.setattr(orion_kernel, "ROOT", tmp_path)
    monkeypatch.setattr(orion_kernel, "STATE", tmp_path / "ORION_STATE.json")
    monkeypatch.setattr(orion_kernel, "PROOFS", tmp_path / "PROOFS.jsonl")
    monkeypatch.setattr(orion_kernel, "MANIFEST", tmp_path / "PROOF_MANIFEST.json")
    yield tmp_path
