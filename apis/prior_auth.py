"""
Prior Authorization Status API.
Port of: prior-auth-radar/lib/optum-pa-status.ts
"""

import os
import time
from uuid import uuid4

import httpx

from auth import get_optum_bearer_token


PA_STATUS_QUERY = """
query PAStatus($authorizationNumber: String!, $tradingPartnerServiceId: String!) {
  priorAuthorizationStatus(
    authorizationNumber: $authorizationNumber
    tradingPartnerServiceId: $tradingPartnerServiceId
  ) {
    authorizationNumber
    tradingPartnerServiceId
    status {
      statusCode
      statusDescription
      statusCategory
      effectiveDate
      expirationDate
    }
    requestedProcedure {
      procedureCode
      procedureDescription
      serviceTypeCode
      quantity
      unitType
    }
    requestedProvider {
      npi
      organizationName
      firstName
      lastName
    }
    requestingProvider {
      npi
      organizationName
    }
    member {
      memberId
      firstName
      lastName
      dateOfBirth
      groupNumber
    }
    payer {
      name
      payerId
    }
    submittedDate
    scheduledProcedureDate
    urgencyType
    denialInfo {
      isDenied
      denialReason
      denialCode
      appealDeadline
      peerToPeerAvailable
    }
    additionalInfoRequired {
      isRequired
      infoType
      description
      dueDate
    }
    cmsComplianceStatus {
      standardResponseWindowDays
      submittedDate
      responseDeadline
      isResponseOverdue
      daysOverdue
    }
  }
}
""".strip()


def build_variables(user_input: dict) -> dict:
    return {
        "authorizationNumber": user_input["authorizationNumber"],
        "tradingPartnerServiceId": user_input["tradingPartnerServiceId"],
    }


def get_endpoint() -> str:
    url = os.environ.get("OPTUM_PA_STATUS_URL")
    if not url:
        raise RuntimeError("OPTUM_PA_STATUS_URL is not configured in .env")
    return url


def build_headers(token: str) -> dict:
    provider_tax_id = os.environ.get("OPTUM_PROVIDER_TAX_ID", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-optum-consumer-correlation-id": f"api-console-pa-{uuid4()}",
        "environment": "sandbox",
    }
    if provider_tax_id:
        headers["providerTaxId"] = provider_tax_id
    return headers


def execute(user_input: dict) -> dict:
    """Run PA status query. Returns standard result dict."""
    token = get_optum_bearer_token()
    endpoint = get_endpoint()
    headers = build_headers(token)
    variables = build_variables(user_input)

    request_body = {
        "query": PA_STATUS_QUERY,
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

    return {
        "api_name": "Prior Authorization Status",
        "endpoint": endpoint,
        "headers": headers,
        "request_body": request_body,
        "response_status": response.status_code,
        "response_headers": dict(response.headers),
        "response_body": response_body,
        "duration_ms": duration_ms,
    }
