"""
Save API test results as JSON or Markdown files.
"""

import json
import os
from datetime import datetime


RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")


def _ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _sanitize_name(api_name: str) -> str:
    return api_name.lower().replace(" ", "_").replace("&", "and").replace("-", "_")


def save_json(
    api_name: str,
    endpoint: str,
    request_headers: dict,
    request_body: dict,
    response_status: int,
    response_headers: dict,
    response_body: dict | str,
    duration_ms: int,
) -> str:
    """Save full request/response as JSON. Returns the file path."""
    _ensure_results_dir()

    output = {
        "api": api_name,
        "endpoint": endpoint,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "duration_ms": duration_ms,
        "request": {
            "headers": {k: v for k, v in request_headers.items() if k.lower() != "authorization"},
            "body": request_body,
        },
        "response": {
            "status_code": response_status,
            "headers": dict(response_headers),
            "body": response_body,
        },
    }

    filename = f"output_{_timestamp()}_{_sanitize_name(api_name)}.json"
    filepath = os.path.join(RESULTS_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return filepath


def save_markdown(api_name: str, markdown_content: str) -> str:
    """Save Markdown report. Returns the file path."""
    _ensure_results_dir()

    filename = f"output_{_timestamp()}_{_sanitize_name(api_name)}.md"
    filepath = os.path.join(RESULTS_DIR, filename)

    with open(filepath, "w") as f:
        f.write(markdown_content)

    return filepath
