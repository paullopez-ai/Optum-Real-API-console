#!/usr/bin/env python3
"""
Optum Real API Console v1.0
Interactive Python CLI for testing Optum sandbox APIs.

Usage:
    python optum_console.py
"""

import json
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich import box

# Load .env from the script's directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_script_dir, ".env"))

# Ensure our package is importable
sys.path.insert(0, _script_dir)

from models.inputs import (
    InputField,
    ELIGIBILITY_FIELDS, ELIGIBILITY_PRESETS,
    PA_STATUS_FIELDS, PA_STATUS_PRESETS,
    CLAIM_PRECHECK_RAW_FIELDS, CLAIM_PRECHECK_STRUCTURED_FIELDS, CLAIM_PRECHECK_PRESETS,
)
from apis import eligibility, prior_auth, claim_precheck
from output.formatter import (
    pretty_json, parse_x12_segments, analyze_field_population, build_markdown_report,
)
from output.saver import save_json, save_markdown

console = Console()


# ── Startup validation ──

REQUIRED_ENV_VARS = [
    "OPTUM_CLIENT_ID",
    "OPTUM_CLIENT_SECRET",
    "OPTUM_AUTH_URL",
    "OPTUM_PROVIDER_TAX_ID",
]

API_ENV_VARS = {
    1: ["OPTUM_ELIGIBILITY_URL"],
    2: ["OPTUM_PA_STATUS_URL"],
    3: ["OPTUM_CLAIM_PRECHECK_URL"],
}


def check_env_vars():
    """Check that required environment variables are set."""
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        console.print(
            Panel(
                f"[bold red]Missing required environment variables:[/]\n\n"
                + "\n".join(f"  - {v}" for v in missing)
                + "\n\n[dim]Copy .env.example to .env and fill in your credentials.[/]",
                title="Configuration Error",
                border_style="red",
            )
        )
        sys.exit(1)


def check_api_env(api_num: int):
    """Check API-specific env vars before calling."""
    missing = [v for v in API_ENV_VARS.get(api_num, []) if not os.environ.get(v)]
    if missing:
        console.print(f"[bold red]Missing: {', '.join(missing)}[/]")
        console.print("[dim]Add these to your .env file.[/]")
        return False
    return True


# ── Input collection ──

def display_field_table(fields: list[InputField], title: str):
    """Show a table of all input fields with their types and requirements."""
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Req", style="bold")
    table.add_column("Default", style="yellow")
    table.add_column("Description", style="dim")

    current_group = ""
    for f in fields:
        if f.group and f.group != current_group:
            current_group = f.group
            table.add_row(f"[bold magenta]── {current_group} ──[/]", "", "", "", "")

        req = "[bold red]YES[/]" if f.required else "no"
        default = f.default if f.default else "—"
        table.add_row(f.name, f.field_type, req, default, f.description)

    console.print(table)


def display_presets(presets: list[dict]) -> dict | None:
    """Show presets and let user pick one. Returns values dict or None."""
    if not presets:
        return None

    console.print("\n[bold]Available presets:[/]")
    for i, p in enumerate(presets, 1):
        console.print(f"  [cyan]{i}[/]. {p['name']}")
    console.print(f"  [cyan]0[/]. Manual entry")

    choice = Prompt.ask("Select preset", default="1")
    try:
        idx = int(choice)
        if 1 <= idx <= len(presets):
            console.print(f"[green]Loaded preset:[/] {presets[idx - 1]['name']}\n")
            return presets[idx - 1]["values"].copy()
    except ValueError:
        pass

    return None


