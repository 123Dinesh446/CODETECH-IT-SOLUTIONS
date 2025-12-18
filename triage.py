from __future__ import annotations

from typing import Optional
import re

from app.models.schemas import TriageRequest, TriageResponse
from app.services.recommendations import generate_recommendation
from app.core.config import get_settings


SEVERITY_SCORES = {
    "critical": 0.95,
    "high": 0.8,
    "moderate": 0.55,
    "low": 0.25,
}


def _rule_based_severity(req: TriageRequest) -> str:
    text = (req.message or "").lower()

    keywords_critical = [
        "not breathing",
        "no pulse",
        "unconscious",
        "severe bleeding",
        "cardiac arrest",
        "choking",
    ]
    if any(k in text for k in keywords_critical) or (req.breathing is False) or (req.conscious is False):
        return "critical"

    keywords_high = [
        "heavy bleeding",
        "bone protruding",
        "seizure",
        "stroke",
        "chest pain",
    ]
    if any(k in text for k in keywords_high) or (req.bleeding is True):
        return "high"

    keywords_moderate = ["fracture", "burn", "accident", "fall", "sprain"]
    if any(k in text for k in keywords_moderate):
        return "moderate"

    return "low"


async def _deepseek_severity(req: TriageRequest) -> Optional[str]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return None
    try:
        import httpx
        system = (
            "You are a medical triage classifier. Respond with ONLY one of: "
            "critical, high, moderate, low."
        )
        user = (
            f"message: {req.message}\n"
            f"incident_type: {req.incident_type}\n"
            f"age: {req.age}\n"
            f"conscious: {req.conscious}\n"
            f"breathing: {req.breathing}\n"
            f"bleeding: {req.bleeding}\n"
        )
        body = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": 2,
        }
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(base_url=settings.deepseek_base_url, timeout=20) as client:
            resp = await client.post("/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip().lower()
        m = re.search(r"(critical|high|moderate|low)", text)
        return m.group(1) if m else None
    except Exception:
        return None


async def _openai_severity(req: TriageRequest, openai_api_key: Optional[str]) -> Optional[str]:
    if not openai_api_key:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=openai_api_key)
        prompt = (
            "You are a medical triage classifier. Classify the incident severity as one of: "
            "critical, high, moderate, low. Consider fields: message, age, conscious, "
            "breathing, bleeding, incident_type. Respond with ONLY the single word.\n\n"
            f"message: {req.message}\n"
            f"incident_type: {req.incident_type}\n"
            f"age: {req.age}\n"
            f"conscious: {req.conscious}\n"
            f"breathing: {req.breathing}\n"
            f"bleeding: {req.bleeding}\n"
        )
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2,
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip().lower()
        match = re.search(r"(critical|high|moderate|low)", text)
        return match.group(1) if match else None
    except Exception:
        return None


async def analyze_incident(req: TriageRequest, openai_api_key: Optional[str]) -> TriageResponse:
    # Prefer DeepSeek if configured, then OpenAI, then rules
    severity_deepseek = await _deepseek_severity(req)
    severity_openai = await _openai_severity(req, openai_api_key) if not severity_deepseek else None
    severity_rule = _rule_based_severity(req)

    final_severity = severity_deepseek or severity_openai or severity_rule
    confidence = SEVERITY_SCORES.get(final_severity, 0.5)

    rec = generate_recommendation(final_severity, req)

    advice = [
        "Stay calm and ensure your safety first.",
        "If trained, begin first aid while help is on the way.",
    ]
    if final_severity in ("critical", "high"):
        advice.insert(0, "Call local emergency number immediately if not already connected.")

    return TriageResponse(
        severity=final_severity,
        confidence=confidence,
        recommendation=rec,
        advice=advice,
    )
