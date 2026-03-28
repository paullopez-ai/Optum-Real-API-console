# A Claim Got Denied. Now What? This API Lets You Submit, Dispute, and Attach Documents Without Leaving Your System.

The Optum Claim Actions API is the post-adjudication workhorse. It handles three things your billing team does every day: submitting claims (with built-in pre-check validation), creating rework tickets (reconsiderations, appeals, pends), and uploading supporting attachments. All through a single GraphQL endpoint.

If Claim Pre-Check is the spell checker before you hit send, Claim Actions is the entire mailroom — submission, dispute resolution, and document delivery in one API.

This is a walkthrough of the API: authentication, the three GraphQL mutations, request/response structure, and the workflow that connects them. It is based on the official OpenAPI spec (v1.0.0).

## What This API Does

The Claim Actions API at `/oihub/claim/actions/v1` supports three mutations:

1. **SubmitClaimWithPreCheck** — Submit an 837 X12 claim that automatically runs pre-check validation before submission. You get back a 999 acknowledgment and 277CA with validation outcomes, *plus* the claim is actually submitted to the payer.

2. **SubmitClaimTicket** — Create or update a rework ticket: reconsideration (RECON), appeal (APPEAL), or pend (PEND). This is how you dispute a denial, request reconsideration of an underpayment, or flag a claim for review — all programmatically.

3. **SubmitClaimAttachment** — Upload supporting documents (medical records, consent forms, EOBs) for a claim or rework ticket. Uses multipart form upload with a pre-signed AWS URL for bulk documents.

The critical distinction from Claim Pre-Check: that API *validates* but does not submit. This API *validates and submits*. It also adds the entire dispute and attachment workflow that Pre-Check does not touch.

## Getting Credentials

