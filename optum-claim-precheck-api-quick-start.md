# Stop Submitting Claims That Will Get Rejected. Pre-Check Them First.

The Optum Claim Pre-Check API validates a claim *before* you submit it. Feed it an 837 X12 claim string and it runs HIPAA validation, membership/eligibility checks, coordination of benefits, prior auth requirements, and payment/medical policy adherence — all in one call. You get back a 999 acknowledgment and a 277CA claim acknowledgment that tells you exactly what needs to be fixed.

This is architecturally different from the other Optum Real APIs. The Eligibility, Benefit Check, and Document Search APIs use clean GraphQL inputs with named fields. This one takes raw X12 EDI data as input and returns X12 EDI data in the response. The GraphQL wrapper is thin — it is essentially a transport layer for X12 payloads.

This guide covers authentication, the query structure, how to read the response, and why this API is worth the extra complexity.

## What This API Does

Through a single GraphQL call, the Claim Pre-Check API validates a claim against five checks:

1. **X12 Claim Validation (HIPAA)** — Is the 837 structurally valid? Are required segments present? Are code values legitimate?
2. **Membership & Eligibility** — Is the patient covered on the date of service?
3. **Coordination of Benefits (COB)** — Is this the right payer? What is the primacy order?
4. **Prior Authorization** — Does this procedure require PA? Is one on file?
5. **Payment & Medical Policy** — Does the claim comply with payer-specific edit rules?

The idea is simple: find out what would cause a rejection *before* you submit, so you can fix it first. Every rejected claim costs your billing team time and your practice money. This API is the spell checker before you hit send.

## Getting Credentials

