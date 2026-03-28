"""
Claim Pre-Check API with X12 837P builder.
Port of: claim-precheck-starter/lib/optum-claim-precheck.ts
         claim-precheck-starter/lib/x12-builder.ts
"""

import os
import math
import random
import time
from datetime import datetime
from uuid import uuid4

import httpx

from auth import get_optum_bearer_token


CLAIM_PRECHECK_QUERY = """
query getClaimPrecheck($input: ClaimInput!) {
  claimPreCheck(input: $input) {
    transactionId
    x12ResponseData
    responseType
    x12Response277CA
    message
    statusCode
  }
}
""".strip()


# ── X12 837P Builder (port of x12-builder.ts) ──

def _pad(value: str, length: int) -> str:
    return value.ljust(length)[:length]


def _format_date8(date_str: str) -> str:
    """Convert YYYY-MM-DD to YYYYMMDD."""
    return date_str.replace("-", "")


def _now8() -> str:
    d = datetime.now()
    return f"{d.year}{d.month:02d}{d.day:02d}"


def _now4() -> str:
    d = datetime.now()
    return f"{d.hour:02d}{d.minute:02d}"


def _control_number_9() -> str:
    return str(random.randint(100000000, 999999999))


def _control_number_4() -> str:
    return str(random.randint(1000, 9999))


def build_x12_837p(claim: dict) -> str:
    """
    Build an X12 837P claim string from structured claim data.
    Port of claim-precheck-starter/lib/x12-builder.ts
    """
    ctrl9 = _control_number_9()
    ctrl4 = _control_number_4()
    date8 = _now8()
    time4 = _now4()
    segments: list[str] = []

    provider_tax_id = claim.get("providerTaxId") or os.environ.get("OPTUM_PROVIDER_TAX_ID", "")

    # ISA - Interchange Control Header (fixed-width fields)
    segments.append(
        f"ISA*00*{_pad('', 10)}*00*{_pad('', 10)}"
        f"*ZZ*{_pad(provider_tax_id, 15)}*ZZ*{_pad(claim['payerId'], 15)}"
        f"*{date8[2:]}*{time4}*^*00501*{ctrl9}*0*P*:~"
    )

    # GS - Functional Group Header
    segments.append(
        f"GS*HC*{provider_tax_id}*{claim['payerId']}*{date8}*{time4}*{ctrl4}*X*005010X222A1~"
    )

    # ST - Transaction Set Header
    segments.append(f"ST*837*{ctrl4}*005010X222A1~")

    # BHT - Beginning of Hierarchical Transaction
    claim_id = claim.get("claimId", f"CLM{random.randint(100000, 999999)}")
    segments.append(f"BHT*0019*00*{claim_id}*{date8}*{time4}*CH~")

    # 1000A - Submitter Name
    segments.append(f"NM1*41*2*{claim['providerOrganization']}*****46*{provider_tax_id}~")
    segments.append(f"PER*IC*{claim['providerLastName']}*TE*5555555555~")

    # 1000B - Receiver Name
    segments.append(f"NM1*40*2*{claim['payerName']}*****46*{claim['payerId']}~")

    # HL*1 - 2000A Billing Provider
    segments.append("HL*1**20*1~")
    segments.append("PRV*BI*PXC*207Q00000X~")

    # 2010AA - Billing Provider Name
    segments.append(f"NM1*85*2*{claim['providerOrganization']}*****XX*{claim['providerNpi']}~")
    segments.append(f"N3*{claim['providerStreet']}~")
    segments.append(f"N4*{claim['providerCity']}*{claim['providerState']}*{claim['providerZip']}~")
    segments.append(f"REF*EI*{provider_tax_id}~")

    # HL*2 - 2000B Subscriber
    segments.append("HL*2*1*22*0~")
    segments.append("SBR*P*18*******CI~")

    # 2010BA - Subscriber Name
    segments.append(
        f"NM1*IL*1*{claim['patientLastName']}*{claim['patientFirstName']}****MI*{claim['memberId']}~"
    )
    segments.append(f"N3*{claim['patientStreet']}~")
    segments.append(f"N4*{claim['patientCity']}*{claim['patientState']}*{claim['patientZip']}~")
    segments.append(f"DMG*D8*{_format_date8(claim['patientDob'])}*{claim['patientGender']}~")

    # 2010BB - Payer Name
    segments.append(f"NM1*PR*2*{claim['payerName']}*****PI*{claim['payerId']}~")

    # 2300 - Claim Information
    pos_code = claim.get("placeOfService", "11").zfill(2)
    freq_code = claim.get("claimFrequencyCode", "1")
    total_charge = float(claim.get("totalChargeAmount", 0))
    segments.append(f"CLM*{claim_id}*{total_charge:.2f}***{pos_code}:B:{freq_code}*Y*A*Y*Y~")

    # HI - Diagnosis Codes
    diag_codes = claim.get("diagnosisCodes", "")
    if isinstance(diag_codes, str):
        diag_codes = [c.strip() for c in diag_codes.split(",") if c.strip()]
    hi_parts = []
    for i, code in enumerate(diag_codes):
        qualifier = "ABK" if i == 0 else "ABF"
        hi_parts.append(f"{qualifier}:{code}")
    segments.append(f"HI*{'*'.join(hi_parts)}~")

    # 2400 - Service Lines
    service_lines = claim.get("serviceLines", [])
    if not service_lines:
        # Build a single service line from flat fields
        modifiers_str = claim.get("modifiers", "")
        if isinstance(modifiers_str, str):
            modifiers = [m.strip() for m in modifiers_str.split(",") if m.strip()]
        else:
            modifiers = modifiers_str or []

        pointers_str = claim.get("diagnosisPointers", "0")
        if isinstance(pointers_str, str):
            pointers = [int(p.strip()) for p in pointers_str.split(",") if p.strip()]
        else:
            pointers = pointers_str or [0]

        service_lines = [{
            "procedureCode": claim["procedureCode"],
            "chargeAmount": float(claim.get("chargeAmount", 0)),
            "units": int(claim.get("units", 1)),
            "dateOfService": claim.get("dateOfService", str(datetime.now().date())),
            "modifiers": modifiers,
            "diagnosisPointers": pointers,
        }]

    for i, line in enumerate(service_lines):
        segments.append(f"LX*{i + 1}~")

        mod_str = ""
        if line.get("modifiers"):
            mod_str = ":" + ":".join(line["modifiers"])

        diag_ptrs = ":".join(str(p + 1) for p in line.get("diagnosisPointers", [0]))
        charge = float(line["chargeAmount"])
        units = int(line.get("units", 1))

        segments.append(
            f"SV1*HC:{line['procedureCode']}{mod_str}*{charge:.2f}*UN*{units}***{diag_ptrs}~"
        )
        segments.append(f"DTP*472*D8*{_format_date8(line['dateOfService'])}~")

    # Segment count: from ST through SE inclusive, excluding ISA and GS
    seg_count = len(segments) - 2 + 1  # exclude ISA, GS; include SE itself

    # SE - Transaction Set Trailer
    segments.append(f"SE*{seg_count}*{ctrl4}~")

    # GE - Functional Group Trailer
    segments.append(f"GE*1*{ctrl4}~")

    # IEA - Interchange Control Trailer
    segments.append(f"IEA*1*{ctrl9}~")

    return "".join(segments)


