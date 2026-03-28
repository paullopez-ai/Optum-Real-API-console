"""
Response formatting: JSON pretty-printing, Markdown generation, X12 parsing,
and field population analysis.
"""

import json
from datetime import datetime, timezone


def pretty_json(data: dict | list | str) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data
    return json.dumps(data, indent=2, ensure_ascii=False)


def parse_x12_segments(x12_string: str) -> str:
    """Split X12 EDI string into one segment per line."""
    if not x12_string:
        return "(empty)"
    segments = x12_string.split("~")
    return "\n".join(seg.strip() for seg in segments if seg.strip())


def analyze_field_population(data: dict, prefix: str = "") -> list[dict]:
    """
    Recursively walk a JSON response and report which fields are populated vs null/empty.
    Returns list of {path, populated, preview}.
    """
    results = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                results.extend(analyze_field_population(value, path))
            elif isinstance(value, list):
                if len(value) == 0:
                    results.append({"path": path, "populated": False, "preview": "[]"})
                else:
                    results.append({"path": path, "populated": True, "preview": f"[{len(value)} items]"})
                    if isinstance(value[0], dict):
                        results.extend(analyze_field_population(value[0], f"{path}[0]"))
            elif value is None:
                results.append({"path": path, "populated": False, "preview": "null"})
            elif isinstance(value, str) and value == "":
                results.append({"path": path, "populated": False, "preview": '""'})
            else:
                preview = str(value)
                if len(preview) > 60:
                    preview = preview[:57] + "..."
                results.append({"path": path, "populated": True, "preview": preview})
    return results


def build_markdown_report(
    api_name: str,
    endpoint: str,
    request_headers: dict,
    request_body: dict,
    response_status: int,
    response_headers: dict,
    response_body: dict | str,
    field_analysis: list[dict],
    duration_ms: int,
    x12_fields: dict[str, str] | None = None,
) -> str:
    """Build a Markdown report of the API request and response."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"# Optum API Test: {api_name}",
        f"**Date:** {now}",
        f"**Endpoint:** `{endpoint}`",
        f"**HTTP Status:** {response_status}",
        f"**Duration:** {duration_ms}ms",
        "",
        "## Request",
        "",
        "### Headers",
        "",
        "| Header | Value |",
        "|--------|-------|",
    ]

    for k, v in request_headers.items():
        display_v = v
        if k.lower() == "authorization":
            display_v = v[:20] + "..." if len(v) > 20 else v
        lines.append(f"| `{k}` | `{display_v}` |")

    lines.extend([
        "",
        "### GraphQL Variables",
        "",
        "```json",
        pretty_json(request_body.get("variables", {})),
        "```",
        "",
        "## Response",
        "",
        "### Full JSON Response",
        "",
        "```json",
        pretty_json(response_body) if isinstance(response_body, dict) else str(response_body),
        "```",
        "",
    ])

    if x12_fields:
        lines.append("### X12 Segment Breakdown")
        lines.append("")
        for field_name, x12_data in x12_fields.items():
            lines.append(f"#### `{field_name}`")
            lines.append("")
            lines.append("```")
            lines.append(parse_x12_segments(x12_data))
            lines.append("```")
            lines.append("")

    lines.extend([
        "### Field Population Summary",
        "",
        "| Field Path | Populated | Value Preview |",
        "|------------|-----------|---------------|",
    ])

    for entry in field_analysis:
        check = "Y" if entry["populated"] else "-"
        lines.append(f"| `{entry['path']}` | {check} | {entry['preview']} |")

    lines.append("")
    return "\n".join(lines)
