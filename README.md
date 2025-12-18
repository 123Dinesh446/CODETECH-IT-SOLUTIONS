## EmergiAR AI

AI-powered emergency response assistant (FastAPI backend).

### Setup (Windows PowerShell)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env to add your keys (DeepSeek optional, OpenAI optional)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for API docs, or open `static/test.html` in a browser.

### LLM Configuration
- Preferred: DeepSeek (no OpenAI required)
  - Set `DEEPSEEK_API_KEY`, optional `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com/v1`), and `DEEPSEEK_MODEL` (default `deepseek-chat`).
- Optional: OpenAI
  - Set `OPENAI_API_KEY` to enable OpenAI fallback.

### Endpoint
- POST `/api/v1/analyze` with body:

```json
{
  "message": "Person unconscious, not breathing",
  "location": "123 Main St",
  "incident_type": "cardiac_arrest",
  "age": 54,
  "conscious": false,
  "breathing": false,
  "bleeding": true,
  "symptoms": ["blue lips"]
}
```

Response includes `severity`, `confidence`, and `recommendation`.

### Nearby Hospitals (No API Key)
- `GET /api/v1/nearby/hospitals?lat=..&lon=..&radius_m=..` uses OpenStreetMap Overpass.

### Notes
- Works without any LLM via rule-based fallback.
- With DeepSeek or OpenAI set, LLM refines severity classification.
