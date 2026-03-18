#!/usr/bin/env python3
"""
LLM scoring for AI exposure via OpenRouter.

Loads .env for OPENROUTER_API_KEY, reads occupation data from
data/final/occupations_india.json, sends each occupation to an LLM
with an India-specific AI exposure scoring rubric, and checkpoints
results to data/final/india_scores.json after each call.

Resumable: skips already-scored occupations.
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
OCCUPATIONS_PATH = ROOT / "data" / "final" / "occupations_india.json"
SCORES_PATH = ROOT / "data" / "final" / "india_scores.json"

# ---------------------------------------------------------------------------
# OpenRouter config
# ---------------------------------------------------------------------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-flash-1.5"
TEMPERATURE = 0.2

# ---------------------------------------------------------------------------
# India-specific AI exposure scoring rubric (system prompt)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert analyst evaluating how exposed different occupations are to AI, specifically in the Indian labour market context.

Rate the occupation's overall AI Exposure on a scale from 0 to 10.

AI Exposure measures: how much will AI reshape this occupation in India? Consider direct effects (AI automating tasks) and indirect effects (AI making workers so productive that fewer are needed).

India-specific considerations:
- Informality: Many occupations operate outside digital workflows with cash-based, relationship-driven transactions. AI exposure is lower for informal work.
- Physical presence: India has proportionally more physical, field-based, and manual work than the US.
- Human intermediation: Trust layers, local language negotiation, and in-person verification are common in Indian business.
- Multilingual interaction: Customer-facing work often requires navigating multiple languages and dialects.
- Digital infrastructure: Rural and semi-urban areas have lower internet penetration and digitization.
- Low-software but high-coordination work: Many Indian occupations involve coordination, logistics, and people management without heavy software use.

Calibration anchors for India:
- 0-1 Minimal: agricultural labourers, construction workers, domestic helpers, street vendors
- 2-3 Low: electricians, auto mechanics, security guards, anganwadi workers, tailors
- 4-5 Moderate: nurses, police constables, bank clerks, primary school teachers, lab technicians
- 6-7 High: college lecturers, middle managers, chartered accountants, journalists, pharmacists
- 8-9 Very high: software developers, data analysts, content writers, graphic designers, financial analysts
- 10 Maximum: data entry operators, BPO/KPO voice agents, medical transcriptionists

Respond with ONLY a JSON object:
{"exposure": <0-10>, "rationale": "<2-3 sentences explaining key factors in India context>"}"""


def build_user_prompt(occupation: dict) -> str:
    """Build user prompt with occupation details for scoring."""
    parts = []
    parts.append(f"Occupation: {occupation.get('occupation_title', 'Unknown')}")
    parts.append(f"NCO Code: {occupation.get('occupation_code', 'N/A')}")

    if occupation.get("description"):
        parts.append(f"Description: {occupation['description'][:1000]}")

    if occupation.get("tasks"):
        tasks_str = "; ".join(occupation["tasks"][:10])
        parts.append(f"Key tasks: {tasks_str}")

    if occupation.get("education_proxy"):
        parts.append(f"Education/Training: {occupation['education_proxy']}")

    if occupation.get("skill_level"):
        parts.append(f"Skill level: {occupation['skill_level']}")

    if occupation.get("key_competencies"):
        comps = ", ".join(occupation["key_competencies"][:8])
        parts.append(f"Key competencies: {comps}")

    if occupation.get("sectors"):
        sectors_str = ", ".join(occupation["sectors"][:5])
        parts.append(f"Sectors: {sectors_str}")

    if occupation.get("demand_index") is not None:
        parts.append(f"Portal demand index: {occupation['demand_index']}/100")

    parts.append("\nRate this occupation's AI exposure for the Indian context.")
    return "\n".join(parts)


