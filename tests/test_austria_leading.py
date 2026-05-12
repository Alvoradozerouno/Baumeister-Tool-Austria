"""
Austria-leading Feature Tests
==============================

Tests for the Austria-first features:
- All 9 Bundesländer coverage in /api/v1/bundesland
- Bundesland comparison endpoint
- Förderungen per Bundesland
- Austrian data sources (OIB-RL, Baupreisindex, Kostenrichtwerte, Materialien)
- Project workspace (CRUD, compliance summary)
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)

ALL_BUNDESLAENDER = [
    "burgenland",
    "kaernten",
    "niederoesterreich",
    "oberoesterreich",
    "salzburg",
    "steiermark",
    "tirol",
    "vorarlberg",
    "wien",
]


# ---------------------------------------------------------------------------
# Bundesland Router — all 9 Bundesländer
# ---------------------------------------------------------------------------


class TestBundeslandList:
    def test_list_returns_all_nine(self):
        r = client.get("/api/v1/bundesland/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 9
        kuerzel = {bl["kuerzel"] for bl in data}
        assert kuerzel == {"B", "K", "NÖ", "OÖ", "S", "ST", "T", "V", "W"}

    def test_list_items_have_required_fields(self):
        r = client.get("/api/v1/bundesland/")
        assert r.status_code == 200
        for bl in r.json():
            assert "kuerzel" in bl
            assert "name" in bl
            assert "bauordnung_kurz" in bl
            assert "oib_2023_status" in bl
            assert "digitale_einreichung" in bl


class TestBundeslandDetail:
    @pytest.mark.parametrize("bundesland", ALL_BUNDESLAENDER)
    def test_all_bundeslaender_return_200(self, bundesland):
        r = client.get(f"/api/v1/bundesland/{bundesland}")
        assert r.status_code == 200, f"{bundesland} returned {r.status_code}"

    @pytest.mark.parametrize("bundesland", ALL_BUNDESLAENDER)
    def test_all_bundeslaender_have_complete_fields(self, bundesland):
        r = client.get(f"/api/v1/bundesland/{bundesland}")
        data = r.json()
        required = [
            "name", "kuerzel", "bauordnung", "bauordnung_kurz", "raumordnung",
            "oib_2023_status", "stellplatz_factor", "aufzug_ab_geschoss",
            "schneelastzone", "erdbebenzone", "windzone", "digitale_einreichung",
            "kontakt", "besonderheiten", "regionale_kostenfaktor",
        ]
        for field in required:
            assert field in data, f"{bundesland} missing field '{field}'"

    def test_salzburg_oib_rl6_sonderweg_flagged(self):
        r = client.get("/api/v1/bundesland/salzburg")
        data = r.json()
        assert "NICHT" in data["oib_2023_status"] or "Sonderweg" in data["oib_2023_status"]

    def test_wien_aufzug_ab_3_geschoss(self):
        r = client.get("/api/v1/bundesland/wien")
        data = r.json()
        assert data["aufzug_ab_geschoss"] == 3

    def test_unknown_bundesland_returns_404(self):
        r = client.get("/api/v1/bundesland/testland")
        assert r.status_code == 404

    def test_case_insensitive_lookup(self):
        r = client.get("/api/v1/bundesland/Wien")
        assert r.status_code == 200
        assert r.json()["name"] == "Wien"


class TestBundeslandStellplaetze:
    def test_wien_stellplaetze(self):
        r = client.get("/api/v1/bundesland/wien/stellplaetze?wohnungen=10")
        assert r.status_code == 200
        data = r.json()
        assert data["stellplatz_faktor"] == 1.2
        assert data["erforderliche_stellplaetze"] == 12

    def test_tirol_higher_factor(self):
        r = client.get("/api/v1/bundesland/tirol/stellplaetze?wohnungen=10")
        assert r.status_code == 200
        data = r.json()
        assert data["stellplatz_faktor"] == 1.5
        assert data["erforderliche_stellplaetze"] == 15


class TestBundeslandAufzug:
    def test_wien_aufzug_ab_3(self):
        r = client.get("/api/v1/bundesland/wien/aufzug?geschosse=3")
        assert r.status_code == 200
        data = r.json()
        assert data["aufzug_erforderlich"] is True
        assert data["aufzugspflicht_ab_geschoss"] == 3

    def test_tirol_aufzug_ab_4(self):
        r = client.get("/api/v1/bundesland/tirol/aufzug?geschosse=3")
        assert r.status_code == 200
        data = r.json()
        assert data["aufzug_erforderlich"] is False


class TestBundeslandVergleich:
    def test_compare_two_bundeslaender(self):
        r = client.get("/api/v1/bundesland/compare?bundeslaender=wien&bundeslaender=tirol")
        assert r.status_code == 200
        data = r.json()
        assert "wien" in data["daten"]
        assert "tirol" in data["daten"]
        assert len(data["verglichen"]) == 2

    def test_compare_three_bundeslaender(self):
        r = client.get(
            "/api/v1/bundesland/compare?bundeslaender=wien&bundeslaender=salzburg&bundeslaender=tirol"
        )
        assert r.status_code == 200
        assert len(r.json()["verglichen"]) == 3

    def test_compare_unknown_bundesland_returns_404(self):
        r = client.get("/api/v1/bundesland/compare?bundeslaender=wien&bundeslaender=musterland")
        assert r.status_code == 404

    def test_compare_data_has_stellplatz_and_aufzug(self):
        r = client.get("/api/v1/bundesland/compare?bundeslaender=wien&bundeslaender=tirol")
        data = r.json()
        for bl_data in data["daten"].values():
            assert "stellplatz_factor" in bl_data
            assert "aufzug_ab_geschoss" in bl_data
            assert "regionale_kostenfaktor" in bl_data


class TestBundeslandFoerderungen:
    @pytest.mark.parametrize("bundesland", ALL_BUNDESLAENDER)
    def test_all_bundeslaender_have_foerderungen(self, bundesland):
        r = client.get(f"/api/v1/bundesland/{bundesland}/foerderungen")
        assert r.status_code == 200
        data = r.json()
        assert len(data["bundesfoerderungen"]) > 0
        assert len(data["landesfoerderungen"]) > 0

    def test_foerderungen_have_info_url(self):
        r = client.get("/api/v1/bundesland/wien/foerderungen")
        data = r.json()
        for f in data["bundesfoerderungen"] + data["landesfoerderungen"]:
            assert "name" in f
            assert "betrag" in f
            assert "info_url" in f

    def test_unknown_bundesland_returns_404(self):
        r = client.get("/api/v1/bundesland/unknown/foerderungen")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# AT Data Sources Router
# ---------------------------------------------------------------------------


class TestBaupreisindex:
    def test_returns_200(self):
        r = client.get("/api/v1/at-data/baupreisindex")
        assert r.status_code == 200

    def test_has_required_fields(self):
        r = client.get("/api/v1/at-data/baupreisindex")
        data = r.json()
        assert "basis_jahr" in data
        assert "aktueller_wert" in data
        assert "zeitreihe" in data
        assert data["basis_jahr"] == 2020

    def test_zeitreihe_not_empty(self):
        r = client.get("/api/v1/at-data/baupreisindex")
        assert len(r.json()["zeitreihe"]) > 0

    def test_filter_by_quartal(self):
        r = client.get("/api/v1/at-data/baupreisindex?von_quartal=Q1 2023&bis_quartal=Q4 2023")
        assert r.status_code == 200
        zeitreihe = r.json()["zeitreihe"]
        assert len(zeitreihe) == 4


class TestKostenrichtwerte:
    def test_returns_200(self):
        r = client.get("/api/v1/at-data/kostenrichtwerte")
        assert r.status_code == 200

    def test_has_all_kategorien(self):
        data = client.get("/api/v1/at-data/kostenrichtwerte").json()
        assert "wohnbau" in data["kategorien"]
        assert "sanierung" in data["kategorien"]
        assert "nebengebaeude" in data["kategorien"]

    def test_filter_by_kategorie(self):
        r = client.get("/api/v1/at-data/kostenrichtwerte?kategorie=wohnbau")
        assert r.status_code == 200
        data = r.json()
        assert "wohnbau" in data["kategorien"]
        assert "sanierung" not in data["kategorien"]

    def test_with_bundesland_applies_faktor(self):
        r = client.get("/api/v1/at-data/kostenrichtwerte?bundesland=wien")
        assert r.status_code == 200
        data = r.json()
        assert data["regionaler_faktor"] == 1.15
        assert "regionalisierte_kosten" in data

    def test_invalid_kategorie_returns_400(self):
        r = client.get("/api/v1/at-data/kostenrichtwerte?kategorie=invalid")
        assert r.status_code == 400

    def test_all_nine_bundeslaender_have_kostenfaktor(self):
        r = client.get("/api/v1/at-data/kostenrichtwerte")
        faktoren = r.json()["regionale_faktoren"]
        for bl in ALL_BUNDESLAENDER:
            assert bl in faktoren, f"{bl} missing from regionale_faktoren"


class TestOIBRichtlinien:
    def test_returns_all_7_richtlinien(self):
        r = client.get("/api/v1/at-data/oib-richtlinien")
        assert r.status_code == 200
        data = r.json()
        assert len(data["richtlinien"]) == 7

    def test_filter_single_richtlinie(self):
        r = client.get("/api/v1/at-data/oib-richtlinien?nummer=OIB-RL 6")
        assert r.status_code == 200
        data = r.json()
        assert len(data["richtlinien"]) == 1
        assert data["richtlinien"][0]["nummer"] == "OIB-RL 6"

    def test_salzburg_sonderweg_in_oib_rl_6(self):
        r = client.get("/api/v1/at-data/oib-richtlinien?nummer=OIB-RL 6&bundesland=salzburg")
        data = r.json()
        rl6 = data["richtlinien"][0]
        abw = rl6.get("abweichung_fuer_bundesland", "")
        assert abw and "NICHT" in abw

    def test_unknown_nummer_returns_404(self):
        r = client.get("/api/v1/at-data/oib-richtlinien?nummer=OIB-RL 99")
        assert r.status_code == 404


class TestMaterialien:
    def test_returns_200(self):
        r = client.get("/api/v1/at-data/materialien")
        assert r.status_code == 200

    def test_has_daemmung_materials(self):
        r = client.get("/api/v1/at-data/materialien?typ=D%C3%A4mmung")
        assert r.status_code == 200
        data = r.json()
        assert data["anzahl_materialien"] > 0
        for m in data["materialien"]:
            assert m["typ"] == "Dämmung"

    def test_unknown_typ_returns_404(self):
        r = client.get("/api/v1/at-data/materialien?typ=Fantasiematerial")
        assert r.status_code == 404

    def test_all_materials_have_lambda(self):
        r = client.get("/api/v1/at-data/materialien")
        for m in r.json()["materialien"]:
            assert "lambda_wm_k" in m
            assert m["lambda_wm_k"] > 0


class TestATDataSources:
    def test_sources_endpoint_returns_list(self):
        r = client.get("/api/v1/at-data/sources")
        assert r.status_code == 200
        assert len(r.json()["datenquellen"]) > 0


# ---------------------------------------------------------------------------
# Projects Router
# ---------------------------------------------------------------------------


class TestProjectsCRUD:
    def _create_project(self, name="Testprojekt Wien", bundesland="wien"):
        return client.post(
            "/api/v1/projects/",
            json={
                "name": name,
                "bundesland": bundesland,
                "building_type": "mehrfamilienhaus",
                "bgf_m2": 1500.0,
                "geschosse": 5,
                "wohnungen": 20,
                "beschreibung": "Testprojekt für ORION AT",
                "buero_name": "Architekturbüro Muster OG",
                "ziviltechniker": "DI Max Muster",
            },
        )

    def test_create_project_returns_201(self):
        r = self._create_project()
        assert r.status_code == 201

    def test_created_project_has_id(self):
        r = self._create_project()
        data = r.json()
        assert "id" in data
        assert len(data["id"]) == 36  # UUID format

    def test_created_project_default_status_is_planung(self):
        r = self._create_project()
        assert r.json()["status"] == "planung"

    def test_get_project(self):
        create_r = self._create_project()
        project_id = create_r.json()["id"]
        r = client.get(f"/api/v1/projects/{project_id}")
        assert r.status_code == 200
        assert r.json()["id"] == project_id

    def test_list_projects(self):
        self._create_project("Projekt A", "wien")
        self._create_project("Projekt B", "tirol")
        r = client.get("/api/v1/projects/")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_list_filter_by_bundesland(self):
        self._create_project("Projekt Tirol", "tirol")
        r = client.get("/api/v1/projects/?bundesland=tirol")
        assert r.status_code == 200
        for p in r.json():
            assert p["bundesland"] == "tirol"

    def test_update_project(self):
        project_id = self._create_project().json()["id"]
        r = client.put(
            f"/api/v1/projects/{project_id}",
            json={"status": "einreichung", "beschreibung": "Aktualisierte Beschreibung"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "einreichung"
        assert data["beschreibung"] == "Aktualisierte Beschreibung"

    def test_update_unknown_project_returns_404(self):
        r = client.put(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            json={"status": "planung"},
        )
        assert r.status_code == 404

    def test_delete_project(self):
        project_id = self._create_project().json()["id"]
        r = client.delete(f"/api/v1/projects/{project_id}")
        assert r.status_code == 204
        r2 = client.get(f"/api/v1/projects/{project_id}")
        assert r2.status_code == 404

    def test_invalid_bundesland_returns_422(self):
        r = client.post(
            "/api/v1/projects/",
            json={
                "name": "Test",
                "bundesland": "deutschland",
                "building_type": "wohngebaeude",
                "bgf_m2": 200,
                "geschosse": 2,
            },
        )
        assert r.status_code == 422

    def test_invalid_status_update_returns_400(self):
        project_id = self._create_project().json()["id"]
        r = client.put(
            f"/api/v1/projects/{project_id}",
            json={"status": "ungueltig"},
        )
        assert r.status_code == 400

    def test_get_nonexistent_project_returns_404(self):
        r = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


class TestProjectComplianceSummary:
    def _make_project(self, bundesland="wien", geschosse=5, bgf=1500, wohnungen=20):
        return client.post(
            "/api/v1/projects/",
            json={
                "name": "Compliance Test",
                "bundesland": bundesland,
                "building_type": "mehrfamilienhaus",
                "bgf_m2": bgf,
                "geschosse": geschosse,
                "wohnungen": wohnungen,
            },
        ).json()["id"]

    def test_compliance_summary_returns_200(self):
        pid = self._make_project()
        r = client.get(f"/api/v1/projects/{pid}/compliance-summary")
        assert r.status_code == 200

    def test_salzburg_flags_oib_rl6_sonderweg(self):
        pid = self._make_project(bundesland="salzburg")
        r = client.get(f"/api/v1/projects/{pid}/compliance-summary")
        flags = r.json()["compliance_flags"]
        energy_flags = [f for f in flags if "OIB-RL 6" in f["bereich"] or "Energie" in f["bereich"]]
        assert any("Salzburg" in f["meldung"] or "WSchVO" in f["meldung"] for f in energy_flags)

    def test_pv_flag_for_large_building(self):
        pid = self._make_project(bgf=1200)
        r = client.get(f"/api/v1/projects/{pid}/compliance-summary")
        flags = r.json()["compliance_flags"]
        assert any("PV" in f["meldung"] for f in flags)

    def test_aufzug_flag_for_high_rise(self):
        pid = self._make_project(geschosse=5)
        r = client.get(f"/api/v1/projects/{pid}/compliance-summary")
        flags = r.json()["compliance_flags"]
        assert any("Aufzug" in f["meldung"] for f in flags)

    def test_compliance_summary_has_counts(self):
        pid = self._make_project()
        r = client.get(f"/api/v1/projects/{pid}/compliance-summary")
        data = r.json()
        assert "anzahl_warnungen" in data
        assert "anzahl_hinweise" in data

    def test_compliance_unknown_project_returns_404(self):
        r = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000/compliance-summary")
        assert r.status_code == 404


class TestProjectExport:
    def test_export_json_returns_200(self):
        pid = client.post(
            "/api/v1/projects/",
            json={
                "name": "Export Test",
                "bundesland": "tirol",
                "building_type": "einfamilienhaus",
                "bgf_m2": 200,
                "geschosse": 2,
            },
        ).json()["id"]
        r = client.get(f"/api/v1/projects/{pid}/export?format=json")
        assert r.status_code == 200
        data = r.json()
        assert data["export_format"] == "json"
        assert "projekt" in data

    def test_export_unsupported_format_returns_400(self):
        pid = client.post(
            "/api/v1/projects/",
            json={
                "name": "Export Test",
                "bundesland": "wien",
                "building_type": "mehrfamilienhaus",
                "bgf_m2": 500,
                "geschosse": 4,
            },
        ).json()["id"]
        r = client.get(f"/api/v1/projects/{pid}/export?format=pdf")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Team member management (Bürofähigkeit)
# ---------------------------------------------------------------------------


class TestProjectTeamMembers:
    def _make_project(self, name="Team-Projekt"):
        return client.post(
            "/api/v1/projects/",
            json={
                "name": name,
                "bundesland": "wien",
                "building_type": "buerogebaeude",
                "bgf_m2": 800,
                "geschosse": 4,
            },
        ).json()["id"]

    def test_add_member_returns_201(self):
        pid = self._make_project()
        r = client.post(
            f"/api/v1/projects/{pid}/members",
            json={
                "user_id": "arch-001",
                "name": "Mag. Arch. Maria Müller",
                "rolle": "architekt",
                "email": "m.mueller@buero.at",
                "berechtigungen": ["lesen", "bearbeiten"],
            },
        )
        assert r.status_code == 201

    def test_add_member_data_returned(self):
        pid = self._make_project()
        r = client.post(
            f"/api/v1/projects/{pid}/members",
            json={
                "user_id": "ing-002",
                "name": "DI Thomas Huber",
                "rolle": "ingenieur",
                "berechtigungen": ["lesen"],
            },
        )
        data = r.json()
        assert data["mitglied"]["user_id"] == "ing-002"
        assert data["mitglied"]["rolle"] == "ingenieur"
        assert data["team_groesse"] == 1

    def test_list_members_returns_200(self):
        pid = self._make_project()
        client.post(
            f"/api/v1/projects/{pid}/members",
            json={"user_id": "u1", "name": "User One", "rolle": "bauleiter", "berechtigungen": ["lesen"]},
        )
        r = client.get(f"/api/v1/projects/{pid}/members")
        assert r.status_code == 200
        data = r.json()
        assert data["team_groesse"] == 1
        assert len(data["mitglieder"]) == 1

    def test_list_empty_project_has_no_members(self):
        pid = self._make_project("Leeres Projekt")
        r = client.get(f"/api/v1/projects/{pid}/members")
        assert r.status_code == 200
        assert r.json()["team_groesse"] == 0

    def test_duplicate_member_returns_409(self):
        pid = self._make_project()
        payload = {"user_id": "dup-001", "name": "Duplikat", "rolle": "gaest", "berechtigungen": ["lesen"]}
        client.post(f"/api/v1/projects/{pid}/members", json=payload)
        r = client.post(f"/api/v1/projects/{pid}/members", json=payload)
        assert r.status_code == 409

    def test_remove_member_returns_204(self):
        pid = self._make_project()
        client.post(
            f"/api/v1/projects/{pid}/members",
            json={"user_id": "del-001", "name": "To Delete", "rolle": "gaest", "berechtigungen": ["lesen"]},
        )
        r = client.delete(f"/api/v1/projects/{pid}/members/del-001")
        assert r.status_code == 204
        # Verify removed
        members = client.get(f"/api/v1/projects/{pid}/members").json()["mitglieder"]
        assert all(m["user_id"] != "del-001" for m in members)

    def test_remove_nonexistent_member_returns_404(self):
        pid = self._make_project()
        r = client.delete(f"/api/v1/projects/{pid}/members/does-not-exist")
        assert r.status_code == 404

    def test_invalid_rolle_returns_422(self):
        pid = self._make_project()
        r = client.post(
            f"/api/v1/projects/{pid}/members",
            json={"user_id": "u-bad", "name": "Bad Role", "rolle": "ceo", "berechtigungen": ["lesen"]},
        )
        assert r.status_code == 422

    def test_invalid_berechtigung_returns_422(self):
        pid = self._make_project()
        r = client.post(
            f"/api/v1/projects/{pid}/members",
            json={"user_id": "u-bad2", "name": "Bad Perm", "rolle": "architekt", "berechtigungen": ["superadmin"]},
        )
        assert r.status_code == 422

    def test_add_member_to_unknown_project_returns_404(self):
        r = client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/members",
            json={"user_id": "u1", "name": "X", "rolle": "gaest", "berechtigungen": ["lesen"]},
        )
        assert r.status_code == 404

    @pytest.mark.parametrize("rolle", ["architekt", "ingenieur", "bauleiter", "sachverstaendiger", "auftraggeber", "gaest"])
    def test_all_valid_rollen(self, rolle):
        pid = self._make_project(f"Rollen-Test-{rolle}")
        r = client.post(
            f"/api/v1/projects/{pid}/members",
            json={"user_id": f"u-{rolle}", "name": f"Test {rolle}", "rolle": rolle, "berechtigungen": ["lesen"]},
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# AT data: changelog, at-kpis (Vertrauen & Erfolg messbar machen)
# ---------------------------------------------------------------------------


class TestChangelog:
    def test_changelog_returns_200(self):
        r = client.get("/api/v1/at-data/changelog")
        assert r.status_code == 200

    def test_changelog_has_entries(self):
        data = client.get("/api/v1/at-data/changelog").json()
        assert "changelog" in data
        assert len(data["changelog"]) >= 1

    def test_changelog_has_version_and_datum(self):
        entry = client.get("/api/v1/at-data/changelog").json()["changelog"][0]
        assert "version" in entry
        assert "datum" in entry
        assert "aenderungen" in entry

    def test_changelog_aktuellste_version_matches_first_entry(self):
        data = client.get("/api/v1/at-data/changelog").json()
        assert data["aktuellste_version"] == data["changelog"][0]["version"]

    def test_changelog_contains_oib_and_bundesland_items(self):
        entries = client.get("/api/v1/at-data/changelog").json()["changelog"]
        all_changes = " ".join(c for e in entries for c in e["aenderungen"])
        assert "OIB" in all_changes or "Bundesland" in all_changes


class TestATKPIs:
    def test_at_kpis_returns_200(self):
        r = client.get("/api/v1/at-data/at-kpis")
        assert r.status_code == 200

    def test_bundesland_abdeckung_100pct(self):
        data = client.get("/api/v1/at-data/at-kpis").json()
        assert data["bundesland_abdeckung"]["abdeckung_pct"] == 100.0
        assert data["bundesland_abdeckung"]["implementiert"] == 9

    def test_oib_abdeckung_100pct(self):
        data = client.get("/api/v1/at-data/at-kpis").json()
        assert data["oib_rl_abdeckung"]["abdeckung_pct"] == 100.0
        assert data["oib_rl_abdeckung"]["implementiert"] == 7

    def test_api_endpunkte_sections_present(self):
        data = client.get("/api/v1/at-data/at-kpis").json()
        assert "bundesland" in data["api_endpunkte"]
        assert "at_daten" in data["api_endpunkte"]
        assert "projekte" in data["api_endpunkte"]
        assert "berechnungen" in data["api_endpunkte"]

    def test_vertrauen_features_changelog_active(self):
        data = client.get("/api/v1/at-data/at-kpis").json()
        assert data["vertrauen_features"]["oeffentliches_changelog"] is True
        assert data["vertrauen_features"]["audit_trail"] is True

    def test_bim_support_present(self):
        data = client.get("/api/v1/at-data/at-kpis").json()
        assert "IFC4" in data["bim_unterstuetzung"]["formate"]

    def test_has_messung_zeitpunkt(self):
        data = client.get("/api/v1/at-data/at-kpis").json()
        assert "messung_zeitpunkt" in data


# ---------------------------------------------------------------------------
# Austria-first Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_returns_200(self):
        r = client.get("/dashboard")
        assert r.status_code == 200

    def test_dashboard_is_html(self):
        r = client.get("/dashboard")
        assert "text/html" in r.headers.get("content-type", "")

    def test_dashboard_contains_austria_branding(self):
        r = client.get("/dashboard")
        assert "Österreich" in r.text or "Austria" in r.text or "ORION" in r.text

    def test_dashboard_contains_9_bundeslaender(self):
        r = client.get("/dashboard")
        # Dashboard mentions all 9
        text = r.text
        assert "Wien" in text
        assert "Tirol" in text
        assert "Salzburg" in text

    def test_dashboard_contains_oib_reference(self):
        r = client.get("/dashboard")
        assert "OIB" in r.text

    def test_dashboard_contains_api_links(self):
        r = client.get("/dashboard")
        assert "/api/v1/bundesland/" in r.text
        assert "/api/v1/at-data/oib-richtlinien" in r.text


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


class TestAuthEndpoints:
    def test_auth_me_without_token_returns_403(self):
        """HTTPBearer raises 403 when no Authorization header is present"""
        r = client.get("/auth/me")
        assert r.status_code in [401, 403]

    def test_auth_me_with_weak_token_returns_401(self):
        r = client.get("/auth/me", headers={"Authorization": "Bearer 123"})
        assert r.status_code == 401

    def test_auth_me_with_none_alg_returns_401(self):
        r = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0In0."},
        )
        assert r.status_code == 401

    def test_auth_status_returns_200(self):
        r = client.get("/auth/status")
        assert r.status_code == 200
        data = r.json()
        assert data["auth_required"] is True
        assert "algorithm" in data
