"""
Comprehensive API Test Suite - ORION Architekt-AT
==================================================

Complete test coverage for all API endpoints with 80%+ coverage target.
Tests input validation, business logic, error handling, and edge cases.

Author: ORION Engineering Team
Date: 2026-04-11
Status: PRODUCTION
Coverage Target: 80%+
"""

import json
import os
import sys
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app
from api.main import app
from api.validation import (
    BuildingType,
    Bundesland,
    sanitize_string,
    validate_api_key,
    validate_jwt_format,
)

# Create test client
client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_uwert_request():
    """Valid U-value calculation request"""
    return {
        "schichten": [
            {"material": "Beton C30/37", "dicke_mm": 200, "lambda_wert": 2.3},
            {"material": "EPS Dämmung", "dicke_mm": 160, "lambda_wert": 0.035},
            {"material": "Kalkzementputz", "dicke_mm": 15, "lambda_wert": 0.70},
        ],
        "innen_uebergang": 0.13,
        "aussen_uebergang": 0.04,
    }


@pytest.fixture
def valid_stellplatz_request():
    """Valid parking space request"""
    return {"bundesland": "wien", "wohnungen": 10, "building_type": "mehrfamilienhaus"}


@pytest.fixture
def valid_flaeche_request():
    """Valid area calculation request"""
    return {"raumtyp": "wohnung", "laenge_m": 15.5, "breite_m": 10.2, "hoehe_m": 2.7}


@pytest.fixture
def valid_auth_token():
    """Valid JWT token for testing (mock)"""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImV4cCI6OTk5OTk5OTk5OX0.fake_signature"


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestHealthChecks:
    """Test health and monitoring endpoints"""

    def test_health_check(self):
        """Test basic health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_liveness_check(self):
        """Test Kubernetes liveness probe"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ORION Architekt-AT API"
        assert "unique_features" in data
        assert len(data["unique_features"]) > 0


# ============================================================================
# CALCULATION ENDPOINT TESTS
# ============================================================================