# ── API call ──

def build_variables(user_input: dict, x12_string: str | None = None) -> dict:
    """Build GraphQL variables. If x12_string is provided, use it directly."""
    if x12_string:
        return {
            "input": {
                "x12RequestData": x12_string,
                "payerId": user_input.get("payerId", "87726"),
            }
        }
    # Raw mode — user provided x12RequestData directly
    return {
        "input": {
            "x12RequestData": user_input["x12RequestData"],
            "payerId": user_input.get("payerId", "87726"),
        }
    }


def get_endpoint() -> str:
    url = os.environ.get("OPTUM_CLAIM_PRECHECK_URL")
    if not url:
        raise RuntimeError("OPTUM_CLAIM_PRECHECK_URL is not configured in .env")
    return url


def build_headers(token: str) -> dict:
    provider_tax_id = os.environ.get("OPTUM_PROVIDER_TAX_ID", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-optum-consumer-correlation-id": str(uuid4()),
        "environment": "sandbox",
    }
    if provider_tax_id:
        headers["providerTaxId"] = provider_tax_id
    return headers


def execute(user_input: dict, mode: str = "structured") -> dict:
    """
    Run claim pre-check.
    mode="raw" — user_input contains x12RequestData directly.
    mode="structured" — user_input contains structured fields, we build X12.
    """
    token = get_optum_bearer_token()
    endpoint = get_endpoint()
    headers = build_headers(token)

    x12_string = None
    if mode == "structured":
        x12_string = build_x12_837p(user_input)

    variables = build_variables(user_input, x12_string)

    request_body = {
        "query": CLAIM_PRECHECK_QUERY,
        "variables": variables,
    }

    start = time.time()
    response = httpx.post(
        endpoint,
        json=request_body,
        headers=headers,
        timeout=60.0,
    )
    duration_ms = int((time.time() - start) * 1000)

    try:
        response_body = response.json()
    except Exception:
        response_body = {"raw_text": response.text}

    result = {
        "api_name": "Claim Pre-Check",
        "endpoint": endpoint,
        "headers": headers,
        "request_body": request_body,
        "response_status": response.status_code,
        "response_headers": dict(response.headers),
        "response_body": response_body,
        "duration_ms": duration_ms,
    }

    # Include the built X12 for display
    if x12_string:
        result["x12_built"] = x12_string

    return result
