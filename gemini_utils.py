"""
Gemini AI helper functions for CogniTask AI.
Handles NLP task parsing and task breakdown.
"""

import json
from datetime import datetime, timezone
import streamlit as st

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def get_api_key() -> str | None:
    """Get the Google AI API key from Streamlit secrets."""
    try:
        return st.secrets.get("GOOGLE_AI_API_KEY")
    except Exception:
        return None


def is_configured() -> bool:
    """Check if Gemini AI is properly configured."""
    if not GEMINI_AVAILABLE:
        return False
    api_key = get_api_key()
    return api_key is not None and len(api_key) > 0 and api_key != "your-google-ai-api-key-here"


def call_gemini(prompt: str) -> dict | None:
    """
    Call the Gemini API with a prompt and return parsed JSON response.
    Returns None on failure.
    """
    if not is_configured():
        return None

    try:
        api_key = get_api_key()
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )

        # Parse the JSON response
        result = json.loads(response.text)
        return result

    except json.JSONDecodeError as e:
        st.error(f"Failed to parse AI response as JSON: {e}")
        return None
    except Exception as e:
        st.error(f"AI API error: {e}")
        return None


def parse_task_input(user_input: str) -> dict | None:
    """
    Parse natural language task input into structured task data.

    Returns dict with keys: title, description, priority, due_date
    Or None on failure.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""You are a task parsing assistant. Parse the following natural language input into a structured task.

Today's date is: {today}

User input: "{user_input}"

Extract the following information and return as JSON:
- title: The main task action (required, be concise but complete)
- description: Any additional details or context (null if none)
- priority: One of "low", "medium", "high", "urgent" (default to "medium" if not specified)
- due_date: ISO format date string YYYY-MM-DD if a date/time is mentioned, null otherwise. Interpret relative dates like "tomorrow", "next week", "friday" relative to today's date.

Examples of priority indicators:
- "urgent", "ASAP", "immediately", "critical" → "urgent"
- "important", "high priority", "soon" → "high"
- "when you can", "low priority", "eventually" → "low"
- No indicator → "medium"

Return ONLY valid JSON in this exact format:
{{"title": "string", "description": "string or null", "priority": "string", "due_date": "string or null"}}
"""

    result = call_gemini(prompt)

    if result and "title" in result:
        # Validate and normalize the result
        return {
            "title": str(result.get("title", ""))[:255],
            "description": result.get("description"),
            "priority": result.get("priority", "medium") if result.get("priority") in ["low", "medium", "high", "urgent"] else "medium",
            "due_date": result.get("due_date")
        }

    return None


def breakdown_task(title: str, description: str | None = None) -> list[str] | None:
    """
    Break down a task into actionable sub-tasks.

    Returns a list of sub-task titles (3-7 items).
    Or None on failure.
    """
    task_context = title
    if description:
        task_context += f"\n\nAdditional context: {description}"

    prompt = f"""You are a task breakdown assistant. Break down the following task into smaller, actionable sub-tasks.

Task: {task_context}

Rules:
- Create 3-7 specific, actionable sub-tasks
- Each sub-task should be a clear, single action
- Sub-tasks should be in logical order of execution
- Keep each sub-task title concise (under 100 characters)
- Don't include the original task as a sub-task
- Focus on concrete steps, not vague items like "research" without specifics

Return ONLY valid JSON in this exact format:
{{"sub_tasks": ["First sub-task", "Second sub-task", "Third sub-task"]}}
"""

    result = call_gemini(prompt)

    if result and "sub_tasks" in result:
        sub_tasks = result["sub_tasks"]
        if isinstance(sub_tasks, list) and len(sub_tasks) >= 1:
            # Clean and validate sub-tasks
            return [str(task)[:255] for task in sub_tasks if task and str(task).strip()]

    return None