class TestCalculations:
    """Test building calculation endpoints"""

    def test_uwert_calculation_valid(self, valid_uwert_request):
        """Test valid U-value calculation"""
        response = client.post("/api/v1/calculations/uwert", json=valid_uwert_request)
        assert response.status_code == 200
        data = response.json()
        assert "uwert" in data
        assert "oib_rl6_compliant" in data
        assert "energy_class" in data
        assert data["uwert"] > 0
        assert data["gesamtdicke_mm"] == 375  # 200 + 160 + 15

    def test_uwert_calculation_empty_layers(self):
        """Test U-value with no layers - should fail"""
        request = {"schichten": [], "innen_uebergang": 0.13, "aussen_uebergang": 0.04}
        response = client.post("/api/v1/calculations/uwert", json=request)
        assert response.status_code == 422  # Validation error

    def test_uwert_calculation_negative_thickness(self):
        """Test U-value with negative thickness - should fail"""
        request = {"schichten": [{"material": "Beton", "dicke_mm": -100, "lambda_wert": 2.3}]}
        response = client.post("/api/v1/calculations/uwert", json=request)
        assert response.status_code == 422

    def test_uwert_calculation_zero_lambda(self):
        """Test U-value with zero lambda - should fail"""
        request = {"schichten": [{"material": "Invalid", "dicke_mm": 100, "lambda_wert": 0}]}
        response = client.post("/api/v1/calculations/uwert", json=request)
        assert response.status_code == 422

    def test_stellplaetze_valid(self, valid_stellplatz_request):
        """Test valid parking space calculation"""
        response = client.post("/api/v1/calculations/stellplaetze", json=valid_stellplatz_request)
        assert response.status_code == 200
        data = response.json()
        assert "required_stellplaetze" in data
        assert "factor" in data
        assert data["required_stellplaetze"] > 0
        assert data["bundesland"] == "wien"

    def test_stellplaetze_invalid_bundesland(self):
        """Test parking calculation with invalid Bundesland"""
        request = {"bundesland": "invalid", "wohnungen": 10}
        response = client.post("/api/v1/calculations/stellplaetze", json=request)
        assert response.status_code == 400 or response.status_code == 422

    def test_stellplaetze_zero_wohnungen(self):
        """Test parking calculation with zero apartments"""
        request = {"bundesland": "wien", "wohnungen": 0}
        response = client.post("/api/v1/calculations/stellplaetze", json=request)
        assert response.status_code == 422

    def test_stellplaetze_all_bundeslaender(self):
        """Test parking calculation for all Bundesländer"""
        bundeslaender = [
            "wien",
            "tirol",
            "salzburg",
            "vorarlberg",
            "burgenland",
            "kaernten",
            "steiermark",
            "oberoesterreich",
            "niederoesterreich",
        ]

        for bl in bundeslaender:
            request = {"bundesland": bl, "wohnungen": 10}
            response = client.post("/api/v1/calculations/stellplaetze", json=request)
            assert response.status_code == 200
            data = response.json()
            assert data["required_stellplaetze"] > 0

    def test_flaeche_calculation_valid(self, valid_flaeche_request):
        """Test valid area calculation"""
        response = client.post("/api/v1/calculations/flaeche", json=valid_flaeche_request)
        assert response.status_code == 200
        data = response.json()
        assert "bgf_m2" in data
        assert "ngf_m2" in data
        assert "nrf_m2" in data
        assert "vgf_m2" in data
        assert data["standard"] == "ÖNORM B 1800"
        # Verify calculations
        expected_bgf = 15.5 * 10.2
        assert abs(data["bgf_m2"] - expected_bgf) < 0.01

    def test_flaeche_negative_dimensions(self):
        """Test area calculation with negative dimensions"""
        request = {"raumtyp": "wohnung", "laenge_m": -10, "breite_m": 10, "hoehe_m": 2.7}
        response = client.post("/api/v1/calculations/flaeche", json=request)
        assert response.status_code == 422

    def test_flaeche_unrealistic_dimensions(self):
        """Test area calculation with unrealistic dimensions"""
        request = {"raumtyp": "wohnung", "laenge_m": 10000, "breite_m": 10, "hoehe_m": 2.7}
        response = client.post("/api/v1/calculations/flaeche", json=request)
        assert response.status_code == 422

    def test_barrierefreiheit_check_valid(self):
        """Test valid accessibility check"""
        request = {
            "tuer_breite_cm": 95,
            "rampe_vorhanden": True,
            "rampe_steigung_prozent": 5,
            "aufzug_vorhanden": False,
            "geschosse": 3,
        }
        response = client.post("/api/v1/calculations/barrierefreiheit-check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data
        assert "standard" in data
        assert data["standard"] == "ÖNORM B 1600"

    def test_barrierefreiheit_door_too_narrow(self):
        """Test accessibility check with narrow door"""
        request = {"tuer_breite_cm": 80, "rampe_vorhanden": False, "geschosse": 2}
        response = client.post("/api/v1/calculations/barrierefreiheit-check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["compliant"] is False
        assert len(data["mangel"]) > 0

    def test_barrierefreiheit_elevator_required(self):
        """Test elevator requirement for 4+ floors"""
        request = {
            "tuer_breite_cm": 95,
            "rampe_vorhanden": False,
            "aufzug_vorhanden": False,
            "geschosse": 4,
        }
        response = client.post("/api/v1/calculations/barrierefreiheit-check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["compliant"] is False
        assert any("Aufzug" in m for m in data["mangel"])

    def test_fluchtweg_check_valid(self):
        """Test valid emergency exit check"""
        request = {
            "max_entfernung_m": 35,
            "treppenhaus_breite_m": 1.25,
            "geschosse": 3,
            "gebaudetyp": "wohngebaeude",
        }
        response = client.post("/api/v1/calculations/fluchtweg-check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data
        assert "standard" in data
        assert data["standard"] == "OIB-RL 4"

    def test_fluchtweg_distance_too_long(self):
        """Test emergency exit with excessive distance"""
        request = {
            "max_entfernung_m": 50,
            "treppenhaus_breite_m": 1.25,
            "geschosse": 2,
            "gebaudetyp": "wohngebaeude",
        }
        response = client.post("/api/v1/calculations/fluchtweg-check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["compliant"] is False

    def test_schallschutz_berechnung_valid(self):
        """Test valid sound insulation calculation"""
        request = {
            "wandaufbau": [{"material": "Ziegel 25cm", "dicke_mm": 250, "lambda_wert": 0.65}],
            "gebaudetyp": "mehrfamilienhaus",
        }
        response = client.post("/api/v1/calculations/schallschutz-berechnung", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "rw_estimated" in data
        assert "required_rw" in data
        assert "standard" in data
        assert data["standard"] == "ÖNORM B 8115-2"

    def test_heizlast_berechnung_valid(self):
        """Test valid heating load calculation"""
        request = {
            "bgf_m2": 150,
            "uwert_wand": 0.20,
            "uwert_dach": 0.15,
            "uwert_fenster": 0.90,
            "bundesland": "wien",
        }
        response = client.post("/api/v1/calculations/heizlast-berechnung", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "heizlast_gesamt_w" in data
        assert "spezifische_heizlast_w_m2" in data
        assert "standard" in data
        assert data["standard"] == "ÖNORM EN 12831"

    def test_materialdatenbank_all(self):
        """Test material database - all materials"""
        response = client.get("/api/v1/calculations/materialdatenbank")
        assert response.status_code == 200
        data = response.json()
        assert "materials" in data
        assert "total" in data
        assert data["total"] > 0

    def test_materialdatenbank_filtered(self):
        """Test material database - filtered by category"""
        response = client.get("/api/v1/calculations/materialdatenbank?material_typ=Dämmung")
        assert response.status_code == 200
        data = response.json()
        assert "materials" in data
        # All returned materials should be in Dämmung category
        for mat in data["materials"]:
            assert mat["kategorie"] == "Dämmung"


# ============================================================================
# VALIDATION HELPER TESTS
# ============================================================================


class TestValidationHelpers:
    """Test validation utility functions"""

    def test_sanitize_string_valid(self):
        """Test string sanitization with valid input"""
        result = sanitize_string("Test Building 123")
        assert result == "Test Building 123"

    def test_sanitize_string_with_umlaut(self):
        """Test string sanitization with German umlauts"""
        result = sanitize_string("Gebäude München")
        assert result == "Gebäude München"

    def test_sanitize_string_removes_null_bytes(self):
        """Test null byte removal"""
        result = sanitize_string("Test\x00Building")
        assert "\x00" not in result

    def test_sanitize_string_too_long(self):
        """Test string length validation"""
        with pytest.raises(ValueError, match="too long"):
            sanitize_string("A" * 2000, max_length=100)

    def test_validate_api_key_valid(self):
        """Test valid API key format"""
        valid_key = "orion_premium_" + "a" * 32
        assert validate_api_key(valid_key) is True

    def test_validate_api_key_invalid_format(self):
        """Test invalid API key format"""
        assert validate_api_key("invalid_key") is False
        assert validate_api_key("") is False
        assert validate_api_key("orion_invalid_abc") is False

    def test_validate_jwt_format_valid(self):
        """Test valid JWT format"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIn0.signature"
        assert validate_jwt_format(token) is True

    def test_validate_jwt_format_invalid(self):
        """Test invalid JWT format"""
        assert validate_jwt_format("") is False
        assert validate_jwt_format("invalid") is False
        assert validate_jwt_format("part1.part2") is False


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================


class TestRateLimiting:
    """Test rate limiting middleware"""

    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are included in response"""
        response = client.get("/health")
        assert response.status_code == 200
        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_not_exceeded_normal_use(self):
        """Test normal use doesn't trigger rate limit"""
        # Make 10 requests - should all succeed
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_404_endpoint_not_found(self):
        """Test 404 for non-existent endpoint"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_invalid_json_body(self):
        """Test handling of invalid JSON"""
        response = client.post(
            "/api/v1/calculations/uwert",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_field(self):
        """Test validation with missing required field"""
        request = {"bundesland": "wien"}  # Missing wohnungen
        response = client.post("/api/v1/calculations/stellplaetze", json=request)
        assert response.status_code == 422

    def test_wrong_data_type(self):
        """Test validation with wrong data type"""
        request = {"bundesland": "wien", "wohnungen": "not_a_number"}  # Should be int
        response = client.post("/api/v1/calculations/stellplaetze", json=request)
        assert response.status_code == 422


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Test multi-step workflows"""

    def test_full_building_workflow(self):
        """Test complete building validation workflow"""
        # Step 1: Calculate U-value
        uwert_request = {
            "schichten": [
                {"material": "Beton", "dicke_mm": 200, "lambda_wert": 2.3},
                {"material": "Dämmung", "dicke_mm": 160, "lambda_wert": 0.035},
            ]
        }
        response1 = client.post("/api/v1/calculations/uwert", json=uwert_request)
        assert response1.status_code == 200
        uwert_data = response1.json()

        # Step 2: Calculate parking spaces
        stellplatz_request = {"bundesland": "wien", "wohnungen": 20}
        response2 = client.post("/api/v1/calculations/stellplaetze", json=stellplatz_request)
        assert response2.status_code == 200
        stellplatz_data = response2.json()

        # Step 3: Check accessibility
        barrierefreiheit_request = {
            "tuer_breite_cm": 95,
            "rampe_vorhanden": True,
            "rampe_steigung_prozent": 5,
            "geschosse": 3,
        }
        response3 = client.post(
            "/api/v1/calculations/barrierefreiheit-check", json=barrierefreiheit_request
        )
        assert response3.status_code == 200
        barrierefreiheit_data = response3.json()

        # Verify all steps completed successfully
        assert uwert_data["oib_rl6_compliant"] is not None
        assert stellplatz_data["required_stellplaetze"] > 0
        assert barrierefreiheit_data["compliant"] is not None


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Test API performance"""

    def test_response_time_health_check(self):
        """Test health check responds quickly"""
        import time

        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0  # Should respond in < 1 second

    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


# ============================================================================
# BUG-FIX REGRESSION TESTS
# ============================================================================


class TestOIBRLCheckJsonBody:
    """Fix 1: OIB-RL POST endpoint now takes JSON body instead of query params"""

    def test_oib_rl_check_json_body(self):
        """POST /oib-rl-check must accept JSON body (not query params)"""
        payload = {
            "bundesland": "wien",
            "building_type": "wohngebaeude",
            "bgf_m2": 1200.0,
            "geschosse": 5,
            "wohnungen": 20,
            "richtlinien": [1, 2, 3, 4, 5, 6],
        }
        response = client.post("/api/v1/compliance/oib-rl-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 6
        for result in data:
            assert "richtlinie" in result
            assert "status" in result
            assert "checks" in result
            assert "summary" in result

    def test_oib_rl_check_salzburg_sonderweg(self):
        """Salzburg uses WSchVO instead of OIB-RL 6 — must return warning"""
        payload = {
            "bundesland": "salzburg",
            "building_type": "wohngebaeude",
            "bgf_m2": 800.0,
            "geschosse": 3,
            "richtlinien": [6],
        }
        response = client.post("/api/v1/compliance/oib-rl-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        rl6 = next(r for r in data if "OIB-RL 6" in r["richtlinie"])
        assert rl6["status"] == "warning"
        assert "WSchVO" in rl6["summary"] or "Sonderregelung" in rl6["checks"][0]["details"]

    def test_oib_rl_check_invalid_geschosse(self):
        """geschosse must be >= 1"""
        payload = {
            "bundesland": "wien",
            "building_type": "wohngebaeude",
            "bgf_m2": 500.0,
            "geschosse": 0,
        }
        response = client.post("/api/v1/compliance/oib-rl-check", json=payload)
        assert response.status_code == 422

    def test_oib_rl_check_negative_bgf(self):
        """bgf_m2 must be > 0"""
        payload = {
            "bundesland": "wien",
            "building_type": "wohngebaeude",
            "bgf_m2": -100.0,
            "geschosse": 3,
        }
        response = client.post("/api/v1/compliance/oib-rl-check", json=payload)
        assert response.status_code == 422

    def test_oib_rl_check_radon_tirol(self):
        """Tirol is a radon risk area — additional result expected"""
        payload = {
            "bundesland": "tirol",
            "building_type": "wohngebaeude",
            "bgf_m2": 600.0,
            "geschosse": 2,
            "richtlinien": [1, 2, 3],
        }
        response = client.post("/api/v1/compliance/oib-rl-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        summaries = [r["richtlinie"] for r in data]
        assert any("Radon" in s for s in summaries)

    def test_oib_rl_check_query_params_rejected(self):
        """Sending data as query string instead of body must be rejected (missing required fields)"""
        response = client.post(
            "/api/v1/compliance/oib-rl-check"
            "?bundesland=wien&building_type=wohngebaeude&bgf_m2=800&geschosse=3"
        )
        # Without JSON body the required fields are missing → 422
        assert response.status_code == 422


class TestMaterialdatenbankUmlaut:
    """Fix 2: Materialdatenbank filter normalises German umlauts"""

    def test_filter_with_umlaut(self):
        """Filter with exact umlaut 'Dämmung' returns 2 materials"""
        response = client.get("/api/v1/calculations/materialdatenbank?material_typ=Dämmung")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for mat in data["materials"]:
            assert mat["kategorie"] == "Dämmung"

    def test_filter_without_umlaut(self):
        """Filter 'daemmung' (no umlaut) must return same results as 'Dämmung'"""
        response = client.get("/api/v1/calculations/materialdatenbank?material_typ=daemmung")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for mat in data["materials"]:
            assert mat["kategorie"] == "Dämmung"

    def test_filter_case_insensitive(self):
        """Filter must be case-insensitive"""
        response = client.get("/api/v1/calculations/materialdatenbank?material_typ=DAEMMUNG")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_tragkonstruktion(self):
        """Filter 'Tragkonstruktion' returns Beton and Holz"""
        response = client.get(
            "/api/v1/calculations/materialdatenbank?material_typ=Tragkonstruktion"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_unknown_category(self):
        """Unknown category returns empty list"""
        response = client.get("/api/v1/calculations/materialdatenbank?material_typ=NichtVorhanden")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["materials"] == []

    def test_no_filter_returns_all(self):
        """Without filter all 8 materials are returned"""
        response = client.get("/api/v1/calculations/materialdatenbank")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 8


class TestRateLimitMiddleware:
    """Fix 3: Rate-limit middleware returns proper 429 JSONResponse (not HTTPException)"""

    def test_normal_request_succeeds(self):
        """Regular requests below rate limit succeed with rate-limit headers"""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_headers_present(self):
        """API endpoints return rate-limit headers"""
        response = client.get("/api/v1/calculations/materialdatenbank")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        remaining = int(response.headers["X-RateLimit-Remaining"])
        limit = int(response.headers["X-RateLimit-Limit"])
        assert remaining <= limit


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests"""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    yield
    # Cleanup
    if os.path.exists("test.db"):
        os.remove("test.db")


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=api",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ]
    )
