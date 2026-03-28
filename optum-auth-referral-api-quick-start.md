# Your Staff Needs Prior Auth Status in Seconds, Not After a Fax Machine Staring Contest.

The Optum Auth & Referral Submission API returns a GraphQL response with authorization status, denial reasons, appeal deadlines, CMS compliance windows, peer-to-peer review availability, and scheduled procedure details that nobody in your auth department has time to chase across three different payer portals. So I built a dashboard that queries the API for an entire batch of prior authorizations at once, hands the raw responses to Claude, and gets back prioritized actions with outcome predictions and CMS compliance alerts.

This is a walkthrough of the API. Clone the repo, add credentials, and you have a working prior auth dashboard. Or skip the credentials and explore the full UI on mock data first. No API keys required for that.

The repo is at [github.com/paullopez-ai/prior-auth-radar](https://github.com/paullopez-ai/prior-auth-radar).

## What You Are Building

A single-page Next.js app that does three things:

1. Authenticates with Optum via OAuth 2.0 (client credentials flow)
2. Sends GraphQL prior authorization status queries in parallel for a batch of PAs
3. Passes all results to Claude, which returns per-PA action plans, outcome predictions, and a macro summary with CMS compliance alerts

The front end renders a tabbed dashboard: per-PA actions on one tab, outcome predictions on another, macro summary on a third, with priority badges (CRITICAL, URGENT, ACTION_REQUIRED, MONITOR, APPROVED) across the top. Ten synthetic prior authorizations cover the scenarios your auth team actually encounters: approved, pending clinical review, denied with appeal window, CMS compliance violation, urgent surgery, and more.

Think of it as mission control for your prior auth portfolio. Except instead of launching rockets, you are preventing denied surgeries and regulatory violations.

## The Stack

Next.js 16 with App Router, TypeScript in strict mode, Tailwind CSS v4, shadcn/ui components, and Framer Motion for loading animations. Bun handles package management. The entire app is one API route and one page component.

## Getting Started in Three Minutes

```bash
git clone https://github.com/paullopez-ai/prior-auth-radar.git
cd prior-auth-radar
bun install
cp .env.local.example .env.local
bun dev
```

Open `http://localhost:3000`. That's it. With no API keys configured, the app defaults to mock mode and returns realistic PA status responses with Claude analysis. Every scenario works. Every panel renders. You can explore the entire UI without spending a dollar or registering anywhere.

When you are ready for real API calls, you need two sets of credentials:

**Optum sandbox credentials** from [marketplace.optum.com](https://marketplace.optum.com/apiservices/api-sandbox-access). Register for sandbox access to the Auth & Referral Submission API. You get a client ID and client secret.

**Anthropic API key** from [console.anthropic.com](https://console.anthropic.com). The app uses `claude-sonnet-4-6` by default.

Drop them in `.env.local`:

```bash
OPTUM_CLIENT_ID=your_sandbox_client_id
OPTUM_CLIENT_SECRET=your_sandbox_client_secret
OPTUM_AUTH_URL=https://idx.linkhealth.com/auth/realms/developer-platform/protocol/openid-connect/token
OPTUM_GRAPHQL_URL=https://sandbox-apigw.optum.com/oihub/prior-auth/v1/graphql
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

The PA status query in `lib/optum-pa-status.ts` takes two variables and returns the full picture of a prior authorization — from submission through payer decision, including CMS compliance tracking and denial details.

### Query Variables

```graphql
query PAStatus($authorizationNumber: String!, $tradingPartnerServiceId: String!) {
  priorAuthorizationStatus(
    authorizationNumber: $authorizationNumber
    tradingPartnerServiceId: $tradingPartnerServiceId
  ) {
    ...
  }
}
```

The input is minimal:

| Variable | Type | Description |
|----------|------|-------------|
| `authorizationNumber` | `String!` | The PA authorization number (e.g., `AUTH-2026-0210-4471`) |
| `tradingPartnerServiceId` | `String!` | Payer identifier (e.g., `UHC-87726`, `AETNA-60054`) |

### Response Fields

The response is comprehensive. Here is everything the query returns:

**PA Header:**
| Field | Type | Notes |
|-------|------|-------|
| `authorizationNumber` | `String` | Echo of the auth number |
| `tradingPartnerServiceId` | `String` | Echo of the payer ID |
| `submittedDate` | `String` | When the PA was submitted (YYYY-MM-DD) |
| `scheduledProcedureDate` | `String?` | When the procedure is scheduled — null for non-scheduled |
| `urgencyType` | `String?` | `STANDARD` or `URGENT` |

**Authorization Status:**
| Field | Type | Notes |
|-------|------|-------|
| `statusCode` | `String` | Status code (e.g., `A1`, `P1`, `P2`, `D1`) |
| `statusDescription` | `String` | Human-readable status |
| `statusCategory` | `String` | `APPROVED`, `PENDING`, or `DENIED` |
| `effectiveDate` | `String?` | When the authorization becomes active |
| `expirationDate` | `String?` | When the authorization expires |

**Requested Procedure:**
| Field | Type | Notes |
|-------|------|-------|
| `procedureCode` | `String` | CPT code (e.g., `27447` for knee replacement) |
| `procedureDescription` | `String?` | Human-readable procedure name |
| `serviceTypeCode` | `String?` | Service type classification |
| `quantity` | `Number?` | Number of units requested |
| `unitType` | `String?` | Unit type (e.g., `UN`) |

**Denial Info:**
| Field | Type | Notes |
|-------|------|-------|
| `isDenied` | `Boolean` | Whether the PA has been denied |
| `denialReason` | `String?` | Why the PA was denied |
| `denialCode` | `String?` | Denial code (e.g., `CR-044`, `CR-112`) |
| `appealDeadline` | `String?` | Last date to file an appeal |
| `peerToPeerAvailable` | `Boolean?` | Whether a peer-to-peer review can be requested |

**Additional Info Required:**
| Field | Type | Notes |
|-------|------|-------|
| `isRequired` | `Boolean` | Whether payer needs more documentation |
| `infoType` | `String?` | Category (e.g., `CLINICAL_DOCUMENTATION`) |
| `description` | `String?` | Specific documentation requirements |
| `dueDate` | `String?` | Deadline to submit documentation |

**CMS Compliance Status:**
| Field | Type | Notes |
|-------|------|-------|
| `standardResponseWindowDays` | `Number?` | Regulatory window (7 days standard, 72 hours urgent per CMS-0057-F) |
| `submittedDate` | `String?` | When the PA was submitted |
| `responseDeadline` | `String?` | When the payer must respond |
| `isResponseOverdue` | `Boolean?` | Whether the payer has violated the CMS response window |
| `daysOverdue` | `Number?` | How many days past the deadline |

**Provider, Member, and Payer objects** are also returned with NPI, names, member ID, date of birth, group number, payer name, and payer ID.

### The HTTP Headers That Matter

```typescript
headers: {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'providerTaxId': '448835440',                                  // HTTP header, NOT a query variable
  'x-optum-consumer-correlation-id': `prior-auth-radar-${Date.now()}`,  // Your lifeline for support calls
  'environment': 'sandbox',                                       // Required for sandbox
}
```

Three gotchas that will cost you time:

1. **`providerTaxId` is a header, not a query variable.** Every Optum Real API puts the TIN in the HTTP headers. Miss this and your query silently returns empty data.

2. **`environment: sandbox` is required.** Without it, the sandbox gateway may reject your request or route it incorrectly.

3. **GraphQL returns HTTP 200 even for errors.** You must check the `errors` array in the response body, not just the HTTP status code. A 200 with errors means your query is malformed or the auth number doesn't exist on this endpoint.

## PA Status Categories

The `statusCategory` field is the primary signal for workflow automation:

| Category | Status Codes | What Your Team Should Do |
|----------|-------------|------------------------|
| `APPROVED` | `A1` | Verify effective/expiration dates, schedule procedure |
| `PENDING` | `P1`, `P2` | Check for additional info requests, monitor CMS response window |
| `DENIED` | `D1` | Check appeal deadline, consider peer-to-peer if available |

## CMS Compliance: The Rules That Make This API Critical

The CMS Prior Authorization Final Rule (CMS-0057-F) sets mandatory response windows for payers:

- **Standard requests**: Payer must respond within **7 calendar days**
- **Urgent requests**: Payer must respond within **72 hours**

The `cmsComplianceStatus` object in the response tracks this automatically. When `isResponseOverdue` is `true`, you have documentation for a CMS complaint. The `daysOverdue` field tells you exactly how far past the deadline the payer is.

This is the kind of data that turns a "we're still waiting" phone call into a "you are in violation of federal regulation and here's the proof" letter. Which tends to get authorizations approved faster.

## Parallel PA Queries

The Auth & Referral API supports one PA per query. The POC fires all 10 synthetic PAs in parallel using `Promise.all()`:

```typescript
const results = await Promise.all(
  PA_ITEMS.map(pa => fetchPAStatus(pa.authorizationNumber, pa.tradingPartnerServiceId, token))
)
```

Individual failures don't block other requests. If one PA query fails, the rest still return. For production batches of 50+ PAs, consider chunking into batches of 10-15 with a small delay between batches.

## The Ten PA Scenarios

The app ships with ten synthetic PAs in `lib/pa-items.ts`. Each triggers a different authorization scenario:

- **Approved — standard** — Authorization active with valid effective/expiration dates
- **Pending clinical review** — Waiting for medical director decision
- **Pending additional documentation** — Payer needs operative notes or clinical records
- **Denied — medical necessity** — Appeal window open, peer-to-peer available
- **Denied — site of service** — Wrong facility type, peer-to-peer recommended
- **CMS compliance violation** — Payer response overdue, CMS complaint eligible
- **Urgent — surgery tomorrow** — Critical priority, CMS violation, needs immediate action
- **Approved but expiring** — Authorization valid but approaching expiration date
- **Forwarded to secondary** — Primary payer authorized, secondary review pending
- **Rejected on submission** — Missing information, needs resubmission

These are mock-mode constructs. The Optum sandbox validates your auth and query structure but returns generic data. The rich, scenario-specific responses with real denial codes and CMS compliance tracking come from production credentials.

## Error Handling

The API route wraps each PA query in its own try/catch. If one PA fails, the others still return. The AI analysis is a separate try/catch — if Claude fails, the raw PA data still comes back with default MONITOR priorities.

```typescript
try {
  const statusResponse = await fetchPAStatus(pa.authorizationNumber, pa.tradingPartnerServiceId, token)
  return { pa, statusResponse, error: null }
} catch (err) {
  return { pa, statusResponse: null, error: err.message }
}
```

Partial data is always better than no data. A PA status without AI analysis is still a PA status your team can act on.

## Quick Start Checklist

1. Register at [marketplace.optum.com](https://marketplace.optum.com)
2. Subscribe to sandbox access for the Auth & Referral Submission API
3. Get your `client_id` and `client_secret`
4. Clone the repo and run `bun install`
5. Copy `.env.local.example` to `.env.local` and add your credentials
6. Run `bun dev` and open `http://localhost:3000`
7. Click through the PA scenarios and explore the priority dashboard
8. Read `lib/optum-pa-status.ts` to understand the GraphQL query
9. Read `lib/claude-pa-analyzer.ts` to see how the AI analysis works
10. Add your own PAs, customize priorities, or swap the AI model

## The Sandbox Reality Check

The sandbox validates your authentication flow, query structure, and error handling. It proves your code works end to end. But it returns generic data regardless of which authorization you query. The scenario-specific responses with real denial codes, CMS compliance windows, and peer-to-peer availability only come from a production Optum account with real provider credentials.

Think of the sandbox as the fire drill. Everyone practices the evacuation, but nobody is actually on fire. The real smoke comes later.

---

*Built by [Paul Lopez](https://paullopez.ai) as a reference implementation for healthcare developers working with the Optum Auth & Referral Submission API.*
