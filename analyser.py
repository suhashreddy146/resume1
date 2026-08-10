"""AI resume analysis using any OpenAI-compatible API."""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) and career coach.
Analyse the candidate's resume and produce a strict JSON object with exactly
these keys:

{
  "overall_score": int 0-100,
  "ats_score": int 0-100,
  "sections_found": [string],
  "missing_sections": [string],
  "contact_present": bool,
  "contact_missing": [string],
  "keyword_coverage": {string: int}  // job-description keyword -> present(1)/absent(0),
  "keyword_match_rate": int 0-100,
  "strengths": [string],
  "weaknesses": [string],
  "suggestions": [string],
  "improved_summary": string
}

Rules:
- Base every score on the actual resume text.
- If a job description is provided, derive keywords from it and score keyword
  match rate as a percentage of the important keywords that appear in the resume
  (case-insensitive).
- suggestions must be concrete, actionable, and specific to the resume.
- improved_summary is a rewritten professional summary the candidate can paste
  into the resume.
- Do not invent facts. Return ONLY valid JSON."""


def build_user_prompt(resume_text: str, job_description: str = "") -> str:
    parts = ["### RESUME\n" + (resume_text or "(empty resume)")]
    if job_description and job_description.strip():
        parts.append("### JOB DESCRIPTION\n" + job_description.strip())
    else:
        parts.append("### JOB DESCRIPTION\n(not provided - evaluate the resume on its own merits)")
    return "\n\n".join(parts)


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Create a .env file from .env.example "
            "or set the environment variable."
        )
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )


def _parse_json(raw: str) -> dict:
    """Parse LLM output, tolerating markdown fences or surrounding text."""
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def analyse_resume(resume_text: str, job_description: str = "") -> dict:
    model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    client = _client()
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(resume_text, job_description)},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    return _parse_json(raw)


def keyword_overlap(resume_text: str, job_description: str) -> dict:
    """Local, cheap keyword check used as a fallback if no API key is set."""
    import re

    stop = {
        "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with",
        "is", "are", "be", "by", "as", "at", "that", "this", "it", "you",
        "your", "we", "our", "will", "can", "must", "should", "have", "has",
        "experience", "years", "work", "working", "role", "team", "skills",
    }
    resume_lower = resume_text.lower()
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", job_description.lower())
    coverage = {}
    for word in words:
        if word in stop or len(word) < 2:
            continue
        coverage.setdefault(word, 1 if word in resume_lower else 0)
    return coverage
