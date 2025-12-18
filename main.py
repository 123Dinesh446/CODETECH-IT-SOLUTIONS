from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.models.schemas import TriageRequest, TriageResponse
from app.services.triage import analyze_incident
from app.services.places import fetch_nearby_hospitals
from app.services.faq import search_faq
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="EmergiAR AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static site
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

api = APIRouter(prefix="/api/v1")


@api.get("/health")
async def health():
    return {"status": "ok"}


@api.post("/analyze", response_model=TriageResponse)
async def analyze(request: TriageRequest):
    try:
        result = await analyze_incident(request, openai_api_key=settings.openai_api_key)
        return result
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


@api.get("/nearby/hospitals")
async def nearby_hospitals(lat: float = Query(...), lon: float = Query(...), radius_m: int = Query(2000, ge=200, le=10000)):
    try:
        items = await fetch_nearby_hospitals(lat=lat, lon=lon, radius_m=radius_m)
        return {"count": len(items), "items": items}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


@api.get("/faq/search")
async def faq_search(q: str = Query("", min_length=0), limit: int = Query(5, ge=1, le=10)):
    try:
        items = search_faq(q, limit=limit)
        return {"count": len(items), "items": items}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


app.include_router(api)


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")