**Optum sandbox credentials** from [marketplace.optum.com](https://marketplace.optum.com). Subscribe to the **Optum Real Claim Pre-Check API**.

**Auth endpoint** (same across all Optum Real APIs):

```
https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
```

**API endpoint** (inferred from health check URL in portal):

```
https://sandbox-apigw.optum.com/oihub/claim/precheck/v1
```

**Environment variables**:

```bash
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
OPTUM_CLAIM_PRECHECK_URL=https://sandbox-apigw.optum.com/oihub/claim/precheck/v1
OPTUM_PROVIDER_TAX_ID=your_provider_tax_id
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Authentication

Same OAuth 2.0 client credentials flow as every other Optum Real API. One-hour token, cache with 60-second refresh buffer.

## The GraphQL Query

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

### The Variables

```json
{
  "input": {
    "x12RequestData": "<your 837 X12 claim string>"
  }
}
```

That is it. One field: `x12RequestData`. The entire claim goes in as a single X12 EDI string.

### The Response

```json
{
  "data": {
    "claimPreCheck": {
      "transactionId": "A111111111",
      "x12ResponseData": "",
      "responseType": "837999",
      "x12Response277CA": "",
      "message": "Precheck validations completed. Refer 277CA for validation outcomes",
      "statusCode": "000"
    }
  }
}
```

### Response Fields Explained

| Field | What It Contains |
|-------|-----------------|
| `transactionId` | Unique tracking ID for this pre-check. Use it when contacting Optum support. |
| `responseType` | `837999` for success, `ERR837` for internal failures. |
| `x12ResponseData` | The X12 999 functional acknowledgment. Contains segment-level validation results. |
| `x12Response277CA` | The 277CA claim acknowledgment. Contains the detailed validation outcomes — this is where the real information lives. |
| `message` | Human-readable status. "Precheck validations completed. Refer 277CA for validation outcomes." |
| `statusCode` | Numeric code. `000` means validations completed. See error codes below. |

## Understanding the X12 Response

The `x12Response277CA` field contains X12 EDI segments. The key segments to parse:

**STC (Status Information) segments** contain the validation results:
```
STC*A3:21:20251009*...
```
- `A3` = Action code (e.g., Acknowledgment)
- `21` = Status category (e.g., "Claim accepted with errors")
- `20251009` = Date

**INFO patterns** describe specific issues found:
```
[Pattern 36335] NDC 6999123456 should be reported with number of tablets or pills and not the number of units.
[Pattern 55208] Unsupported place of service code.
```

These are **SmartEdits** — payer-specific validation rules. They are not necessarily fatal errors. Many are warnings that indicate the claim *can* be submitted but may face delays or denials.

### What the Validation Outcomes Mean

- **Claim accepted**: No errors found. Safe to submit.
- **Claim accepted with errors**: Validation completed but issues were found. Review the STC segments and INFO patterns. Some are warnings (fix recommended), others are blocking (fix required).
- **Internal failure** (`responseType: ERR837`): The pre-check system itself failed. Retry or contact Optum.

## The X12 Input Challenge

Here is the honest truth: building the X12 837 claim string is the hard part. The Optum API is straightforward — one query, one input, one response. But constructing a valid 837 Professional (837P) or Institutional (837I) claim in X12 EDI format requires knowledge of the X12 specification.

An 837P claim includes segments for:
- ISA/GS (interchange and functional group headers)
- ST/BHT (transaction set header)
- Loop 2000A (billing provider)
- Loop 2000B (subscriber)
- Loop 2300 (claim information)
- Loop 2400 (service lines)
- SE/GE/IEA (trailers)

**Practical approaches for building the X12 input:**

1. **Export from your PM/EHR system.** Most practice management and EHR systems can export claims in 837 format. Feed that directly into this API before submitting to the clearinghouse.

2. **Use an X12 library.** Libraries like `x12-parser` (Node.js) or `pyx12` (Python) can construct and parse X12 segments programmatically.

3. **Use Claude to translate.** Feed Claude the claim data as structured JSON and ask it to produce a valid 837P/837I string. This is surprisingly effective for prototyping, though you would want to validate the output against a reference implementation for production.

4. **Start with your clearinghouse's test claims.** If you already submit claims through a clearinghouse, you likely have sample 837 files. Use those as templates.

### Critical Constraint

**Only one claim per request.** The API explicitly rejects requests with multiple claims (status code `702`: "Multiple Claims are not allowed through Claim Pre-check process"). One claim in, one validation out.

### TIN Matching

The TIN in your `providerTaxId` header **must match** the TIN in the X12 request data. A mismatch produces status code `701`. This is a common gotcha when testing with sample X12 files from a different provider.

## Required HTTP Headers

```typescript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'providerTaxId': OPTUM_PROVIDER_TAX_ID,
  'environment': 'sandbox',
  'x-optum-consumer-correlation-id': crypto.randomUUID(),
}
```

Same header pattern as all Optum Real APIs. `providerTaxId` in headers, must match the X12 content.

## Status Codes

| Code | Meaning |
|------|---------|
| `000` | Pre-check validations completed. Check the 277CA for details. |
| `101-133, 506-509, 605-608, 611, 902` | Invalid or missing data in request. Details in 277CA. |
| `109, 301-305, 404-405, 408, 413, 504, 510` | Member not found. |
| `701` | TIN in header does not match TIN in X12 request. |
| `702` | Multiple claims submitted. Only one per request allowed. |
| `706` | Invalid X12 request (malformed EDI). |
| `107, 114, 117, 505` | Platform/plan not supported. |
| `501, 511` | Multiple member matches found. Refine the search criteria. |
| `512` | Transaction ID not identified for COB from eligibility call. |
| `520` | Claims pre-check not supported for this member's plan. |
| `521` | Payer ID mismatch between request and member's plan. |
| `202, 303, 306, 401-403, 406-407, 503, 606, 612-619, 907, 927` | System unavailable. Retry later. |
| `926` | X12 transformation failed. |

HTTP-level errors: `400` (bad request/schema validation), `401` (auth failed), `500` (internal server error).

## Where Claude Adds Value

The raw X12 277CA response is dense EDI that even experienced billers need time to parse. This is a perfect Claude use case:

1. Send the `x12Response277CA` string to Claude
2. Ask it to extract: which validations passed, which failed, what the specific issues are, and what needs to be fixed
3. Present the plain-English summary to the billing team

Example Claude prompt approach:
```
Parse this X12 277CA claim acknowledgment and extract:
- Overall claim status (accepted, accepted with errors, rejected)
- Each STC segment with the action code, status category, and date
- Each INFO pattern with the pattern number and description
- A prioritized list of issues to fix before submitting
- Whether any issues are blocking vs. advisory
```

The X12 parsing is where Claude earns its keep. Instead of training your billing staff to read EDI segments, let Claude be the translator.

## Case Types That Return PA Information

Same list as the Benefit Check API — PA information is returned based on case type and plan combination:

- **Standard Medical, Genetic Molecular Testing, Inpatient, Skilled Nursing** — All Plans
- **Cardiology** — Surest (25463), People's Health Plan (87726)
- **Gastroenterology, Physical Health, Radiation Oncology, Radiology, Specialty Pharmacy** — Select plans (see data dictionary for full list)
- **Oncology** — No plans currently

## A Practical Workflow

1. **Before claim submission**: Export the 837 from your PM system, run it through Claim Pre-Check, review the 277CA for issues, fix them, then submit the clean claim.

2. **Batch validation**: For end-of-day claim batches, split into individual claims (one per request), pre-check each one, flag the ones with errors for review, and auto-submit the clean ones.

3. **Training tool**: New billers can submit test claims and see exactly what would fail and why, without risking real rejections.

4. **Denial prevention dashboard**: Track pre-check failure patterns over time to identify systemic coding or documentation issues in your practice.

## The Sandbox Reality Check

The sandbox validates your auth flow, X12 formatting, and error handling. It will tell you if your 837 structure is valid and return sample STC/INFO patterns. But the specific SmartEdits and payer-specific rules that catch real-world issues only fire in production against real payer systems.

## Quick Start Checklist

1. Register at [marketplace.optum.com](https://marketplace.optum.com)
2. Subscribe to sandbox access for the **Claim Pre-Check API**
3. Get your `client_id` and `client_secret`
4. Auth endpoint is `idx.linkhealth.com` — same as all Optum Real APIs
5. Obtain or construct a valid 837P or 837I X12 claim string
6. Ensure the TIN in the X12 matches your `providerTaxId` header
7. Submit one claim per request — multi-claim requests are rejected
8. Parse the `x12Response277CA` for validation results (or let Claude do it)
9. Fix flagged issues and re-validate before submitting to the clearinghouse
10. Use `transactionId` and `x-optum-consumer-correlation-id` for support cases

---

*Quick start guide for healthcare developers working with the Optum Real Claim Pre-Check API. Based on the official Optum data dictionary v2.0 (Feb 2026).*
