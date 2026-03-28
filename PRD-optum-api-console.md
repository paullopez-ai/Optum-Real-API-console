# PRD: Optum Real API Console — Python CLI Testing Tool

**Version:** 1.0
**Date:** 2026-03-27
**Author:** Paul Lopez
**Status:** Draft

---

## 1. Purpose

Build a Python console application that allows a developer to interactively test the Optum Real APIs used in the three existing Next.js POC applications (patient-cost-clarity-starter, prior-auth-radar, claim-precheck-starter). The tool must display all input fields for each API, send requests to the Optum sandbox, and display the full raw response in its native format (JSON/X12). Users can save outputs as Markdown or JSON files.

This tool answers the questions raised in the March 2026 demo meeting:
- What is the raw input and output for each API?
- Which fields are mandatory vs. optional?
- What does the JSON coming back actually look like?
- Are all response fields populated or only some?

---

## 2. Scope

### Phase 1 (This PRD): Three APIs from the existing POCs

| # | API Name | Endpoint | Used In |
|---|----------|----------|---------|
| 1 | **Pre-Service Eligibility & Benefits** | `https://sandbox-apigw.optum.com/oihub/eligibility/v1/pre-service/member` | patient-cost-clarity-starter |
| 2 | **Prior Authorization Status** | `https://sandbox-apigw.optum.com/oihub/prior-auth/v1/graphql` | prior-auth-radar |
| 3 | **Claim Pre-Check** | `https://sandbox-apigw.optum.com/oihub/pre-service/v1/claim/precheck` | claim-precheck-starter |

### Future Phases
The architecture must support adding the remaining Optum Real APIs (Patient Benefit Check, Claims Inquiry, Claim Actions, Document Search) with minimal code changes.

---

## 3. Reference Documents

All reference materials reside in the project folder `/Optum-Real-API-console/`:

| Document | Purpose |
|----------|---------|
| `Pre_Service_Eligibility.json` | OpenAPI 3.0 spec for the Eligibility API — full GraphQL schema, request/response models |
| `Claims_Pre_Check.json` | OpenAPI 3.0 spec for the Claim Pre-Check API — GraphQL schema, payer IDs, status codes |
| `Claim_Actions.json` | OpenAPI 3.0 spec for Claim Actions API (future phase reference) |
| `optum-benefit-check-api-quick-start.md` | Quick start guide: Patient Benefit Check API operations, field requirements, outcome codes |
| `optum-auth-referral-api-quick-start.md` | Quick start guide: Prior Auth Status API fields, PA categories, CMS compliance |
| `optum-claim-precheck-api-quick-start.md` | Quick start guide: Claim Pre-Check API, X12 input/output, status codes |
| `optum-claims-inquiry-api-quick-start.md` | Quick start guide for Claims Inquiry (future phase) |
| `optum-claim-actions-api-quick-start.md` | Quick start guide for Claim Actions (future phase) |
| `optum-document-search-api-quick-start.md` | Quick start guide for Document Search (future phase) |
| `Real Claim Precheck_API.xlsx` | Excel reference for Claim Pre-Check field mapping |
| `Real_Patient_Benefit _Check_API.xlsx` | Excel reference for Patient Benefit Check field mapping |
| `Real_DocumentSearch_API.xlsx` | Excel reference for Document Search field mapping |

### Existing POC Source Code (Convert from TypeScript to Python)

The following files from the three Next.js POCs contain the working API integration code that must be ported to Python:

**Authentication (shared across all APIs):**
- `patient-cost-clarity-starter/lib/optum-auth.ts` — OAuth 2.0 client credentials flow, token caching with 60-second buffer

**API 1: Pre-Service Eligibility & Benefits:**
- `patient-cost-clarity-starter/lib/optum-eligibility.ts` — Full `CheckEligibility` GraphQL query (534 lines of field selection), variable builder, response extraction
- `patient-cost-clarity-starter/lib/optum-benefit-check.ts` — Derives benefit breakdown from eligibility response
- `patient-cost-clarity-starter/types/optum.types.ts` — Complete TypeScript interfaces for all eligibility response types (365 lines)

