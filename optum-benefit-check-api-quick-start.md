# Your Clinic Needs to Know If a Procedure Requires Prior Auth Before the Patient Leaves the Waiting Room.

The Optum Patient Benefit Check API returns a GraphQL response that tells you whether prior authorization is required, whether one is already on file, what the referral requirements are, and what the plan's benefit language says about a specific service. It packs four distinct operations into a single endpoint. Handing that to a scheduler or care coordinator without translation is like handing them a fax in Klingon.

This is a walkthrough of the API. It covers authentication, the four GraphQL operations, request/response structure, and the gotchas that will cost you hours if you discover them the hard way. Pair this with Claude for plain-English translation and you have a benefit verification workflow that takes seconds instead of phone calls.

## What This API Does

The Patient Benefit Check API at `/oihub/patient/benefit/check/v1` supports four operations through a single GraphQL endpoint:

1. **CheckPriorAuthBenefitCoverage** — The main event. Submit a procedure code and patient info, get back whether prior auth is required, whether one is already on file, and the decision status of any matched authorizations.

2. **ReferralInquiry** — Returns a simple yes/no indicator for whether a referral is required for the requested service.

3. **PlanBenefitCategory** — Search for benefit categories by keyword (e.g., "MRI"). Returns category names, benefit IDs, and summary text. Think of it as the table of contents for the patient's plan.

4. **PlanBenefitLanguage** — Given a specific benefit ID from PlanBenefitCategory, returns the full benefit details: coverage description, network-specific costs, and limits/exceptions. This is the fine print, machine-readable.

These four operations chain together. Check PA requirements first, then look up benefit categories and language if you need cost details for the patient conversation.

## The Stack (If You Build a POC)

Same pattern as the Eligibility starter: Next.js with App Router, TypeScript, Tailwind CSS, shadcn/ui. The API integration is one auth module and one GraphQL query module. Claude annotates the raw response into something a human can act on.

## Getting Credentials

