from typing import List

from app.models.schemas import TriageRequest, Recommendation


def _resources_for(severity: str, incident_type: str | None) -> List[str]:
    if severity == "critical":
        return ["ALS ambulance", "Nearest ER pre-alert", "AED if available"]
    if severity == "high":
        return ["BLS ambulance", "ER triage"]
    if severity == "moderate":
        return ["Urgent care", "Transport if needed"]
    return ["Self-care", "Telehealth"]


def _actions_for(severity: str, req: TriageRequest) -> List[str]:
    common = ["Gather medical history and allergies"]
    if severity == "critical":
        return [
            "Initiate CPR if no breathing/pulse",
            "Apply direct pressure to severe bleeding",
            "Place in recovery position if unconscious and breathing",
        ] + common
    if severity == "high":
        return [
            "Control bleeding and immobilize injuries",
            "Monitor airway, breathing, circulation",
        ] + common
    if severity == "moderate":
        return [
            "Apply cold pack/splint if needed",
            "Consider over-the-counter pain relief if appropriate",
        ] + common
    return ["Provide reassurance and observe", "Home care guidance"] + common


def generate_recommendation(severity: str, req: TriageRequest) -> Recommendation:
    resources = _resources_for(severity, req.incident_type)
    actions = _actions_for(severity, req)
    return Recommendation(priority=severity, actions=actions, resources=resources)
