#!/usr/bin/env python3
"""
Client Intake & Fragebogen System
==================================
Autonomous client onboarding with:
- Interactive questionnaire
- Automatic project classification
- Budget feasibility analysis
- Risk assessment

Author: ORION Swarm - Team C
Date: 2026-05-25
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum
import json
from datetime import datetime


class ProjectScope(Enum):
    """Project size classification"""
    SMALL = "Klein (<500m²)"
    MEDIUM = "Mittel (500-2000m²)"
    LARGE = "Groß (2000-5000m²)"
    XL = "Sehr Groß (>5000m²)"


class BudgetTier(Enum):
    """Budget classification"""
    ECONOMY = "Economy (€20-30k/100m²)"
    STANDARD = "Standard (€30-45k/100m²)"
    PREMIUM = "Premium (€45-65k/100m²)"
    LUXURY = "Luxury (€65k+/100m²)"


@dataclass
class ClientProfile:
    """Client information"""
    name: str
    email: str
    phone: str
    company: Optional[str]
    role: str  # "Bauherr", "Architekt", "Ingenieur"
    experience: str  # "Neu", "Erfahren", "Profi"


@dataclass
class ProjectProfile:
    """Project classification"""
    name: str
    location_bundesland: str
    location_address: str
    project_type: str  # "Neubau", "Sanierung", "Umbau"
    building_type: str  # "Wohngebäude", "Bürogebäude", etc.
    bgf_m2: float
    scope: ProjectScope
    
    # Client requirements
    sustainability: bool  # NZEB, Sanierungspass
    bim_required: bool
    deadline_months: int
    budget_eur: float
    budget_tier: BudgetTier
    
    # Regulatory
    has_planning_permission: bool
    protected_building: bool  # Denkmalschutz
    hazard_area: bool  # Lawinen, Hochwasser, etc.
    
    # Classification result
    complexity: str  # "Einfach", "Mittel", "Komplex"
    risk_level: str  # "Niedrig", "Mittel", "Hoch"
    feasibility: str  # "Leicht machbar", "Machbar", "Schwierig"


class ClientIntakeQuestionnaire:
    """Interactive client intake system"""
    
    def __init__(self):
        self.questions = self._build_questions()
        self.responses = {}
    
    def _build_questions(self) -> List[Dict]:
        """Build questionnaire structure"""
        return [
            # Section 1: Client Info
            {
                "section": "Clientinformation",
                "id": "client_name",
                "question": "Wie heißen Sie?",
                "type": "text",
                "required": True,
            },
            {
                "section": "Clientinformation",
                "id": "client_email",
                "question": "Ihre E-Mail?",
                "type": "email",
                "required": True,
            },
            {
                "section": "Clientinformation",
                "id": "client_phone",
                "question": "Ihre Telefonnummer?",
                "type": "phone",
                "required": True,
            },
            {
                "section": "Clientinformation",
                "id": "client_role",
                "question": "Ihre Rolle?",
                "type": "select",
                "options": ["Bauherr", "Architekt", "Ingenieur", "Projektmanager"],
                "required": True,
            },
            
            # Section 2: Project Location
            {
                "section": "Projekt Standort",
                "id": "bundesland",
                "question": "In welchem Bundesland?",
                "type": "select",
                "options": [
                    "Wien", "Niederösterreich", "Oberösterreich", "Salzburg",
                    "Tirol", "Vorarlberg", "Steiermark", "Kärnten", "Burgenland"
                ],
                "required": True,
            },
            {
                "section": "Projekt Standort",
                "id": "project_address",
                "question": "Adresse (Straße, Hausnummer)?",
                "type": "text",
                "required": True,
            },
            
            # Section 3: Project Type
            {
                "section": "Projekttyp",
                "id": "project_type",
                "question": "Was ist Ihr Projekt?",
                "type": "select",
                "options": ["Neubau", "Sanierung", "Umbau", "Anbau"],
                "required": True,
            },
            {
                "section": "Projekttyp",
                "id": "building_type",
                "question": "Gebäudetyp?",
                "type": "select",
                "options": [
                    "Wohngebäude", "Bürogebäude", "Industrie", "Einzelhandel",
                    "Hotel", "Schule", "Krankenhaus", "Sonstiges"
                ],
                "required": True,
            },
            {
                "section": "Projekttyp",
                "id": "bgf_m2",
                "question": "Brutto-Grundfläche (m²)?",
                "type": "number",
                "min": 10,
                "max": 500000,
                "required": True,
            },
            
            # Section 4: Requirements
            {
                "section": "Anforderungen",
                "id": "nzeb_required",
                "question": "NZEB (Zero-Emission-Gebäude) gewünscht?",
                "type": "boolean",
                "required": False,
            },
            {
                "section": "Anforderungen",
                "id": "bim_required",
                "question": "BIM-Modelierung erforderlich?",
                "type": "boolean",
                "required": False,
            },
            {
                "section": "Anforderungen",
                "id": "sustainability",
                "question": "Nachhaltigkeit wichtig?",
                "type": "boolean",
                "required": False,
            },
            
            # Section 5: Timeline & Budget
            {
                "section": "Zeitplan & Budget",
                "id": "deadline_months",
                "question": "Zeitrahmen (Monate bis Baubeginn)?",
                "type": "number",
                "min": 1,
                "max": 120,
                "required": True,
            },
            {
                "section": "Zeitplan & Budget",
                "id": "budget_eur",
                "question": "Budget (EUR)?",
                "type": "number",
                "min": 10000,
                "max": 100000000,
                "required": True,
            },
            
            # Section 6: Risk Assessment
            {
                "section": "Risikoanalyse",
                "id": "protected_building",
                "question": "Denkmalschutz?",
                "type": "boolean",
                "required": False,
            },
            {
                "section": "Risikoanalyse",
                "id": "hazard_area",
                "question": "Gefahrenzone (Lawinen, Hochwasser, etc.)?",
                "type": "boolean",
                "required": False,
            },
            {
                "section": "Risikoanalyse",
                "id": "planning_permission",
                "question": "Widmung/Baugenehmigung vorhanden?",
                "type": "boolean",
                "required": False,
            },
        ]
    
    def get_questionnaire_json(self) -> str:
        """Export questionnaire as JSON"""
        return json.dumps(self.questions, indent=2, ensure_ascii=False)
    
    def validate_responses(self, responses: Dict) -> tuple[bool, List[str]]:
        """Validate all responses"""
        errors = []
        
        for question in self.questions:
            if question["required"] and question["id"] not in responses:
                errors.append(f"Required: {question['question']}")
        
        return len(errors) == 0, errors


class ProjectClassifier:
    """Automatic project classification based on responses"""
    
    def classify(self, responses: Dict) -> ProjectProfile:
        """Classify project and generate profile"""
        
        # Calculate scope
        bgf_m2 = float(responses.get("bgf_m2", 1000))
        if bgf_m2 < 500:
            scope = ProjectScope.SMALL
        elif bgf_m2 < 2000:
            scope = ProjectScope.MEDIUM
        elif bgf_m2 < 5000:
            scope = ProjectScope.LARGE
        else:
            scope = ProjectScope.XL
        
        # Calculate budget tier
        budget_eur = float(responses.get("budget_eur", 100000))
        price_per_m2 = budget_eur / bgf_m2
        
        if price_per_m2 < 30000:
            budget_tier = BudgetTier.ECONOMY
        elif price_per_m2 < 45000:
            budget_tier = BudgetTier.STANDARD
        elif price_per_m2 < 65000:
            budget_tier = BudgetTier.PREMIUM
        else:
            budget_tier = BudgetTier.LUXURY
        
        # Complexity assessment
        complexity = self._assess_complexity(responses, scope, budget_tier)
        
        # Risk assessment
        risk_level = self._assess_risk(responses)
        
        # Feasibility
        feasibility = self._assess_feasibility(responses, complexity, risk_level)
        
        return ProjectProfile(
            name=responses.get("project_name", f"Project {datetime.now().strftime('%Y%m%d')}"),
            location_bundesland=responses.get("bundesland", "Wien"),
            location_address=responses.get("project_address", ""),
            project_type=responses.get("project_type", "Neubau"),
            building_type=responses.get("building_type", "Wohngebäude"),
            bgf_m2=bgf_m2,
            scope=scope,
            sustainability=responses.get("sustainability", False),
            bim_required=responses.get("bim_required", False),
            deadline_months=int(responses.get("deadline_months", 12)),
            budget_eur=budget_eur,
            budget_tier=budget_tier,
            has_planning_permission=responses.get("planning_permission", False),
            protected_building=responses.get("protected_building", False),
            hazard_area=responses.get("hazard_area", False),
            complexity=complexity,
            risk_level=risk_level,
            feasibility=feasibility,
        )
    
    def _assess_complexity(self, responses: Dict, scope: ProjectScope, budget_tier: BudgetTier) -> str:
        """Assess project complexity"""
        complexity_score = 0
        
        # Size factor
        if scope == ProjectScope.XL:
            complexity_score += 3
        elif scope == ProjectScope.LARGE:
            complexity_score += 2
        elif scope == ProjectScope.MEDIUM:
            complexity_score += 1
        
        # Requirements
        if responses.get("bim_required"):
            complexity_score += 2
        if responses.get("nzeb_required"):
            complexity_score += 1
        if responses.get("sustainability"):
            complexity_score += 1
        
        # Risk factors
        if responses.get("protected_building"):
            complexity_score += 2
        if responses.get("hazard_area"):
            complexity_score += 2
        
        if complexity_score >= 7:
            return "Komplex"
        elif complexity_score >= 4:
            return "Mittel"
        else:
            return "Einfach"
    
    def _assess_risk(self, responses: Dict) -> str:
        """Assess project risk level"""
        risk_score = 0
        
        if responses.get("protected_building"):
            risk_score += 3
        if responses.get("hazard_area"):
            risk_score += 2
        if not responses.get("planning_permission"):
            risk_score += 2
        if int(responses.get("deadline_months", 12)) < 3:
            risk_score += 1
        
        if risk_score >= 5:
            return "Hoch"
        elif risk_score >= 2:
            return "Mittel"
        else:
            return "Niedrig"
    
    def _assess_feasibility(self, responses: Dict, complexity: str, risk_level: str) -> str:
        """Assess project feasibility"""
        if complexity == "Komplex" and risk_level == "Hoch":
            return "Schwierig"
        elif complexity == "Komplex" or risk_level == "Hoch":
            return "Machbar"
        else:
            return "Leicht machbar"


class BudgetFeasibilityChecker:
    """Analyze budget feasibility and suggest optimizations"""
    
    @staticmethod
    def check_feasibility(project: ProjectProfile) -> Dict:
        """Check if budget is realistic"""
        
        # Market rates (EUR/m², 2026 Austria)
        market_rates = {
            "Neubau": {
                "Wohngebäude": (2500, 4500),  # min, max
                "Bürogebäude": (2000, 4000),
                "Industrie": (1000, 2500),
            },
            "Sanierung": {
                "Wohngebäude": (1500, 3000),
                "Bürogebäude": (1200, 2500),
                "Industrie": (800, 1800),
            },
        }
        
        project_type = project.project_type
        building_type = project.building_type
        
        rates = market_rates.get(project_type, {}).get(building_type, (1500, 3000))
        min_rate, max_rate = rates
        
        total_min = project.bgf_m2 * min_rate
        total_max = project.bgf_m2 * max_rate
        actual_rate = project.budget_eur / project.bgf_m2
        
        feasibility = {
            "budget_eur": project.budget_eur,
            "actual_rate_per_m2": actual_rate,
            "market_range": {
                "min_per_m2": min_rate,
                "max_per_m2": max_rate,
                "min_total": total_min,
                "max_total": total_max,
            },
            "is_feasible": total_min <= project.budget_eur <= total_max,
            "recommendation": "",
            "adjustments": [],
        }
        
        if project.budget_eur < total_min:
            feasibility["recommendation"] = "KRITISCH: Budget zu niedrig!"
            feasibility["adjustments"].append(
                f"Erhöhen Sie Budget auf €{total_min:,.0f} "
                f"(oder reduzieren Sie Fläche auf {project.budget_eur / max_rate:.0f}m²)"
            )
        elif project.budget_eur > total_max:
            feasibility["recommendation"] = "Budget ausreichend (ggf. optimierbar)"
            feasibility["adjustments"].append(
                f"Sie könnten €{project.budget_eur - total_max:,.0f} sparen "
                f"durch Standard-Ausstattung"
            )
        else:
            feasibility["recommendation"] = "Budget realistische"
        
        # Additional checks
        if project.bim_required:
            feasibility["adjustments"].append("BIM: +5-10% Kosten, -15% Planungszeit")
        
        if project.sustainability:
            feasibility["adjustments"].append("Nachhaltigkeit: +8-15% Material-Kosten")
        
        if project.deadline_months < 6:
            feasibility["adjustments"].append("Straffer Timeline: +10-20% Kosten (Mehrschicht, Express)")
        
        return feasibility


def intake_workflow(responses: Dict) -> Dict:
    """Complete intake workflow: validate → classify → check feasibility"""
    
    # Step 1: Validate
    questionnaire = ClientIntakeQuestionnaire()
    is_valid, errors = questionnaire.validate_responses(responses)
    
    if not is_valid:
        return {
            "status": "error",
            "errors": errors,
        }
    
    # Step 2: Classify
    classifier = ProjectClassifier()
    project = classifier.classify(responses)
    
    # Step 3: Check feasibility
    feasibility = BudgetFeasibilityChecker.check_feasibility(project)
    
    return {
        "status": "success",
        "client": {
            "name": responses.get("client_name"),
            "email": responses.get("client_email"),
            "phone": responses.get("client_phone"),
            "role": responses.get("client_role"),
        },
        "project": asdict(project),
        "feasibility": feasibility,
        "next_steps": [
            "1. Standort-Analyse (HORA-Integration)",
            "2. Bebauungsplan-Prüfung",
            "3. Detailliertes Angebot",
            "4. Projektstart",
        ],
        "generated_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # Example: Complete intake workflow
    example_responses = {
        "client_name": "Max Mustermann",
        "client_email": "max@example.com",
        "client_phone": "+43 1 234 56789",
        "client_role": "Bauherr",
        "bundesland": "Wien",
        "project_address": "Ringstrasse 1, Wien",
        "project_type": "Neubau",
        "building_type": "Wohngebäude",
        "bgf_m2": 1500,
        "nzeb_required": True,
        "bim_required": True,
        "sustainability": True,
        "deadline_months": 18,
        "budget_eur": 4500000,
        "protected_building": False,
        "hazard_area": False,
        "planning_permission": True,
    }
    
    result = intake_workflow(example_responses)
    print(json.dumps(result, indent=2, ensure_ascii=False))