**API 2: Prior Authorization Status:**
- `prior-auth-radar/lib/optum-pa-status.ts` — `PAStatus` GraphQL query, request builder, response extraction

**API 3: Claim Pre-Check:**
- `claim-precheck-starter/lib/optum-claim-precheck.ts` — `getClaimPrecheck` GraphQL query, request builder
- `claim-precheck-starter/lib/x12-builder.ts` — Builds X12 837P claim strings from structured form data

---

## 4. Technical Architecture

### 4.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Team requirement |
| HTTP client | `httpx` | Async support, modern API, timeout handling |
| CLI framework | Standard `input()` + `rich` library | Rich provides colored tables, panels, and syntax highlighting for JSON/X12 output in the terminal |
| Configuration | `.env` file via `python-dotenv` | Same pattern as the existing Next.js POCs |
| Output | `json` stdlib + custom Markdown formatter | Save responses as `.json` or `.md` files |

### 4.2 File Structure

```
Optum-Real-API-console/
├── optum_console.py          # Main entry point — menu loop, API selection
├── auth.py                   # OAuth 2.0 token management (port of optum-auth.ts)
├── apis/
│   ├── __init__.py
│   ├── eligibility.py        # Pre-Service Eligibility API (port of optum-eligibility.ts)
│   ├── prior_auth.py         # Prior Auth Status API (port of optum-pa-status.ts)
│   └── claim_precheck.py     # Claim Pre-Check API (port of optum-claim-precheck.ts + x12-builder.ts)
├── models/
│   ├── __init__.py
│   └── inputs.py             # Input field definitions: name, type, required/optional, default value
├── output/
│   ├── __init__.py
│   ├── formatter.py          # JSON pretty-printer, Markdown generator, X12 segment parser
│   └── saver.py              # File save logic (JSON and Markdown)
├── .env.example              # Template with all required environment variables
├── requirements.txt          # httpx, python-dotenv, rich
├── README.md                 # Setup and usage instructions
│
│ # Existing reference documents (already in folder):
├── Pre_Service_Eligibility.json
├── Claims_Pre_Check.json
├── Claim_Actions.json
├── optum-benefit-check-api-quick-start.md
├── optum-auth-referral-api-quick-start.md
├── optum-claim-precheck-api-quick-start.md
├── optum-claims-inquiry-api-quick-start.md
├── optum-claim-actions-api-quick-start.md
├── optum-document-search-api-quick-start.md
├── Real Claim Precheck_API.xlsx
├── Real_Patient_Benefit _Check_API.xlsx
└── Real_DocumentSearch_API.xlsx
```

### 4.3 Environment Variables

Create `.env.example` with:

```bash
# OAuth 2.0 Credentials (from marketplace.optum.com)
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret

# Auth endpoint (same for all Optum Real APIs)
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token

# API Endpoints
OPTUM_ELIGIBILITY_URL=https://sandbox-apigw.optum.com/oihub/eligibility/v1/pre-service/member
OPTUM_PA_STATUS_URL=https://sandbox-apigw.optum.com/oihub/prior-auth/v1/graphql
OPTUM_CLAIM_PRECHECK_URL=https://sandbox-apigw.optum.com/oihub/pre-service/v1/claim/precheck

# Provider Tax ID (goes in HTTP headers, NOT GraphQL variables)
OPTUM_PROVIDER_TAX_ID=your_provider_tax_id
```

---

## 5. Functional Requirements

### 5.1 Main Menu

On launch, display:

```
╔══════════════════════════════════════════════╗
║       Optum Real API Console v1.0            ║
╠══════════════════════════════════════════════╣
║  1. Pre-Service Eligibility & Benefits       ║
║  2. Prior Authorization Status               ║
║  3. Claim Pre-Check                          ║
║  0. Exit                                     ║
╚══════════════════════════════════════════════╝
Select API [1-3, 0 to exit]:
```

After a successful API call, return to this menu.

### 5.2 Input Collection Flow

For each API, the program must:

