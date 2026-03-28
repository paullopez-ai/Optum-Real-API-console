# Optum Real API Console

Interactive Python CLI for testing Optum Real APIs against the sandbox environment.

## Setup

```bash
cd Optum-Real-API-console

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Optum sandbox credentials from marketplace.optum.com
```

## Usage

```bash
source .venv/bin/activate
python optum_console.py
```

The menu lets you pick an API, fill in input fields (or load a preset), review the request, and see the full raw response with field population analysis.

## Supported APIs

| # | API | Endpoint |
|---|-----|----------|
| 1 | Pre-Service Eligibility & Benefits | `/oihub/eligibility/v1/pre-service/member` |
| 2 | Prior Authorization Status | `/oihub/prior-auth/v1/graphql` |
| 3 | Claim Pre-Check | `/oihub/pre-service/v1/claim/precheck` |

## Features

- **Preset test data** — Load predefined inputs for each API with one keystroke
- **Request preview** — See the full GraphQL payload before sending
- **Full raw response** — Syntax-highlighted JSON with line numbers
- **Field population analysis** — See which response fields came back populated vs null
- **X12 segment parsing** — Claim Pre-Check responses broken into readable segments
- **X12 837P builder** — Enter structured claim data, the tool builds the X12 string
- **Save output** — Export results as JSON or Markdown to the `results/` folder

## File Structure

```
optum_console.py        # Main entry point
auth.py                 # OAuth 2.0 token management
apis/
  eligibility.py        # Pre-Service Eligibility API
  prior_auth.py         # Prior Auth Status API
  claim_precheck.py     # Claim Pre-Check + X12 builder
models/
  inputs.py             # Field definitions and preset data
output/
  formatter.py          # JSON/X12/Markdown formatting
  saver.py              # File save logic
results/                # Saved outputs go here
```

## Key Notes

- Auth URL is `idx.linkhealth.com`, NOT `sandbox-apigw.optum.com`
- `providerTaxId` goes in HTTP headers, not GraphQL variables
- GraphQL returns HTTP 200 even for errors — check the `errors` array
- Claim Pre-Check: one claim per request, TIN must match between header and X12