def collect_inputs(fields: list[InputField], presets: list[dict]) -> dict:
    """Collect input values from user, with preset support."""
    display_field_table(fields, "Input Fields")

    preset_values = display_presets(presets)
    if preset_values:
        # Show loaded values and allow overrides
        console.print("[dim]Press Enter to accept each value, or type a new value:[/]\n")
        result = {}
        for f in fields:
            default = preset_values.get(f.name, f.default or "")
            value = Prompt.ask(f"  {f.name}", default=str(default) if default else "")
            if not value and f.required:
                console.print(f"  [red]Required field — cannot be empty[/]")
                value = Prompt.ask(f"  {f.name}")
            result[f.name] = value
        return result

    # Manual entry
    console.print("\n[dim]Enter values for each field (press Enter for default):[/]\n")
    result = {}
    for f in fields:
        default = f.default or ""
        prompt_str = f"  {f.name}"
        if f.required:
            prompt_str += " [red]*[/]"

        value = Prompt.ask(prompt_str, default=str(default) if default else "")
        if not value and f.required:
            while not value:
                console.print(f"  [red]Required field — cannot be empty[/]")
                value = Prompt.ask(prompt_str)
        result[f.name] = value
    return result


# ── Request review and confirmation ──

def show_request_preview(endpoint: str, headers: dict, body: dict):
    """Display the request that will be sent."""
    # Build a safe headers display (mask auth token)
    safe_headers = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            safe_headers[k] = v[:25] + "..." if len(v) > 25 else v
        else:
            safe_headers[k] = v

    console.print(Panel(
        f"[bold]POST[/] {endpoint}\n\n"
        f"[bold]Headers:[/]\n"
        + "\n".join(f"  {k}: {v}" for k, v in safe_headers.items())
        + "\n\n[bold]Body (variables):[/]\n"
        + pretty_json(body.get("variables", {})),
        title="REQUEST PREVIEW",
        border_style="blue",
        box=box.DOUBLE,
    ))


# ── Response display ──

def show_response(result: dict):
    """Display the API response with syntax highlighting and field analysis."""
    status = result["response_status"]
    duration = result["duration_ms"]
    body = result["response_body"]

    # Status line
    status_color = "green" if status == 200 else "red"
    console.print(f"\n[bold {status_color}]HTTP {status}[/]  ({duration}ms)\n")

    # Check for GraphQL errors
    if isinstance(body, dict) and "errors" in body:
        console.print("[bold red]GraphQL Errors:[/]")
        for err in body["errors"]:
            msg = err.get("message", "Unknown error")
            classification = err.get("extensions", {}).get("classification", "")
            console.print(f"  [red]- {msg}[/]")
            if classification:
                console.print(f"    [dim]Classification: {classification}[/]")
        console.print()

    # Full JSON response
    json_str = pretty_json(body)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True, word_wrap=True)
    console.print(Panel(syntax, title="RESPONSE BODY", border_style="green"))

    # X12 segment breakdown (for Claim Pre-Check)
    x12_fields = {}
    if isinstance(body, dict):
        precheck_data = body.get("data", {}).get("claimPreCheck", {})
        if precheck_data:
            for field_name in ["x12ResponseData", "x12Response277CA"]:
                x12_data = precheck_data.get(field_name, "")
                if x12_data:
                    x12_fields[field_name] = x12_data
                    console.print(Panel(
                        parse_x12_segments(x12_data),
                        title=f"X12 SEGMENTS: {field_name}",
                        border_style="yellow",
                    ))

    # Also show the built X12 if we constructed it
    if "x12_built" in result:
        console.print(Panel(
            parse_x12_segments(result["x12_built"]),
            title="X12 837P BUILT (sent as input)",
            border_style="cyan",
        ))

    # Field population analysis
    if isinstance(body, dict):
        analysis = analyze_field_population(body)
        populated = sum(1 for a in analysis if a["populated"])
        total = len(analysis)

        table = Table(
            title=f"Field Population: {populated}/{total} populated",
            box=box.SIMPLE,
            show_lines=False,
        )
        table.add_column("Field Path", style="cyan", max_width=70)
        table.add_column("Pop", style="bold", justify="center", width=3)
        table.add_column("Preview", style="dim", max_width=40)

        for entry in analysis:
            check = "[green]Y[/]" if entry["populated"] else "[red]-[/]"
            table.add_row(entry["path"], check, entry["preview"])

        console.print(table)

    return x12_fields


# ── Save output ──