def call_openrouter(api_key: str, occupation: dict) -> dict | None:
    """
    Call OpenRouter API to score a single occupation.
    Returns parsed JSON response or None on failure.
    """
    user_prompt = build_user_prompt(occupation)

    payload = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/jobs-india",
        "X-Title": "Indian Job Market AI Exposure Scorer",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(OPENROUTER_URL, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()

        result = json.loads(content)

        # Validate
        if "exposure" not in result:
            print(f"    [WARN] Missing 'exposure' field in response")
            return None

        exposure = result["exposure"]
        if not isinstance(exposure, (int, float)) or exposure < 0 or exposure > 10:
            print(f"    [WARN] Invalid exposure value: {exposure}")
            return None

        return {
            "exposure": round(float(exposure), 1),
            "rationale": result.get("rationale", ""),
        }

    except httpx.HTTPStatusError as exc:
        print(f"    [ERROR] HTTP {exc.response.status_code}: {exc.response.text[:200]}")
        return None
    except json.JSONDecodeError as exc:
        print(f"    [ERROR] JSON parse error: {exc}")
        return None
    except Exception as exc:
        print(f"    [ERROR] {type(exc).__name__}: {exc}")
        return None


def load_scores() -> dict[str, dict]:
    """Load existing scores checkpoint."""
    if not SCORES_PATH.exists():
        return {}
    try:
        with open(SCORES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {
                entry["occupation_code"]: entry
                for entry in data
                if "occupation_code" in entry
            }
    except Exception:
        pass
    return {}


def save_scores(scores: dict[str, dict]):
    """Save scores checkpoint."""
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)


def score_all():
    """Main scoring loop."""
    if not HAS_HTTPX or not HAS_DOTENV:
        missing = []
        if not HAS_HTTPX:
            missing.append("httpx")
        if not HAS_DOTENV:
            missing.append("python-dotenv")
        print(f"[ERROR] Missing dependencies for scoring: {', '.join(missing)}")
        print("        Install project dependencies before running score.py.")
        sys.exit(1)

    # Load environment
    load_dotenv(ENV_PATH)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key or api_key == "your-openrouter-api-key-here":
        print("[ERROR] OPENROUTER_API_KEY not set or still placeholder.")
        print("        Set it in .env file at project root.")
        print(f"        Expected location: {ENV_PATH}")
        sys.exit(1)

    # Load occupations
    if not OCCUPATIONS_PATH.exists():
        print(f"[ERROR] Occupations file not found: {OCCUPATIONS_PATH}")
        print("        Run merge_occupations.py first.")
        sys.exit(1)

    with open(OCCUPATIONS_PATH, "r", encoding="utf-8") as f:
        occupations = json.load(f)

    print(f"[INFO] Loaded {len(occupations)} occupations from {OCCUPATIONS_PATH}")

    # Load existing scores (for resumability)
    scores = load_scores()
    already_done = len(scores)
    print(f"[INFO] {already_done}/{len(occupations)} already scored — will skip those.")

    scored_count = 0
    error_count = 0

    for i, occ in enumerate(occupations, start=1):
        code = occ.get("occupation_code", "")
        title = occ.get("occupation_title", "Unknown")

        if code in scores:
            continue  # already scored

        label = f"[{i}/{len(occupations)}]"
        print(f"{label} Scoring NCO {code}: {title} ...")

        result = call_openrouter(api_key, occ)

        if result:
            scores[code] = {
                "occupation_code": code,
                "occupation_title": title,
                "ai_exposure": result["exposure"],
                "ai_rationale": result["rationale"],
            }
            scored_count += 1
            print(f"    -> exposure={result['exposure']}")

            # Checkpoint after each successful call
            save_scores(scores)
        else:
            error_count += 1
            print(f"    -> FAILED (will retry on next run)")

            # Back off after errors
            if error_count >= 3:
                print("[WARN] Multiple errors; waiting 10s before continuing ...")
                time.sleep(10)

        # Small delay between API calls
        time.sleep(1)

    print(f"\n[INFO] Scoring complete.")
    print(f"       Scored: {scored_count} new")
    print(f"       Errors: {error_count}")
    print(f"       Total:  {len(scores)}/{len(occupations)}")
    print(f"       Output: {SCORES_PATH}")


if __name__ == "__main__":
    score_all()