1. **Display all input fields** in a table showing: field name, type, required/optional, description, and default value (if any)
2. **Prompt the user for each field** — pressing Enter accepts the default value
3. **Validate required fields** are not empty before sending
4. **Show the complete request payload** (the JSON body that will be POST'd) and ask for confirmation before sending
5. **Offer preset test scenarios** — user can type `preset` or `p` to load a predefined set of test values (ported from the mock data in the POCs)

### 5.3 API-Specific Input Fields

#### API 1: Pre-Service Eligibility & Benefits

Source: `patient-cost-clarity-starter/lib/optum-eligibility.ts` lines 545-563 and `patient-cost-clarity-starter/types/optum.types.ts` lines 4-17

GraphQL Operation: `CheckEligibility`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `memberId` | string | **Yes** | — | Member ID (e.g., `963997463`) |
| `firstName` | string | **Yes** | — | Subscriber first name |
| `lastName` | string | **Yes** | — | Subscriber last name |
| `groupNumber` | string | **Yes** | — | Insurance group number |
| `dateOfBirth` | string | **Yes** | — | Format: `YYYY-MM-DD` |
| `serviceStartDate` | string | **Yes** | today | Service start date `YYYY-MM-DD` |
| `serviceEndDate` | string | **Yes** | today | Service end date `YYYY-MM-DD` |
| `payerId` | string | **Yes** | — | Payer ID (e.g., `87726`) |
| `providerNPI` | string | **Yes** | — | Provider NPI number |
| `providerFirstName` | string | **Yes** | `Sample` | Provider first name |
| `providerLastName` | string | **Yes** | `Provider` | Provider last name |
| `serviceLevelCodes` | string[] | Optional | `["30"]` | Service type codes (comma-separated) |

**GraphQL Query** (port verbatim from `optum-eligibility.ts` lines 9-543):

```graphql
query CheckEligibility($input: EligibilityInput!) {
  checkEligibility(input: $input) {
    eligibility {
      eligibilityInfo {
        trnId
        member {
          memberId, firstName, lastName, middleName, suffix,
          dateOfBirth, gender, relationshipCode, dependentSequenceNumber,
          individualRelationship { code, description }
          relationshipType { code, description }
        }
        contact { addresses { type, street1, street2, city, state, country, zip, zip4 } }
        insuranceInfo {
          policyNumber, eligibilityStartDate, eligibilityEndDate,
          planStartDate, planEndDate, policyStatus, planTypeDescription,
          groupName, address { type, street1, street2, city, state, country, zip, zip4 },
          stateOfIssueCode, productType, productId, productCode, payerId,
          lineOfBusinessCode, governmentProgramCode, coverageType,
          insuranceTypeCode, insuranceType, paidThroughDate, consumerName
        }
        associatedIds {
          alternateId, medicaidRecipientId, exchangeMemberId,
          alternateSubscriberId, hicNumber, mbiNumber,
          subscriberMemberFacingIdentifier, survivingSpouseId,
          subscriberId, memberReplacementId, legacyMemberId,
          healthInsuranceExchangeId
        }
        planLevels {
          level
          family { networkStatus, planAmount, planAmountFrequency, remainingAmount }
          individual { networkStatus, planAmount, planAmountFrequency, remainingAmount }
        }
        delegatedInfo {
          entity, payerId
          contact { phone, fax, email }
          addresses { type, street1, street2, city, state, country, zip, zip4 }
        }
      }
      primaryCarePhysician {
        lastName, firstName, middleName, phoneNumber,
        address { type, street1, street2, city, state, country, zip, zip4 },
        affiliateHospitalName, providerGroupName, pcpSpeciality,
        pcpStartDate, pcpEndDate, providerNPI, providerTIN,
        acoNetworkDescription, acoNetworkId
      }
      providerNetwork { status, tier, speciality }
      serviceLevels {
        vendorServices { key, vendorName, url, phone, serviceDescription, serviceTypeCode }
        family { networkStatus, services { ... full service detail tree ... } }
        individual { networkStatus, services { ... full service detail tree ... } }
      }
      additionalInfo {
        fundingType, fundingArrangementDescription, businessSegment,
        sizeDefinitionDescription, revenueArrangementDescription,
        hsa, cdhp, cmsHId, cmsContractId, benefitPlanId,
        virtualVisit, hraBalance, hraMessage,
        medicareGuidelines, medicareEntitlementReason
      }
    }
  }
}
```

**Implementation note:** Port the COMPLETE GraphQL query from `optum-eligibility.ts` lines 9-543 verbatim. This includes the deeply nested `serviceLevels` with `coPay`, `coInsurance`, `deductible`, `benefitsAllowed`, `benefitsRemaining`, `coPayList`, and `coInsuranceList` sub-trees. The full query is ~534 lines. Do not abbreviate it.

**Preset test data** (from `patient-cost-clarity-starter/lib/patients.ts`):
- Member ID: `963997463`, Name: `Aisha Rahman`, DOB: `1985-06-15`, Group: `GRP-2026-BRONZE`, Payer: `87726`

#### API 2: Prior Authorization Status

Source: `prior-auth-radar/lib/optum-pa-status.ts` lines 3-71

GraphQL Operation: `PAStatus`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `authorizationNumber` | string | **Yes** | — | PA authorization number (e.g., `AUTH-2026-0210-4471`) |
| `tradingPartnerServiceId` | string | **Yes** | — | Payer trading partner ID (e.g., `UHC-87726`) |

**GraphQL Query** (port verbatim from `optum-pa-status.ts` lines 3-71):

```graphql
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
```

**Preset test data** (from `prior-auth-radar/lib/pa-items.ts`):
- PA #1: `AUTH-2026-0210-4471` / `UHC-87726` (Approved — standard)
- PA #2: `AUTH-2026-0215-8823` / `UHC-87726` (Pending clinical review)
- PA #3: `AUTH-2026-0112-3309` / `UHC-87726` (Denied — medical necessity)

#### API 3: Claim Pre-Check

Source: `claim-precheck-starter/lib/optum-claim-precheck.ts` lines 4-13 and `claim-precheck-starter/lib/x12-builder.ts`

GraphQL Operation: `getClaimPrecheck`

The Claim Pre-Check API takes a raw X12 837P string as input. The console must support two input modes:

**Mode A: Raw X12 input** — User pastes a complete X12 837P string directly.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `x12RequestData` | string | **Yes** | — | Complete X12 837P claim string |
| `payerId` | string | **Yes** | — | Payer ID (e.g., `87726`) |

**Mode B: Structured input → X12 builder** — User enters structured claim fields and the program builds the X12 string (porting the logic from `x12-builder.ts`).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `claimId` | string | **Yes** | auto-generated | Claim identifier |
| `patientFirstName` | string | **Yes** | — | Patient first name |
| `patientLastName` | string | **Yes** | — | Patient last name |
| `patientDob` | string | **Yes** | — | Patient DOB `YYYY-MM-DD` |
| `patientGender` | string | **Yes** | — | `M` or `F` |
| `patientAddress.street` | string | **Yes** | — | Patient street address |
| `patientAddress.city` | string | **Yes** | — | Patient city |
| `patientAddress.state` | string | **Yes** | — | Patient state (2-letter) |
| `patientAddress.zip` | string | **Yes** | — | Patient ZIP code |
| `memberId` | string | **Yes** | — | Insurance member ID |
| `payerId` | string | **Yes** | `87726` | Payer ID |
| `payerName` | string | **Yes** | `UNITED HEALTHCARE` | Payer name |
| `providerNpi` | string | **Yes** | — | Provider NPI (10 digits) |
| `providerTaxId` | string | **Yes** | from `.env` | Provider TIN |
| `providerOrganization` | string | **Yes** | — | Provider organization name |
| `providerLastName` | string | **Yes** | — | Provider contact last name |
| `providerAddress.street` | string | **Yes** | — | Provider street |
| `providerAddress.city` | string | **Yes** | — | Provider city |
| `providerAddress.state` | string | **Yes** | — | Provider state |
| `providerAddress.zip` | string | **Yes** | — | Provider ZIP |
| `placeOfService` | string | **Yes** | `11` | Place of service code |
| `claimFrequencyCode` | string | **Yes** | `1` | Frequency code (1=original) |
| `totalChargeAmount` | float | **Yes** | — | Total charge in dollars |
| `diagnosisCodes` | string[] | **Yes** | — | Comma-separated ICD-10 codes |
| **Service Lines** (repeating group): |
| `procedureCode` | string | **Yes** | — | CPT code |
| `chargeAmount` | float | **Yes** | — | Line charge |
| `units` | int | **Yes** | `1` | Number of units |
| `dateOfService` | string | **Yes** | today | `YYYY-MM-DD` |
| `modifiers` | string[] | Optional | — | Comma-separated modifiers |
| `diagnosisPointers` | int[] | Optional | `[0]` | Comma-separated 0-based indices |

**GraphQL Query** (from `optum-claim-precheck.ts` lines 4-13):

```graphql
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
```

**Preset test data** (from `claim-precheck-starter/lib/mock/sample-claims.ts`):
- Load a sample 837P with predefined patient/provider/claim data

**Critical constraints** (from quick start guide):
- Only ONE claim per request (status code `702` if multiple)
- TIN in `providerTaxId` header MUST match TIN in X12 data (status code `701` on mismatch)
- Supported UHC Payer IDs: `87726, 03432, 96385, 95467, 86050, 86047, 95378, 06111, 00773, 36273, 37602, 39026, 41161, 41194, 52461, 65088, 74227, 76342, 76343, 78857, 81400, 88337, 94265, 95958, USN01, 25463, UHNDC`

### 5.4 HTTP Headers (Universal for All APIs)

All API requests must include these headers (ported from the existing POC code):

```python
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}",
    "providerTaxId": OPTUM_PROVIDER_TAX_ID,      # HTTP header, NOT a GraphQL variable
    "environment": "sandbox",                      # Required for sandbox
    "x-optum-consumer-correlation-id": str(uuid4()),  # Unique per request
}
```

**Key gotcha from all three POCs:** `providerTaxId` goes in HTTP headers, never in GraphQL variables.

### 5.5 Request Display

Before sending, display:

```
┌─ REQUEST ─────────────────────────────────────────┐
│ POST https://sandbox-apigw.optum.com/oihub/...    │
│                                                    │
│ Headers:                                           │
│   Authorization: Bearer eyJ...                     │
│   providerTaxId: 448835440                        │
│   environment: sandbox                             │
│   x-optum-consumer-correlation-id: abc-123-...    │
│                                                    │
│ Body (GraphQL):                                    │
│   { "query": "...", "variables": { ... } }        │
└───────────────────────────────────────────────────┘
Send request? [Y/n]:
```

### 5.6 Response Display

Display the full raw response with syntax highlighting:

1. **HTTP Status** — Status code and reason
2. **Response Headers** — All headers returned
3. **Response Body** — Full JSON response, pretty-printed with syntax highlighting via `rich`
4. **Field Population Analysis** — Show which response fields are populated vs. null/empty (addresses the meeting question "are all of them populated or some populated")
5. **For Claim Pre-Check specifically:** Parse and display the `x12ResponseData` and `x12Response277CA` fields with X12 segment-by-segment breakdown (one segment per line, replacing `~` delimiters with newlines)

### 5.7 Output Saving

After displaying the response, prompt:

```
Save output? [j]son / [m]arkdown / [b]oth / [n]o:
```

**JSON output** (`output_YYYYMMDD_HHMMSS_apiname.json`):
```json
{
  "api": "Pre-Service Eligibility",
  "endpoint": "https://sandbox-apigw.optum.com/oihub/eligibility/v1/pre-service/member",
  "timestamp": "2026-03-27T14:30:00Z",
  "request": {
    "headers": { ... },
    "body": { ... }
  },
  "response": {
    "status_code": 200,
    "headers": { ... },
    "body": { ... }
  }
}
```

**Markdown output** (`output_YYYYMMDD_HHMMSS_apiname.md`):

```markdown
# Optum API Test: Pre-Service Eligibility
**Date:** 2026-03-27 14:30:00
**Endpoint:** `https://sandbox-apigw.optum.com/oihub/eligibility/v1/pre-service/member`
**HTTP Status:** 200 OK

## Request
### Headers
| Header | Value |
|--------|-------|
| providerTaxId | 448835440 |
| environment | sandbox |

### GraphQL Variables
```json
{ ... }
```

## Response
### Full JSON Response
```json
{ ... }
```

### Field Population Summary
| Field Path | Populated | Value Preview |
|------------|-----------|---------------|
| data.checkEligibility.eligibility[0].eligibilityInfo.member.memberId | ✓ | "963997463" |
| data.checkEligibility.eligibility[0].eligibilityInfo.member.middleName | ✗ | null |
...
```

Save files to a `results/` subfolder within the project directory.

### 5.8 Error Handling

Port the error handling patterns from the existing POCs:

1. **GraphQL returns HTTP 200 even for errors** — Always check for `errors` array in the response body before accessing `data`. Display GraphQL errors with their `message`, `locations`, and `extensions.classification`.

2. **OAuth token errors** — Display the full error response text if authentication fails. Common issues: expired credentials, wrong auth URL.

3. **Missing environment variables** — On startup, check all required env vars. If any are missing, display which ones and exit with instructions.

4. **Network errors** — Catch `httpx` connection/timeout errors and display with retry suggestion.

---

## 6. Authentication Module (`auth.py`)

Port directly from `patient-cost-clarity-starter/lib/optum-auth.ts`:

```python
# Pseudocode — port the exact logic from optum-auth.ts

import httpx
import time
from dataclasses import dataclass

@dataclass
class TokenCache:
    token: str
    expires_at: float  # Unix timestamp in seconds

_cached_token: TokenCache | None = None

async def get_optum_bearer_token() -> str:
    """
    OAuth 2.0 client credentials flow.
    Caches token with 60-second safety buffer before expiry.
    Port of: patient-cost-clarity-starter/lib/optum-auth.ts
    """
    global _cached_token

    # Check cache — 60-second buffer before expiry
    if _cached_token and time.time() < _cached_token.expires_at - 60:
        return _cached_token.token

    # Fetch new token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OPTUM_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": OPTUM_CLIENT_ID,
                "client_secret": OPTUM_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    response.raise_for_status()
    data = response.json()

    _cached_token = TokenCache(
        token=data["access_token"],
        expires_at=time.time() + data["expires_in"],
    )

    return _cached_token.token
```

---

## 7. X12 837P Builder (`apis/claim_precheck.py`)

Port the X12 builder from `claim-precheck-starter/lib/x12-builder.ts`. Key implementation details:

- **ISA segment**: Fixed-width fields — padded to exact lengths (15 chars for IDs, 10 chars for auth info)
- **GS segment**: Functional group with version `005010X222A1`
- **BHT segment**: `0019*00*{claimId}*{date}*{time}*CH`
- **NM1 segments**: Submitter (qualifier `41`), Receiver (`40`), Billing Provider (`85`), Subscriber (`IL`), Payer (`PR`), Rendering Provider (`82`)
- **CLM segment**: Claim info with place of service formatted as `{POS}:B:{freq}`
- **HI segment**: Diagnosis codes with `ABK` for primary, `ABF` for secondary
- **SV1 segments**: Service lines with `HC:{cpt}:{modifiers}*{charge}*UN*{units}***{pointers}`
- **DTP*472**: Date of service per line
- **Segment count in SE**: Count from ST through SE (inclusive), excluding ISA and GS
- **Trailers**: SE, GE, IEA with matching control numbers

Reference implementation: `claim-precheck-starter/lib/x12-builder.ts` (143 lines)

---

## 8. Adding New APIs (Extensibility)

Each API module in `apis/` must follow this pattern:

```python
# apis/base.py
class OptumAPI:
    name: str                    # Display name
    endpoint_env_var: str        # Env var key for the URL
    graphql_query: str           # The GraphQL query string
    input_fields: list[Field]    # Field definitions (name, type, required, default, description)

    def build_variables(self, user_input: dict) -> dict:
        """Build GraphQL variables from user input."""

    def format_response(self, response: dict) -> str:
        """Custom response formatting (e.g., X12 parsing for Claim Pre-Check)."""
```

To add a new API (e.g., Claims Inquiry), create `apis/claims_inquiry.py` implementing this interface and register it in `optum_console.py`.

---

## 9. User Flow Summary

```
1. Launch: python optum_console.py
2. Startup validation: Check .env, verify all required vars exist
3. Main menu: Select API (1-3) or exit (0)
4. Input phase:
   a. Display field table with types, required/optional, defaults
   b. Offer: [m]anual entry or [p]reset test data
   c. If manual: prompt for each field, accept defaults with Enter
   d. If preset: load test values, display them, allow overrides
5. Review phase:
   a. Display complete request payload (URL + headers + body JSON)
   b. Confirm: Send request? [Y/n]
6. Execution phase:
   a. Authenticate (get/refresh OAuth token)
   b. Send GraphQL POST request
   c. Display timing (request duration in ms)
7. Response phase:
   a. Display HTTP status
   b. Display full response body with syntax highlighting
   c. Display field population analysis
   d. For Claim Pre-Check: display parsed X12 segments
8. Save phase:
   a. Prompt: Save as JSON / Markdown / Both / No
   b. Save to results/ folder with timestamped filename
9. Return to main menu
```

---

## 10. Non-Requirements (Explicitly Out of Scope)

- **No Claude/AI integration** — This is a raw API testing tool. No LLM interpretation of responses.
- **No web UI** — Console only.
- **No mock mode** — This tool connects to the live Optum sandbox only. The existing POCs already handle mock mode.
- **No batch processing** — One API call at a time, interactively.
- **No database** — Results are saved as flat files only.

---

## 11. Acceptance Criteria

1. Program launches and validates environment variables on startup
2. User can select any of the 3 APIs from the main menu
3. All input fields are displayed with correct required/optional status and types
4. Preset test data loads correctly for each API
5. OAuth token is obtained and cached correctly
6. GraphQL requests are sent with correct headers (including `providerTaxId` in headers, `environment: sandbox`)
7. Full raw response is displayed with syntax highlighting
8. Field population analysis shows which fields came back populated vs. null
9. User can save output as JSON, Markdown, or both
10. Claim Pre-Check X12 builder produces valid 837P strings matching the output of `x12-builder.ts`
11. GraphQL errors (HTTP 200 with `errors` array) are properly detected and displayed
12. Program handles network errors gracefully without crashing

---

## 12. Implementation Notes

### Porting from TypeScript to Python

The existing POC code is TypeScript/Next.js. When porting:

- Replace `fetch()` with `httpx.AsyncClient().post()`
- Replace TypeScript interfaces with Python `dataclass` or `TypedDict` for type hints
- Replace `URLSearchParams` with `dict` passed to `data=` parameter in httpx
- Replace `crypto.randomUUID()` with `uuid.uuid4()`
- Replace `Date.now()` with `time.time() * 1000` or `int(time.time() * 1000)`
- Replace `JSON.stringify(body, null, 2)` with `json.dumps(body, indent=2)`
- The X12 builder string concatenation logic ports directly — Python string formatting is equivalent

### Key Gotchas (from the quick start guides and POC code)

1. **Auth URL is NOT at sandbox-apigw.optum.com** — it's at `idx.linkhealth.com`. This trips everyone up.
2. **providerTaxId is an HTTP header** — not a GraphQL variable. Every Optum Real API works this way.
3. **GraphQL always returns HTTP 200** — you must check the `errors` array in the response body.
4. **Claim Pre-Check: one claim per request** — status code `702` if you submit multiple.
5. **Claim Pre-Check: TIN must match** — the TIN in the `providerTaxId` header must match the TIN in the X12 content. Status code `701` on mismatch.
6. **Sandbox returns generic data** — the sandbox validates your auth flow and query structure but returns generic responses regardless of input values. Real scenario-specific data comes only from production.

---

## 13. Dependencies

```
# requirements.txt
httpx>=0.27.0
python-dotenv>=1.0.0
rich>=13.7.0
```

No other dependencies required. The program uses Python stdlib for JSON, UUID, datetime, asyncio, and dataclasses.