**Optum sandbox credentials** from [marketplace.optum.com](https://marketplace.optum.com). Subscribe to the **Optum Real Patient Benefit Check API** specifically. You get a client ID and client secret.

**Auth endpoint** (same as Eligibility — this trips people up because the portal does not make it obvious):

```
https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
```

**API endpoint**:

```
https://sandbox-apigw.optum.com/oihub/patient/benefit/check/v1
```

**Environment variables** you will need:

```bash
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
OPTUM_BENEFIT_CHECK_URL=https://sandbox-apigw.optum.com/oihub/patient/benefit/check/v1
OPTUM_PROVIDER_TAX_ID=your_provider_tax_id
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## How Authentication Works

Identical to the Eligibility API. OAuth 2.0 client credentials flow against the `idx.linkhealth.com` token endpoint. Tokens last one hour. Cache the token and refresh 60 seconds before expiry.

```typescript
const response = await fetch(OPTUM_AUTH_URL, {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    grant_type: 'client_credentials',
    client_id: OPTUM_CLIENT_ID,
    client_secret: OPTUM_CLIENT_SECRET,
  }),
})
```

The token goes in the `Authorization: Bearer <token>` header on every GraphQL request.

## Operation 1: CheckPriorAuthBenefitCoverage

This is the operation you will use most. "Does this procedure need prior auth? Is one already on file?"

### The GraphQL Query

```graphql
query CheckPriorAuthBenefitCoverage($benChkInput: CheckPriorAuthBenefitCoverageInput!) {
  benefitCheckResponse(input: $benChkInput) {
    caseOutcome {
      casePriorAuth {
        requestMessages { messageText }
        requestOutcomeCode
        requestOutcomeCodeDescription
        requestReferenceNumber
      }
    }
    caseSummary {
      member { groupNumber memberId }
      placeOfServiceCode
      requestingProviderNPI
      requestingProviderTin
    }
    matchedPriorAuths {
      caseDecision
      caseServices {
        procedureCode
        serviceDecision
        serviceMessage
      }
      caseStatus
      serviceReferenceNumber
    }
    serviceOutcomes {
      procedureCode
      procedureCodeDescription
      servicePriorAuth {
        isPriorAuthOnFile
        messages { messageText }
        serviceOutcomeCode
      }
    }
  }
}
```

### The Variables

```json
{
  "benChkInput": {
    "beneficiaryDetail": {
      "beneficiaryId": "M123456789",
      "dateOfBirth": "1985-06-15",
      "firstName": "John",
      "groupNumber": "G123456",
      "lastName": "Doe",
      "serviceEndDate": "2023-01-01",
      "serviceStartDate": "2023-01-01"
    },
    "caseDetailProvider": [
      {
        "address": {
          "city": "Hastings",
          "line1": "1234 CHARDAVE",
          "line2": "",
          "state": "TX",
          "zip": "12133",
          "zip4": "1001"
        },
        "procedureDetails": [
          {
            "codeType": "CPT",
            "diagnosisCode": "J01.90",
            "isPrimary": true,
            "procedureBilledChargeAmount": "100",
            "procedureCode": "99213",
            "procedureFrequency": "1",
            "procedureUnitCount": "1",
            "procedureUnitOfMeasure": "UN",
            "procedureUnitPerFrequencyCount": "1",
            "serviceDetailDescription": "Medical",
            "serviceEndDate": "2025-08-01",
            "serviceStartDate": "2025-08-01"
          }
        ],
        "providerFirstName": "John",
        "providerLastOrOrganizationName": "Doe Clinic",
        "providerNPI": "9876543210",
        "providerRoles": [{ "role": "Requesting" }],
        "providerTaxIdNumber": "123456789",
        "providerType": "Physician"
      }
    ],
    "diagnosisCodes": [
      {
        "diagnosisCode": "J01.90",
        "diagnosisTypeCode": "ABK"
      }
    ],
    "facilityServiceDetail": {
      "facilityServiceEndDate": "2025-08-01",
      "facilityServiceStartDate": "2025-08-01",
      "isPatientAdmitted": false,
      "isPatientDischarged": false
    },
    "payerId": "",
    "serviceLocation": {
      "claimType": "I",
      "placeOfServiceCode": "11",
      "serviceDescription": "Scheduled",
      "serviceDetail": "Medical"
    }
  }
}
```

### The Response (What You Get Back)

```json
{
  "data": {
    "checkPriorAuthBenefitCoverage": {
      "caseSummary": {
        "member": { "memberId": "M123456789", "groupNumber": "G123456" },
        "requestingProviderTin": "123456789",
        "requestingProviderNPI": "9876543210",
        "placeOfServiceCode": "11"
      },
      "caseOutcome": {
        "casePriorAuth": {
          "requestReferenceNumber": "REQ123456789",
          "requestOutcomeCode": "1",
          "requestOutcomeCodeDescription": "Authorization Required",
          "requestMessages": [{ "messageText": "Prior authorization required" }]
        }
      },
      "serviceOutcomes": [
        {
          "procedureCode": "98941",
          "procedureCodeDescription": "Chiropractic adjustment involving 3-4 areas of the spine",
          "servicePriorAuth": {
            "serviceOutcomeCode": "1",
            "isPriorAuthOnFile": false,
            "messages": [{ "messageText": "Prior authorization required for the requested service" }]
          }
        }
      ],
      "matchedPriorAuths": [
        {
          "serviceReferenceNumber": "AUTH123456",
          "caseDecision": "Approved",
          "caseStatus": "Closed",
          "caseServices": [
            {
              "procedureCode": "99213",
              "serviceDecision": "Approved",
              "serviceMessage": "Prior authorization valid through 2025-12-31"
            }
          ]
        }
      ]
    }
  }
}
```

### Decoding the Outcome Codes

The `requestOutcomeCode` and `serviceOutcomeCode` fields are the critical decision points:

| Code | Meaning | What to Do |
|------|---------|------------|
| `1` | PA Required | Submit a prior auth before scheduling the service |
| `2` | PA Not Required | Proceed. No authorization needed |
| `3` | System Unavailable | Retry later or call the payer |
| `4` | Member Blocking | Member-level issue preventing determination. Investigate |
| `5` | Conditionally Not Required | PA may not be required based on certain conditions |

The `isPriorAuthOnFile` boolean in `servicePriorAuth` tells you whether an existing authorization already covers this service. If `true`, check `matchedPriorAuths` for the auth details, decision status, and expiration.

## Operation 2: ReferralInquiry

A lightweight check: does this patient's plan require a referral?

### Query

```graphql
query ReferralInquiry($refInqInput: CheckReferralInquiryInput!) {
  referralInquiry(refInqInput: $refInqInput) {
    referralIndicator
  }
}
```

### Variables

```json
{
  "refInqInput": {
    "beneficiaryDetail": {
      "beneficiaryId": "M123456789",
      "dateOfBirth": "1985-06-15",
      "firstName": "John",
      "lastName": "Doe",
      "groupNumber": "G123456",
      "serviceStartDate": "2023-01-01",
      "serviceEndDate": "2023-01-01"
    },
    "providerDetail": {
      "providerLastOrOrganizationName": "Doe Clinic",
      "providerFirstName": "John",
      "providerNPI": "9876543210"
    },
    "payerId": "87726"
  }
}
```

### Response

```json
{
  "data": {
    "referralInquiry": {
      "referralIndicator": "Y"
    }
  }
}
```

`Y` means a referral is required. Simple as that.

## Operation 3: PlanBenefitCategory

Search the patient's plan for benefit categories by keyword. Useful for answering "what does this plan cover for MRI?" before looking up the specific benefit language.

### Query

```graphql
query CheckPlanBenefitCategory($benCatgInput: CheckPlanBenefitCategoryInput!) {
  checkPlanBenefitCategory(benCatgInput: $benCatgInput) {
    eligibilityTransactionId
    newBenefits
    benefitCategory {
      categoryName
      categoryDetail {
        benefitId
        benefitName
        benefitSummaryText
      }
    }
  }
}
```

### Variables

```json
{
  "benCatgInput": {
    "beneficiaryDetail": {
      "beneficiaryId": "M123456789",
      "dateOfBirth": "1985-06-15",
      "firstName": "John",
      "lastName": "Doe",
      "groupNumber": "G123456",
      "serviceStartDate": "2023-01-01",
      "serviceEndDate": "2023-01-01"
    },
    "searchPhrase": "MRI",
    "payerId": "87726"
  }
}
```

### Response

```json
{
  "data": {
    "checkPlanBenefitCategory": {
      "eligibilityTransactionId": "abcdefg",
      "newBenefits": true,
      "benefitCategory": [
        {
          "categoryName": "MRI services",
          "categoryDetail": [
            {
              "benefitId": "abc2fe-89b57",
              "benefitName": "X-Ray",
              "benefitSummaryText": "UnitedHealthcare X-Ray Program"
            }
          ]
        }
      ]
    }
  }
}
```

Save the `eligibilityTransactionId` and `benefitId` — you need them for the next operation.

## Operation 4: PlanBenefitLanguage

Given a benefit ID from PlanBenefitCategory, returns the full benefit details including costs, network status, and limits.

### Query

```graphql
query CheckPlanBenefitLanguage($benLangInput: CheckPlanBenefitLanguageInput!) {
  checkPlanBenefitLanguage(benLangInput: $benLangInput) {
    newBenefits
    benefits {
      benefitName
      benefitDetails
      benefitInformationSection
      benefitNetworkSection {
        costs
        networkStatus
      }
      limitsAndExceptions {
        description
        details
      }
    }
  }
}
```

### Variables

```json
{
  "benLangInput": {
    "beneficiaryDetail": {
      "beneficiaryId": "M123456789",
      "dateOfBirth": "1985-06-15",
      "firstName": "John",
      "lastName": "Doe",
      "groupNumber": "G123456",
      "serviceStartDate": "2023-01-01",
      "serviceEndDate": "2023-01-01"
    },
    "eligibilityTransactionId": "",
    "benefitId": "ben-a111-b222-c333",
    "payerId": "87726"
  }
}
```

### Response

```json
{
  "data": {
    "checkPlanBenefitLanguage": {
      "newBenefits": true,
      "benefits": {
        "benefitName": "Hearing Aids",
        "benefitDetails": "What are hearing aids: Electronic amplifying devices designed to bring sound more effectively into the ear.",
        "benefitInformationSection": ["text"],
        "benefitNetworkSection": [
          {
            "costs": "UHC Network: co-insurance after you pay the deductible.",
            "networkStatus": ["IN-NETWORK"]
          }
        ],
        "limitsAndExceptions": [
          {
            "description": "General",
            "details": "No coverage for bone anchored hearing aids except Craniofacial anomalies."
          }
        ]
      }
    }
  }
}
```

This is where you find the actual cost language to share with the patient. Network-specific costs, coverage limits, and exclusions — all in structured, parseable fields.

## Required HTTP Headers

Same pattern as the Eligibility API:

```typescript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'providerTaxId': OPTUM_PROVIDER_TAX_ID,           // Required
  'environment': 'sandbox',                           // Required for sandbox
  'x-optum-consumer-correlation-id': crypto.randomUUID(), // Optional but recommended
}
```

The `providerTaxId` goes in headers, not in the GraphQL variables. This is consistent across all Optum Real APIs.

## Request Field Requirements by Service Type

The Benefit Check API has different required fields depending on the type of service:

| Field | Inpatient | Outpatient | Outpatient Facility |
|-------|-----------|------------|---------------------|
| BeneficiaryId | Required | Required | Required |
| DateOfBirth | Required | Required | Required |
| FirstName | Required | Optional | Optional |
| LastName | Required | Optional | Optional |
| GroupNumber | Required | Required | Required |
| PlaceOfServiceCode | Required | Required | Required |
| ClaimType (I/P/D) | Required | Required | Required |
| ProviderNPI | Required | Required | Required |
| DiagnosisCode | Required | Required | Required |
| ProcedureCode | Required | Required | Required |
| ProcedureUnitPerFrequencyCount | Conditional | Required | Optional |
| ProcedureUnitOfMeasure | Conditional | Required | Optional |
| ProcedureFrequency | Conditional | Required | Optional |
| FacilityServiceStartDate | Required | Not Required | Required |
| FacilityServiceEndDate | Required | Not Required | Required |

Outpatient services require the most procedure-level detail. Inpatient requires facility dates. Getting these wrong produces `MISSING_REQUIRED_FIELD` errors that are clear enough to debug.

## Case Types That Return PA Information

Not all plan/case type combinations return prior auth data. The API will return PA information for these case types:

- **Standard Medical** — All Plans
- **Genetic Molecular Testing** — All Plans
- **Inpatient** — All Plans
- **Skilled Nursing** — All Plans
- **Cardiology** — Surest (25463), People's Health Plan (87726)
- **Gastroenterology Endoscopy** — Medicare (87726), Medicaid (state-specific), Exchange/ACA (87726), Surest (25463), People's Health Plan (87726)
- **Physical Health (PT/OT/ST)** — Medicaid (state-specific), Oxford (06111), Exchange/ACA (87726), Surest (25463), People's Health Plan (87726)
- **Oncology** — No plans currently

If you query a case type/plan combination not on this list, you will get a valid response but without PA information.

## Error Handling

The API returns GraphQL errors with descriptive codes:

| Error Type | Examples |
|------------|---------|
| `MISSING_REQUIRED_FIELD` | Missing mandatory header or request field |
| `INVALID_FIELD` | Invalid field value or format |
| `BAD_USER_INPUT` | Schema validation failure (typos in field names, wrong types) |
| `VALIDATION_FAILED` | Business rule failures — invalid date format, member not found, multiple members matched, unsupported payer ID |
| `INTERNAL_SERVER_ERROR` | Optum system unavailable |

Date format must be `yyyy-MM-dd`. Using `MM/dd/yyyy` or `yyyyMMdd` will produce a validation error.

## The Sandbox Reality Check

Same as Eligibility: the sandbox validates your auth flow, query structure, and error handling. It returns generic data regardless of patient. The rich PA determinations and benefit language only come from production. The sandbox is the dress rehearsal with cardboard props.

## Quick Start Checklist

1. Register at [marketplace.optum.com](https://marketplace.optum.com)
2. Subscribe to sandbox access for the **Patient Benefit Check API**
3. Get your `client_id` and `client_secret`
4. Use the auth endpoint at `idx.linkhealth.com` (not `sandbox-apigw.optum.com`)
5. Start with CheckPriorAuthBenefitCoverage — it is the most common operation
6. Use ReferralInquiry for quick referral checks
7. Chain PlanBenefitCategory → PlanBenefitLanguage for detailed cost conversations
8. Pipe any response through Claude for plain-English translation
9. Remember: `providerTaxId` goes in HTTP headers, not GraphQL variables
10. Use `x-optum-consumer-correlation-id` on every request — it is your support lifeline

---

*Quick start guide for healthcare developers working with the Optum Real Patient Benefit Check API. Based on the official Optum data dictionary v4.0 (Feb 2026).*