def prompt_save(result: dict, x12_fields: dict):
    """Ask user if they want to save output."""
    console.print()
    choice = Prompt.ask(
        "Save output? [bold][j][/]son / [bold][m][/]arkdown / [bold][b][/]oth / [bold][n][/]o",
        default="n",
    ).lower()

    if choice in ("n", ""):
        return

    api_name = result["api_name"]
    body = result["response_body"]
    analysis = analyze_field_population(body) if isinstance(body, dict) else []

    if choice in ("j", "b"):
        path = save_json(
            api_name=api_name,
            endpoint=result["endpoint"],
            request_headers=result["headers"],
            request_body=result["request_body"],
            response_status=result["response_status"],
            response_headers=result["response_headers"],
            response_body=body,
            duration_ms=result["duration_ms"],
        )
        console.print(f"  [green]JSON saved:[/] {path}")

    if choice in ("m", "b"):
        md = build_markdown_report(
            api_name=api_name,
            endpoint=result["endpoint"],
            request_headers=result["headers"],
            request_body=result["request_body"],
            response_status=result["response_status"],
            response_headers=result["response_headers"],
            response_body=body,
            field_analysis=analysis,
            duration_ms=result["duration_ms"],
            x12_fields=x12_fields or None,
        )
        path = save_markdown(api_name, md)
        console.print(f"  [green]Markdown saved:[/] {path}")


# ── API flows ──

def run_eligibility():
    """Flow for Pre-Service Eligibility & Benefits API."""
    if not check_api_env(1):
        return

    console.print(Panel(
        "[bold]Pre-Service Eligibility & Benefits[/]\n"
        "Checks member eligibility, benefits, deductibles, copays, coinsurance, network status.\n"
        f"[dim]Endpoint: {os.environ.get('OPTUM_ELIGIBILITY_URL', 'NOT SET')}[/]",
        title="API 1",
        border_style="cyan",
    ))

    user_input = collect_inputs(ELIGIBILITY_FIELDS, ELIGIBILITY_PRESETS)

    # Build preview
    from apis.eligibility import build_variables, build_headers, get_endpoint, ELIGIBILITY_QUERY
    from auth import get_optum_bearer_token

    console.print("\n[bold]Authenticating with Optum...[/]")
    try:
        token = get_optum_bearer_token()
        console.print("[green]Token acquired.[/]\n")
    except Exception as e:
        console.print(f"[bold red]Auth failed:[/] {e}")
        return

    headers = build_headers(token)
    variables = build_variables(user_input)
    request_body = {"query": ELIGIBILITY_QUERY, "variables": variables}

    show_request_preview(get_endpoint(), headers, request_body)

    if not Confirm.ask("Send request?", default=True):
        console.print("[yellow]Cancelled.[/]")
        return

    console.print("[bold]Sending request...[/]")
    try:
        result = eligibility.execute(user_input)
    except Exception as e:
        console.print(f"[bold red]Request failed:[/] {e}")
        return

    x12_fields = show_response(result)
    prompt_save(result, x12_fields)


def run_prior_auth():
    """Flow for Prior Authorization Status API."""
    if not check_api_env(2):
        return

    console.print(Panel(
        "[bold]Prior Authorization Status[/]\n"
        "Query PA status by authorization number and trading partner ID.\n"
        f"[dim]Endpoint: {os.environ.get('OPTUM_PA_STATUS_URL', 'NOT SET')}[/]",
        title="API 2",
        border_style="cyan",
    ))

    user_input = collect_inputs(PA_STATUS_FIELDS, PA_STATUS_PRESETS)

    from apis.prior_auth import build_variables, build_headers, get_endpoint, PA_STATUS_QUERY
    from auth import get_optum_bearer_token

    console.print("\n[bold]Authenticating with Optum...[/]")
    try:
        token = get_optum_bearer_token()
        console.print("[green]Token acquired.[/]\n")
    except Exception as e:
        console.print(f"[bold red]Auth failed:[/] {e}")
        return

    headers = build_headers(token)
    variables = build_variables(user_input)
    request_body = {"query": PA_STATUS_QUERY, "variables": variables}

    show_request_preview(get_endpoint(), headers, request_body)

    if not Confirm.ask("Send request?", default=True):
        console.print("[yellow]Cancelled.[/]")
        return

    console.print("[bold]Sending request...[/]")
    try:
        result = prior_auth.execute(user_input)
    except Exception as e:
        console.print(f"[bold red]Request failed:[/] {e}")
        return

    x12_fields = show_response(result)
    prompt_save(result, x12_fields)


