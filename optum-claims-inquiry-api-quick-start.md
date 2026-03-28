# Your Billing Team Needs Claim Status in Real Time, Not After Three Phone Calls.

The Optum Claims Inquiry API returns a GraphQL response with claim status codes, adjudication details, payment amounts, denial reasons, appeal deadlines, and service line breakdowns that nobody in your revenue cycle department has time to chase down manually. So I built a dashboard that queries the API for an entire batch of claims at once, hands the raw responses to Claude, and gets back prioritized action plans with estimated collectables and filing deadline warnings.

This is a walkthrough of the API. Clone the repo, add credentials, and you have a working claim status dashboard. Or skip the credentials and explore the full UI on mock data first. No API keys required for that.

The repo is at [github.com/paullopez-ai/claim-status-radar](https://github.com/paullopez-ai/claim-status-radar).

## What You Are Building

A single-page Next.js app that does three things:

1. Authenticates with Optum via OAuth 2.0 (client credentials flow)
2. Sends GraphQL claim inquiry queries in parallel for a batch of claims
3. Passes all results to Claude, which returns per-claim action plans with priorities, filing deadlines, and a macro AR summary

The front end renders a tabbed dashboard: per-claim actions on one tab, macro AR summary on another, with priority badges (URGENT, ACTION_REQUIRED, MONITOR, ON_TRACK) across the top. Eight synthetic claims cover the scenarios your billing team actually encounters: pending review, partially paid, fully denied, timely filing risk, and more.

Think of it as an air traffic control radar for your accounts receivable, except instead of tracking planes, it tracks the claims that keep your practice solvent.

## The Stack

Next.js 16 with App Router, TypeScript in strict mode, Tailwind CSS v4, shadcn/ui components, and Framer Motion for loading animations. Bun handles package management. The entire app is one API route and one page component.

## Getting Started in Three Minutes

```bash
git clone https://github.com/paullopez-ai/claim-status-radar.git
cd claim-status-radar
bun install
cp .env.local.example .env.local
bun dev
```

Open `http://localhost:3000`. That's it. With no API keys configured, the app defaults to mock mode and returns realistic claim status responses with Claude analysis. Every scenario works. Every panel renders. You can explore the entire UI without spending a dollar or registering anywhere.

When you are ready for real API calls, you need two sets of credentials:

**Optum sandbox credentials** from [marketplace.optum.com](https://marketplace.optum.com/apiservices/api-sandbox-access). Register for sandbox access to the Claims Inquiry API. You get a client ID and client secret.

**Anthropic API key** from [console.anthropic.com](https://console.anthropic.com). The app uses `claude-sonnet-4-6` by default.

Drop them in `.env.local`:

```bash
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
OPTUM_GRAPHQL_URL=https://sandbox-apigw.optum.com/oihub/claim/inquiry/v1/graphql
OPTUM_PROVIDER_TAX_ID=448835440
ANTHROPIC_API_KEY=your_anthropic_api_key
NEXT_PUBLIC_APP_ENV=sandbox
```

## How the OAuth Flow Works

The auth URL is *not* at `sandbox-apigw.optum.com`. The working token endpoint lives at a completely different host:

```
https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
```

The developer portal does not make this obvious. The auth module handles token caching with a 60-second safety buffer before expiry. Tokens last one hour. The code requests a new one only when the cached token is about to expire:

```typescript
if (cachedToken && Date.now() < cachedToken.expiresAt - 60000) {
  return cachedToken.token
}
```

The token request is a standard OAuth2 client credentials grant:

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

No token management library needed. Just a module-scoped variable and a timestamp check.

## The GraphQL Query (Where the Magic Happens)

The claim inquiry query in `lib/optum-claim-inquiry.ts` takes two variables and returns the full lifecycle of a claim — from receipt through adjudication to payment or denial.

### Query Variables

```graphql
query ClaimInquiry($claimControlNumber: String!, $tradingPartnerServiceId: String!) {
  claimInquiry(
    claimControlNumber: $claimControlNumber
    tradingPartnerServiceId: $tradingPartnerServiceId
  ) {
    ...
  }
}
```

The input is minimal:

| Variable | Type | Description |
|----------|------|-------------|
| `claimControlNumber` | `String!` | The unique claim identifier (e.g., `CLM-2026-001847`) |
| `tradingPartnerServiceId` | `String!` | Payer identifier (e.g., `UHC001`, `CIGNA001`, `BCBSTX001`) |

### Response Fields

The response is deep. Here is everything the query returns:

**Claim Header:**
| Field | Type | Notes |
|-------|------|-------|
| `controlNumber` | `String` | Echo of the claim control number |
| `tradingPartnerServiceId` | `String` | Echo of the payer ID |
| `payerControlNumber` | `String?` | Payer's internal claim ID |
| `claimReceivedDate` | `String` | Date payer received the claim (YYYY-MM-DD) |
| `patientAccountNumber` | `String?` | Your internal account number |

**Claim Status:**
| Field | Type | Notes |
|-------|------|-------|
| `statusCode` | `String` | X12 276/277 status code (e.g., `A1`, `F1`, `R3`) |
| `statusCodeDescription` | `String` | Human-readable status |
| `statusCategoryCode` | `String` | Category grouping |
| `statusCategoryDescription` | `String` | Category description |
| `effectiveDate` | `String` | Status effective date |
| `checkDate` | `String?` | Payment date — only populated when paid |
| `checkNumber` | `String?` | Check/EFT number — only populated when paid |

**Financial Summary:**
| Field | Type | Notes |
|-------|------|-------|
| `totalBilledAmount` | `String` | What you billed (e.g., `$285.00`) |
| `totalAllowedAmount` | `String?` | Payer's allowed amount |
| `totalPaidAmount` | `String?` | What the payer paid |
| `patientResponsibilityAmount` | `String?` | What the patient owes |

**Service Lines (array):**
| Field | Type | Notes |
|-------|------|-------|
| `lineNumber` | `String` | Service line number |
| `procedureCode` | `String` | CPT/HCPCS code |
| `billedAmount` | `String` | Billed for this line |
| `allowedAmount` | `String?` | Allowed for this line |
| `paidAmount` | `String?` | Paid for this line |
| `adjustmentReasonCode` | `String?` | CARC code for adjustments |
| `adjustmentReasonDescription` | `String?` | Adjustment reason text |
| `remarkCode` | `String?` | RARC remark code |
| `remarkDescription` | `String?` | Remark text |

**Adjudication Info:**
| Field | Type | Notes |
|-------|------|-------|
| `isAdjudicated` | `Boolean` | Whether final decision has been made |
| `adjudicationDate` | `String?` | Date of decision |
| `eraAvailable` | `Boolean` | Whether electronic remittance is available |
| `denialReason` | `String?` | Why the claim was denied |
| `denialCode` | `String?` | Denial code |
| `appealDeadline` | `String?` | Deadline to file an appeal |

**Additional Information Requested:**
| Field | Type | Notes |
|-------|------|-------|
| `isRequested` | `Boolean` | Whether payer needs more info |
| `requestType` | `String?` | What type of info is needed |
| `requestDescription` | `String?` | Detailed description |
| `responseDueDate` | `String?` | Deadline to respond |

**Provider, Subscriber, and Payer objects** are also returned with NPI, name, member ID, date of birth, payer name, and payer ID.

### The HTTP Headers That Matter

```typescript
headers: {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'providerTaxId': '448835440',                               // HTTP header, NOT a query variable
  'x-optum-consumer-correlation-id': `claim-radar-${Date.now()}`,  // Your lifeline for support calls
  'environment': 'sandbox',                                    // Required for sandbox
}
```

Three gotchas that will cost you time:

1. **`providerTaxId` is a header, not a query variable.** Every Optum Real API puts the TIN in the HTTP headers. Miss this and your query silently returns empty data.

2. **`environment: sandbox` is required.** Without it, the sandbox gateway may reject your request or route it incorrectly.

3. **GraphQL returns HTTP 200 even for errors.** You must check the `errors` array in the response body, not just the HTTP status code. A 200 with `"errors": [{ "message": "FieldUndefined" }]` means your query field doesn't exist on this endpoint.

## X12 Status Codes (The Claim Status Rosetta Stone)

The `statusCode` field uses X12 276/277 standard codes. Here are the ones you will see most often:

| Code | Meaning | What Your Team Should Do |
|------|---------|------------------------|
| `A1` | Acknowledged/Received | Nothing yet — claim is in the queue |
| `A2` | Accepted | Claim passed initial validation |
| `A3` | Rejected | Fix and resubmit immediately |
| `F0` | Finalized — Payment | Check the `checkDate` and `totalPaidAmount` |
| `F1` | Finalized — Denial | Check `denialReason` and `appealDeadline` |
| `F3` | Finalized — Revised | Review adjustments, may need appeal |
| `F4` | Finalized — Forwarded | Claim sent to another payer |
| `P0` | Pending — General | Check back in 7-14 days |
| `R0` | Request for Info — General | Respond before `responseDueDate` |
| `R3` | Request for Info — Clinical | Send medical records before deadline |

If you are building revenue cycle automation, these status codes are the API's primary signal. Map them to your workflow engine to trigger automatic follow-ups.

## Parallel Claim Queries

The Claims Inquiry API supports one claim per query. The POC fires all 8 synthetic claims in parallel using `Promise.all()`:

```typescript
const results = await Promise.all(
  claims.map(claim => fetchClaimInquiry(claim.claimControlNumber, claim.tradingPartnerServiceId, token))
)
```

This is significantly faster than sequential queries. For a production batch of 50+ claims, consider chunking into batches of 10-15 with a small delay between batches to avoid rate limiting.

## The Eight Claim Scenarios

The app ships with eight synthetic claims in `lib/claims.ts`. Each triggers a different AR scenario:

- **Pending review** — Claim received, no action taken yet
- **Partially paid** — Some service lines paid, others adjusted
- **Fully denied** — Denial with appeal deadline approaching
- **Timely filing risk** — Approaching the payer's filing limit
- **Additional info requested** — Payer needs documentation before proceeding
- **Payment issued** — Check number and date available
- **Rejected on submission** — Failed initial validation
- **Forwarded to secondary** — Primary payer processed, now with secondary

These are mock-mode constructs. The Optum sandbox validates your auth and query structure but returns generic data. The rich, scenario-specific responses with real CARC codes and appeal deadlines come from production credentials.

## Error Handling

The API route wraps each claim query in its own try/catch. If one claim fails, the others still return. The AI analysis is a separate try/catch — if Claude fails, the raw claim data still comes back with default MONITOR priorities.

```typescript
try {
  const statusResponse = await fetchClaimInquiry(claim.claimControlNumber, claim.tradingPartnerServiceId, token)
  return { claim, statusResponse, error: null }
} catch (err) {
  return { claim, statusResponse: null, error: err.message }
}
```

This is intentional. In revenue cycle workflows, partial data is always better than no data. A claim status without AI analysis is still a claim status.

## Quick Start Checklist

1. Register at [marketplace.optum.com](https://marketplace.optum.com)
2. Subscribe to sandbox access for the Claims Inquiry API
3. Get your `client_id` and `client_secret`
4. Clone the repo and run `bun install`
5. Copy `.env.local.example` to `.env.local` and add your credentials
6. Run `bun dev` and open `http://localhost:3000`
7. Click through the claim scenarios and explore the priority dashboard
8. Read `lib/optum-claim-inquiry.ts` to understand the GraphQL query
9. Read `lib/claude-ar-analyzer.ts` to see how the AI analysis works
10. Add your own claims, customize priorities, or swap the AI model

## The Sandbox Reality Check

The sandbox validates your authentication flow, query structure, and error handling. It proves your code works end to end. But it returns generic data regardless of which claim you query. The scenario-specific responses with real X12 status codes, CARC adjustments, and appeal deadlines only come from a production Optum account with real provider credentials.

Think of the sandbox as the flight simulator. It proves you can fly the plane. But the turbulence is all simulated.

---

*Built by [Paul Lopez](https://paullopez.ai) as a reference implementation for healthcare developers working with the Optum Claims Inquiry API.*
