"""
ORION Architekt-AT - Load Testing with Locust
==============================================

Performance and load testing scenarios for production validation.
Covers Austria-first endpoints: Bundesländer, AT-Data, Projects, Compliance.

Author: ORION Engineering Team
Date: 2026-05-12
Status: PRODUCTION TESTING
"""

import json
import random
import time
from typing import Any, Dict

from locust import HttpUser, between, events, task

# ============================================================================
# Test Data
# ============================================================================

BUNDESLAENDER = [
    "wien",
    "tirol",
    "salzburg",
    "vorarlberg",
    "steiermark",
    "oberoesterreich",
    "niederoesterreich",
    "kaernten",
    "burgenland",
]

BUILDING_TYPES = [
    "einfamilienhaus",
    "mehrfamilienhaus",
    "wohngebaeude",
    "buerogebaeude",
    "gewerbe",
    "industrie",
]

MATERIALS = [
    ("Außenputz", 10, 0.7),
    ("Dämmung EPS", 160, 0.035),
    ("Beton", 200, 2.1),
    ("Innendämmung", 40, 0.04),
    ("Gipskarton", 12, 0.21),
]

OIB_NUMMERN = ["OIB-RL 1", "OIB-RL 2", "OIB-RL 3", "OIB-RL 4", "OIB-RL 5", "OIB-RL 6"]


# ============================================================================
# Test Scenarios
# ============================================================================


class BaseORIONUser(HttpUser):
    """Base user with common functionality"""

    host = "http://localhost"
    wait_time = between(1, 3)

    def on_start(self):
        """Called when user starts"""
        # Check if API is healthy
        response = self.client.get("/health")
        if response.status_code != 200:
            events.test_stop()
            raise Exception("API is not healthy")


class AnonymousUser(BaseORIONUser):
    """
    Anonymous user browsing documentation
    Weight: 50% of users
    """

    weight = 5

    @task(5)
    def view_health(self):
        """Health check endpoint"""
        self.client.get("/health", name="/health")

    @task(3)
    def view_docs(self):
        """View API documentation"""
        self.client.get("/docs", name="/docs")

    @task(2)
    def view_openapi(self):
        """View OpenAPI spec"""
        self.client.get("/openapi.json", name="/openapi.json")

    @task(4)
    def browse_bundeslaender(self):
        """Browse Bundesländer list (public AT data)"""
        self.client.get("/api/v1/bundesland/", name="/api/v1/bundesland/")

    @task(3)
    def view_bundesland_detail(self):
        """View single Bundesland details"""
        bl = random.choice(BUNDESLAENDER)
        self.client.get(f"/api/v1/bundesland/{bl}", name="/api/v1/bundesland/{bl}")

    @task(2)
    def view_oib_richtlinien(self):
        """Browse OIB-RL overview"""
        self.client.get("/api/v1/at-data/oib-richtlinien", name="/api/v1/at-data/oib-richtlinien")

    @task(2)
    def view_baupreisindex(self):
        """View Baupreisindex (Statistik Austria)"""
        self.client.get("/api/v1/at-data/baupreisindex", name="/api/v1/at-data/baupreisindex")