def run_claim_precheck():
    """Flow for Claim Pre-Check API."""
    if not check_api_env(3):
        return

    console.print(Panel(
        "[bold]Claim Pre-Check[/]\n"
        "Validate an 837 X12 claim for HIPAA, eligibility, COB, prior auth, and payer policies.\n"
        f"[dim]Endpoint: {os.environ.get('OPTUM_CLAIM_PRECHECK_URL', 'NOT SET')}[/]",
        title="API 3",
        border_style="cyan",
    ))

    # Choose input mode
    console.print("\n[bold]Input Mode:[/]")
    console.print("  [cyan]1[/]. Structured fields (builds X12 for you)")
    console.print("  [cyan]2[/]. Raw X12 paste")
    mode_choice = Prompt.ask("Select mode", default="1")

    if mode_choice == "2":
        # Raw X12 mode
        user_input = collect_inputs(CLAIM_PRECHECK_RAW_FIELDS, [])
        mode = "raw"
    else:
        # Structured mode
        user_input = collect_inputs(CLAIM_PRECHECK_STRUCTURED_FIELDS, CLAIM_PRECHECK_PRESETS)

        # Use provider tax ID from .env if not provided
        if not user_input.get("providerTaxId"):
            user_input["providerTaxId"] = os.environ.get("OPTUM_PROVIDER_TAX_ID", "")

        # Show the built X12
        console.print("\n[bold]Building X12 837P...[/]")
        try:
            x12_string = claim_precheck.build_x12_837p(user_input)
            console.print(Panel(
                parse_x12_segments(x12_string),
                title="BUILT X12 837P",
                border_style="cyan",
            ))
        except Exception as e:
            console.print(f"[bold red]X12 build failed:[/] {e}")
            return
        mode = "structured"

    from apis.claim_precheck import build_variables, build_headers, get_endpoint, CLAIM_PRECHECK_QUERY
    from auth import get_optum_bearer_token

    console.print("\n[bold]Authenticating with Optum...[/]")
    try:
        token = get_optum_bearer_token()
        console.print("[green]Token acquired.[/]\n")
    except Exception as e:
        console.print(f"[bold red]Auth failed:[/] {e}")
        return

    headers = build_headers(token)
    x12_for_vars = x12_string if mode == "structured" else None
    variables = build_variables(user_input, x12_for_vars)
    request_body = {"query": CLAIM_PRECHECK_QUERY, "variables": variables}

    show_request_preview(get_endpoint(), headers, request_body)

    if not Confirm.ask("Send request?", default=True):
        console.print("[yellow]Cancelled.[/]")
        return

    console.print("[bold]Sending request...[/]")
    try:
        result = claim_precheck.execute(user_input, mode=mode)
    except Exception as e:
        console.print(f"[bold red]Request failed:[/] {e}")
        return

    x12_fields = show_response(result)
    prompt_save(result, x12_fields)


# ── Main menu ──

def main():
    check_env_vars()

    while True:
        console.print()
        console.print(Panel(
            "[bold white]1.[/] Pre-Service Eligibility & Benefits\n"
            "[bold white]2.[/] Prior Authorization Status\n"
            "[bold white]3.[/] Claim Pre-Check\n"
            "[bold white]0.[/] Exit",
            title="[bold]Optum Real API Console v1.0[/]",
            subtitle="[dim]sandbox testing tool[/]",
            border_style="bright_blue",
            box=box.DOUBLE,
            padding=(1, 2),
        ))

        choice = Prompt.ask("Select API", choices=["0", "1", "2", "3"], default="0")

        if choice == "0":
            console.print("[dim]Goodbye.[/]")
            break
        elif choice == "1":
            run_eligibility()
        elif choice == "2":
            run_prior_auth()
        elif choice == "3":
            run_claim_precheck()


if __name__ == "__main__":
    main()
