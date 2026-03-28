# Your Billing Team Spends Hours Hunting for Claim Documents. This API Finds Them in Seconds.

The Optum Document Search API lets you search for and download provider documents — prior auth notifications, claim attachments, 835 files, appeal letters, payment records, and more — through a single GraphQL endpoint. Instead of logging into a portal and clicking through a document library, your system can query by date range, category, claim number, or check ID and get back a list of matching documents with metadata. Then download any document as a base64-encoded file.

This is a walkthrough of the API: authentication, the two GraphQL operations, request/response structure, and the things that will bite you if nobody warns you first.

## What This API Does

The Document Search API at `/oihub/document/search/v1` (endpoint pattern based on the Optum Real suite) supports two operations:

1. **DocumentMetadata** — Search for documents by date range, category, claim number, check ID, notification ID, or patient account number. Returns a paginated list of matching documents with full metadata (document ID, file name, category, dates, physician name, patient info).

2. **GetDocument** — Given a document ID from the metadata search, downloads the actual document as a base64-encoded string. PDFs, images, whatever the source system stored.

Search first, then download. Two calls and you have the document.

## Getting Credentials

**Optum sandbox credentials** from [marketplace.optum.com](https://marketplace.optum.com). Subscribe to the **Optum Real Document Search API** specifically.

**Auth endpoint** (same across all Optum Real APIs):

```
https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
```

**Environment variables**:

```bash
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
OPTUM_DOC_SEARCH_URL=https://sandbox-apigw.optum.com/oihub/document/search/v1
OPTUM_PROVIDER_TAX_ID=your_provider_tax_id
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Authentication

Identical to every other Optum Real API. OAuth 2.0 client credentials, one-hour token, cache and refresh 60 seconds before expiry.

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

## Operation 1: DocumentMetadata

Search for documents by date range and optional filters. This is where you start every document retrieval workflow.

### The GraphQL Query

```graphql
query DocumentMetadata($documentMetadataInput: DocumentMetadataInput!) {
  documentMetadata(documentMetadataInput: $documentMetadataInput) {
    documentList {
      documentInfo {
        tin
        claimNumber
        memberId
        category
        documentId
        fileName
        createdDate
        expiryDate
        physicianName
        policyNbr
        serviceDate
        patientName
        checkId
        notificationId
        contentType
        filePath
        patientAccountNumber
      }
    }
    pagination {
      hasMoreRecords
      nextPageToken
    }
  }
}
```

### The Variables

```json
{
  "documentMetadataInput": {
    "fromDate": "09/17/2021",
    "toDate": "09/17/2021",
    "categories": "Claim",
    "patientAccountNumber": "1234567890",
    "claimNumber": "1234567890",
    "filePath": "File Path",
    "checkId": "12345678",
    "notificationId": "12345678",
    "payerId": "87726"
  }
}
```

### The Response

```json
{
  "data": {
    "documentMetadata": {
      "documentList": [
        {
          "documentInfo": {
            "tin": "12345678",
            "claimNumber": "",
            "memberId": "12345678",
            "category": "Prior Auth Notification",
            "documentId": "11111111-1111-1111-1111-111111111111",
            "fileName": "111111.PDF",
            "createdDate": "09/13/2021",
            "expiryDate": "09/13/2023",
            "physicianName": "RAM ROY",
            "policyNbr": "51017",
            "serviceDate": "09/20/2021",
            "patientName": "Test Name",
            "checkId": "",
            "notificationId": "1111111",
            "contentType": "application/pdf",
            "filePath": "Commercial Appeals and Disputes/Acknowledgement, Notification, and Response",
            "patientAccountNumber": " patientAccountNumber"
          }
        }
      ],
      "pagination": {
        "hasMoreRecords": true,
        "nextPageToken": "trwmem123451416167"
      }
    }
  }
}
```

### Gotchas That Will Cost You Time

**Date format is `MM/dd/yyyy`, not `yyyy-MM-dd`.** This is the opposite of the Benefit Check and Eligibility APIs. Yes, it is inconsistent across Optum Real APIs. Yes, it will cause you a validation error if you assume consistency.

**The date range must be 31 days or less.** `fromDate` and `toDate` refer to when the document was *received and stored in the document library*, not the service date. If you need a broader range, paginate across multiple 31-day windows.

**`categories` is optional but strongly recommended.** Without it, you get everything in the date range, which can be a lot. The supported categories narrow results significantly.

**Pagination**: check `hasMoreRecords` in the response. If `true`, use the `nextPageToken` value (pass it as `getpage` in the next request) to retrieve the next page.

### Supported Document Categories and Their Primary IDs

Each category has a primary search field that narrows results most effectively:

| Category | Primary Search Field |
|----------|---------------------|
| 835 Files | `checkId` |
| Appeals and Disputes | `claimNumber` |
| Claim | `claimNumber` |
| Episodes of Care | Date range only |
| Gap in Process | Date range only |
| Overpayment Documents | Date range only |
| NY PCMH | Date range only |
| Provider Payment Document | `checkId` |
| Payment from Members | `checkId` |
| PCR | Date range only |
| Prior Auth Notification | `notificationId` |
| Providers | Date range only |
| House Call | Date range only |
| Management Documents | Date range only |

For payment-related documents, use `checkId`. For claim-related documents, use `claimNumber`. For prior auth notifications, use `notificationId`. For everything else, filter by category and date range.

## Operation 2: GetDocument

Once you have a `documentId` from the metadata search, download the actual file.

### The GraphQL Query

```graphql
query GetDocument($documentInput: DocumentInput!) {
  getDocument(documentInput: $documentInput) {
    base64Document
  }
}
```

### The Variables

```json
{
  "documentInput": {
    "documentId": "5e63205d-9517-4043-9231-ea1a47fb6c07~repoid~fdsid~cloudspaceid",
    "payerId": "87726"
  }
}
```

### The Response

```json
{
  "data": {
    "getDocument": {
      "base64Document": "<base64-encoded file content>"
    }
  }
}
```

The `base64Document` field contains the full file. Decode it and write to disk using the `contentType` and `fileName` from the metadata response:

```typescript
const buffer = Buffer.from(response.data.getDocument.base64Document, 'base64')
// contentType from metadata tells you the MIME type (e.g., "application/pdf")
// fileName from metadata gives you the original filename (e.g., "111111.PDF")
```

### Gotchas for GetDocument

**The document ID format is composite.** It is not a simple UUID. It includes repository and storage identifiers separated by tildes (`~`). Use the exact `documentId` string from the metadata response. Do not try to construct one.

**Large documents may hit size limits.** The API can return `Request Entity Too Large` for very large files. If you encounter this, the document may need to be retrieved through an alternative channel.

**Access control is per-TIN.** You can only retrieve documents associated with your provider TIN. Attempting to access another provider's documents returns `Access Denied: Resource Forbidden Exception`.

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

Same header pattern as all Optum Real APIs. `providerTaxId` in headers, not GraphQL variables.

## Request Fields Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `payerId` | String | Required | Payer ID from member search |
| `fromDate` | String | Required | `MM/dd/yyyy` format — when doc was stored |
| `toDate` | String | Required | `MM/dd/yyyy` format — max 31 days from fromDate |
| `getpage` | String | Required | Page number for pagination |
| `TIN` | String | Required | Tax identification number |
| `categories` | String | Optional | Document category filter (strongly recommended) |
| `patientAccountNumber` | String | Optional | Patient account number |
| `claimNumber` | String | Optional | Claim number |
| `checkId` | String | Optional | Check/validation ID |
| `notificationId` | String | Optional | Notification number |
| `filePath` | String | Optional | Document source path |
| `SourceCreatedDtFromDt` | String | Optional | Source system creation date range start |
| `SourceCreatedDtToDt` | String | Optional | Source system creation date range end |

The two date types serve different purposes: `fromDate`/`toDate` filter by when the document was stored in the library, while `SourceCreatedDtFromDt`/`SourceCreatedDtToDt` filter by when the source system originally generated the document.

## Error Handling

| Error Type | Common Causes |
|------------|---------------|
| `MISSING_REQUIRED_FIELD` | Missing mandatory header or request field |
| `INVALID_FIELD` | Invalid document ID, non-integer nextPageToken |
| `VALIDATION_FAILED` | Date range > 31 days, invalid date format, no documents found, unauthorized access |
| `INTERNAL_SERVER_ERROR` | Optum system unavailable |

"No documents found" is a `VALIDATION_FAILED`, not an empty success response. Plan for it.

## A Practical Workflow

Here is how a billing team would use this in practice:

1. **Daily 835 check**: Query DocumentMetadata with `categories: "835 Files"` and yesterday's date range. Download each 835 file for remittance processing.

2. **Claim follow-up**: When a claim is stuck, query with `categories: "Claim"` and the claim number. Download attachments to see what was submitted and what the payer received.

3. **Prior auth tracking**: Query with `categories: "Prior Auth Notification"` to pull PA decision letters. Parse or pipe through Claude to extract approval/denial status and effective dates.

4. **Appeals documentation**: Query with `categories: "Appeals and Disputes"` and the claim number to retrieve the full appeal correspondence history.

Each of these is two API calls: search, then download. Automate the search on a schedule and you eliminate the daily portal login entirely.

## The Sandbox Reality Check

Same story as the other Optum Real APIs. The sandbox validates your auth, query structure, and error handling. The document content and metadata will be generic. Real documents — actual PDFs, actual 835 files, actual PA letters — only come from production with real provider credentials.

## Quick Start Checklist

1. Register at [marketplace.optum.com](https://marketplace.optum.com)
2. Subscribe to sandbox access for the **Document Search API**
3. Get your `client_id` and `client_secret`
4. Auth endpoint is `idx.linkhealth.com` — same as all Optum Real APIs
5. Start with DocumentMetadata using a date range and category filter
6. Use the `documentId` from results to call GetDocument
7. Decode the base64 response using the `contentType` from metadata
8. Remember: dates are `MM/dd/yyyy` here, not `yyyy-MM-dd`
9. Date range max is 31 days — paginate for broader searches
10. `providerTaxId` goes in HTTP headers, not GraphQL variables

---

*Quick start guide for healthcare developers working with the Optum Real Document Search API. Based on the official Optum data dictionary v1.0 (Feb 2026).*