**Optum sandbox credentials** from [marketplace.optum.com](https://marketplace.optum.com). Subscribe to the **Optum Real Claim Actions API**.

**Auth endpoint** (same across all Optum Real APIs):

```
https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
```

**API endpoint**:

```
https://sandbox-apigw.optum.com/oihub/claim/actions/v1
```

**Environment variables**:

```bash
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
OPTUM_CLAIM_ACTIONS_URL=https://sandbox-apigw.optum.com/oihub/claim/actions/v1
OPTUM_PROVIDER_TAX_ID=your_provider_tax_id
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Authentication

Same OAuth 2.0 client credentials flow as every other Optum Real API. One-hour token, cache with 60-second refresh buffer.

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

## Required HTTP Headers

```typescript
const headers = {
  'Content-Type': 'application/json',       // or 'multipart/form-data' for attachments
  'Authorization': `Bearer ${token}`,
  'providerTaxId': OPTUM_PROVIDER_TAX_ID,   // Required
  'environment': 'sandbox',                  // Optional, for sandbox testing
  'x-optum-consumer-correlation-id': crypto.randomUUID(), // Optional but recommended
}
```

Same pattern as all Optum Real APIs. `providerTaxId` in headers, not in the GraphQL variables.

## Mutation 1: SubmitClaimWithPreCheck

Submit a claim *and* validate it in one call. The claim goes through pre-check validation and then on to the payer.

### The GraphQL Mutation

```graphql
mutation SubmitClaimWithPreCheck($input: ClaimSubmissionInput!) {
  claimSubmission(input: $input) {
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
    "x12RequestData": "<your 837 X12 claim string>",
    "payerId": "87726"
  }
}
```

Two fields: the X12 claim data and the payer ID. The `payerId` is required here (unlike Claim Pre-Check where it is part of the X12 payload).

### Example X12 Input

Here is a real 837P (Professional claim) structure from the spec:

```
ISA*00*          *00*          *ZZ*BRT219996150   *ZZ*87726          *250625*0826*^*00501*888251331*1*P*:~
GS*HC*BRT219996150*87726*20250625*0826*525620842*X*005010X222A1~
ST*837*101770887*005010X222A1~
BHT*0019*00*25062588055*20250625*0826*CH~
NM1*41*2*RTS*****46*223832302~
PER*IC*LORAINE GOETSCH*TE*7328735133~
NM1*40*2*UNITED HEALTHCARE 1500*****46*87726~
HL*1**20*1~
NM1*85*2*MERCY GILBERT MEDICAL CENTER*****XX*1992735088~
N3*3555 S VAL VISTA DR~
N4*EDWARDSVILLE*IL*620253776~
REF*EI*352263845~
...
CLM*9283712345*330***11:B:1*Y*A*Y*Y~
DTP*435*D8*20250624~
HI*ABK:B351*ABF:D649*ABF:R600~
...
SV1*HC:99214*165*UN*1***1:2:3~
DTP*472*D8*20250624~
SE*33*101770887~
GE*1*525620842~
IEA*1*888251331~
```

### The Response

```json
{
  "data": {
    "claimSubmission": {
      "transactionId": "8841512345678901",
      "x12ResponseData": "ISA*00*...(999 acknowledgment)...~IEA*1*000000000~",
      "responseType": "837999",
      "x12Response277CA": "ISA*00*...(277CA claim acknowledgment)...~IEA*1*000000000~",
      "message": "Claim submitted successfully. Refer 277CA for validation outcomes.",
      "statusCode": "000"
    }
  }
}
```

### Response Fields

| Field | What It Contains |
|-------|-----------------|
| `transactionId` | Payer-assigned unique ID for this claim submission |
| `x12ResponseData` | X12 999 functional acknowledgment |
| `responseType` | `837999` for success, `ERR837` for internal failure |
| `x12Response277CA` | X12 277CA claim acknowledgment with detailed validation outcomes |
| `message` | Human-readable status |
| `statusCode` | `000` = success. See error codes below |

### Reading the 277CA Response

The 277CA contains STC segments with validation results. Key patterns from the spec's example:

```
STC*A3:21*20250911*U*170********Prior auth validation could not be completed due to service failure
STC*A1:19*20250911*WQ*170********[BTH-V106 LOB Filters applied, ace was not called-Bypassing claim edits]
```

- `A1:19` = Accepted
- `A3:21` = Accepted with errors — review the trailing message
- `REF*D9*P3QAVH0FGU03H4` = Payer claim reference number (save this for follow-up)

This is ideal Claude territory. Feed the 277CA to Claude and ask for a plain-English summary of what passed, what flagged, and what needs attention.

## Mutation 2: SubmitClaimTicket

This is the dispute resolution engine. Create or update rework tickets for claims that need reconsideration, appeal, or pend review.

### The GraphQL Mutation

```graphql
mutation submitClaimTicket($claimTicketInput: ClaimTicketInput!) {
  submitClaimTicket(claimTicketInput: $claimTicketInput) {
    ticketNumber
    ticketStatus
    preSignedUrl
  }
}
```

### The Variables

```json
{
  "claimTicketInput": {
    "lineDetails": [
      {
        "lineKey": "lrlspg8hgksv971756148162162",
        "lineAmountOwed": "450.00"
      }
    ],
    "claimActionIdentifier": "fd00e249-fb5f-4601-a392-1ee032df61d0-1756148161470",
    "ticketType": "RECON",
    "ticketAction": "Create",
    "ticketNumber": "PIQ-12345678",
    "providerComments": "Reconsideration request",
    "hasAttachment": true,
    "isAttachmentUploaded": true,
    "operator": {
      "operatorEmailId": "john.doe@gmail.com",
      "operatorFirstName": "John",
      "operatorLastName": "Doe",
      "operatorPhoneNumber": "512-888-9999",
      "operatorCity": "Minneapolis",
      "operatorState": "MN",
      "operatorStreet": "1555 lex ave",
      "operatorZip": "12345"
    },
    "claimAmountOwed": "1000.00",
    "requestReconsiderationReason": "INCORRECT_PAYMENT",
    "placeOfServiceState": "MN",
    "isAppealOnBehalfOfMember": false,
    "isExternalReviewAppeal": false,
    "payerId": "00123"
  }
}
```

### The Response

```json
{
  "data": {
    "submitClaimTicket": {
      "ticketNumber": "PIQ-12345678",
      "ticketStatus": "Under Review",
      "preSignedUrl": "https://AWS-pre-signed-url"
    }
  }
}
```

### Key Fields Explained

| Field | Description | Required |
|-------|-------------|----------|
| `lineDetails` | Array of service lines being disputed, with `lineKey` (from Claim Inquiry API) and `lineAmountOwed` | Yes |
| `claimActionIdentifier` | Unique key from the Claim Inquiry API response. Links this ticket to the original claim | Yes (for new tickets) |
| `ticketType` | `RECON` (reconsideration), `APPEAL`, or `PEND` | Yes |
| `ticketAction` | `Create` or `Resubmit/Update` | Yes |
| `ticketNumber` | Payer-assigned ticket number. Required when updating an existing ticket | For updates |
| `providerComments` | Free-text explanation of why the rework is needed | No |
| `hasAttachment` / `isAttachmentUploaded` | Boolean flags indicating attachment intent and status | No |
| `operator` | Contact details of the person submitting the request | No |
| `claimAmountOwed` | Expected reimbursement amount | No |
| `requestReconsiderationReason` | Reason code for RECON tickets (values come from Claim Inquiry response) | For RECON |
| `placeOfServiceState` | Required for appeal submissions | For APPEAL |
| `isAppealOnBehalfOfMember` | Is this appeal filed on behalf of the patient? | For APPEAL |
| `isExternalReviewAppeal` | Is this an external review appeal? | For APPEAL |
| `payerId` | Payer ID | Yes |

### The Connection to Claim Inquiry

This mutation requires data from the **Claim Inquiry API** (which you already have a POC for in `claim-status-radar`):

- `claimActionIdentifier` — comes from the Claim Inquiry response
- `lineKey` values — come from the service line details in Claim Inquiry
- `requestReconsiderationReason` options — come from the Claim Inquiry response

The workflow is: query claim status via Claim Inquiry → identify a denied/underpaid claim → use the identifiers from that response to create a rework ticket via Claim Actions.

### The preSignedUrl Response

When `hasAttachment: true`, the response includes a `preSignedUrl` — an AWS pre-signed URL where you can upload bulk documents (as a zip file) related to the rework ticket. This URL is temporary and expires, so upload promptly after receiving it.

## Mutation 3: SubmitClaimAttachment

Upload supporting documents for a claim or rework ticket. This uses **multipart form data**, not JSON.

### The GraphQL Mutation

```graphql
mutation submitClaimAttachment($attachmentInput: AttachmentInput!, $file: Upload!) {
  submitClaimAttachment(attachmentInput: $attachmentInput, file: $file) {
    attachmentId
  }
}
```

### The Multipart Request Structure

This mutation uses the GraphQL multipart request spec. The request has three form fields:

| Field | Type | Description |
|-------|------|-------------|
| `operations` | JSON string | The GraphQL mutation and variables |
| `map` | JSON string | Maps file fields to the variables |
| `0` | Binary file | The actual attachment file |

```typescript
const formData = new FormData()

formData.append('operations', JSON.stringify({
  query: `mutation submitClaimAttachment($attachmentInput: AttachmentInput!, $file: Upload!) {
    submitClaimAttachment(attachmentInput: $attachmentInput, file: $file) {
      attachmentId
    }
  }`,
  variables: {
    attachmentInput: {
      documentTypeCode: 'M1',                    // M1 = Medical Records, CK = Consent Form
      documentName: 'attachment-control-number',
      claimReceiptLocatorNumber: '9162500112345', // FLN from Claim Inquiry
      claimNumber: 'FE12345678',                 // ICN from Claim Inquiry (for unsolicited)
      editCode: 'EDIT123',
      expiryDate: '2025-12-31',
      claimActionIdentifier: 'fd00e249-fb5f-4601-a392-1ee032df61d0-1756148161470',
      ticketNumber: 'PIQ-12345678',              // Required when updating existing ticket
      payerId: '00123',
    },
    file: null,  // Placeholder — mapped via the 'map' field
  },
}))

formData.append('map', JSON.stringify({ '0': ['variables.file'] }))
formData.append('0', fileBuffer, 'medical-records.pdf')
```

### The Response

```json
{
  "data": {
    "submitClaimAttachment": {
      "attachmentId": "1234-1111-46a9-111-11117Cu_prov_attch_2021-11"
    }
  }
}
```

### Attachment Input Fields

| Field | Required | Description |
|-------|----------|-------------|
| `payerId` | Yes | Payer ID |
| `documentTypeCode` | Yes | EDI 837 PWK01 report type code. `M1` = Medical Records, `CK` = Consent Form, etc. |
| `documentName` | No | Document name or attachment control number |
| `claimReceiptLocatorNumber` | No | Claim FLN from Claim Inquiry |
| `claimNumber` | No | Claim ICN from Claim Inquiry. Required for unsolicited attachments |
| `editCode` | No | Edit code applied to the claim |
| `expiryDate` | No | Attachment expiry date |
| `claimActionIdentifier` | No | Required when creating a new ticket alongside the attachment |
| `ticketNumber` | No | Required when attaching to an existing ticket |

## The Complete Workflow

Here is how these three mutations work together in a real billing workflow:

### Scenario: Submit a new claim

```
1. Build 837 X12 claim
2. Call SubmitClaimWithPreCheck
3. Parse 277CA for validation outcomes
4. If clean → claim is submitted, you're done
5. If errors → fix the X12, resubmit
```

### Scenario: Dispute a denied claim

```
1. Query claim status via Claim Inquiry API (your claim-status-radar POC)
2. Identify denied claim → get claimActionIdentifier and lineKeys
3. Call SubmitClaimTicket with ticketType: "RECON" and reason from Claim Inquiry
4. If supporting docs needed → Call SubmitClaimAttachment with the ticketNumber
5. Track ticket status via the ticketNumber
```

### Scenario: Appeal a denial

```
1. Query claim via Claim Inquiry API
2. Call SubmitClaimTicket with ticketType: "APPEAL"
   - Include placeOfServiceState (required for appeals)
   - Set isAppealOnBehalfOfMember and isExternalReviewAppeal flags
3. Upload appeal letter and supporting docs via SubmitClaimAttachment
4. Use preSignedUrl for bulk document upload if needed
```

## Error Handling

### GraphQL Errors

```json
{
  "errors": [{
    "extensions": { "classification": "ValidationError" },
    "locations": [{ "line": 1, "column": 87 }],
    "message": "Validation error (FieldUndefined@[claimSubmission/transactionId]) : Field 'transactionId' in type 'ClaimSubmissionResponse' is undefined"
  }]
}
```

GraphQL validation errors include the exact field location and a descriptive message. These are schema-level issues — typos in field names, wrong types, missing required fields.

### HTTP Errors

| Code | Meaning |
|------|---------|
| `400` | Bad request — schema validation errors |
| `401` | Unauthorized — authentication failed |
| `500` | Internal server error |

### Submission Status Codes

The `statusCode` in the claim submission response follows the same pattern as Claim Pre-Check. `000` means success. Non-zero codes indicate validation issues, member not found, system unavailable, or payer-specific errors. Refer to the Claim Pre-Check quick start guide for the full status code table — they share the same code set.

## Where Claude Adds Value

Three high-value Claude integration points:

1. **277CA Translation** — Same as Claim Pre-Check. Parse the X12 277CA response into plain English. "Claim accepted but prior auth validation failed. Two SmartEdit warnings: unsupported place of service code and NDC unit reporting issue."

2. **Ticket Drafting** — Given a denied claim from Claim Inquiry, have Claude draft the `providerComments` for a reconsideration request. Feed it the denial reason, service details, and any relevant medical context.

3. **Attachment Triage** — Given a denial reason code, have Claude recommend which document types to attach. "Denial for medical necessity on CPT 99214 — attach the clinical notes (M1) and the prior authorization letter."

## The Sandbox Reality Check

Same as all Optum Real APIs. The sandbox validates your auth, mutation structure, and error handling. Claim submissions will return sample responses. Ticket creation and attachment uploads will go through the flow but against test data. Real payer interactions only happen in production.

## Quick Start Checklist

1. Register at [marketplace.optum.com](https://marketplace.optum.com)
2. Subscribe to sandbox access for the **Claim Actions API**
3. Get your `client_id` and `client_secret`
4. Auth endpoint is `idx.linkhealth.com` — same as all Optum Real APIs
5. Start with SubmitClaimWithPreCheck — it is the most common operation
6. You need data from the **Claim Inquiry API** to use SubmitClaimTicket (lineKeys, claimActionIdentifier, reason codes)
7. Attachments use multipart form data, not JSON — adjust your Content-Type header
8. The `preSignedUrl` in ticket responses is temporary — upload promptly
9. `providerTaxId` goes in HTTP headers, must match the X12 content
10. Use `x-optum-consumer-correlation-id` on every request — your support lifeline

---

*Quick start guide for healthcare developers working with the Optum Real Claim Actions API. Based on the official OpenAPI spec v1.0.0.*
