# Optum Pre-Service Eligibility API — Schema Validation Error

## API Affected

**Pre-Service Eligibility & Benefits**
Endpoint: `POST /oihub/eligibility/v1/pre-service/member` (GraphQL)

## Problem

The `LimitationInfo` type in the GraphQL schema no longer includes a singular `message` field. Requesting it in a query returns a `400 Bad Request` with multiple `FieldUndefined` validation errors:

```
Validation error (FieldUndefined@[checkEligibility/eligibility/serviceLevels/family/services/message/coPay/limitationInfo/message]):
Field 'message' in type 'LimitationInfo' is undefined
```

This error repeats for every `limitationInfo` block in the query — 10 total across `family` and `individual` service levels, covering `coPay`, `coInsurance`, `deductible`, `benefitsAllowed`, and `benefitsRemaining`.

## Root Cause

The Optum developer documentation and downloadable GraphQL reference query include a singular `message` field inside `limitationInfo`:

```graphql
limitationInfo {
  lmtPeriod
  lmtType
  lmtOccurPerPeriod
  lmtDollarPerPeriod
  message        # ← This field is undefined in the schema
  messages
}
```

The schema only recognizes the plural `messages` field. The singular `message` was either removed from the schema or was never valid, but it still appears in the reference materials.

## Fix

Remove every instance of the singular `message` field from `limitationInfo` blocks in the query. The plural `messages` field remains valid and returns data as expected:

```graphql
limitationInfo {
  lmtPeriod
  lmtType
  lmtOccurPerPeriod
  lmtDollarPerPeriod
  messages
}
```

## Affected Locations in the Reference Query

The singular `message` field appears in 10 `limitationInfo` blocks across the `checkEligibility` query:

| Service Level | Benefit Category | Query Path |
|---------------|-----------------|------------|
| Family | coPay | `serviceLevels/family/services/message/coPay/limitationInfo/message` |
| Family | coInsurance | `serviceLevels/family/services/message/coInsurance/limitationInfo/message` |
| Family | deductible | `serviceLevels/family/services/message/deductible/limitationInfo/message` |
| Family | benefitsAllowed | `serviceLevels/family/services/message/benefitsAllowed/limitationInfo/message` |
| Family | benefitsRemaining | `serviceLevels/family/services/message/benefitsRemaining/limitationInfo/message` |
| Individual | coPay | `serviceLevels/individual/services/message/coPay/limitationInfo/message` |
| Individual | coInsurance | `serviceLevels/individual/services/message/coInsurance/limitationInfo/message` |
| Individual | deductible | `serviceLevels/individual/services/message/deductible/limitationInfo/message` |
| Individual | benefitsAllowed | `serviceLevels/individual/services/message/benefitsAllowed/limitationInfo/message` |
| Individual | benefitsRemaining | `serviceLevels/individual/services/message/benefitsRemaining/limitationInfo/message` |

## Recommendation

Update the downloadable reference query and API documentation on the Optum Developer Portal to remove the singular `message` field from all `LimitationInfo` blocks, or re-add the field to the schema if its removal was unintentional.
