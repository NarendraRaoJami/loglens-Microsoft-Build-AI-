from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import anthropic
import json
import re
from typing import Optional
import os

app = FastAPI(title="LogLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert log and email intelligence analyst. Your job is to parse raw, unstructured logs or email text and return a structured JSON analysis.

Given input text (logs, emails, or mixed), extract and return ONLY valid JSON (no markdown, no explanation) with this exact schema:

{
  "summary": "2-3 sentence executive summary of what happened",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "total_events": <number>,
  "alerts": [
    {
      "id": <number>,
      "level": "ERROR|WARN|INFO|SUCCESS|ALERT",
      "title": "short title",
      "message": "cleaned, human-readable message",
      "timestamp": "extracted or inferred timestamp or null",
      "source": "service/system/sender name or null",
      "tags": ["tag1", "tag2"]
    }
  ],
  "patterns": [
    {
      "name": "pattern name",
      "count": <number>,
      "description": "what this pattern means"
    }
  ],
  "recommendations": ["actionable recommendation 1", "actionable recommendation 2"],
  "stats": {
    "errors": <count>,
    "warnings": <count>,
    "info": <count>,
    "success": <count>
  }
}

Be thorough. Extract ALL meaningful events. Deduplicate and group similar events as patterns."""


class TextInput(BaseModel):
    text: str
    source_type: Optional[str] = "auto"


@app.post("/api/analyze/text")
async def analyze_text(payload: TextInput):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")
    return await run_analysis(payload.text)


@app.post("/api/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")
    return await run_analysis(text)


async def run_analysis(text: str):
    # Truncate to ~8000 chars to stay within limits
    truncated = text[:8000]
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyze this input:\n\n{truncated}"}],
    )
    raw = message.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned malformed JSON. Please retry.")
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "LogLens"}


# Serve frontend
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")