class AuthenticatedFreeUser(BaseORIONUser):
    """
    Authenticated free tier user
    Weight: 30% of users
    """

    weight = 3

    @task(10)
    def calculate_uwert(self):
        """U-value calculation (most common)"""
        schichten = []
        num_layers = random.randint(3, 6)

        for i in range(num_layers):
            material, dicke, lambda_val = random.choice(MATERIALS)
            schichten.append(
                {
                    "material": material,
                    "dicke_mm": dicke + random.randint(-10, 10),
                    "lambda_wert": lambda_val,
                }
            )

        payload = {"schichten": schichten, "innen_uebergang": 0.13, "aussen_uebergang": 0.04}

        with self.client.post(
            "/api/v1/calculations/uwert",
            json=payload,
            name="/api/v1/calculations/uwert",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "u_wert" in result:
                    response.success()
                else:
                    response.failure("Missing u_wert in response")
            elif response.status_code == 429:
                response.success()  # Rate limit is expected
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(5)
    def calculate_stellplaetze(self):
        """Parking space calculation via Bundesland endpoint"""
        bl = random.choice(BUNDESLAENDER)
        wohnungen = random.randint(10, 100)
        self.client.get(
            f"/api/v1/bundesland/{bl}/stellplaetze?wohnungen={wohnungen}",
            name="/api/v1/bundesland/{bl}/stellplaetze",
        )

    @task(4)
    def check_aufzug(self):
        """Elevator requirement check via Bundesland endpoint"""
        bl = random.choice(BUNDESLAENDER)
        geschosse = random.randint(1, 10)
        self.client.get(
            f"/api/v1/bundesland/{bl}/aufzug?geschosse={geschosse}",
            name="/api/v1/bundesland/{bl}/aufzug",
        )

    @task(3)
    def check_barrierefreiheit(self):
        """Accessibility check"""
        payload = {
            "tuer_breite_cm": random.randint(80, 120),
            "rampe_vorhanden": random.choice([True, False]),
            "rampe_steigung_prozent": random.uniform(3, 6),
            "aufzug_vorhanden": random.choice([True, False]),
            "geschosse": random.randint(1, 8),
            "bundesland": random.choice(BUNDESLAENDER),
        }

        self.client.post(
            "/api/v1/calculations/barrierefreiheit-check",
            json=payload,
            name="/api/v1/calculations/barrierefreiheit-check",
        )

    @task(2)
    def calculate_heizlast(self):
        """Heating load calculation"""
        payload = {
            "bgf_m2": random.randint(100, 500),
            "uwert_wand": random.uniform(0.15, 0.35),
            "uwert_dach": random.uniform(0.12, 0.25),
            "uwert_fenster": random.uniform(0.8, 1.3),
            "bundesland": random.choice(BUNDESLAENDER),
        }

        self.client.post(
            "/api/v1/calculations/heizlast-berechnung",
            json=payload,
            name="/api/v1/calculations/heizlast-berechnung",
        )

    @task(3)
    def browse_kostenrichtwerte(self):
        """Browse cost reference values"""
        bl = random.choice(BUNDESLAENDER)
        self.client.get(
            f"/api/v1/at-data/kostenrichtwerte?bundesland={bl}",
            name="/api/v1/at-data/kostenrichtwerte",
        )

    @task(2)
    def browse_foerderungen(self):
        """Browse Förderungen per Bundesland"""
        bl = random.choice(BUNDESLAENDER)
        self.client.get(
            f"/api/v1/bundesland/{bl}/foerderungen",
            name="/api/v1/bundesland/{bl}/foerderungen",
        )

    @task(1)
    def compare_bundeslaender(self):
        """Compare two Bundesländer"""
        bl1, bl2 = random.sample(BUNDESLAENDER, 2)
        self.client.get(
            f"/api/v1/bundesland/compare?bundeslaender={bl1}&bundeslaender={bl2}",
            name="/api/v1/bundesland/compare",
        )


class AuthenticatedPremiumUser(BaseORIONUser):
    """
    Authenticated premium user
    Weight: 15% of users
    Higher usage patterns, projects, BIM
    """

    weight = 1.5

    @task(20)
    def calculate_uwert_bulk(self):
        """Multiple U-value calculations"""
        for _ in range(3):  # Premium users do batch operations
            schichten = []
            num_layers = random.randint(4, 8)

            for i in range(num_layers):
                material, dicke, lambda_val = random.choice(MATERIALS)
                schichten.append(
                    {
                        "material": material,
                        "dicke_mm": dicke + random.randint(-10, 10),
                        "lambda_wert": lambda_val,
                    }
                )

            payload = {"schichten": schichten, "innen_uebergang": 0.13, "aussen_uebergang": 0.04}

            self.client.post(
                "/api/v1/calculations/uwert",
                json=payload,
                name="/api/v1/calculations/uwert",
            )

            time.sleep(0.1)  # Small delay between batch operations

    @task(10)
    def comprehensive_compliance_check(self):
        """Full OIB compliance check"""
        payload = {
            "bundesland": random.choice(BUNDESLAENDER),
            "building_type": random.choice(BUILDING_TYPES),
            "bgf_m2": random.randint(200, 2000),
            "geschosse": random.randint(2, 12),
            "wohnungen": random.randint(20, 200),
        }

        self.client.post(
            "/api/v1/compliance/oib-rl-check",
            json=payload,
            name="/api/v1/compliance/oib-rl-check",
        )

    @task(8)
    def project_lifecycle(self):
        """Create a project and check compliance summary"""
        # Create project
        payload = {
            "name": f"Projekt {random.randint(1, 9999)}",
            "bundesland": random.choice(BUNDESLAENDER),
            "building_type": random.choice(BUILDING_TYPES),
            "bgf_m2": random.uniform(200, 5000),
            "geschosse": random.randint(2, 8),
            "wohnungen": random.randint(5, 50),
        }

        with self.client.post(
            "/api/v1/projects/",
            json=payload,
            name="/api/v1/projects/ [create]",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                project_id = response.json().get("id")
                response.success()
                if project_id:
                    # Check compliance summary
                    self.client.get(
                        f"/api/v1/projects/{project_id}/compliance-summary",
                        name="/api/v1/projects/{id}/compliance-summary",
                    )
            else:
                response.failure(f"Project creation failed: {response.status_code}")

    @task(5)
    def browse_oib_single(self):
        """Browse single OIB-RL with Bundesland filter"""
        nummer = random.choice(OIB_NUMMERN)
        bl = random.choice(BUNDESLAENDER)
        self.client.get(
            f"/api/v1/at-data/oib-richtlinien?nummer={nummer}&bundesland={bl}",
            name="/api/v1/at-data/oib-richtlinien?nummer=",
        )


class EnterpriseUser(BaseORIONUser):
    """
    Enterprise user with highest limits
    Weight: 5% of users
    Heavy API usage — projects, compliance, AT data
    """

    weight = 0.5

    @task(30)
    def batch_processing(self):
        """Enterprise batch processing"""
        # Simulate processing multiple projects
        for project_id in range(5):
            # Multiple calculations per project
            for _ in range(2):
                schichten = [
                    {
                        "material": f"Material_{i}",
                        "dicke_mm": random.randint(50, 200),
                        "lambda_wert": random.uniform(0.03, 2.0),
                    }
                    for i in range(random.randint(4, 10))
                ]

                payload = {"schichten": schichten}
                self.client.post(
                    "/api/v1/calculations/uwert",
                    json=payload,
                    name="/api/v1/calculations/uwert [Enterprise]",
                )

            time.sleep(0.05)  # Minimal delay

    @task(15)
    def at_data_bulk(self):
        """Bulk AT data queries"""
        # Query all Bundesländer
        self.client.get("/api/v1/bundesland/", name="/api/v1/bundesland/ [Enterprise]")

        # Baupreisindex
        self.client.get(
            "/api/v1/at-data/baupreisindex", name="/api/v1/at-data/baupreisindex [Enterprise]"
        )

        # Kostenrichtwerte for 3 random Bundesländer
        for bl in random.sample(BUNDESLAENDER, 3):
            self.client.get(
                f"/api/v1/at-data/kostenrichtwerte?bundesland={bl}",
                name="/api/v1/at-data/kostenrichtwerte [Enterprise]",
            )


# ============================================================================
# Stress Test User
# ============================================================================


class StressTestUser(BaseORIONUser):
    """
    Aggressive user for stress testing
    Only used in stress test scenarios
    """

    weight = 10  # Only active during stress tests

    wait_time = between(0.1, 0.5)  # Very short wait time

    @task
    def rapid_fire_requests(self):
        """Rapid fire requests to stress the system"""
        endpoints = [
            (
                "POST",
                "/api/v1/calculations/uwert",
                {"schichten": [{"material": "Test", "dicke_mm": 100, "lambda_wert": 1.0}]},
            ),
            (
                "GET",
                f"/api/v1/bundesland/{random.choice(BUNDESLAENDER)}/stellplaetze?wohnungen=10",
                None,
            ),
            ("GET", "/health", None),
            ("GET", "/api/v1/bundesland/", None),
            ("GET", "/api/v1/at-data/baupreisindex", None),
        ]

        method, endpoint, payload = random.choice(endpoints)

        if method == "POST":
            self.client.post(endpoint, json=payload, name=f"{endpoint} [STRESS]")
        else:
            self.client.get(endpoint, name=f"{endpoint} [STRESS]")


# ============================================================================
# Test Lifecycle Events
# ============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("=" * 80)
    print("ORION Austria-leading Load Test Starting")
    print("=" * 80)
    print(f"Target: {environment.host}")
    print(
        f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'Unknown'}"
    )
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("=" * 80)
    print("ORION Austria-leading Load Test Completed")
    print("=" * 80)


# ============================================================================
# Custom Metrics
# ============================================================================


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics"""
    if exception:
        print(f"Request failed: {name} - {exception}")

    # Track slow requests (>1s)
    if response_time > 1000:
        print(f"SLOW REQUEST: {name} took {response_time}ms")

